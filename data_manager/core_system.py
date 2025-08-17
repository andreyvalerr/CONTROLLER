#!/usr/bin/env python3
"""
Основная система ядра контроллера криптокотла
Координация модулей и управление потоком данных
"""

import threading
import time
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Добавляем путь к модулю температуры
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from .data_manager import DataManager, DataType, DataEntry
from .settings_manager import SettingsManager, get_settings_manager

# Импорт модуля температуры
try:
    from get_temperature_from_asic import (
        start_temperature_monitoring,
        stop_temperature_monitoring,
        get_current_temperature,
        get_all_temperature_data,
        is_temperature_monitoring_active
    )
    TEMPERATURE_MODULE_AVAILABLE = True
except ImportError as e:
    print(f"Предупреждение: Модуль температуры недоступен: {e}")
    TEMPERATURE_MODULE_AVAILABLE = False


@dataclass
class SystemData:
    """Структура системных данных"""
    temperature: Optional[float] = None
    temperature_status: Optional[str] = None
    system_status: str = "unknown"
    uptime_seconds: float = 0.0
    last_update: Optional[datetime] = None
    errors: Optional[list] = None


class CoreSystem:
    """Основная система ядра"""
    
    def __init__(self, temperature_ip: str = "192.168.0.127", 
                 temperature_update_interval: float = 1.0):
        """
        Инициализация ядра системы
        
        Args:
            temperature_ip: IP адрес асика для мониторинга температуры
            temperature_update_interval: Интервал обновления температуры в секундах
        """
        self.temperature_ip = temperature_ip
        self.temperature_update_interval = temperature_update_interval
        
        # Менеджер данных
        self.data_manager = DataManager()
        
        # Менеджер настроек
        self.settings_manager = get_settings_manager()
        
        # Состояние системы
        self.is_running = False
        self.start_time = None
        self._system_lock = threading.Lock()
        
        # Потоки для различных задач
        self._temperature_thread = None
        self._monitoring_thread = None
        
        # Статистика
        self._stats = {
            "temperature_updates": 0,
            "temperature_errors": 0,
            "system_errors": 0,
            "last_temperature_update": None,
            "last_error": None
        }
        
        # Загрузка настроек температуры при инициализации
        self._load_temperature_settings_on_init()
    
    def start(self) -> bool:
        """
        Запуск ядра системы
        
        Returns:
            bool: True если запуск успешен
        """
        with self._system_lock:
            if self.is_running:
                return True
            
            try:
                self.start_time = datetime.now()
                self.is_running = True
                
                # Установка начального статуса
                self.data_manager.set_data(
                    DataType.SYSTEM_STATUS,
                    "starting",
                    "core_system",
                    {"start_time": self.start_time.isoformat()}
                )
                
                # Запуск мониторинга температуры
                if TEMPERATURE_MODULE_AVAILABLE:
                    success = self._start_temperature_monitoring()
                    if not success:
                        self._log_error("Не удалось запустить мониторинг температуры")
                else:
                    self._log_error("Модуль температуры недоступен")
                
                # Запуск основного потока мониторинга
                self._monitoring_thread = threading.Thread(
                    target=self._monitoring_loop, 
                    daemon=True
                )
                self._monitoring_thread.start()
                
                # Обновление статуса
                self.data_manager.set_data(
                    DataType.SYSTEM_STATUS,
                    "running",
                    "core_system",
                    {"modules_started": TEMPERATURE_MODULE_AVAILABLE}
                )
                
                print(f"Ядро системы запущено (температура: {'доступна' if TEMPERATURE_MODULE_AVAILABLE else 'недоступна'})")
                return True
                
            except Exception as e:
                self._log_error(f"Ошибка при запуске ядра: {e}")
                self.is_running = False
                return False
    
    def stop(self):
        """Остановка ядра системы"""
        with self._system_lock:
            if not self.is_running:
                return
            
            print("Остановка ядра системы...")
            self.is_running = False
            
            # Остановка мониторинга температуры
            if TEMPERATURE_MODULE_AVAILABLE:
                try:
                    stop_temperature_monitoring()
                except Exception as e:
                    self._log_error(f"Ошибка при остановке мониторинга температуры: {e}")
            
            # Обновление статуса
            self.data_manager.set_data(
                DataType.SYSTEM_STATUS,
                "stopped",
                "core_system",
                {"stop_time": datetime.now().isoformat()}
            )
            
            print("Ядро системы остановлено")
    
    def _start_temperature_monitoring(self) -> bool:
        """Запуск мониторинга температуры"""
        try:
            success = start_temperature_monitoring(
                ip_address=self.temperature_ip,
                update_interval=self.temperature_update_interval
            )
            
            if success:
                # Запуск потока синхронизации данных температуры
                self._temperature_thread = threading.Thread(
                    target=self._temperature_sync_loop,
                    daemon=True
                )
                self._temperature_thread.start()
                print(f"Мониторинг температуры запущен для {self.temperature_ip}")
                return True
            else:
                self._log_error("Не удалось запустить мониторинг температуры")
                return False
                
        except Exception as e:
            self._log_error(f"Ошибка при запуске мониторинга температуры: {e}")
            return False
    
    def _temperature_sync_loop(self):
        """Основной цикл синхронизации данных температуры"""
        while self.is_running:
            try:
                # Получение данных температуры
                temp_data = get_all_temperature_data()
                
                if temp_data:
                    # Сохранение температуры в ядре
                    if temp_data.get("liquid_temperature") is not None:
                        self.data_manager.set_data(
                            DataType.TEMPERATURE,
                            temp_data["liquid_temperature"],
                            "temperature_module",
                            {
                                "psu_temperature": temp_data.get("psu_temperature"),
                                "fan_speed": temp_data.get("fan_speed"),
                                "status": temp_data.get("status"),
                                "full_data": temp_data
                            }
                        )
                        
                        self._stats["temperature_updates"] += 1
                        self._stats["last_temperature_update"] = datetime.now()
                    
                    # Проверка на ошибки
                    if temp_data.get("status") == "error":
                        error_msg = temp_data.get("error_message", "Неизвестная ошибка температуры")
                        self._log_error(f"Ошибка температуры: {error_msg}")
                
                else:
                    self._stats["temperature_errors"] += 1
                    self._log_error("Не удалось получить данные температуры")
                
                time.sleep(self.temperature_update_interval)
                
            except Exception as e:
                self._stats["temperature_errors"] += 1
                self._log_error(f"Ошибка в цикле синхронизации температуры: {e}")
                time.sleep(self.temperature_update_interval)
    
    def _monitoring_loop(self):
        """Основной цикл мониторинга системы"""
        while self.is_running:
            try:
                # Проверка состояния системы
                self._check_system_health()
                
                # Пауза между проверками
                time.sleep(5.0)
                
            except Exception as e:
                self._log_error(f"Ошибка в цикле мониторинга: {e}")
                time.sleep(5.0)
    
    def _check_system_health(self):
        """Проверка здоровья системы"""
        try:
            # Проверка свежести данных температуры
            temp_fresh = self.data_manager.is_data_fresh(DataType.TEMPERATURE, max_age_seconds=10.0)
            
            # Определение общего статуса
            if temp_fresh:
                status = "healthy"
            elif TEMPERATURE_MODULE_AVAILABLE:
                status = "warning"  # Температура доступна, но данные не свежие
            else:
                status = "degraded"  # Модуль температуры недоступен
            
            # Обновление статуса системы
            self.data_manager.set_data(
                DataType.SYSTEM_STATUS,
                status,
                "core_system",
                {
                    "temperature_fresh": temp_fresh,
                    "temperature_available": TEMPERATURE_MODULE_AVAILABLE,
                    "uptime_seconds": self.get_uptime_seconds()
                }
            )
            
        except Exception as e:
            self._log_error(f"Ошибка при проверке здоровья системы: {e}")
    
    def _log_error(self, error_message: str):
        """Логирование ошибки"""
        timestamp = datetime.now()
        print(f"[{timestamp}] ОШИБКА: {error_message}")
        
        self._stats["system_errors"] += 1
        self._stats["last_error"] = error_message
        
        # Сохранение ошибки в менеджер данных
        self.data_manager.set_data(
            DataType.ERROR,
            error_message,
            "core_system",
            {"timestamp": timestamp.isoformat()}
        )
    
    def get_uptime_seconds(self) -> float:
        """Получение времени работы в секундах"""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0
    
    def get_system_data(self) -> SystemData:
        """Получение сводки системных данных"""
        temperature_entry = self.data_manager.get_data(DataType.TEMPERATURE)
        status_entry = self.data_manager.get_data(DataType.SYSTEM_STATUS)
        
        return SystemData(
            temperature=temperature_entry.value if temperature_entry else None,
            temperature_status=temperature_entry.metadata.get("status") if temperature_entry and temperature_entry.metadata else None,
            system_status=status_entry.value if status_entry else "unknown",
            uptime_seconds=self.get_uptime_seconds(),
            last_update=temperature_entry.timestamp if temperature_entry else None,
            errors=[self._stats["last_error"]] if self._stats["last_error"] else []
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики работы ядра"""
        return {
            "system": {
                "is_running": self.is_running,
                "uptime_seconds": self.get_uptime_seconds(),
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "temperature_module_available": TEMPERATURE_MODULE_AVAILABLE
            },
            "data_manager": self.data_manager.get_statistics(),
            "modules": {
                "temperature": {
                    "updates": self._stats["temperature_updates"],
                    "errors": self._stats["temperature_errors"],
                    "last_update": self._stats["last_temperature_update"].isoformat() if self._stats["last_temperature_update"] else None,
                    "is_active": is_temperature_monitoring_active() if TEMPERATURE_MODULE_AVAILABLE else False
                }
            },
            "errors": {
                "system_errors": self._stats["system_errors"],
                "last_error": self._stats["last_error"]
            }
        }

    def _load_temperature_settings_on_init(self):
        """Загрузка настроек температуры при инициализации"""
        try:
            # Проверяем, существует ли файл настроек
            settings_info = self.settings_manager.get_settings_file_info()
            
            if not settings_info["exists"]:
                # Если файл не существует, создаем его из defaults
                print("Файл настроек не найден, создаю из defaults...")
                self.settings_manager.copy_defaults_to_settings()
            
            # Загружаем настройки
            settings = self.settings_manager.load_settings()
            
            if settings:
                # Преобразуем в формат data_manager
                dm_settings = {
                    "max_temperature": settings["max_temp"],
                    "min_temperature": settings["min_temp"],
                    "hysteresis": settings["max_temp"] - settings["min_temp"],
                    "updated_at": datetime.now().isoformat()
                }
                
                self.data_manager.set_data(
                    DataType.TEMPERATURE_SETTINGS,
                    dm_settings,
                    "settings_manager",
                    {"validation": "passed", "loaded_from_file": True}
                )
                
                print(f"Настройки температуры загружены: min={settings['min_temp']}°C, max={settings['max_temp']}°C")

            # Загружаем IP адрес ASIC из файла, если он сохранен, и публикуем в data_manager
            ip_addr = self.settings_manager.load_ip_address()
            if isinstance(ip_addr, str) and ip_addr:
                # Переопределяем IP, который будет использоваться при запуске мониторинга
                self.temperature_ip = ip_addr
                self.data_manager.set_data(
                    DataType.IP_ADDRESS_ASIC,
                    ip_addr,
                    "settings_manager",
                    {"loaded_from_file": True, "updated_at": datetime.now().isoformat()}
                )
                print(f"IP адрес ASIC загружен из настроек: {ip_addr}")
            
        except Exception as e:
            self._log_error(f"Ошибка при загрузке настроек температуры: {e}")
    
    def save_current_settings(self) -> bool:
        """
        Сохранение текущих настроек температуры в файл
        
        Returns:
            bool: True если сохранение успешно
        """
        try:
            # Получаем текущие настройки из data_manager
            entry = self.data_manager.get_data(DataType.TEMPERATURE_SETTINGS)
            
            if not entry or not entry.value:
                self._log_error("Нет текущих настроек для сохранения")
                return False
            
            settings = entry.value
            
            # Преобразуем в формат для settings_manager
            save_data = {
                "min_temp": settings.get("min_temperature", 45.0),
                "max_temp": settings.get("max_temperature", 55.0),
                "source": entry.source_module
            }
            
            # Сохраняем через settings_manager
            return self.settings_manager.save_settings(save_data)
            
        except Exception as e:
            self._log_error(f"Ошибка при сохранении настроек: {e}")
            return False
    
    def reload_settings_from_file(self) -> bool:
        """
        Перезагрузка настроек из файла
        
        Returns:
            bool: True если перезагрузка успешна
        """
        try:
            settings = self.settings_manager.load_settings()
            
            if settings:
                # Преобразуем в формат data_manager
                dm_settings = {
                    "max_temperature": settings["max_temp"],
                    "min_temperature": settings["min_temp"],
                    "hysteresis": settings["max_temp"] - settings["min_temp"],
                    "updated_at": datetime.now().isoformat()
                }
                
                self.data_manager.set_data(
                    DataType.TEMPERATURE_SETTINGS,
                    dm_settings,
                    "settings_manager",
                    {"validation": "passed", "reloaded_from_file": True}
                )
                
                print(f"Настройки перезагружены: min={settings['min_temp']}°C, max={settings['max_temp']}°C")
                return True
            
            return False
            
        except Exception as e:
            self._log_error(f"Ошибка при перезагрузке настроек: {e}")
            return False
    
    def get_settings_file_info(self) -> Dict[str, Any]:
        """
        Получение информации о файле настроек
        
        Returns:
            Dict: Информация о файле настроек
        """
        return self.settings_manager.get_settings_file_info()


# Глобальный экземпляр ядра
_global_core_system = None
_core_lock = threading.Lock()


def get_core_instance() -> Optional[CoreSystem]:
    """Получение глобального экземпляра ядра"""
    global _global_core_system
    with _core_lock:
        return _global_core_system


def start_core_system(temperature_ip: str = "192.168.0.127", 
                     temperature_update_interval: float = 1.0) -> bool:
    """
    Запуск глобального ядра системы
    
    Args:
        temperature_ip: IP адрес асика
        temperature_update_interval: Интервал обновления температуры
        
    Returns:
        bool: True если запуск успешен
    """
    global _global_core_system
    
    with _core_lock:
        if _global_core_system is not None:
            return True  # Уже запущено
        
        _global_core_system = CoreSystem(temperature_ip, temperature_update_interval)
        return _global_core_system.start()


def stop_core_system():
    """Остановка глобального ядра системы"""
    global _global_core_system
    
    with _core_lock:
        if _global_core_system is not None:
            _global_core_system.stop()
            _global_core_system = None


def is_core_system_running() -> bool:
    """Проверка активности ядра системы"""
    core = get_core_instance()
    return core is not None and core.is_running


def get_temperature_data() -> Optional[float]:
    """Получение актуальной температуры из ядра"""
    core = get_core_instance()
    if core:
        return core.data_manager.get_value(DataType.TEMPERATURE)
    return None


def get_system_status() -> str:
    """
    Получение статуса системы
    
    Returns:
        str: Статус системы
    """
    global _global_core_system
    if _global_core_system and _global_core_system.is_running:
        entry = _global_core_system.data_manager.get_data(DataType.SYSTEM_STATUS)
        return entry.value if entry else "unknown"
    return "stopped"


# Новые функции для управления настройками температуры
def set_temperature_settings(max_temp: float, min_temp: float, source_module: str = "external") -> bool:
    """
    Установка настроек температуры в data_manager с автоматическим сохранением
    
    Args:
        max_temp: Максимальная температура
        min_temp: Минимальная температура  
        source_module: Модуль-источник настроек
        
    Returns:
        bool: True если настройки успешно установлены и сохранены
    """
    global _global_core_system
    if not _global_core_system:
        return False
    
    # Валидация настроек перед установкой
    temp_settings = {"min_temp": min_temp, "max_temp": max_temp}
    if not _global_core_system.settings_manager.validate_settings(temp_settings):
        print(f"Ошибка: Настройки не прошли валидацию")
        return False
    
    settings = {
        "max_temperature": max_temp,
        "min_temperature": min_temp,
        "hysteresis": max_temp - min_temp,
        "updated_at": datetime.now().isoformat()
    }
    
    # Установка в data_manager
    success = _global_core_system.data_manager.set_data(
        DataType.TEMPERATURE_SETTINGS,
        settings,
        source_module,
        {"validation": "passed", "auto_save": True}
    )
    
    if success:
        # Автоматическое сохранение в файл
        save_success = _global_core_system.save_current_settings()
        if save_success:
            print(f"Настройки температуры установлены и сохранены: min={min_temp}°C, max={max_temp}°C")
        else:
            print(f"Настройки установлены, но не удалось сохранить в файл")
        return save_success
    
    return False


def get_temperature_settings() -> Optional[Dict[str, float]]:
    """
    Получение настроек температуры из data_manager
    
    Returns:
        Optional[Dict]: Словарь с настройками температуры или None
    """
    global _global_core_system
    if not _global_core_system:
        return None
    
    entry = _global_core_system.data_manager.get_data(DataType.TEMPERATURE_SETTINGS)
    return entry.value if entry else None


def is_temperature_settings_available() -> bool:
    """
    Проверка доступности настроек температуры
    
    Returns:
        bool: True если настройки доступны
    """
    settings = get_temperature_settings()
    return settings is not None and "max_temperature" in settings and "min_temperature" in settings


def save_current_temperature_settings() -> bool:
    """
    Сохранение текущих настроек температуры в файл
    
    Returns:
        bool: True если сохранение успешно
    """
    core = get_core_instance()
    if core:
        return core.save_current_settings()
    return False


def reload_temperature_settings_from_file() -> bool:
    """
    Перезагрузка настроек температуры из файла
    
    Returns:
        bool: True если перезагрузка успешна
    """
    core = get_core_instance()
    if core:
        return core.reload_settings_from_file()
    return False


def get_temperature_settings_file_info() -> Dict[str, Any]:
    """
    Получение информации о файле настроек температуры
    
    Returns:
        Dict: Информация о файле настроек
    """
    core = get_core_instance()
    if core:
        return core.get_settings_file_info()
    return {"exists": False, "error": "Core system not available"} 


# Работа с IP адресом ASIC (ip_address_asic)
def set_asic_ip(ip_address: str, source_module: str = "external") -> bool:
    """
    Установка IP адреса ASIC в data_manager
    
    Args:
        ip_address: Строка IP адреса (формат IPv4)
        source_module: Источник данных (например, "gui_interface")
    
    Returns:
        bool: True если значение сохранено
    """
    global _global_core_system
    if not _global_core_system:
        return False
    try:
        saved_to_dm = _global_core_system.data_manager.set_data(
            DataType.IP_ADDRESS_ASIC,
            ip_address,
            source_module,
            {"updated_at": datetime.now().isoformat()}
        )
        # Обновляем текущий IP ядра для нового запуска мониторинга/переподключений
        _global_core_system.temperature_ip = ip_address
        # Сохраняем IP в файле настроек
        _global_core_system.settings_manager.save_ip_address(ip_address)
        return saved_to_dm
    except Exception:
        return False


def get_asic_ip() -> Optional[str]:
    """
    Получение текущего IP адреса ASIC из data_manager
    
    Returns:
        Optional[str]: IP адрес или None, если не установлен
    """
    core = get_core_instance()
    if core:
        return core.data_manager.get_value(DataType.IP_ADDRESS_ASIC)
    return None