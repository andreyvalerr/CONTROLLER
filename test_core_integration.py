#!/usr/bin/env python3
"""
Тестовый скрипт для демонстрации интеграции ядра с модулем температуры
Показывает как ядро получает данные от модуля температуры и предоставляет их другим модулям
"""

import time
import sys
import os
from datetime import datetime

# Добавление путей
sys.path.append(os.path.dirname(__file__))

# Импорт ядра системы
from data_manager import (
    start_core_system,
    stop_core_system,
    get_core_instance,
    get_temperature_data,
    get_system_status,
    is_core_system_running,
    DataType
)


def test_core_integration():
    """Тест интеграции ядра с модулем температуры"""
    print("=== ТЕСТ ИНТЕГРАЦИИ ЯДРА С МОДУЛЕМ ТЕМПЕРАТУРЫ ===\n")
    
    try:
        # 1. Запуск ядра системы
        print("1. Запуск ядра системы...")
        success = start_core_system(
            temperature_ip="192.168.0.127",
            temperature_update_interval=2.0
        )
        
        if success:
            print("✓ Ядро системы успешно запущено")
        else:
            print("✗ Ошибка при запуске ядра системы")
            return
        
        # 2. Проверка статуса
        print(f"2. Статус системы: {get_system_status()}")
        print(f"   Ядро активно: {is_core_system_running()}")
        
        # 3. Получение экземпляра ядра для детальной информации
        core = get_core_instance()
        if core:
            print(f"   Время работы: {core.get_uptime_seconds():.1f} сек")
        
        # 4. Мониторинг данных температуры в реальном времени
        print("\n3. Мониторинг температуры (30 секунд)...")
        print("   Время     | Температура | Статус системы | Источник")
        print("   " + "-" * 55)
        
        for i in range(15):  # 30 секунд при интервале 2 сек
            # Получение температуры через ядро (как это будут делать другие модули)
            temperature = get_temperature_data()
            system_status = get_system_status()
            
            # Получение дополнительной информации
            if core:
                temp_entry = core.data_manager.get_data(DataType.TEMPERATURE)
                source = temp_entry.source_module if temp_entry else "N/A"
                timestamp = temp_entry.timestamp.strftime("%H:%M:%S") if temp_entry else "N/A"
            else:
                source = "N/A"
                timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Форматирование температуры
            temp_str = f"{temperature:.1f}°C" if temperature is not None else "N/A"
            
            print(f"   {timestamp} | {temp_str:11} | {system_status:13} | {source}")
            
            time.sleep(2)
        
        # 5. Отображение статистики
        print("\n4. Статистика работы ядра:")
        if core:
            stats = core.get_statistics()
            print(f"   Общее время работы: {stats['system']['uptime_seconds']:.1f} сек")
            print(f"   Обновлений температуры: {stats['modules']['temperature']['updates']}")
            print(f"   Ошибок температуры: {stats['modules']['temperature']['errors']}")
            print(f"   Общих ошибок системы: {stats['errors']['system_errors']}")
            
            # Статистика менеджера данных
            dm_stats = stats['data_manager']
            print(f"   Всего обновлений данных: {dm_stats['total_updates']}")
            print(f"   Обновлений по типам:")
            for data_type, count in dm_stats['updates_by_type'].items():
                print(f"     - {data_type}: {count}")
        
        # 6. Демонстрация получения исторических данных
        print("\n5. Последние 5 измерений температуры:")
        if core:
            history = core.data_manager.get_history(DataType.TEMPERATURE, limit=5)
            for entry in history[-5:]:
                timestamp = entry.timestamp.strftime("%H:%M:%S")
                temp = entry.value
                status = entry.metadata.get("status", "unknown") if entry.metadata else "unknown"
                print(f"   {timestamp}: {temp:.1f}°C (статус: {status})")
        
        print("\n6. Демонстрация завершена. Ядро продолжит работать...")
        print("   Другие модули могут использовать функции:")
        print("   - get_temperature_data() - для получения текущей температуры")
        print("   - get_system_status() - для проверки статуса системы")
        print("   - get_core_instance() - для доступа к полному API ядра")
        
    except KeyboardInterrupt:
        print("\n\nПрерывание пользователем...")
    except Exception as e:
        print(f"\nОшибка в тесте: {e}")
    finally:
        # 7. Остановка ядра
        print("\n7. Остановка ядра системы...")
        stop_core_system()
        print("✓ Ядро системы остановлено")


def demo_other_module_usage():
    """Демонстрация использования ядра другим модулем"""
    print("\n=== ДЕМОНСТРАЦИЯ ИСПОЛЬЗОВАНИЯ ДРУГИМ МОДУЛЕМ ===\n")
    
    # Проверка состояния ядра
    if not is_core_system_running():
        print("Ядро не запущено. Запускаем...")
        if not start_core_system():
            print("Не удалось запустить ядро")
            return
    
    print("Модуль подключился к ядру системы")
    
    # Получение данных (как это будет делать любой другой модуль)
    for i in range(5):
        temp = get_temperature_data()
        status = get_system_status()
        
        print(f"Цикл {i+1}: Температура = {temp}°C, Статус = {status}")
        
        # Имитация работы модуля
        time.sleep(3)
    
    print("Модуль завершил работу")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_other_module_usage()
    else:
        test_core_integration() 