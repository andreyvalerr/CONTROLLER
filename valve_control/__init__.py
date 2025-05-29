#!/usr/bin/env python3
"""
Модуль управления клапанами через релейный модуль
Предоставляет API для контроля температуры жидкости криптокотла
"""

from .relay_controller import RelayController
from .valve_controller import ValveController, ValveControllerConfig
from .temperature_regulator import TemperatureRegulator, RegulatorConfig
from .manual_control import manual_valve_control

__version__ = "1.0.0"
__author__ = "Система контроллера температуры криптокотла"

# Экспорт основных классов и функций
__all__ = [
    # Основные классы
    "RelayController",
    "ValveController", 
    "ValveControllerConfig",
    "TemperatureRegulator",
    "RegulatorConfig",
    
    # Утилиты
    "manual_valve_control",
] 