#!/usr/bin/env python3
"""
Ядро системы контроллера криптокотла
Централизованное управление данными и координация модулей
"""

from .core_system import (
    CoreSystem,
    SystemData,
    get_core_instance,
    get_temperature_data,
    get_system_status,
    start_core_system,
    stop_core_system,
    is_core_system_running
)

from .data_manager import DataManager, DataType

__version__ = "1.0.0"
__author__ = "Система контроллера криптокотла"

# Экспорт основных классов и функций
__all__ = [
    # Основная система
    "CoreSystem",
    "SystemData",
    "get_core_instance",
    "get_temperature_data",
    "get_system_status",
    "start_core_system",
    "stop_core_system",
    "is_core_system_running",
    
    # Управление данными
    "DataManager",
    "DataType",
] 