#!/usr/bin/env python3
"""
Простой CLI-скрипт для ручного управления выводом GPIO.

По умолчанию управляет GPIO 22 (нумерация BCM) и предполагает активный LOW
(многие релейные модули включаются уровнем LOW). Можно переключить на
активный HIGH флагом --active-high.

Примеры:
  sudo python3 gpio22_manual.py on                # Включить (LOW по умолчанию)
  sudo python3 gpio22_manual.py off               # Выключить (HIGH по умолчанию)
  sudo python3 gpio22_manual.py status            # Показать состояние
  sudo python3 gpio22_manual.py toggle            # Переключить состояние

Дополнительно:
  --pin 22                # Изменить номер пина (BCM)
  --board                 # Использовать нумерацию BOARD вместо BCM
  --active-high           # Считать, что устройство активно на HIGH
  --cleanup               # Очистить GPIO при выходе (сбросит пин)
"""

import sys
import argparse
import atexit

try:
    import RPi.GPIO as GPIO
except Exception as e:
    print(f"Ошибка импорта RPi.GPIO: {e}")
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ручное управление GPIO выводом (по умолчанию GPIO 22, BCM)",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "command",
        choices=["on", "off", "status", "toggle"],
        help="Действие: on/off/status/toggle",
    )

    parser.add_argument("--pin", type=int, default=22, help="Номер GPIO (в выбранной схеме нумерации)")
    parser.add_argument("--board", action="store_true", help="Использовать нумерацию BOARD (по умолчанию BCM)")
    parser.add_argument("--active-high", action="store_true", dest="active_high", help="Активный уровень HIGH")
    parser.add_argument("--cleanup", action="store_true", help="Выполнить GPIO.cleanup() при выходе")

    return parser.parse_args()


def setup_gpio(use_board: bool, pin: int):
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD if use_board else GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)


def main() -> int:
    args = parse_args()

    # Настройка GPIO и опциональная очистка при выходе
    setup_gpio(args.board, args.pin)

    if args.cleanup:
        atexit.register(GPIO.cleanup)

    on_level = GPIO.HIGH if args.active_high else GPIO.LOW
    off_level = GPIO.LOW if args.active_high else GPIO.HIGH

    try:
        if args.command == "on":
            GPIO.output(args.pin, on_level)
            print(f"GPIO {args.pin}: ON ({'HIGH' if on_level == GPIO.HIGH else 'LOW'})")
            return 0

        if args.command == "off":
            GPIO.output(args.pin, off_level)
            print(f"GPIO {args.pin}: OFF ({'HIGH' if off_level == GPIO.HIGH else 'LOW'})")
            return 0

        if args.command == "status":
            state = GPIO.input(args.pin)
            level = "HIGH" if state == GPIO.HIGH else "LOW"
            # Логический статус с учётом активной логики
            logical_on = (state == GPIO.HIGH) if args.active_high else (state == GPIO.LOW)
            print(f"GPIO {args.pin}: {level}  ->  {'ON' if logical_on else 'OFF'} (active-{'HIGH' if args.active_high else 'LOW'})")
            return 0

        if args.command == "toggle":
            current = GPIO.input(args.pin)
            # Переключаем физический уровень
            new_level = GPIO.LOW if current == GPIO.HIGH else GPIO.HIGH
            GPIO.output(args.pin, new_level)
            level = "HIGH" if new_level == GPIO.HIGH else "LOW"
            logical_on = (new_level == GPIO.HIGH) if args.active_high else (new_level == GPIO.LOW)
            print(f"GPIO {args.pin}: TOGGLED -> {level}  ->  {'ON' if logical_on else 'OFF'}")
            return 0

        return 0

    except Exception as e:
        print(f"Ошибка управления GPIO: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


