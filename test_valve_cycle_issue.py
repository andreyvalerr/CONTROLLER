#!/usr/bin/env python3
"""
Тест для диагностики проблемы с циклическим включением охлаждения
"""

import time
import sys
import os
import threading
from datetime import datetime

# Добавляем пути
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_valve_cycling():
    """Тест циклического включения/выключения valve control"""
    
    print("🔬 ТЕСТ ЦИКЛИЧЕСКОГО РЕГУЛИРОВАНИЯ TEMPERATURE")
    print("=" * 60)
    
    try:
        # Импорты
        from data_manager.core_system import (
            start_core_system, 
            set_temperature_settings, 
            get_temperature_settings,
            get_current_temperature,
            stop_core_system
        )
        from valve_control.data_manager_integration import (
            start_temperature_data_provider,
            get_temperature_for_valve_controller
        )
        from valve_control.valve_controller import ValveController, ValveControllerConfig
        from valve_control.config import load_config_from_env
        
        # 1. Запуск data_manager
        print("1️⃣ Запуск data_manager...")
        if not start_core_system(temperature_ip="192.168.0.127", temperature_update_interval=1.0):
            print("❌ Не удалось запустить data_manager")
            return False
        print("✅ Data manager запущен")
        time.sleep(2)
        
        # 2. Установка тестовых настроек
        print("2️⃣ Установка тестовых настроек температуры...")
        if not set_temperature_settings(max_temp=48.0, min_temp=46.0, source_module="test"):
            print("❌ Не удалось установить настройки")
            return False
        
        settings = get_temperature_settings()
        print(f"✅ Настройки: {settings['min_temperature']:.1f}°C - {settings['max_temperature']:.1f}°C")
        
        # 3. Запуск valve provider
        print("3️⃣ Запуск valve temperature provider...")
        if not start_temperature_data_provider(update_interval=1.0):
            print("❌ Не удалось запустить valve provider")
            return False
        print("✅ Valve provider запущен")
        time.sleep(1)
        
        # 4. Создание valve controller
        print("4️⃣ Создание valve controller...")
        relay_config, temp_config, monitoring_config, safety_config = load_config_from_env()
        config = ValveControllerConfig(
            relay_config=relay_config,
            temperature_config=temp_config,
            monitoring_config=monitoring_config,
            safety_config=safety_config
        )
        
        valve_controller = ValveController(
            temperature_callback=get_temperature_for_valve_controller,
            config=config
        )
        
        # Синхронизация с data_manager
        if not valve_controller.sync_temperature_settings_with_data_manager():
            print("❌ Не удалось синхронизировать настройки")
            return False
        
        print("✅ Valve controller создан и настроен")
        
        # 5. Запуск valve controller в отдельном потоке
        print("5️⃣ Запуск регулирования температуры...")
        controller_running = threading.Event()
        
        def run_controller():
            try:
                if valve_controller.start():
                    controller_running.set()
                    valve_controller.run_forever()
            except Exception as e:
                print(f"❌ Ошибка в контроллере: {e}")
        
        controller_thread = threading.Thread(target=run_controller, daemon=True)
        controller_thread.start()
        
        # Ждем запуска контроллера
        if not controller_running.wait(timeout=5):
            print("❌ Контроллер не запустился")
            return False
        
        print("✅ Регулирование запущено")
        
        # 6. Мониторинг работы в течение 60 секунд
        print("6️⃣ Мониторинг работы (60 секунд)...")
        print("=" * 60)
        
        start_time = time.time()
        cycles_logged = 0
        
        while time.time() - start_time < 60:
            try:
                # Получение текущих данных
                temp = get_temperature_for_valve_controller()
                settings = get_temperature_settings()
                cooling_active = valve_controller.is_cooling_active()
                
                if temp is not None and settings:
                    min_temp = settings['min_temperature']
                    max_temp = settings['max_temperature']
                    
                    # Логируем каждые 5 секунд
                    if cycles_logged % 5 == 0:
                        status_icon = "🔥" if cooling_active else "❄️"
                        should_cool = "ДОЛЖНО ОХЛАЖДАТЬ" if temp >= max_temp else "НЕ ДОЛЖНО ОХЛАЖДАТЬ"
                        should_stop = "ДОЛЖНО ОСТАНОВИТЬ" if temp <= min_temp else "НЕ ДОЛЖНО ОСТАНАВЛИВАТЬ"
                        
                        print(f"{status_icon} T={temp:.1f}°C, охлаждение={'ВКЛ' if cooling_active else 'ВЫКЛ'}, "
                              f"пороги=[{min_temp:.1f}-{max_temp:.1f}°C]")
                        
                        if cooling_active:
                            print(f"   -> {should_stop}")
                        else:
                            print(f"   -> {should_cool}")
                        
                        # Проверка на проблему
                        if not cooling_active and temp >= max_temp:
                            print("🚨 ПРОБЛЕМА: Охлаждение должно быть включено, но выключено!")
                        elif cooling_active and temp <= min_temp:
                            print("🚨 ПРОБЛЕМА: Охлаждение должно быть выключено, но включено!")
                
                cycles_logged += 1
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Ошибка мониторинга: {e}")
                break
        
        print("\n7️⃣ Остановка системы...")
        valve_controller.stop()
        stop_core_system()
        print("✅ Тест завершен")
        
        return True
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        return False

if __name__ == "__main__":
    try:
        success = test_valve_cycling()
        if success:
            print("\n✅ Тест успешно завершен")
        else:
            print("\n❌ Тест завершился с ошибками")
    except KeyboardInterrupt:
        print("\n\n⏹️ Тест прерван пользователем")
    except Exception as e:
        print(f"\n❌ Непредвиденная ошибка: {e}") 