#!/usr/bin/env python3
"""
Конфигурация модуля управления клапанами
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class RelayConfig:
    """Конфигурация релейного модуля"""
    # GPIO настройки
    relay_pin: int = 17  # GPIO пин для реле (по умолчанию GPIO 17)
    gpio_mode: str = "BCM"  # Режим нумерации GPIO (BCM или BOARD)
    
    # Логика управления (инвертированная для большинства релейных модулей)
    relay_on_state: int = 0   # GPIO.LOW для включения реле
    relay_off_state: int = 1  # GPIO.HIGH для выключения реле
    
    # Безопасность
    enable_warnings: bool = False  # Отключить предупреждения GPIO
    cleanup_on_exit: bool = True   # Очистка GPIO при выходе

@dataclass 
class TemperatureConfig:
    """Конфигурация температурных порогов"""
    # Пороговые значения температуры (°C)
    max_temperature: float = 52.0  # Максимальная температура для включения охлаждения
    min_temperature: float = 51.9  # Минимальная температура для выключения охлаждения
    
    # Критические значения
    critical_max_temp: float = 65.0  # Критическая температура
    emergency_temp: float = 70.0     # Аварийная температура
    
    # Гистерезис
    hysteresis: float = 0.1  # Разница между max и min температурой
    
    # Таймауты
    temperature_timeout: float = 10.0  # Таймаут получения температуры (сек)
    control_interval: float = 1.0      # Интервал контроля температуры (сек)

@dataclass
class MonitoringConfig:
    """Конфигурация мониторинга"""
    # Настройки подключения к асику
    asic_ip: str = "192.168.0.127"  # IP адрес асика
    update_interval: float = 1.0    # Интервал обновления температуры (сек)
    
    # Логирование
    log_level: str = "INFO"
    log_file: Optional[str] = None
    enable_console_log: bool = True
    
    # Статистика
    enable_statistics: bool = True
    stats_interval: float = 60.0  # Интервал сохранения статистики (сек)

@dataclass
class SafetyConfig:
    """Конфигурация безопасности"""
    # Максимальное время работы охлаждения без перерыва (минуты)
    max_cooling_time: float = 60.0
    
    # Минимальное время между включениями (секунды)
    min_cycle_time: float = 1.0
    
    # Максимальное количество переключений в час
    max_switches_per_hour: int = 6600
    
    # Аварийное отключение при потере связи с асиком (секунды)
    emergency_timeout: float = 300.0

# Глобальная конфигурация
DEFAULT_RELAY_CONFIG = RelayConfig()
DEFAULT_TEMPERATURE_CONFIG = TemperatureConfig()
DEFAULT_MONITORING_CONFIG = MonitoringConfig()
DEFAULT_SAFETY_CONFIG = SafetyConfig()

def load_config_from_env() -> tuple[RelayConfig, TemperatureConfig, MonitoringConfig, SafetyConfig]:
    """
    Загрузка конфигурации из переменных окружения
    
    Returns:
        tuple: Кортеж с конфигурациями (relay, temperature, monitoring, safety)
    """
    
    # Релейная конфигурация
    relay_config = RelayConfig(
        relay_pin=int(os.getenv("RELAY_PIN", DEFAULT_RELAY_CONFIG.relay_pin)),
        gpio_mode=os.getenv("GPIO_MODE", DEFAULT_RELAY_CONFIG.gpio_mode),
        enable_warnings=os.getenv("GPIO_WARNINGS", "false").lower() == "true",
        cleanup_on_exit=os.getenv("GPIO_CLEANUP", "true").lower() == "true"
    )
    
    # Температурная конфигурация
    temp_config = TemperatureConfig(
        max_temperature=float(os.getenv("MAX_TEMP", DEFAULT_TEMPERATURE_CONFIG.max_temperature)),
        min_temperature=float(os.getenv("MIN_TEMP", DEFAULT_TEMPERATURE_CONFIG.min_temperature)),
        critical_max_temp=float(os.getenv("CRITICAL_TEMP", DEFAULT_TEMPERATURE_CONFIG.critical_max_temp)),
        emergency_temp=float(os.getenv("EMERGENCY_TEMP", DEFAULT_TEMPERATURE_CONFIG.emergency_temp)),
        hysteresis=float(os.getenv("TEMP_HYSTERESIS", DEFAULT_TEMPERATURE_CONFIG.hysteresis)),
        temperature_timeout=float(os.getenv("TEMP_TIMEOUT", DEFAULT_TEMPERATURE_CONFIG.temperature_timeout)),
        control_interval=float(os.getenv("CONTROL_INTERVAL", DEFAULT_TEMPERATURE_CONFIG.control_interval))
    )
    
    # Конфигурация мониторинга
    monitoring_config = MonitoringConfig(
        asic_ip=os.getenv("ASIC_IP", DEFAULT_MONITORING_CONFIG.asic_ip),
        update_interval=float(os.getenv("UPDATE_INTERVAL", DEFAULT_MONITORING_CONFIG.update_interval)),
        log_level=os.getenv("LOG_LEVEL", DEFAULT_MONITORING_CONFIG.log_level),
        log_file=os.getenv("LOG_FILE", DEFAULT_MONITORING_CONFIG.log_file),
        enable_console_log=os.getenv("CONSOLE_LOG", "true").lower() == "true",
        enable_statistics=os.getenv("ENABLE_STATS", "true").lower() == "true",
        stats_interval=float(os.getenv("STATS_INTERVAL", DEFAULT_MONITORING_CONFIG.stats_interval))
    )
    
    # Конфигурация безопасности
    safety_config = SafetyConfig(
        max_cooling_time=float(os.getenv("MAX_COOLING_TIME", DEFAULT_SAFETY_CONFIG.max_cooling_time)),
        min_cycle_time=float(os.getenv("MIN_CYCLE_TIME", DEFAULT_SAFETY_CONFIG.min_cycle_time)),
        max_switches_per_hour=int(os.getenv("MAX_SWITCHES_HOUR", DEFAULT_SAFETY_CONFIG.max_switches_per_hour)),
        emergency_timeout=float(os.getenv("EMERGENCY_TIMEOUT", DEFAULT_SAFETY_CONFIG.emergency_timeout))
    )
    
    return relay_config, temp_config, monitoring_config, safety_config

def validate_config(relay_config: RelayConfig, temp_config: TemperatureConfig) -> list[str]:
    """
    Валидация конфигурации
    
    Args:
        relay_config: Конфигурация реле
        temp_config: Конфигурация температуры
        
    Returns:
        list: Список ошибок валидации
    """
    errors = []
    
    # Проверка GPIO пина
    if not (1 <= relay_config.relay_pin <= 40):
        errors.append(f"Неверный GPIO пин: {relay_config.relay_pin}. Должен быть от 1 до 40")
    
    # Проверка температурных порогов
    if temp_config.min_temperature >= temp_config.max_temperature:
        errors.append(f"Минимальная температура ({temp_config.min_temperature}) должна быть меньше максимальной ({temp_config.max_temperature})")
    
    if temp_config.max_temperature >= temp_config.critical_max_temp:
        errors.append(f"Максимальная температура ({temp_config.max_temperature}) должна быть меньше критической ({temp_config.critical_max_temp})")
    
    if temp_config.critical_max_temp >= temp_config.emergency_temp:
        errors.append(f"Критическая температура ({temp_config.critical_max_temp}) должна быть меньше аварийной ({temp_config.emergency_temp})")
    
    # Проверка интервалов
    if temp_config.control_interval <= 0:
        errors.append(f"Интервал контроля должен быть положительным: {temp_config.control_interval}")
    
    if temp_config.temperature_timeout <= 0:
        errors.append(f"Таймаут температуры должен быть положительным: {temp_config.temperature_timeout}")
    
    return errors 