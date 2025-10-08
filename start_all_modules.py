#!/usr/bin/env python3
"""
Скрипт запуска всех модулей системы контроллера криптокотла
Запускает data_manager, get_temperature_from_asic, valve_control и GUI интерфейс
"""

import os
import sys
import time
import threading
from datetime import datetime
from collections import deque

# Глобальная переменная для valve controller
valve_controller_instance = None
_rolling_log_thread = None
_rolling_log_stop = threading.Event()
_rolling_log_buffer = deque(maxlen=120)

# Добавляем пути к модулям
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'data_manager'))
sys.path.append(os.path.join(current_dir, 'get_temperature_from_asic'))
sys.path.append(os.path.join(current_dir, 'valve_control'))
sys.path.append(os.path.join(current_dir, 'gui_interface'))

def start_data_manager():
    """Запуск data_manager core system"""
    try:
        print("[ЗАПУСК] Инициализация data_manager...")
        from data_manager.core_system import start_core_system, is_core_system_running
        
        if not is_core_system_running():
            success = start_core_system(temperature_ip="192.168.0.127", temperature_update_interval=1.0)
            if success:
                print("✅ Data Manager запущен успешно")
                return True
            else:
                print("❌ Ошибка запуска Data Manager")
                return False
        else:
            print("✅ Data Manager уже запущен")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при запуске data_manager: {e}")
        return False

def start_valve_control():
    """Запуск valve_control в отдельном потоке"""
    try:
        print("[ЗАПУСК] Инициализация valve_control...")
        from valve_control.data_manager_integration import (
            start_temperature_data_provider,
            is_temperature_provider_running,
            get_temperature_for_valve_controller,
            is_temperature_settings_available,
            register_valve_controller_instance,
            initialize_mode_from_settings,
            start_mode_cooling_listener,
            stop_mode_cooling_listener
        )
        from valve_control.valve_controller import ValveController, ValveControllerConfig
        from valve_control.config import load_config_from_env
        
        # Запуск интеграции с data_manager
        if not is_temperature_provider_running():
            success = start_temperature_data_provider(update_interval=1.0)
            if not success:
                print("❌ Ошибка запуска интеграции Valve Control с data_manager")
                return False
            print("✅ Интеграция Valve Control с data_manager запущена")
        else:
            print("✅ Интеграция Valve Control с data_manager уже запущена")
        
        # Проверка настроек температуры
        if not is_temperature_settings_available():
            print("❌ Настройки температуры недоступны для valve_control")
            return False
        
        # Создание конфигурации для контроллера
        relay_config, temp_config, monitoring_config, safety_config = load_config_from_env()
        config = ValveControllerConfig(
            relay_config=relay_config,
            temperature_config=temp_config,
            monitoring_config=monitoring_config,
            safety_config=safety_config
        )
        
        # Создание и запуск valve controller
        global valve_controller_instance
        valve_controller_instance = ValveController(
            temperature_callback=get_temperature_for_valve_controller,
            config=config
        )
        # Регистрируем инстанс для внешнего управления (GUI)
        register_valve_controller_instance(valve_controller_instance)
        
        # Синхронизация настроек температуры с data_manager
        if not valve_controller_instance.sync_temperature_settings_with_data_manager():
            print("❌ Не удалось синхронизировать настройки температуры")
            return False
        
        # Запуск контроллера в отдельном потоке
        def run_valve_controller():
            try:
                valve_controller_instance.run_forever()
            except Exception as e:
                print(f"❌ Ошибка в valve_controller: {e}")
        
        valve_thread = threading.Thread(target=run_valve_controller, daemon=True)
        valve_thread.start()

        # Фоновая инициализация режима после старта контроллера и запуск listener
        def apply_mode_when_ready():
            try:
                for _ in range(50):  # до ~10 секунд ожидания
                    try:
                        if valve_controller_instance and valve_controller_instance.is_running():
                            initialize_mode_from_settings()
                            # Запускаем listener режима/охлаждения
                            try:
                                start_mode_cooling_listener()
                            except Exception:
                                pass
                            return
                    except Exception:
                        pass
                    time.sleep(0.2)
            except Exception:
                pass

        threading.Thread(target=apply_mode_when_ready, daemon=True).start()
        
        print("✅ Valve Controller запущен и работает")
        return True
            
    except Exception as e:
        print(f"❌ Ошибка при запуске valve_control: {e}")
        return False

