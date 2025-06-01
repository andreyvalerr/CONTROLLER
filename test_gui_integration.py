#!/usr/bin/env python3
"""
Тест взаимодействия GUI с valve_control
Диагностика проблемы передачи настроек температуры
"""

import time
import sys
import os
import threading
from datetime import datetime

# Добавляем пути
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_gui_valve_interaction():
    """Тест взаимодействия GUI с valve control"""
    
    print("🔍 ТЕСТ ВЗАИМОДЕЙСТВИЯ GUI ↔ VALVE CONTROL")
    print("=" * 60)
    
    try:
        # Импорты
        from data_manager.core_system import (
            start_core_system, 
            set_temperature_settings, 
            get_temperature_settings,
            stop_core_system,
            is_core_system_running
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
        
        # 2. Установка начальных настроек
        print("2️⃣ Установка начальных настроек...")
        if not set_temperature_settings(max_temp=55.0, min_temp=45.0, source_module="test_initial"):
            print("❌ Не удалось установить начальные настройки")
            return False
        
        settings = get_temperature_settings()
        print(f"✅ Начальные настройки: {settings['min_temperature']:.1f}°C - {settings['max_temperature']:.1f}°C")
        
        # 3. Запуск valve системы
        print("3️⃣ Запуск valve control...")
        if not start_temperature_data_provider(update_interval=1.0):
            print("❌ Не удалось запустить valve provider")
            return False
        
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
        
        if not valve_controller.sync_temperature_settings_with_data_manager():
            print("❌ Не удалось синхронизировать настройки")
            return False
        
        # Запуск контроллера
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
        
        if not controller_running.wait(timeout=5):
            print("❌ Контроллер не запустился")
            return False
        
        print("✅ Valve control запущен")
        
        # 4. Симуляция изменений через GUI
        print("4️⃣ Симуляция изменений настроек через GUI...")
        print("=" * 60)
        
        test_cases = [
            {"max_temp": 47.0, "min_temp": 45.0, "source": "gui_test_1"},
            {"max_temp": 46.5, "min_temp": 44.5, "source": "gui_test_2"},
            {"max_temp": 48.5, "min_temp": 46.5, "source": "gui_test_3"},
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🔄 ТЕСТ {i}: Изменение настроек на {test_case['min_temp']:.1f}°C - {test_case['max_temp']:.1f}°C")
            
            # Изменяем настройки (симуляция GUI)
            success = set_temperature_settings(
                max_temp=test_case['max_temp'],
                min_temp=test_case['min_temp'],
                source_module=test_case['source']
            )
            
            if not success:
                print(f"❌ Не удалось установить настройки для теста {i}")
                continue
            
            print(f"✅ Настройки изменены через GUI-симуляцию")
            
            # Ждем и проверяем как система реагирует
            for check_round in range(10):  # 10 секунд наблюдения
                time.sleep(1)
                
                # Проверяем что data_manager видит изменения
                current_settings = get_temperature_settings()
                if current_settings:
                    dm_min = current_settings['min_temperature']
                    dm_max = current_settings['max_temperature']
                else:
                    print("❌ Data manager не возвращает настройки")
                    continue
                
                # Проверяем что valve_controller видит изменения
                valve_status = valve_controller.get_status()
                vc_min = valve_status.get('min_temperature', 0.0)
                vc_max = valve_status.get('max_temperature', 0.0)
                
                # Получаем текущую температуру
                temp = get_temperature_for_valve_controller()
                cooling_active = valve_controller.is_cooling_active()
                
                # Логируем состояние каждые 3 секунды
                if check_round % 3 == 0:
                    print(f"   🕐 +{check_round+1}с:")
                    print(f"     📊 Data Manager: {dm_min:.1f}°C - {dm_max:.1f}°C")
                    print(f"     🔧 Valve Control: {vc_min:.1f}°C - {vc_max:.1f}°C")
                    print(f"     🌡️  Температура: {temp:.1f}°C, охлаждение={'ВКЛ' if cooling_active else 'ВЫКЛ'}")
                    
                    # Проверка синхронизации
                    if abs(dm_min - vc_min) > 0.01 or abs(dm_max - vc_max) > 0.01:
                        print(f"     🚨 РАССИНХРОНИЗАЦИЯ: DM({dm_min:.1f}-{dm_max:.1f}) ≠ VC({vc_min:.1f}-{vc_max:.1f})")
                    else:
                        print(f"     ✅ Настройки синхронизированы")
                    
                    # Проверка логики регулирования
                    if temp >= vc_max and not cooling_active:
                        print(f"     🚨 ПРОБЛЕМА: T≥max, но охлаждение ВЫКЛ")
                    elif temp <= vc_min and cooling_active:
                        print(f"     🚨 ПРОБЛЕМА: T≤min, но охлаждение ВКЛ")
                    else:
                        print(f"     ✅ Логика регулирования корректна")
        
        print("\n5️⃣ Финальная проверка стабильности...")
        
        # Финальная проверка в течение 15 секунд
        for final_check in range(15):
            temp = get_temperature_for_valve_controller()
            settings = get_temperature_settings()
            cooling_active = valve_controller.is_cooling_active()
            
            if settings and temp is not None:
                min_temp = settings['min_temperature']
                max_temp = settings['max_temperature']
                
                if final_check % 5 == 0:
                    status_icon = "🔥" if cooling_active else "❄️"
                    print(f"   {status_icon} T={temp:.1f}°C, пороги=[{min_temp:.1f}-{max_temp:.1f}°C], "
                          f"охлаждение={'ВКЛ' if cooling_active else 'ВЫКЛ'}")
                    
                    # Критическая проверка
                    if not cooling_active and temp >= max_temp:
                        print(f"   🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: Не включается при T≥{max_temp:.1f}°C!")
            
            time.sleep(1)
        
        print("\n6️⃣ Остановка системы...")
        valve_controller.stop()
        stop_core_system()
        print("✅ Тест завершен")
        
        return True
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = test_gui_valve_interaction()
        if success:
            print("\n✅ Тест взаимодействия GUI-Valve завершен")
        else:
            print("\n❌ Тест выявил проблемы")
    except KeyboardInterrupt:
        print("\n\n⏹️ Тест прерван пользователем")
    except Exception as e:
        print(f"\n❌ Непредвиденная ошибка: {e}") 