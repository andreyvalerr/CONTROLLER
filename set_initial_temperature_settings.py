#!/usr/bin/env python3
"""
Скрипт для установки начальных настроек температуры в data_manager
"""

import sys
import os

# Добавляем путь к модулю data_manager
sys.path.append(os.path.dirname(__file__))

from data_manager.core_system import (
    start_core_system, 
    set_temperature_settings, 
    get_temperature_settings,
    is_core_system_running
)

def main():
    print("Установка начальных настроек температуры...")
    
    # Запуск core system если не запущен
    if not is_core_system_running():
        print("Запуск core system...")
        if not start_core_system():
            print("❌ Ошибка запуска core system!")
            return 1
        print("✅ Core system запущен")
    else:
        print("✅ Core system уже запущен")
    
    # Проверим, есть ли уже настройки
    current_settings = get_temperature_settings()
    if current_settings:
        print(f"✅ Настройки температуры уже существуют: {current_settings}")
        return 0
    
    # Установим начальные настройки: 42-45°C (по умолчанию для криптоферм)
    min_temp = 42.0
    max_temp = 45.0
    
    print(f"Установка настроек: {min_temp}°C - {max_temp}°C")
    
    if set_temperature_settings(max_temp, min_temp, "initial_setup"):
        print("✅ Начальные настройки температуры установлены успешно")
        return 0
    else:
        print("❌ Ошибка установки настроек температуры")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 