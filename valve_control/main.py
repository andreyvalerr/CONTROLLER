#!/usr/bin/env python3
"""
Главный исполняемый файл контроллера клапанов
Запуск автоматического регулирования температуры криптокотла
"""

import argparse
import sys
import os
import json
from typing import Optional

from .valve_controller import ValveController, ValveControllerConfig
from .config import (
    RelayConfig, TemperatureConfig, MonitoringConfig, SafetyConfig,
    load_config_from_env, validate_config
)
from .data_manager_integration import (
    get_temperature_for_valve_controller,
    start_temperature_data_provider,
    stop_temperature_data_provider,
    get_temperature_provider_statistics,
    is_temperature_provider_running,
    get_temperature_settings_for_valve_controller,
    set_temperature_settings_from_valve_controller,
    is_temperature_settings_available
)

def load_config_from_file(config_file: str) -> Optional[ValveControllerConfig]:
    """
    Загрузка конфигурации из JSON файла
    
    Args:
        config_file: Путь к файлу конфигурации
        
    Returns:
        ValveControllerConfig: Конфигурация или None при ошибке
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        relay_config = RelayConfig(**data.get('relay', {}))
        temp_config = TemperatureConfig(**data.get('temperature', {}))
        monitoring_config = MonitoringConfig(**data.get('monitoring', {}))
        safety_config = SafetyConfig(**data.get('safety', {}))
        
        return ValveControllerConfig(
            relay_config=relay_config,
            temperature_config=temp_config,
            monitoring_config=monitoring_config,
            safety_config=safety_config
        )
        
    except Exception as e:
        print(f"Ошибка загрузки конфигурации из файла {config_file}: {e}")
        return None

def save_default_config(config_file: str):
    """
    Сохранение конфигурации по умолчанию в файл
    
    Args:
        config_file: Путь к файлу для сохранения
    """
    relay_config, temp_config, monitoring_config, safety_config = load_config_from_env()
    
    config_data = {
        "relay": {
            "relay_pin": relay_config.relay_pin,
            "gpio_mode": relay_config.gpio_mode,
            "relay_on_state": relay_config.relay_on_state,
            "relay_off_state": relay_config.relay_off_state,
            "enable_warnings": relay_config.enable_warnings,
            "cleanup_on_exit": relay_config.cleanup_on_exit
        },
        "temperature": {
            "max_temperature": temp_config.max_temperature,
            "min_temperature": temp_config.min_temperature,
            "critical_max_temp": temp_config.critical_max_temp,
            "emergency_temp": temp_config.emergency_temp,
            "hysteresis": temp_config.hysteresis,
            "temperature_timeout": temp_config.temperature_timeout,
            "control_interval": temp_config.control_interval
        },
        "monitoring": {
            "asic_ip": monitoring_config.asic_ip,
            "update_interval": monitoring_config.update_interval,
            "log_level": monitoring_config.log_level,
            "log_file": monitoring_config.log_file,
            "enable_console_log": monitoring_config.enable_console_log,
            "enable_statistics": monitoring_config.enable_statistics,
            "stats_interval": monitoring_config.stats_interval
        },
        "safety": {
            "max_cooling_time": safety_config.max_cooling_time,
            "min_cycle_time": safety_config.min_cycle_time,
            "max_switches_per_hour": safety_config.max_switches_per_hour,
            "emergency_timeout": safety_config.emergency_timeout
        }
    }
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        print(f"Конфигурация по умолчанию сохранена в {config_file}")
    except Exception as e:
        print(f"Ошибка сохранения конфигурации: {e}")

def print_status(controller: ValveController):
    """
    Вывод статуса контроллера
    
    Args:
        controller: Контроллер клапанов
    """
    status = controller.get_status()
    
    print("\n=== СТАТУС КОНТРОЛЛЕРА КЛАПАНОВ ===")
    
    # Общий статус
    controller_status = status.get('controller', {})
    print(f"Работает: {'да' if controller_status.get('is_running') else 'нет'}")
    
    # Температура
    temp_status = status.get('temperature', {})
    current_temp = temp_status.get('current')
    if current_temp is not None:
        print(f"Текущая температура: {current_temp}°C")
    else:
        print("Температура: недоступна")
    
    # Статистика поставщика температурных данных
    temp_provider_stats = get_temperature_provider_statistics()
    if temp_provider_stats.get('is_running'):
        print(f"Data Manager интеграция: активна")
        print(f"Обновлений температуры: {temp_provider_stats.get('successful_updates', 0)}")
        print(f"Успешность: {temp_provider_stats.get('success_rate', 0):.1f}%")
        if temp_provider_stats.get('data_fresh'):
            print(f"Данные: свежие")
        else:
            print(f"Данные: устаревшие")
    else:
        print("Data Manager интеграция: неактивна")
    
    # Охлаждение
    regulator_status = status.get('regulator', {})
    cooling_active = regulator_status.get('cooling_active', False)
    print(f"Охлаждение: {'включено' if cooling_active else 'выключено'}")
    
    # Состояние регулятора
    reg_state = regulator_status.get('state', 'unknown')
    print(f"Состояние регулятора: {reg_state}")
    
    # Статистика
    total_cycles = regulator_status.get('total_cycles', 0)
    cooling_cycles = regulator_status.get('cooling_cycles', 0)
    print(f"Циклов регулирования: {total_cycles}")
    print(f"Циклов охлаждения: {cooling_cycles}")
    
    # Конфигурация
    config_status = status.get('config', {})
    print(f"Пороги температуры: {config_status.get('min_temp')}°C - {config_status.get('max_temp')}°C")
    print(f"GPIO пин: {config_status.get('gpio_pin')}")
    print(f"IP асика: {config_status.get('asic_ip')}")
    
    print("==================================")

def initialize_temperature_settings_from_data_manager() -> bool:
    """
    Проверка наличия настроек температуры в data_manager
    ТРЕБУЕТ обязательного наличия настроек - НЕ создает значения по умолчанию
    
    Returns:
        bool: True если настройки доступны в data_manager
    """
    try:
        print("Проверка настроек температуры в data_manager...")
        
        if is_temperature_settings_available():
            settings = get_temperature_settings_for_valve_controller()
            if settings:
                print(f"✅ Настройки температуры найдены в data_manager: "
                      f"{settings.get('min_temperature')}°C - {settings.get('max_temperature')}°C")
                return True
            else:
                print("❌ ОШИБКА: Настройки температуры повреждены в data_manager")
                return False
        else:
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: Настройки температуры отсутствуют в data_manager")
            print("❌ Модуль valve_control не может работать без настроек температуры")
            print("❌ Установите настройки температуры в data_manager перед запуском")
            return False
            
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА проверки настроек температуры: {e}")
        return False

def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description="Контроллер клапанов для управления температурой криптокотла",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s                           # Запуск с конфигурацией по умолчанию
  %(prog)s --config config.json      # Запуск с конфигурацией из файла
  %(prog)s --status                  # Показать статус и выйти
  %(prog)s --save-config config.json # Сохранить конфигурацию по умолчанию
  %(prog)s --max-temp 45             # Установить максимальную температуру
  %(prog)s --gpio-pin 18             # Использовать GPIO 18
  %(prog)s --asic-ip 192.168.1.100   # IP адрес асика

Переменные окружения:
  RELAY_PIN=17                       # GPIO пин реле
  MAX_TEMP=40.0                      # Максимальная температура
  MIN_TEMP=35.0                      # Минимальная температура
  ASIC_IP=192.168.0.127              # IP адрес асика
  LOG_LEVEL=INFO                     # Уровень логирования
  LOG_FILE=/var/log/valve_control.log # Файл логов
        """
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Файл конфигурации JSON"
    )
    
    parser.add_argument(
        "--save-config",
        type=str,
        help="Сохранить конфигурацию по умолчанию в файл и выйти"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Показать статус контроллера и выйти"
    )
    
    parser.add_argument(
        "--max-temp",
        type=float,
        help="Максимальная температура для включения охлаждения"
    )
    
    parser.add_argument(
        "--min-temp",
        type=float,
        help="Минимальная температура для выключения охлаждения"
    )
    
    parser.add_argument(
        "--gpio-pin",
        type=int,
        help="GPIO пин для реле"
    )
    
    parser.add_argument(
        "--asic-ip",
        type=str,
        help="IP адрес асика"
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        help="Файл для логирования"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Уровень логирования"
    )
    
    args = parser.parse_args()
    
    # Сохранение конфигурации по умолчанию
    if args.save_config:
        save_default_config(args.save_config)
        return 0
    
    # Загрузка конфигурации
    if args.config:
        config = load_config_from_file(args.config)
        if config is None:
            return 1
    else:
        # Конфигурация из переменных окружения
        relay_config, temp_config, monitoring_config, safety_config = load_config_from_env()
        config = ValveControllerConfig(
            relay_config=relay_config,
            temperature_config=temp_config,
            monitoring_config=monitoring_config,
            safety_config=safety_config
        )
    
    # Переопределение параметров из командной строки
    if args.max_temp is not None:
        config.temperature_config.max_temperature = args.max_temp
    
    if args.min_temp is not None:
        config.temperature_config.min_temperature = args.min_temp
    
    if args.gpio_pin is not None:
        config.relay_config.relay_pin = args.gpio_pin
    
    if args.asic_ip is not None:
        config.monitoring_config.asic_ip = args.asic_ip
    
    if args.log_file is not None:
        config.monitoring_config.log_file = args.log_file
    
    if args.log_level is not None:
        config.monitoring_config.log_level = args.log_level
    
    # Валидация конфигурации
    errors = validate_config(config.relay_config, config.temperature_config)
    if errors:
        print("Ошибки конфигурации:")
        for error in errors:
            print(f"  - {error}")
        return 1
    
    # Создание контроллера
    try:
        # Запуск поставщика температурных данных
        print("Запуск интеграции с data_manager...")
        if not start_temperature_data_provider(update_interval=1.0):
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось запустить интеграцию с data_manager")
            print("❌ Модуль valve_control не может работать без data_manager")
            return 1
        else:
            print("✅ Интеграция с data_manager запущена успешно")
            
            # Проверка настроек температуры в data_manager
            if not initialize_temperature_settings_from_data_manager():
                print("❌ КРИТИЧЕСКАЯ ОШИБКА: Настройки температуры недоступны")
                print("❌ Завершение работы модуля")
                stop_temperature_data_provider()
                return 1
        
        controller = ValveController(
            temperature_callback=get_temperature_for_valve_controller,
            config=config
        )
        
        # Синхронизация настроек температуры с data_manager
        print("Синхронизация настроек температуры с data_manager...")
        if not controller.sync_temperature_settings_with_data_manager():
            print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось синхронизировать настройки температуры")
            print("❌ Завершение работы модуля")
            stop_temperature_data_provider()
            return 1
        else:
            print("✅ Синхронизация настроек температуры завершена успешно")
    except Exception as e:
        print(f"Ошибка создания контроллера: {e}")
        stop_temperature_data_provider()
        return 1
    
    # Показать статус и выйти
    if args.status:
        if not controller.start():
            print("Не удалось запустить контроллер для получения статуса")
            return 1
        
        print_status(controller)
        controller.stop()
        stop_temperature_data_provider()
        return 0
    
    # Запуск контроллера
    try:
        print("Запуск контроллера клапанов...")
        print("Получение температуры каждую секунду через data_manager")
        print("Нажмите Ctrl+C для остановки")
        
        success = controller.run_forever()
        return 0 if success else 1
        
    except Exception as e:
        print(f"Ошибка выполнения: {e}")
        return 1
    finally:
        # Остановка поставщика данных при завершении
        stop_temperature_data_provider()

if __name__ == "__main__":
    sys.exit(main()) 