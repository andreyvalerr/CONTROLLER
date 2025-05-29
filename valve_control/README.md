# Модуль управления клапанами (valve_control)

Модульная система управления клапанами через релейный модуль для контроля температуры жидкости криптокотла на Raspberry Pi.

## Описание

Система автоматически регулирует температуру жидкости в контуре криптокотла, получая данные о температуре от асика через API и управляя клапанами охлаждения через релейный модуль, подключенный к GPIO Raspberry Pi.

## Архитектура

### Основные компоненты:

1. **RelayController** - низкоуровневое управление GPIO реле
2. **TemperatureRegulator** - логика регулирования с гистерезисом и защитой
3. **ValveController** - высокоуровневый API, объединяющий все компоненты
4. **Config** - система конфигурации с поддержкой переменных окружения

### Алгоритм работы:

- **Гистерезис**: включение охлаждения при достижении максимальной температуры, выключение при минимальной
- **Защита от частых переключений**: минимальное время между переключениями
- **Критические температуры**: принудительное включение охлаждения и аварийная остановка
- **Мониторинг**: статистика работы и логирование

## Установка

```bash
# Установка зависимостей
pip install -r requirements.txt

# Для Raspberry Pi также нужно:
sudo apt-get update
sudo apt-get install python3-rpi.gpio
```

## Конфигурация

### Переменные окружения:

```bash
# GPIO настройки
export RELAY_PIN=17              # GPIO пин реле (по умолчанию 17)
export GPIO_MODE=BCM             # Режим GPIO (BCM/BOARD)

# Температурные пороги
export MAX_TEMP=40.0             # Максимальная температура (°C)
export MIN_TEMP=35.0             # Минимальная температура (°C)
export CRITICAL_TEMP=50.0        # Критическая температура (°C)
export EMERGENCY_TEMP=55.0       # Аварийная температура (°C)

# Мониторинг
export ASIC_IP=192.168.0.91      # IP адрес асика
export UPDATE_INTERVAL=1.0       # Интервал обновления (сек)

# Логирование
export LOG_LEVEL=INFO            # Уровень логирования
export LOG_FILE=/var/log/valve_control.log  # Файл логов

# Безопасность
export MAX_COOLING_TIME=60.0     # Максимальное время работы (мин)
export MIN_CYCLE_TIME=30.0       # Минимальное время между переключениями (сек)
export MAX_SWITCHES_HOUR=120     # Максимум переключений в час
```

### Файл конфигурации JSON:

```json
{
  "relay": {
    "relay_pin": 17,
    "gpio_mode": "BCM",
    "relay_on_state": 0,
    "relay_off_state": 1
  },
  "temperature": {
    "max_temperature": 40.0,
    "min_temperature": 35.0,
    "critical_max_temp": 50.0,
    "emergency_temp": 55.0,
    "hysteresis": 5.0
  },
  "monitoring": {
    "asic_ip": "192.168.0.91",
    "update_interval": 1.0,
    "log_level": "INFO"
  },
  "safety": {
    "max_cooling_time": 60.0,
    "min_cycle_time": 30.0,
    "max_switches_per_hour": 120
  }
}
```

## Использование

### Автоматический режим:

```bash
# Запуск с конфигурацией по умолчанию
python -m valve_control.main

# Запуск с файлом конфигурации
python -m valve_control.main --config config.json

# Запуск с параметрами командной строки
python -m valve_control.main --max-temp 45 --gpio-pin 18 --asic-ip 192.168.1.100

# Показать статус
python -m valve_control.main --status

# Сохранить конфигурацию по умолчанию
python -m valve_control.main --save-config default_config.json
```

### Ручное управление:

```bash
# Включить охлаждение
python -m valve_control.manual_control on

# Выключить охлаждение
python -m valve_control.manual_control off

# Переключить состояние
python -m valve_control.manual_control toggle

# Тест реле на 5 секунд
python -m valve_control.manual_control test --duration 5

# Показать статус реле
python -m valve_control.manual_control status

# Использовать другой GPIO пин
python -m valve_control.manual_control on --gpio-pin 18
```

