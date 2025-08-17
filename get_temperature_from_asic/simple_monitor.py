#!/usr/bin/env python3
"""
Упрощенный монитор температуры на основе рабочего простого теста
Решение проблемы с зашифрованными запросами
"""

import time
import signal
import threading
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

from .whatsminer_interface.whatsminer_transport import WhatsminerTCP
from .whatsminer_interface.whatsminer_interface import WhatsminerAPIv3


@dataclass
class TemperatureData:
    """Структура данных температуры"""
    liquid_temperature: Optional[float] = None
    psu_temperature: Optional[float] = None
    fan_speed: Optional[float] = None
    timestamp: Optional[datetime] = None
    status: str = "unknown"
    error_message: Optional[str] = None


class TemperatureMonitor:
    """Монитор температуры для работы с Whatsminer без зашифрованных запросов"""
    
    def __init__(self, ip_address: str, account: str = "super", password: str = "super", 
                 update_interval: float = 1.0):
        self.ip_address = ip_address
        self.account = account
        self.password = password
        self.update_interval = update_interval
        
        # Состояние
        self.is_running = False
        self.monitor_thread = None
        self.current_data = TemperatureData()
        self.data_lock = threading.Lock()
        
        # Колбэки
        self.data_callbacks = []
        self.error_callbacks = []
        
        # Статистика
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.last_error = None
        
    def add_data_callback(self, callback: Callable[[TemperatureData], None]):
        """Добавление колбэка для данных"""
        self.data_callbacks.append(callback)
        
    def add_error_callback(self, callback: Callable[[str], None]):
        """Добавление колбэка для ошибок"""
        self.error_callbacks.append(callback)
    
    def _resolve_current_ip(self) -> str:
        """Возвращает актуальный IP из data_manager, либо fallback на self.ip_address."""
        try:
            # Локальный импорт, чтобы избежать циклических зависимостей
            from data_manager.core_system import get_asic_ip
            ip = get_asic_ip()
            if isinstance(ip, str) and ip:
                return ip
        except Exception:
            pass
        return self.ip_address

    def get_temperature_reading(self) -> Optional[TemperatureData]:
        """Получение одного измерения температуры (как в простом тесте)"""
        current_ip = self._resolve_current_ip()
        api = WhatsminerAPIv3(self.account, self.password)
        tcp = WhatsminerTCP(current_ip, 4433, self.account, self.password)
        
        try:
            self.total_requests += 1
            
            # Подключение
            if not tcp.connect():
                self.failed_requests += 1
                self.last_error = "Не удалось подключиться"
                return TemperatureData(
                    timestamp=datetime.now(),
                    status="error",
                    error_message=self.last_error
                )
            
            # Аутентификация и получение данных
            req = api.get_request_cmds("get.device.info")
            resp = tcp.send(req, len(req), api)
            
            if resp and resp.get('code') == 0:
                self.successful_requests += 1
                
                # Установка salt
                salt = resp['msg'].get('salt')
                if salt:
                    api.set_salt(salt)
                
                # Извлечение данных температуры
                power_data = resp['msg'].get('power', {})
                liquid_temp = power_data.get('liquid-temperature')
                psu_temp = power_data.get('temp0')
                fan_speed = power_data.get('fanspeed')
                
                data = TemperatureData(
                    liquid_temperature=liquid_temp,
                    psu_temperature=psu_temp,
                    fan_speed=fan_speed,
                    timestamp=datetime.now(),
                    status=self._determine_status(liquid_temp),
                    error_message=None
                )
                
                tcp.close()
                return data
            else:
                self.failed_requests += 1
                self.last_error = f"Ошибка API: {resp.get('code', 'unknown') if resp else 'no response'}"
                tcp.close()
                return TemperatureData(
                    timestamp=datetime.now(),
                    status="error",
                    error_message=self.last_error
                )
                
        except Exception as e:
            self.failed_requests += 1
            self.last_error = f"Ошибка: {e}"
            tcp.close()
            return TemperatureData(
                timestamp=datetime.now(),
                status="error",
                error_message=self.last_error
            )
    
    def start_monitoring(self) -> bool:
        """Запуск мониторинга"""
        if self.is_running:
            return True
            
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        return True
    
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitoring_loop(self):
        """Основной цикл мониторинга"""
        while self.is_running:
            try:
                # Получение данных
                data = self.get_temperature_reading()
                
                if data:
                    # Обновление текущих данных
                    with self.data_lock:
                        self.current_data = data
                    
                    # Уведомление колбэков
                    self._notify_data_callbacks(data)
                    
                    # Проверка на ошибки
                    if data.status == "error" and data.error_message:
                        self._notify_error(data.error_message)
                
                # Ожидание следующего цикла
                time.sleep(self.update_interval)
                
            except Exception as e:
                self._notify_error(f"Ошибка в цикле мониторинга: {e}")
                time.sleep(self.update_interval)
    
    def get_current_temperature(self) -> Optional[float]:
        """Получение текущей температуры"""
        with self.data_lock:
            return self.current_data.liquid_temperature
    
    def get_current_data(self) -> TemperatureData:
        """Получение текущих данных"""
        with self.data_lock:
            return TemperatureData(
                liquid_temperature=self.current_data.liquid_temperature,
                psu_temperature=self.current_data.psu_temperature,
                fan_speed=self.current_data.fan_speed,
                timestamp=self.current_data.timestamp,
                status=self.current_data.status,
                error_message=self.current_data.error_message
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики"""
        success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(success_rate, 2),
            "last_error": self.last_error,
            "is_running": self.is_running
        }
    
    def _determine_status(self, liquid_temp: Optional[float]) -> str:
        """Определение статуса температуры"""
        if liquid_temp is None:
            return "unknown"
        
        if liquid_temp < 55:
            return "normal"
        elif liquid_temp < 60:
            return "warning"
        else:
            return "critical"
    
    def _notify_data_callbacks(self, data: TemperatureData):
        """Уведомление колбэков о данных"""
        for callback in self.data_callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"❌ Ошибка в колбэке данных: {e}")
    
    def _notify_error(self, error_message: str):
        """Уведомление колбэков об ошибке"""
        for callback in self.error_callbacks:
            try:
                callback(error_message)
            except Exception as e:
                print(f"❌ Ошибка в колбэке ошибок: {e}")


# Простой API для интеграции с контроллером
class TemperatureController:
    """Простой контроллер температуры для интеграции"""
    
    def __init__(self, ip_address: str = "192.168.0.127", update_interval: float = 1.0):
        self.monitor = TemperatureMonitor(ip_address, update_interval=update_interval)
        self.monitor.start_monitoring()
    
    def get_temperature(self) -> Optional[float]:
        """Получение текущей температуры для контроллера клапанов"""
        return self.monitor.get_current_temperature()
    
    def get_status(self) -> str:
        """Получение статуса температуры"""
        data = self.monitor.get_current_data()
        return data.status
    
    def is_healthy(self) -> bool:
        """Проверка работоспособности"""
        stats = self.monitor.get_statistics()
        return stats['success_rate'] > 50 if stats['total_requests'] > 0 else True
    
    def stop(self):
        """Остановка мониторинга"""
        self.monitor.stop_monitoring()


if __name__ == "__main__":
    # Тест монитора температуры
    def on_data(data: TemperatureData):
        timestamp = data.timestamp.strftime("%H:%M:%S") if data.timestamp else "N/A"
        if data.liquid_temperature is not None:
            print(f"{timestamp} | 🌡️ {data.liquid_temperature}°C | Статус: {data.status}")
        else:
            print(f"{timestamp} | ❌ {data.error_message}")
    
    def on_error(error: str):
        print(f"❌ ОШИБКА: {error}")
    
    monitor = TemperatureMonitor("192.168.0.127", update_interval=2.0)
    monitor.add_data_callback(on_data)
    monitor.add_error_callback(on_error)
    
    print("🌡️ Запуск мониторинга температуры...")
    monitor.start_monitoring()
    
    try:
        time.sleep(30)  # 30 секунд тестирования
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop_monitoring()
        stats = monitor.get_statistics()
        print(f"\n📊 Статистика: {stats}") 