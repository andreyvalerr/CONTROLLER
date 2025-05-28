#!/usr/bin/env python3
"""
Простой API для получения температуры жидкости
Для интеграции с контроллером клапанов криптокотла
"""

import time
import threading
from typing import Optional
from simple_monitor import SimpleTemperatureMonitor, TemperatureData

# Глобальный экземпляр монитора
_global_monitor = None
_monitor_lock = threading.Lock()


def start_temperature_monitoring(ip_address: str = "192.168.0.91", 
                                update_interval: float = 1.0) -> bool:
    """
    Запуск глобального мониторинга температуры
    
    Args:
        ip_address: IP адрес майнера
        update_interval: Интервал обновления в секундах
        
    Returns:
        bool: True если запуск успешен
    """
    global _global_monitor
    
    with _monitor_lock:
        if _global_monitor is not None:
            return True  # Уже запущен
        
        _global_monitor = SimpleTemperatureMonitor(ip_address, update_interval=update_interval)
        return _global_monitor.start_monitoring()


def stop_temperature_monitoring():
    """Остановка глобального мониторинга"""
    global _global_monitor
    
    with _monitor_lock:
        if _global_monitor is not None:
            _global_monitor.stop_monitoring()
            _global_monitor = None


def get_current_temperature() -> Optional[float]:
    """
    Получение текущей температуры жидкости
    
    Returns:
        float: Температура в градусах Цельсия или None при ошибке
    """
    global _global_monitor
    
    with _monitor_lock:
        if _global_monitor is None:
            # Автоматический запуск мониторинга
            if not start_temperature_monitoring():
                return None
        
        return _global_monitor.get_current_temperature()


def get_temperature_status() -> str:
    """
    Получение статуса температуры
    
    Returns:
        str: Статус (normal/warning/critical/unknown/error)
    """
    global _global_monitor
    
    with _monitor_lock:
        if _global_monitor is None:
            if not start_temperature_monitoring():
                return "error"
        
        data = _global_monitor.get_current_data()
        return data.status


def get_all_temperature_data() -> Optional[dict]:
    """
    Получение всех данных температуры
    
    Returns:
        dict: Словарь с данными температуры
    """
    global _global_monitor
    
    with _monitor_lock:
        if _global_monitor is None:
            if not start_temperature_monitoring():
                return None
        
        data = _global_monitor.get_current_data()
        
        return {
            "liquid_temperature": data.liquid_temperature,
            "psu_temperature": data.psu_temperature,
            "fan_speed": data.fan_speed,
            "timestamp": data.timestamp.isoformat() if data.timestamp else None,
            "status": data.status,
            "error_message": data.error_message
        }


def is_temperature_monitoring_active() -> bool:
    """
    Проверка активности мониторинга
    
    Returns:
        bool: True если мониторинг активен
    """
    global _global_monitor
    
    with _monitor_lock:
        return _global_monitor is not None and _global_monitor.is_running


def get_monitoring_statistics() -> dict:
    """
    Получение статистики мониторинга
    
    Returns:
        dict: Статистика работы
    """
    global _global_monitor
    
    with _monitor_lock:
        if _global_monitor is None:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "success_rate": 0.0,
                "last_error": None,
                "is_running": False
            }
        
        return _global_monitor.get_statistics()


class TemperatureAPI:
    """
    Класс API для работы с температурой
    Удобен для использования в контроллере клапанов
    """
    
    def __init__(self, ip_address: str = "192.168.0.91", update_interval: float = 1.0):
        self.ip_address = ip_address
        self.update_interval = update_interval
        self.monitor = None
        
    def start(self) -> bool:
        """Запуск мониторинга"""
        if self.monitor is None:
            self.monitor = SimpleTemperatureMonitor(
                self.ip_address, 
                update_interval=self.update_interval
            )
        
        return self.monitor.start_monitoring()
    
    def stop(self):
        """Остановка мониторинга"""
        if self.monitor is not None:
            self.monitor.stop_monitoring()
    
    def get_temperature(self) -> Optional[float]:
        """Получение температуры"""
        if self.monitor is None:
            return None
        return self.monitor.get_current_temperature()
    
    def get_status(self) -> str:
        """Получение статуса"""
        if self.monitor is None:
            return "error"
        data = self.monitor.get_current_data()
        return data.status
    
    def is_healthy(self) -> bool:
        """Проверка работоспособности"""
        if self.monitor is None:
            return False
        stats = self.monitor.get_statistics()
        return stats['success_rate'] > 50 if stats['total_requests'] > 0 else True
    
    def get_all_data(self) -> Optional[dict]:
        """Получение всех данных"""
        if self.monitor is None:
            return None
        
        data = self.monitor.get_current_data()
        return {
            "liquid_temperature": data.liquid_temperature,
            "psu_temperature": data.psu_temperature,
            "fan_speed": data.fan_speed,
            "timestamp": data.timestamp.isoformat() if data.timestamp else None,
            "status": data.status,
            "error_message": data.error_message
        }
    
    def __enter__(self):
        """Контекстный менеджер - вход"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        self.stop()


# Пример использования для контроллера клапанов
class ValveController:
    """
    Пример контроллера клапанов с обратной связью по температуре
    """
    
    def __init__(self, target_temperature: float = 50.0, ip_address: str = "192.168.0.91"):
        self.target_temperature = target_temperature
        self.temp_api = TemperatureAPI(ip_address, update_interval=1.0)
        self.temp_api.start()
        
        # ПИД-регулятор (упрощенный)
        self.kp = 0.1  # Пропорциональный коэффициент
        self.ki = 0.01  # Интегральный коэффициент
        self.kd = 0.05  # Дифференциальный коэффициент
        
        self.previous_error = 0.0
        self.integral = 0.0
        
    def calculate_valve_position(self) -> Optional[float]:
        """
        Расчет положения клапана на основе температуры
        
        Returns:
            float: Положение клапана от -1.0 до 1.0 или None при ошибке
        """
        current_temp = self.temp_api.get_temperature()
        
        if current_temp is None:
            return None  # Ошибка получения температуры
        
        # Расчет ошибки
        error = self.target_temperature - current_temp
        
        # ПИД-регулятор
        self.integral += error
        derivative = error - self.previous_error
        
        output = (self.kp * error + 
                 self.ki * self.integral + 
                 self.kd * derivative)
        
        self.previous_error = error
        
        # Ограничение выхода
        return max(-1.0, min(1.0, output))
    
    def get_temperature_info(self) -> dict:
        """Получение информации о температуре"""
        return {
            "current_temperature": self.temp_api.get_temperature(),
            "target_temperature": self.target_temperature,
            "status": self.temp_api.get_status(),
            "is_healthy": self.temp_api.is_healthy()
        }
    
    def stop(self):
        """Остановка контроллера"""
        self.temp_api.stop()


if __name__ == "__main__":
    # Тест API
    print("🌡️ Тест простого API температуры")
    
    # Запуск мониторинга
    if start_temperature_monitoring():
        print("✅ Мониторинг запущен")
        
        # Ожидание первых данных
        time.sleep(3)
        
        # Получение данных
        temp = get_current_temperature()
        status = get_temperature_status()
        all_data = get_all_temperature_data()
        stats = get_monitoring_statistics()
        
        print(f"🌡️ Температура: {temp}°C")
        print(f"📊 Статус: {status}")
        print(f"📈 Статистика: {stats}")
        print(f"📋 Все данные: {all_data}")
        
        # Остановка
        stop_temperature_monitoring()
        print("✅ Мониторинг остановлен")
    else:
        print("❌ Не удалось запустить мониторинг") 