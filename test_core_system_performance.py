#!/usr/bin/env python3
"""
Тест производительности core_system без GUI
Проверяет как часто обновляются данные температуры
"""

import os
import sys
import time
from datetime import datetime

# Добавляем путь к модулям
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'data_manager'))

from data_manager.core_system import (
    start_core_system,
    get_core_instance,
    is_core_system_running,
    get_temperature_data,
    get_system_status
)

def test_temperature_updates():
    """Тестирование частоты обновления температуры"""
    print("🔧 Запуск теста производительности core_system...")
    print("=" * 60)
    
    # Запуск core_system
    if not is_core_system_running():
        print("📡 Запускаю core_system...")
        success = start_core_system(
            temperature_ip="192.168.0.127", 
            temperature_update_interval=1.0
        )
        if not success:
            print("❌ Не удалось запустить core_system")
            return
        
        # Ждем инициализации
        print("⏳ Ждем инициализации системы...")
        time.sleep(3)
    
    print("✅ Core system запущен")
    print()
    
    # Получаем экземпляр core system
    core = get_core_instance()
    if not core:
        print("❌ Не удалось получить экземпляр core system")
        return
    
    print("📊 Мониторинг обновлений температуры (нажмите Ctrl+C для остановки):")
    print("Время          | Температура | Статус   | Интервал")
    print("-" * 55)
    
    last_temp = None
    last_update_time = None
    update_count = 0
    
    try:
        while True:
            # Получаем данные разными способами для сравнения
            current_temp_direct = get_temperature_data()  # Прямой вызов
            system_data = core.get_system_data()          # Через core instance
            current_temp_core = system_data.temperature
            
            current_time = datetime.now()
            
            # Проверяем обновилась ли температура
            if current_temp_direct != last_temp and current_temp_direct is not None:
                update_count += 1
                
                # Вычисляем интервал между обновлениями
                interval_str = "---"
                if last_update_time:
                    interval = (current_time - last_update_time).total_seconds()
                    interval_str = f"{interval:.1f}s"
                
                # Проверяем совпадают ли данные из разных источников
                data_match = "✅" if current_temp_direct == current_temp_core else "❌"
                
                print(f"{current_time.strftime('%H:%M:%S.%f')[:-3]} | "
                      f"{current_temp_direct:>6.1f}°C    | "
                      f"{system_data.system_status:>8} | "
                      f"{interval_str:>8} {data_match}")
                
                last_temp = current_temp_direct
                last_update_time = current_time
            
            time.sleep(0.1)  # Проверяем каждые 100ms
            
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("🛑 Тест остановлен пользователем")
        
        # Показываем статистику
        print(f"\n📈 Результаты теста:")
        print(f"   Общее количество обновлений: {update_count}")
        
        if update_count > 1 and last_update_time:
            test_duration = (last_update_time - 
                           (last_update_time - (current_time - last_update_time) * (update_count - 1))
                          ).total_seconds()
            avg_interval = test_duration / (update_count - 1) if update_count > 1 else 0
            print(f"   Средний интервал обновления: {avg_interval:.2f} секунд")
        
        # Статистика core system
        core_stats = core.get_statistics()
        print(f"\n📊 Статистика core system:")
        for key, value in core_stats.items():
            print(f"   {key}: {value}")

def test_data_manager_direct():
    """Тестирование прямого доступа к data_manager"""
    print("\n🔍 Тест прямого доступа к data_manager...")
    
    core = get_core_instance()
    if not core:
        print("❌ Core system недоступен")
        return
    
    from data_manager.data_manager import DataType
    
    print("Время          | Значение | Источник     | Metadata")
    print("-" * 60)
    
    last_entry = None
    
    try:
        for i in range(20):  # 20 проверок с интервалом 0.5 сек
            entry = core.data_manager.get_data(DataType.TEMPERATURE)
            
            if entry and (not last_entry or entry.timestamp != last_entry.timestamp):
                print(f"{entry.timestamp.strftime('%H:%M:%S.%f')[:-3]} | "
                      f"{entry.value:>6.1f}°C | "
                      f"{entry.source:>11} | "
                      f"{entry.metadata}")
                last_entry = entry
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("Тест остановлен")

def main():
    """Главная функция теста"""
    print("🚀 ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ СИСТЕМЫ (БЕЗ GUI)")
    print("=" * 60)
    
    try:
        # Основной тест обновлений температуры
        test_temperature_updates()
        
        # Дополнительный тест data_manager
        test_data_manager_direct()
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 