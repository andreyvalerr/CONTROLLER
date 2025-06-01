#!/usr/bin/env python3
"""
Тест интеграции valve_control с data_manager
Проверка получения температурных данных каждую секунду
"""

import time
import sys
import os

# Добавляем путь к модулю
sys.path.append(os.path.dirname(__file__))

from data_manager_integration import (
    start_temperature_data_provider,
    stop_temperature_data_provider,
    get_temperature_for_valve_controller,
    get_temperature_provider_statistics,
    is_temperature_provider_running
)

def test_temperature_integration():
    """Тест интеграции температурных данных"""
    print("=== ТЕСТ ИНТЕГРАЦИИ VALVE_CONTROL С DATA_MANAGER ===")
    
    # Запуск поставщика данных
    print("\n1. Запуск поставщика температурных данных...")
    if start_temperature_data_provider(update_interval=1.0):
        print("✓ Поставщик данных запущен успешно")
    else:
        print("✗ Ошибка запуска поставщика данных")
        return False
    
    # Проверка работы
    print("\n2. Проверка работы поставщика...")
    if is_temperature_provider_running():
        print("✓ Поставщик данных работает")
    else:
        print("✗ Поставщик данных не работает")
        return False
    
    # Тест получения температуры
    print("\n3. Тест получения температуры в течение 10 секунд...")
    successful_reads = 0
    total_reads = 0
    
    for i in range(10):
        total_reads += 1
        temperature = get_temperature_for_valve_controller()
        
        if temperature is not None:
            successful_reads += 1
            print(f"   Секунда {i+1}: {temperature}°C")
        else:
            print(f"   Секунда {i+1}: Температура недоступна")
        
        time.sleep(1)
    
    # Статистика
    print(f"\n4. Результаты теста:")
    print(f"   Успешных чтений: {successful_reads}/{total_reads}")
    print(f"   Процент успеха: {(successful_reads/total_reads)*100:.1f}%")
    
    # Подробная статистика
    stats = get_temperature_provider_statistics()
    print(f"\n5. Статистика поставщика данных:")
    print(f"   Работает: {stats.get('is_running')}")
    print(f"   Текущая температура: {stats.get('current_temperature')}°C")
    print(f"   Последнее обновление: {stats.get('last_update')}")
    print(f"   Всего обновлений: {stats.get('total_updates')}")
    print(f"   Успешных обновлений: {stats.get('successful_updates')}")
    print(f"   Неудачных обновлений: {stats.get('failed_updates')}")
    print(f"   Успешность: {stats.get('success_rate'):.1f}%")
    print(f"   Данные свежие: {stats.get('data_fresh')}")
    
    if stats.get('last_error'):
        print(f"   Последняя ошибка: {stats.get('last_error')}")
    
    # Остановка поставщика
    print("\n6. Остановка поставщика данных...")
    stop_temperature_data_provider()
    print("✓ Поставщик данных остановлен")
    
    print("\n=== ТЕСТ ЗАВЕРШЕН ===")
    return successful_reads > 0

def main():
    """Главная функция теста"""
    try:
        success = test_temperature_integration()
        if success:
            print("\n🎉 Тест прошел успешно! Интеграция работает.")
            return 0
        else:
            print("\n❌ Тест завершился неудачно. Проверьте конфигурацию.")
            return 1
    except KeyboardInterrupt:
        print("\n\n⏹️ Тест прерван пользователем")
        stop_temperature_data_provider()
        return 1
    except Exception as e:
        print(f"\n💥 Ошибка во время теста: {e}")
        stop_temperature_data_provider()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 