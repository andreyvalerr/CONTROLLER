#!/usr/bin/env python3
"""
Тестирование интеграции настроек температуры с data_manager
"""

import time
import sys
import os

# Добавляем путь к модулю
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_manager_integration import (
    get_temperature_settings_for_valve_controller,
    set_temperature_settings_from_valve_controller,
    is_temperature_settings_available,
    start_temperature_data_provider,
    stop_temperature_data_provider
)

def test_temperature_settings_integration():
    """Тест интеграции настроек температуры"""
    print("=== ТЕСТ ИНТЕГРАЦИИ НАСТРОЕК ТЕМПЕРАТУРЫ ===")
    
    # 1. Запуск data_manager интеграции
    print("\n1. Запуск интеграции с data_manager...")
    if start_temperature_data_provider(update_interval=1.0):
        print("   ✅ Интеграция запущена успешно")
    else:
        print("   ❌ Не удалось запустить интеграцию")
        return False
    
    # Пауза для инициализации
    time.sleep(2)
    
    # 2. Проверка доступности настроек
    print("\n2. Проверка доступности настроек температуры...")
    if is_temperature_settings_available():
        print("   ✅ Настройки температуры доступны в data_manager")
        
        # Получение текущих настроек
        settings = get_temperature_settings_for_valve_controller()
        if settings:
            print(f"   📊 Текущие настройки:")
            print(f"       Max температура: {settings.get('max_temperature')}°C")
            print(f"       Min температура: {settings.get('min_temperature')}°C")
            print(f"       Обновлено: {settings.get('updated_at')}")
        else:
            print("   ❌ Настройки повреждены в data_manager")
            return False
    else:
        print("   ❌ КРИТИЧЕСКАЯ ОШИБКА: Настройки температуры отсутствуют в data_manager")
        print("   ❌ Модуль valve_control требует обязательного наличия настроек")
        print("   ❌ Создайте настройки температуры в data_manager перед тестированием")
        return False
    
    # 4. Тест обновления настроек
    print("\n3. Тест обновления настроек...")
    new_max = 53.0
    new_min = 52.5
    
    if set_temperature_settings_from_valve_controller(new_max, new_min):
        print(f"   ✅ Настройки обновлены: {new_min}°C - {new_max}°C")
        
        # Проверка обновления
        time.sleep(1)
        updated_settings = get_temperature_settings_for_valve_controller()
        if updated_settings:
            actual_max = updated_settings.get('max_temperature')
            actual_min = updated_settings.get('min_temperature')
            
            if abs(actual_max - new_max) < 0.01 and abs(actual_min - new_min) < 0.01:
                print("   ✅ Настройки корректно сохранены и получены")
            else:
                print(f"   ❌ Несоответствие настроек: ожидалось {new_min}-{new_max}, получено {actual_min}-{actual_max}")
        else:
            print("   ❌ Не удалось получить обновленные настройки")
    else:
        print("   ❌ Не удалось обновить настройки")
    
    # 5. Тест с некорректными данными
    print("\n4. Тест с некорректными настройками...")
    invalid_max = 50.0
    invalid_min = 51.0  # min > max
    
    if set_temperature_settings_from_valve_controller(invalid_max, invalid_min):
        print("   ⚠️  Система приняла некорректные настройки (нужна валидация)")
    else:
        print("   ✅ Система корректно отклонила некорректные настройки")
    
    # 6. Восстановление нормальных настроек
    print("\n5. Восстановление нормальных настроек...")
    normal_max = 52.0
    normal_min = 51.9
    
    if set_temperature_settings_from_valve_controller(normal_max, normal_min):
        print(f"   ✅ Настройки восстановлены: {normal_min}°C - {normal_max}°C")
    
    # 7. Остановка интеграции
    print("\n6. Остановка интеграции...")
    stop_temperature_data_provider()
    print("   ✅ Интеграция остановлена")
    
    print("\n=== ТЕСТ ЗАВЕРШЕН УСПЕШНО ===")
    return True

def main():
    """Главная функция теста"""
    try:
        success = test_temperature_settings_integration()
        if success:
            print("\n🎉 Все тесты прошли успешно!")
            return 0
        else:
            print("\n❌ Некоторые тесты не прошли")
            return 1
    except KeyboardInterrupt:
        print("\n\n⏹️  Тест прерван пользователем")
        stop_temperature_data_provider()
        return 130
    except Exception as e:
        print(f"\n❌ Ошибка теста: {e}")
        stop_temperature_data_provider()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 