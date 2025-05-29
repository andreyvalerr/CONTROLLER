#!/usr/bin/env python3
"""
Утилита ручного управления клапанами
Позволяет управлять реле через командную строку
"""

import argparse
import sys
import time
import logging
from typing import Optional

from .relay_controller import RelayController
from .config import RelayConfig, DEFAULT_RELAY_CONFIG

def setup_logging(verbose: bool = False):
    """Настройка логирования"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def manual_valve_control(action: str, 
                        gpio_pin: Optional[int] = None,
                        duration: Optional[float] = None,
                        verbose: bool = False) -> bool:
    """
    Ручное управление клапанами
    
    Args:
        action: Действие (on/off/toggle/test/status)
        gpio_pin: GPIO пин реле (если None, используется значение по умолчанию)
        duration: Длительность для действия test (секунды)
        verbose: Подробный вывод
        
    Returns:
        bool: True если операция успешна
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    
    # Конфигурация реле
    config = RelayConfig()
    if gpio_pin is not None:
        config.relay_pin = gpio_pin
    
    logger.info(f"Использование GPIO пин {config.relay_pin}")
    
    try:
        with RelayController(config) as relay:
            if not relay.is_initialized():
                logger.error("Не удалось инициализировать GPIO")
                return False
            
            if action == "on":
                logger.info("Включение реле (охлаждения)")
                result = relay.turn_on()
                if result:
                    logger.info("Реле включено")
                else:
                    logger.error("Не удалось включить реле")
                return result
            
            elif action == "off":
                logger.info("Выключение реле (охлаждения)")
                result = relay.turn_off()
                if result:
                    logger.info("Реле выключено")
                else:
                    logger.error("Не удалось выключить реле")
                return result
            
            elif action == "toggle":
                current_state = relay.get_relay_state()
                logger.info(f"Переключение реле (текущее состояние: {'включено' if current_state else 'выключено'})")
                result = relay.toggle()
                new_state = relay.get_relay_state()
                if result:
                    logger.info(f"Реле переключено на: {'включено' if new_state else 'выключено'}")
                else:
                    logger.error("Не удалось переключить реле")
                return result
            
            elif action == "test":
                test_duration = duration or 2.0
                logger.info(f"Тестирование реле на {test_duration} секунд")
                result = relay.test_relay(test_duration)
                if result:
                    logger.info("Тест реле завершен успешно")
                else:
                    logger.error("Тест реле завершился с ошибкой")
                return result
            
            elif action == "status":
                logger.info("Получение статуса реле")
                stats = relay.get_statistics()
                
                print("\n=== СТАТУС РЕЛЕ ===")
                print(f"Состояние: {'включено' if stats['relay_state'] else 'выключено'}")
                print(f"GPIO пин: {stats['gpio_pin']}")
                print(f"Инициализировано: {'да' if stats['is_initialized'] else 'нет'}")
                print(f"Количество переключений: {stats['switch_count']}")
                print(f"Время работы: {stats['total_on_time_seconds']:.1f} сек")
                print(f"Общее время: {stats['uptime_seconds']:.1f} сек")
                print(f"Процент времени работы: {stats['on_time_percentage']:.1f}%")
                if stats['last_switch_time']:
                    print(f"Последнее переключение: {stats['last_switch_time']}")
                print("==================")
                
                return True
            
            else:
                logger.error(f"Неизвестное действие: {action}")
                return False
                
    except Exception as e:
        logger.error(f"Ошибка выполнения команды: {e}")
        return False

def main():
    """Главная функция для командной строки"""
    parser = argparse.ArgumentParser(
        description="Ручное управление клапанами через релейный модуль",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s on                    # Включить охлаждение
  %(prog)s off                   # Выключить охлаждение
  %(prog)s toggle                # Переключить состояние
  %(prog)s test --duration 5     # Тест реле на 5 секунд
  %(prog)s status                # Показать статус
  %(prog)s on --gpio-pin 18      # Использовать GPIO 18
        """
    )
    
    parser.add_argument(
        "action",
        choices=["on", "off", "toggle", "test", "status"],
        help="Действие для выполнения"
    )
    
    parser.add_argument(
        "--gpio-pin",
        type=int,
        default=None,
        help=f"GPIO пин для реле (по умолчанию: {DEFAULT_RELAY_CONFIG.relay_pin})"
    )
    
    parser.add_argument(
        "--duration",
        type=float,
        default=2.0,
        help="Длительность теста в секундах (по умолчанию: 2.0)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Подробный вывод"
    )
    
    args = parser.parse_args()
    
    # Выполнение команды
    success = manual_valve_control(
        action=args.action,
        gpio_pin=args.gpio_pin,
        duration=args.duration,
        verbose=args.verbose
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 