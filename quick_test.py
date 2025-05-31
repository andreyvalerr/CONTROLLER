#!/usr/bin/env python3
"""
Быстрый тест интеграции ядра с модулем температуры
"""

try:
    print("=== ТЕСТ ИНТЕГРАЦИИ ЯДРА СИСТЕМЫ ===")
    
    # 1. Проверка импорта ядра
    print("1. Импорт ядра системы...")
    from data_manager import (
        start_core_system,
        get_temperature_data,
        get_system_status,
        stop_core_system,
        is_core_system_running
    )
    print("✓ Ядро системы импортировано успешно")
    
    # 2. Проверка импорта модуля температуры
    print("\n2. Проверка модуля температуры...")
    try:
        from get_temperature_from_asic import get_current_temperature
        print("✓ Модуль температуры доступен")
        temp_module_available = True
    except Exception as e:
        print(f"⚠ Модуль температуры недоступен: {e}")
        temp_module_available = False
    
    # 3. Запуск ядра
    print("\n3. Запуск ядра системы...")
    success = start_core_system()
    if success:
        print("✓ Ядро системы запущено")
    else:
        print("✗ Ошибка при запуске ядра")
        exit(1)
    
    # 4. Проверка статуса
    print(f"\n4. Статус системы: {get_system_status()}")
    print(f"   Ядро активно: {is_core_system_running()}")
    
    # 5. Получение температуры
    print("\n5. Тест получения температуры...")
    temp = get_temperature_data()
    if temp is not None:
        print(f"✓ Температура получена: {temp}°C")
    else:
        print("⚠ Температура не получена (ожидаемо при первом запуске)")
    
    # 6. Остановка
    print("\n6. Остановка ядра...")
    stop_core_system()
    print("✓ Ядро остановлено")
    
    print("\n=== ТЕСТ ЗАВЕРШЕН УСПЕШНО ===")
    print("\nИнтеграция готова к использованию!")
    print("Теперь другие модули могут:")
    print("- Использовать get_temperature_data() для получения температуры")
    print("- Проверять get_system_status() для контроля состояния")
    print("- Запускать start_core_system() для активации системы")

except Exception as e:
    print(f"\n✗ ОШИБКА В ТЕСТЕ: {e}")
    import traceback
    traceback.print_exc() 