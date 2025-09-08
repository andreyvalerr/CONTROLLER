# Тест ручного управления GPIO (test_gpio_manual.py)

Этот тестовый скрипт позволяет вручную включать/выключать сигнал на выбранном пине Raspberry Pi через терминал.

По умолчанию используется нумерация BCM и пин GPIO 22. Предполагается активная логика LOW (многие релейные модули включаются LOW).

## Запуск

Требуются права root для доступа к GPIO:

```bash
sudo python3 /home/user/CONTROLLER/tests/test_gpio_manual.py <command> [опции]
```

Где `<command>` одна из:
- `on` — включить (LOW по умолчанию)
- `off` — выключить (HIGH по умолчанию)
- `status` — показать текущее состояние пина
- `toggle` — переключить состояние

## Опции

- `--pin <N>` — номер GPIO в выбранной схеме нумерации (по умолчанию `22`)
- `--board` — использовать схему нумерации BOARD вместо BCM
- `--active-high` — устройство активно на HIGH (по умолчанию активно на LOW)
- `--cleanup` — выполнить `GPIO.cleanup()` при выходе (сбросит состояния)

## Примеры

Включить GPIO22 (BCM, активный LOW по умолчанию):
```bash
sudo python3 /home/user/CONTROLLER/tests/test_gpio_manual.py on
```

Выключить GPIO22:
```bash
sudo python3 /home/user/CONTROLLER/tests/test_gpio_manual.py off
```

Показать статус GPIO22:
```bash
sudo python3 /home/user/CONTROLLER/tests/test_gpio_manual.py status
```

Переключить GPIO22:
```bash
sudo python3 /home/user/CONTROLLER/tests/test_gpio_manual.py toggle
```

Использовать BOARD-нумерацию, физический контакт 15 (это тот же GPIO22), активный HIGH:
```bash
sudo python3 /home/user/CONTROLLER/tests/test_gpio_manual.py on --board --pin 15 --active-high
```

С очисткой GPIO при выходе:
```bash
sudo python3 /home/user/CONTROLLER/tests/test_gpio_manual.py off --cleanup
```

## Примечания

- Для корректной работы требуется установленный `RPi.GPIO` (см. `valve_control/requirements.txt`).
- Если у вас другой пин — укажите его флагом `--pin` или используйте `--board` и физический номер контакта.
- Будьте осторожны при переключениях, чтобы не повредить подключённые устройства.