def _ensure_logs_dir() -> str:
    """Гарантированно создаёт директорию логов и возвращает путь."""
    logs_dir = os.path.join(current_dir, 'logs')
    try:
        os.makedirs(logs_dir, exist_ok=True)
    except Exception:
        pass
    return logs_dir

def _get_snapshot_line() -> str:
    """Формирует строку: "HH:MM:SS, уставка 45.0-55.0, текущая темп. 49.6, охл. ВКЛ., нагр. ВЫКЛ.""" 
    ts = datetime.now().strftime('%H:%M:%S')
    temp = None
    upper_on = False
    lower_on = False
    set_min = None
    set_max = None

    try:
        # Температура: сначала пробуем через valve_controller_instance (быстрее и синхронно)
        global valve_controller_instance
        if valve_controller_instance is not None and valve_controller_instance.is_running():
            try:
                temp = valve_controller_instance.get_current_temperature()
            except Exception:
                temp = None

            try:
                upper_on = bool(valve_controller_instance.relay_controller.get_relay_state())
            except Exception:
                upper_on = False
            try:
                lower_on = bool(valve_controller_instance.relay_controller_low.get_relay_state())
            except Exception:
                lower_on = False
        else:
            # Резерв: берём температуру из data_manager
            try:
                from data_manager.core_system import get_temperature_data
                temp = get_temperature_data()
            except Exception:
                temp = None
            # Если контроллер не активен, считаем клапаны выключенными
            upper_on = False
            lower_on = False
        # Уставки стараемся взять из работающего регулятора
        try:
            if valve_controller_instance is not None and valve_controller_instance.is_running():
                cfg = valve_controller_instance.temperature_regulator.config
                set_min = getattr(cfg, 'min_temperature', None)
                set_max = getattr(cfg, 'max_temperature', None)
        except Exception:
            set_min = None
            set_max = None
        # Если нет уставок из контроллера — берём из data_manager
        if set_min is None or set_max is None:
            try:
                from data_manager.core_system import get_temperature_settings
                settings = get_temperature_settings()
                if settings:
                    set_min = settings.get('min_temperature', set_min)
                    set_max = settings.get('max_temperature', set_max)
            except Exception:
                pass
    except Exception:
        pass

    # Человекочитаемая строка
    if temp is None:
        temp_part = "текущая темп. н/д"
    else:
        temp_part = f"текущая темп. {float(temp):.1f}"
    if set_min is not None and set_max is not None:
        set_part = f"уставка {float(set_min):.1f}-{float(set_max):.1f}"
    else:
        set_part = "уставка н/д"
    cooling_part = f"охл. {'ВКЛ.' if upper_on else 'ВЫКЛ.'}"
    heating_part = f"нагр. {'ВКЛ.' if lower_on else 'ВЫКЛ.'}"
    return f"{ts}, {set_part}, {temp_part}, {cooling_part}, {heating_part}"

def _write_rolling_snapshot(lines: list[str]):
    """Атомарно записывает снапшот из последних строк в rolling.log."""
    logs_dir = _ensure_logs_dir()
    target = os.path.join(logs_dir, 'rolling.log')
    tmp = target + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line + '\n')
        os.replace(tmp, target)
    except Exception:
        # В случае ошибки просто игнорируем, чтобы не тормозить основной цикл
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

def _rolling_logger_loop(stop_event: threading.Event):
    """Фоновый цикл: каждую секунду добавляет запись и перезаписывает файл снапшотом."""
    while not stop_event.is_set():
        try:
            line = _get_snapshot_line()
            _rolling_log_buffer.append(line)
            # Снимок текущего буфера
            _write_rolling_snapshot(list(_rolling_log_buffer))
        except Exception:
            pass
        # Ожидание 1 секунду с возможностью досрочной остановки
        stop_event.wait(1.0)

def start_rolling_logger():
    """Запускает фоновый rolling-логгер (120 последних секунд)."""
    global _rolling_log_thread, _rolling_log_stop
    if _rolling_log_thread is not None and _rolling_log_thread.is_alive():
        return
    _rolling_log_stop.clear()
    _rolling_log_thread = threading.Thread(target=_rolling_logger_loop, args=(_rolling_log_stop,), daemon=True)
    _rolling_log_thread.start()

def stop_rolling_logger():
    """Останавливает фоновый rolling-логгер."""
    global _rolling_log_thread, _rolling_log_stop
    try:
        _rolling_log_stop.set()
        if _rolling_log_thread is not None and _rolling_log_thread.is_alive():
            _rolling_log_thread.join(timeout=3.0)
    except Exception:
        pass

