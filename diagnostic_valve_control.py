#!/usr/bin/env python3
"""
Диагностический скрипт для мониторинга valve_control в реальном времени
"""

import time
import sys
import os
from datetime import datetime

# Добавляем пути
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def get_valve_status():
    """Получение подробного статуса valve control"""
    try:
        from valve_control.data_manager_integration import (
            get_temperature_for_valve_controller,
            is_temperature_provider_running
        )
        from data_manager.core_system import (
            get_temperature_settings,
            is_core_system_running,
            get_current_temperature
        )
        
        status = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'core_system_running': False,
            'valve_provider_running': False,
            'temperature_from_valve': None,
            'temperature_from_core': None,
            'temperature_settings': None,
            'error': None
        }
        
        # Проверка core system
        status['core_system_running'] = is_core_system_running()
        
        # Проверка valve provider
        status['valve_provider_running'] = is_temperature_provider_running()
        
        # Получение температуры через valve provider
        if status['valve_provider_running']:
            status['temperature_from_valve'] = get_temperature_for_valve_controller()
        
        # Получение температуры напрямую
        if status['core_system_running']:
            status['temperature_from_core'] = get_current_temperature()
            status['temperature_settings'] = get_temperature_settings()
        
        return status
        
    except Exception as e:
        return {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'error': str(e)
        }

def print_status(status):
    """Красивый вывод статуса"""
    print(f"\n🕐 {status['timestamp']}")
    print("=" * 50)
    
    if status.get('error'):
        print(f"❌ ОШИБКА: {status['error']}")
        return
    
    # Статус систем
    core_status = "✅" if status['core_system_running'] else "❌"
    valve_status = "✅" if status['valve_provider_running'] else "❌"
    
    print(f"📊 Core System:        {core_status}")
    print(f"🔧 Valve Provider:     {valve_status}")
    
    # Температура
    temp_valve = status['temperature_from_valve']
    temp_core = status['temperature_from_core']
    
    if temp_valve is not None:
        print(f"🌡️  Температура (valve): {temp_valve:.1f}°C")
    else:
        print("🌡️  Температура (valve): НЕДОСТУПНА")
    
    if temp_core is not None:
        print(f"🌡️  Температура (core):  {temp_core:.1f}°C")
    else:
        print("🌡️  Температура (core):  НЕДОСТУПНА")
    
    # Настройки температуры
    settings = status['temperature_settings']
    if settings:
        min_temp = settings.get('min_temperature', 'N/A')
        max_temp = settings.get('max_temperature', 'N/A')
        print(f"⚙️  Пороги: {min_temp}°C - {max_temp}°C")
        
        # Анализ состояния
        if temp_valve is not None and isinstance(min_temp, (int, float)) and isinstance(max_temp, (int, float)):
            if temp_valve >= max_temp:
                print("🔥 ДОЛЖНО ВКЛЮЧИТЬСЯ ОХЛАЖДЕНИЕ!")
            elif temp_valve <= min_temp:
                print("❄️  ДОЛЖНО ВЫКЛЮЧИТЬСЯ ОХЛАЖДЕНИЕ!")
            else:
                print("⚡ Температура в норме")
    else:
        print("⚙️  Пороги: НЕДОСТУПНЫ")

def monitor_system():
    """Непрерывный мониторинг системы"""
    print("🔍 ДИАГНОСТИКА VALVE CONTROL")
    print("Нажмите Ctrl+C для остановки")
    print("=" * 50)
    
    try:
        while True:
            status = get_valve_status()
            print_status(status)
            time.sleep(2)  # Обновление каждые 2 секунды
            
    except KeyboardInterrupt:
        print("\n\n✅ Мониторинг остановлен")

if __name__ == "__main__":
    monitor_system() 