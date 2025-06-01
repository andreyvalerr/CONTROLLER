#!/usr/bin/env python3
"""
Тестовый скрипт для проверки интеграции valve_control с data_manager
"""

import sys
import os
import time

# Добавляем пути к модулям
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_integration():
    print("=== ТЕСТ ИНТЕГРАЦИИ VALVE_CONTROL ===")
    
    # 1. Запуск data_manager
    print("\n1. Запуск data_manager...")
    try:
        from data_manager.core_system import (
            start_core_system, 
            is_core_system_running,
            set_temperature_settings,
            get_temperature_settings
        )
        
        if not is_core_system_running():
            success = start_core_system()
            if success:
                print("✅ Data manager запущен")
            else:
                print("❌ Ошибка запуска data manager")
                return False
        else:
            print("✅ Data manager уже запущен")
    except Exception as e:
        print(f"❌ Ошибка data manager: {e}")
        return False
    
    # 2. Установка настроек температуры
    print("\n2. Установка настроек температуры...")
    try:
        success = set_temperature_settings(50.0, 47.0, "test")
        if success:
            print("✅ Настройки температуры установлены: 47-50°C")
        else:
            print("❌ Ошибка установки настроек")
            return False
    except Exception as e:
        print(f"❌ Ошибка установки настроек: {e}")
        return False
    
    # 3. Запуск valve_control интеграции
    print("\n3. Запуск valve_control интеграции...")
    try:
        from valve_control.data_manager_integration import (
            start_temperature_data_provider,
            get_temperature_for_valve_controller,
            get_temperature_settings_for_valve_controller,
            is_temperature_settings_available
        )
        
        success = start_temperature_data_provider()
        if success:
            print("✅ Интеграция valve_control запущена")
        else:
            print("❌ Ошибка запуска интеграции")
            return False
    except Exception as e:
        print(f"❌ Ошибка интеграции: {e}")
        return False
    
    # 4. Проверка получения данных
    print("\n4. Проверка получения данных...")
    time.sleep(2)
    
    try:
        # Температура
        temp = get_temperature_for_valve_controller()
        print(f"Температура: {temp}°C" if temp else "Температура: недоступна")
        
        # Настройки температуры
        if is_temperature_settings_available():
            settings = get_temperature_settings_for_valve_controller()
            if settings:
                print(f"✅ Настройки: {settings['min_temperature']}-{settings['max_temperature']}°C")
            else:
                print("❌ Настройки недоступны")
                return False
        else:
            print("❌ Настройки недоступны")
            return False
    except Exception as e:
        print(f"❌ Ошибка получения данных: {e}")
        return False
    
    print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО")
    return True

if __name__ == "__main__":
    if test_integration():
        print("\n🎉 Интеграция работает корректно!")
        sys.exit(0)
    else:
        print("\n💥 Есть проблемы с интеграцией!")
        sys.exit(1) 