### Программный API:

```python
from valve_control import ValveController

# Создание контроллера
controller = ValveController()

# Запуск автоматического регулирования
controller.start()

# Получение статуса
status = controller.get_status()
print(f"Температура: {status['temperature']['current']}°C")
print(f"Охлаждение: {'включено' if status['regulator']['cooling_active'] else 'выключено'}")

# Ручное управление
controller.manual_cooling_on()   # Включить охлаждение
controller.manual_cooling_off()  # Выключить охлаждение
controller.resume_automatic_control()  # Возобновить автоматику

# Обновление порогов температуры
controller.update_temperature_thresholds(max_temp=45.0, min_temp=40.0)

# Тестирование реле
controller.test_relay(duration=3.0)

# Остановка
controller.stop()
```

### Контекстный менеджер:

```python
from valve_control import ValveController

# Автоматическое управление ресурсами
with ValveController() as controller:
    # Контроллер автоматически запускается
    while True:
        status = controller.get_status()
        print(f"Температура: {status['temperature']['current']}°C")
        time.sleep(10)
# Контроллер автоматически останавливается
```

## Безопасность

### Защитные механизмы:

1. **Гистерезис** - предотвращение частых переключений
2. **Минимальное время цикла** - защита от быстрых переключений
3. **Максимальное время работы** - ограничение непрерывной работы охлаждения
4. **Критические температуры** - принудительное включение охлаждения
5. **Аварийная остановка** - при превышении аварийной температуры
6. **Таймаут связи** - аварийная остановка при потере связи с асиком
7. **Ограничение переключений** - максимум переключений в час

### Логирование:

Система ведет подробные логи всех операций:
- Переключения реле
- Изменения температуры
- Ошибки и предупреждения
- Статистика работы

## Мониторинг

### Статус системы:

```python
status = controller.get_status()

# Общий статус
print(f"Работает: {status['controller']['is_running']}")

# Температура
print(f"Текущая температура: {status['temperature']['current']}°C")
print(f"Время с последнего обновления: {status['temperature']['time_since_update']}с")

# Регулятор
print(f"Состояние регулятора: {status['regulator']['state']}")
print(f"Охлаждение активно: {status['regulator']['cooling_active']}")
print(f"Циклов регулирования: {status['regulator']['total_cycles']}")
print(f"Циклов охлаждения: {status['regulator']['cooling_cycles']}")

# Реле
print(f"GPIO пин: {status['relay']['gpio_pin']}")
print(f"Количество переключений: {status['relay']['switch_count']}")
print(f"Время работы: {status['relay']['on_time_percentage']}%")
```

## Схема подключения

```
Raspberry Pi GPIO 17 ──→ Релейный модуль ──→ Клапан охлаждения
                                          ──→ Питание 220В/12В
```

### Релейный модуль:
- **VCC** → 5V Raspberry Pi
- **GND** → GND Raspberry Pi  
- **IN** → GPIO 17 (или другой настроенный пин)
- **COM/NO** → Клапан охлаждения

## Устранение неполадок

### Ошибки GPIO:
```bash
# Проверка прав доступа
sudo usermod -a -G gpio $USER

# Перезагрузка для применения изменений
sudo reboot
```

### Проблемы с модулем get_temperature:
- Убедитесь, что модуль get_temperature установлен и настроен
- Проверьте IP адрес асика в конфигурации
- При отсутствии модуля система работает в режиме эмуляции

### Отладка:
```bash
# Запуск с подробным логированием
python -m valve_control.main --log-level DEBUG

# Тестирование реле
python -m valve_control.manual_control test --verbose

# Проверка статуса
python -m valve_control.main --status
```

## Лицензия

Система контроллера температуры криптокотла 