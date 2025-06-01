#!/usr/bin/env python3
"""
Простой тест valve_control с автоматическим обновлением настроек температуры
"""

import sys
import os
import time
import threading

# Добавляем пути к модулям
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def main():
    print("=== ТЕСТ VALVE_CONTROL С АВТООБНОВЛЕНИЕМ НАСТРОЕК ===")
    
    # Запуск data_manager
    print("\n1. Запуск data_manager...")
    from data_manager.core_system import (
        start_core_system, 
        set_temperature_settings,
        get_temperature_settings
    )
    
    start_core_system()
    print("✅ Data manager запущен")
    
    # Установка начальных настроек
    set_temperature_settings(50.0, 47.0, "test")
    print("✅ Начальные настройки: 47-50°C")
    
    # Запуск valve_control
    print("\n2. Запуск valve_control...")
    from valve_control.data_manager_integration import (
        start_temperature_data_provider,
        get_temperature_for_valve_controller,
        get_temperature_settings_for_valve_controller
    )
    from valve_control.valve_controller import ValveController, ValveControllerConfig
    from valve_control.config import load_config_from_env
    
    # Интеграция
    start_temperature_data_provider()
    
    # Создание контроллера
    relay_config, temp_config, monitoring_config, safety_config = load_config_from_env()
    config = ValveControllerConfig(
        relay_config=relay_config,
        temperature_config=temp_config,
        monitoring_config=monitoring_config,
        safety_config=safety_config
    )
    
    controller = ValveController(
        temperature_callback=get_temperature_for_valve_controller,
        config=config
    )
    
    # Синхронизация настроек
    controller.sync_temperature_settings_with_data_manager()
    
    # Запуск контроллера в отдельном потоке
    def run_controller():
        controller.run_forever()
    
    controller_thread = threading.Thread(target=run_controller, daemon=True)
    controller_thread.start()
    
    print("✅ Valve_control запущен")
    
    # Проверка работы
    print("\n3. Проверка работы...")
    time.sleep(3)
    
    status = controller.get_status()
    print(f"Статус контроллера: {status['controller']['is_running']}")
    print(f"Текущая температура: {status['temperature']['current']}°C")
    print(f"Настройки: {status['config']['min_temp']}-{status['config']['max_temp']}°C")
    print(f"Охлаждение активно: {status['regulator']['cooling_active']}")
    
    # Изменение настроек для проверки автообновления
    print("\n4. Изменение настроек температуры...")
    set_temperature_settings(48.0, 46.0, "test_update")
    print("✅ Новые настройки установлены: 46-48°C")
    print("Ожидание автообновления (до 2 секунд)...")
    
    # Проверка обновления
    time.sleep(3)
    
    new_status = controller.get_status()
    regulator_status = new_status['regulator']
    
    print(f"\nРезультат:")
    print(f"Настройки в регуляторе: {regulator_status['min_temperature']}-{regulator_status['max_temperature']}°C")
    print(f"Количество обновлений настроек: {regulator_status.get('settings_updates', 0)}")
    print(f"Последняя проверка настроек: {regulator_status.get('settings_check_age_seconds', 'н/д')} сек назад")
    
    if (regulator_status['min_temperature'] == 46.0 and 
        regulator_status['max_temperature'] == 48.0):
        print("🎉 АВТООБНОВЛЕНИЕ РАБОТАЕТ!")
    else:
        print("💥 Автообновление не работает")
    
    # Остановка
    print("\n5. Остановка...")
    controller.stop()
    print("✅ Контроллер остановлен")

if __name__ == "__main__":
    main() 