def start_gui():
    """Запуск GUI интерфейса"""
    try:
        print("[ЗАПУСК] Инициализация GUI интерфейса...")
        from gui_interface.main_gui import TemperatureControllerGUI
        
        app = TemperatureControllerGUI()
        print("✅ GUI интерфейс запущен")
        app.run()  # Блокирующий вызов
        
    except Exception as e:
        print(f"❌ Ошибка при запуске GUI: {e}")
        return False

def setup_temperature_settings():
    """Установка базовых настроек температуры если их нет"""
    try:
        from data_manager.core_system import (
            is_temperature_settings_available,
            set_temperature_settings,
            get_temperature_settings
        )
        
        if not is_temperature_settings_available():
            print("[НАСТРОЙКА] Устанавливаю настройки температуры по умолчанию...")
            success = set_temperature_settings(
                max_temp=55.0,
                min_temp=45.0,
                source_module="startup_script"
            )
            if success:
                print("✅ Настройки температуры установлены: 45.0°C - 55.0°C")
            else:
                print("❌ Не удалось установить настройки температуры")
                return False
        else:
            settings = get_temperature_settings()
            print(f"✅ Настройки температуры: {settings['min_temperature']:.1f}°C - {settings['max_temperature']:.1f}°C")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при настройке температуры: {e}")
        return False

def main():
    """Главная функция запуска системы"""
    print("=" * 50)
    print("КОНТРОЛЛЕР КРИПТОКОТЛА - ЗАПУСК СИСТЕМЫ")
    print("=" * 50)
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Последовательный запуск модулей
    modules_started = 0
    total_modules = 4
    
    # 1. Запуск data_manager (основа системы)
    if start_data_manager():
        modules_started += 1
        time.sleep(2)  # Даем время для инициализации
    else:
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось запустить data_manager")
        print("❌ Система не может работать без data_manager")
        return 1
    
    # 2. Настройка температурных параметров
    if setup_temperature_settings():
        time.sleep(1)
    else:
        print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Проблемы с настройками температуры")
        print("⚠️ Система может работать некорректно")
    
    # 3. Запуск valve_control
    if start_valve_control():
        modules_started += 1
        time.sleep(1)
    else:
        print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Не удалось запустить valve_control")
        print("⚠️ Регулирование температуры будет недоступно")
    
    print()
    print("=" * 50)
    print(f"СИСТЕМА ГОТОВА К РАБОТЕ ({modules_started}/{total_modules} модулей)")
    print("=" * 50)
    print("Модули:")
    print("✅ Data Manager        - Сбор и хранение данных")
    if modules_started >= 2:
        print("✅ Valve Control       - Регулирование температуры") 
    else:
        print("❌ Valve Control       - Недоступен")
    print("🔄 Temperature Monitor - Автоматический")
    print("🖥️ GUI Interface       - Запускается...")
    print()
    print("Для остановки системы нажмите Ctrl+C")
    print("=" * 50)
    print()
    
    # 4. Запуск rolling-логгера (буфер 120 секунд)
    try:
        start_rolling_logger()
        print("✅ Rolling логгер запущен (logs/rolling.log)")
    except Exception as e:
        print(f"⚠️ Не удалось запустить rolling логгер: {e}")
    
    # 5. Запуск GUI (блокирующий)
    try:
        start_gui()
    except KeyboardInterrupt:
        print("\n\n[ОСТАНОВКА] Получен сигнал прерывания...")
    except Exception as e:
        print(f"\n\n[ОШИБКА] Критическая ошибка GUI: {e}")
    
    # Остановка всех модулей
    print("\n[ОСТАНОВКА] Завершение работы системы...")
    
    try:
        # Остановка valve controller
        global valve_controller_instance
        if valve_controller_instance:
            valve_controller_instance.stop()
            print("✅ Valve Controller остановлен")
    except:
        pass
    
    try:
        from data_manager.core_system import stop_core_system
        stop_core_system()
        print("✅ Data Manager остановлен")
    except:
        pass
    
    try:
        from valve_control.data_manager_integration import stop_temperature_data_provider
        stop_temperature_data_provider()
        print("✅ Valve Control интеграция остановлена")
    except:
        pass

    try:
        from valve_control.data_manager_integration import stop_mode_cooling_listener
        stop_mode_cooling_listener()
        print("✅ Valve Control listener режима/охлаждения остановлен")
    except:
        pass
    
    # Остановка rolling-логгера
    try:
        stop_rolling_logger()
        print("✅ Rolling логгер остановлен")
    except Exception:
        pass
    
    print("✅ Система остановлена")
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        sys.exit(1) 