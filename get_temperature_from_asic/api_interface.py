#!/usr/bin/env python3
"""
API интерфейс для модуля получения температуры
Обертка для simple_api.py для совместимости
"""

from .simple_api import (
    TemperatureAPI,
    get_current_temperature,
    get_temperature_status,
    start_temperature_monitoring,
    stop_temperature_monitoring,
    is_temperature_monitoring_active,
    get_all_temperature_data,
    get_monitoring_statistics
)

# Экспорт всех функций
__all__ = [
    "TemperatureAPI",
    "get_current_temperature",
    "get_temperature_status", 
    "start_temperature_monitoring",
    "stop_temperature_monitoring",
    "is_temperature_monitoring_active",
    "get_all_temperature_data",
    "get_monitoring_statistics"
] 