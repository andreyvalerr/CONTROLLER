#!/usr/bin/env python3
"""
Модуль получения температуры жидкости Whatsminer
Предоставляет API для мониторинга температуры в реальном времени
"""

from .api_interface import (
    TemperatureAPI,
    get_current_temperature,
    get_temperature_status,
    start_temperature_monitoring,
    stop_temperature_monitoring,
    is_temperature_monitoring_active,
    get_all_temperature_data
)

from .simple_monitor import TemperatureMonitor, TemperatureData
from .config import TemperatureConfig

__version__ = "1.0.0"
__author__ = "Система контроллера температуры криптокотла"

# Экспорт основных классов и функций
__all__ = [
    # API интерфейс
    "TemperatureAPI",
    "get_current_temperature", 
    "get_temperature_status",
    "start_temperature_monitoring",
    "stop_temperature_monitoring",
    "is_temperature_monitoring_active",
    "get_all_temperature_data",
    
    # Основные классы
    "TemperatureMonitor",
    "TemperatureData",
    "TemperatureConfig",
] 