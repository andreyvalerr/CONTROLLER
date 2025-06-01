#!/usr/bin/env python3
"""
Скрипт для проверки настроек температуры в data_manager
"""

import sys
import os

# Добавляем путь к модулю data_manager
sys.path.append(os.path.dirname(__file__))

from data_manager.core_system import (
    start_core_system, 
    get_temperature_settings,
    is_core_system_running,
    get_core_instance
)

def main():
    print("Проверка настроек температуры в data_manager...")
    
    # Проверим состояние core system
    if is_core_system_running():
        print("✅ Core system запущен")
        
        # Получение core instance
        core = get_core_instance()
        if core:
            print(f"✅ Core instance найден")
            print(f"Статистика: {core.get_statistics()}")
        else:
            print("❌ Core instance не найден")
    else:
        print("❌ Core system не запущен")
        return 1
    
    # Проверим настройки температуры
    settings = get_temperature_settings()
    if settings:
        print(f"✅ Настройки температуры найдены: {settings}")
    else:
        print("❌ Настройки температуры отсутствуют")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 