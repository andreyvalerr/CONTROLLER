#!/usr/bin/env python3
"""
Специальный тест для воспроизведения проблемы с одним циклом охлаждения
"""

import time
import sys
import os
import threading
from datetime import datetime

# Добавляем пути
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_single_cycle_problem():
    """Тест проблемы с одним циклом"""
    
    print("🔍 ТЕСТ ПРОБЛЕМЫ 'ОДИН ЦИКЛ И СТОП'")
    print("=" * 50)
    
    try:
        # Импорты
        from data_manager.core_system import (
            start_core_system, 
            set_temperature_settings, 
            get_temperature_settings,
            stop_core_system
        )
        from valve_control.data_manager_integration import (
            start_temperature_data_provider,
            get_temperature_for_valve_controller
        )
        from valve_control.valve_controller import ValveController, ValveControllerConfig
        from valve_control.config import load_config_from_env
        
        # 1. Запуск системы
        print("1️⃣ Запуск системы...")
        if not start_core_system(temperature_ip="192.168.0.127", temperature_update_interval=1.0):
            return False
        print("✅ Data manager запущен")
        time.sleep(2)
        
        # 2. Установка агрессивных порогов для быстрого тестирования
        current_temp = get_temperature_for_valve_controller() if get_temperature_for_valve_controller else 48.0
        
        # Устанавливаем пороги так, чтобы сразу включилось охлаждение
        max_temp = current_temp - 1.0  # На 1 градус ниже текущей
        min_temp = current_temp - 3.0  # На 3 градуса ниже текущей
        
        print(f"2️⃣ Установка тестовых порогов: {min_temp:.1f}°C - {max_temp:.1f}°C (текущая: {current_temp:.1f}°C)")
        if not set_temperature_settings(max_temp=max_temp, min_temp=min_temp, source_module="cycle_test"):
            return False
        
        # 3. Запуск valve control
        print("3️⃣ Запуск valve control...")
        if not start_temperature_data_provider(update_interval=1.0):
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
            return False
        
        # Запуск в потоке
        controller_running = threading.Event()
        
        def run_controller():
            try:
                if valve_controller.start():
                    controller_running.set()
                    valve_controller.run_forever()
            except Exception as e:
                print(f"❌ Ошибка контроллера: {e}")
        
        controller_thread = threading.Thread(target=run_controller, daemon=True)
        controller_thread.start()
        
        if not controller_running.wait(timeout=5):
            print("❌ Контроллер не запустился")
            return False
        
        print("✅ Valve control запущен")
        
        # 4. Мониторинг циклов охлаждения
        print("4️⃣ Мониторинг циклов охлаждения...")
        print("=" * 50)
        
        cooling_cycles = []
        last_cooling_state = False
        cycle_count = 0
        
        for monitor_round in range(120):  # 2 минуты мониторинга
            try:
                temp = get_temperature_for_valve_controller()
                cooling_active = valve_controller.is_cooling_active()
                settings = get_temperature_settings()
                
                if temp is None or not settings:
                    continue
                
                min_temp = settings['min_temperature']
                max_temp = settings['max_temperature']
                
                # Отслеживание смены состояния охлаждения
                if cooling_active != last_cooling_state:
                    if cooling_active:
                        cycle_count += 1
                        cycle_start = {
                            'cycle': cycle_count,
                            'start_time': datetime.now().strftime('%H:%M:%S'),
                            'start_temp': temp,
                            'max_temp': max_temp,
                            'min_temp': min_temp
                        }
                        cooling_cycles.append(cycle_start)
                        print(f"🔥 ЦИКЛ {cycle_count} НАЧАТ: T={temp:.1f}°C при пороге {max_temp:.1f}°C")
                    else:
                        if cooling_cycles:
                            last_cycle = cooling_cycles[-1]
                            last_cycle['end_time'] = datetime.now().strftime('%H:%M:%S')
                            last_cycle['end_temp'] = temp
                            print(f"❄️ ЦИКЛ {cycle_count} ЗАВЕРШЕН: T={temp:.1f}°C при пороге {min_temp:.1f}°C")
                    
                    last_cooling_state = cooling_active
                
                # Логирование каждые 5 секунд
                if monitor_round % 5 == 0:
                    status = "🔥 ВКЛ" if cooling_active else "❄️ ВЫКЛ"
                    print(f"   [{monitor_round//5+1:2d}] T={temp:.1f}°C, пороги=[{min_temp:.1f}-{max_temp:.1f}°C], охлаждение={status}")
                    
                    # Проверка на проблему
                    if not cooling_active and temp >= max_temp:
                        print(f"   🚨 ПРОБЛЕМА: T={temp:.1f}°C >= {max_temp:.1f}°C, но охлаждение НЕ ВКЛЮЧАЕТСЯ!")
                
                # Симуляция изменения настроек в середине теста (как от GUI)
                if monitor_round == 60:  # Через минуту
                    print("\n🔄 СИМУЛЯЦИЯ ИЗМЕНЕНИЯ НАСТРОЕК GUI...")
                    new_max = current_temp - 0.5  # Еще более агрессивный порог
                    new_min = current_temp - 2.5
                    
                    success = set_temperature_settings(
                        max_temp=new_max,
                        min_temp=new_min, 
                        source_module="gui_simulation"
                    )
                    if success:
                        print(f"✅ Новые пороги: {new_min:.1f}°C - {new_max:.1f}°C")
                    else:
                        print("❌ Не удалось изменить настройки")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Ошибка мониторинга: {e}")
                break
        
        # 5. Анализ результатов
        print("\n5️⃣ АНАЛИЗ РЕЗУЛЬТАТОВ:")
        print("=" * 50)
        
        if not cooling_cycles:
            print("❌ НЕ БЫЛО НИ ОДНОГО ЦИКЛА ОХЛАЖДЕНИЯ!")
        else:
            print(f"✅ Обнаружено {len(cooling_cycles)} циклов охлаждения:")
            for cycle in cooling_cycles:
                start_time = cycle.get('start_time', '?')
                end_time = cycle.get('end_time', 'НЕ ЗАВЕРШЕН')
                start_temp = cycle.get('start_temp', 0)
                end_temp = cycle.get('end_temp', '?')
                
                print(f"   Цикл {cycle['cycle']}: {start_time}-{end_time}, T: {start_temp:.1f}°C -> {end_temp}")
        
        # Проверка проблемы
        if len(cooling_cycles) == 1 and 'end_time' in cooling_cycles[0]:
            print("\n🚨 ОБНАРУЖЕНА ПРОБЛЕМА: ТОЛЬКО ОДИН ЦИКЛ И ОСТАНОВКА!")
        elif len(cooling_cycles) > 1:
            print("\n✅ Система работает циклически - проблема НЕ воспроизведена")
        
        print("\n6️⃣ Остановка...")
        valve_controller.stop()
        stop_core_system()
        
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = test_single_cycle_problem()
        if success:
            print("\n✅ Тест завершен")
        else:
            print("\n❌ Тест завершился с ошибкой")
    except KeyboardInterrupt:
        print("\n\n⏹️ Тест прерван")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}") 