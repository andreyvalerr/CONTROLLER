# 🔥 Контроллер Криптокотла

Система автоматического контроля температуры для майнинг-фермы с графическим интерфейсом на сенсорном дисплее.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

## 📋 Содержание

- [Описание](#описание)
- [Архитектура](#архитектура)
- [Возможности](#возможности)
- [Требования](#требования)
- [Установка](#установка)
- [Быстрый запуск](#быстрый-запуск)
- [Модули системы](#модули-системы)
- [Конфигурация](#конфигурация)
- [GUI Интерфейс](#gui-интерфейс)
- [API Документация](#api-документация)
- [Мониторинг и логи](#мониторинг-и-логи)
- [Устранение неполадок](#устранение-неполадок)
- [Разработка](#разработка)
- [Лицензия](#лицензия)

## 🔍 Описание

**Контроллер Криптокотла** — это комплексная система автоматического регулирования температуры для майнинг-оборудования, разработанная для работы на Raspberry Pi с сенсорным дисплеем.

### Основные функции:
- **Мониторинг температуры** ASIC-майнеров в реальном времени
- **Автоматическое регулирование** охлаждающих клапанов
- **Графический интерфейс** для настройки и мониторинга
- **Централизованное управление** данными и настройками
- **Логирование** всех операций и ошибок

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    КОНТРОЛЛЕР КРИПТОКОТЛА                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────┐  │
│  │   GUI Interface │    │  Data Manager   │    │ Hardware │  │
│  │   (Kivy App)    │◄──►│  (Core System)  │◄──►│   GPIO   │  │
│  └─────────────────┘    └─────────────────┘    └──────────┘  │
│           ▲                       ▲                          │
│           │                       │                          │
│  ┌─────────────────┐    ┌─────────────────┐                  │
│  │ Valve Control   │    │ Temperature     │                  │
│  │   Module        │◄──►│   Monitor       │◄─────────────────┤
│  └─────────────────┘    └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                                   ▲
                          ┌─────────────────┐
                          │  ASIC Miners    │
                          │ (192.168.x.x)   │
                          └─────────────────┘
```

### Модули системы:

#### 🎯 **Data Manager** (`data_manager/`)
- **Центральное ядро** системы
- Управление данными температуры и настройками
- Координация между модулями
- Статистика и мониторинг

#### 🌡️ **Temperature Monitor** (`get_temperature_from_asic/`)
- Подключение к ASIC-майнерам по API
- Получение данных температуры в реальном времени
- Обработка ошибок связи
- Поддержка нескольких устройств

#### 🚰 **Valve Control** (`valve_control/`)
- Управление GPIO реле для клапанов
- Автоматическое регулирование температуры
- Интеграция с Data Manager
- Безопасность и защита от перегрева

#### 🖥️ **GUI Interface** (`gui_interface/`)
- Современный сенсорный интерфейс
- Отображение температуры в реальном времени
- Настройка диапазонов температуры
- Статус системы и управление

## ✨ Возможности

### 🔥 Мониторинг температуры
- **Реальное время**: обновление каждую секунду
- **Множественные источники**: поддержка нескольких ASIC-майнеров
- **Визуализация**: цветовая индикация состояния
- **История**: логирование данных температуры

### 🎛️ Автоматическое управление
- **Умные алгоритмы**: PID-регулирование (опционально)
- **Настраиваемые пороги**: min/max температура
- **Гистерезис**: предотвращение частых переключений
- **Безопасность**: аварийные режимы защиты

### 🖱️ Пользовательский интерфейс
- **Сенсорное управление**: оптимизировано для тачскрина
- **Адаптивный дизайн**: автоматическое масштабирование
- **Интуитивная навигация**: простота использования
- **Темная тема**: подходит для промышленного использования

### 📊 Мониторинг и диагностика
- **Детальные логи**: все операции записываются
- **Статистика работы**: счетчики и метрики
- **Диагностика ошибок**: понятные сообщения об ошибках
- **Системный статус**: отображение состояния модулей

## ⚙️ Требования

### Аппаратные требования:
- **Raspberry Pi 4** (рекомендуется) или Pi 3B+
- **Сенсорный дисплей** 7" (800x480) или больше
- **MicroSD карта** 32GB+ (Class 10)
- **GPIO реле модуль** для управления клапанами
- **Сетевое подключение** к ASIC-майнерам

### Программные требования:
- **Raspberry Pi OS** (Bullseye или новее)
- **Python 3.11+**
- **Библиотеки**: kivy, pycryptodome, RPi.GPIO

### Сетевые требования:
- **Доступ к ASIC API** (обычно порт 4433)
- **Статические IP адреса** для ASIC-майнеров (рекомендуется)

## 🚀 Установка

### 1. Подготовка системы

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и зависимостей
sudo apt install python3-pip python3-kivy python3-pycryptodome -y

# Для GPIO (если не установлено)
sudo apt install python3-rpi.gpio -y
```

### 2. Клонирование проекта

```bash
# Переход в домашнюю директорию
cd /home/user

# Клонирование репозитория (или копирование файлов)
# git clone https://github.com/your-repo/crypto-boiler-controller.git CONTROLLER
```

### 3. Установка зависимостей

```bash
cd CONTROLLER

# Установка Python зависимостей
pip3 install pycryptodome==3.19.0 --break-system-packages

# Проверка установки
python3 -c "import kivy; print('Kivy OK')"
python3 -c "import Crypto; print('Crypto OK')"
```

### 4. Настройка автозапуска (опционально)

```bash
# Создание systemd сервиса
sudo nano /etc/systemd/system/crypto-controller.service
```

Содержимое файла:
```ini
[Unit]
Description=Crypto Boiler Controller
After=network.target

[Service]
Type=simple
User=user
WorkingDirectory=/home/user/CONTROLLER
ExecStart=/usr/bin/python3 /home/user/CONTROLLER/start_all_modules.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активация:
```bash
sudo systemctl enable crypto-controller.service
sudo systemctl start crypto-controller.service
```

## ⚡ Быстрый запуск

### Основной способ запуска

```bash
cd /home/user/CONTROLLER
python3 start_all_modules.py
```

### Запуск отдельных модулей (для отладки)

```bash
# Только Data Manager
cd data_manager
python3 -c "from core_system import start_core_system; start_core_system()"

# Только температурный мониторинг
cd get_temperature_from_asic  
python3 start_monitoring.py

# Только управление клапанами
cd valve_control
python3 main.py

# Только GUI
cd gui_interface
python3 main_gui.py
```

### Первый запуск

1. **Запустите систему**:
   ```bash
   python3 start_all_modules.py
   ```

2. **Настройте температурные пороги** через GUI интерфейс

3. **Проверьте подключение** к ASIC-майнерам

4. **Настройте GPIO пины** для реле клапанов

## 📁 Модули системы

### 🎯 Data Manager

**Расположение**: `data_manager/`

**Основные файлы**:
- `core_system.py` - основное ядро системы
- `data_manager.py` - управление данными

**Функции**:
- Централизованное хранение данных
- Координация между модулями
- Статистика и мониторинг
- API для других модулей

### 🌡️ Temperature Monitor

**Расположение**: `get_temperature_from_asic/`

**Основные файлы**:
- `simple_api.py` - API для ASIC подключения
- `simple_monitor.py` - основной мониторинг
- `start_monitoring.py` - точка входа

**Конфигурация**:
```python
# config.py
ASIC_IP = "192.168.0.127"
UPDATE_INTERVAL = 1.0  # секунды
TIMEOUT = 10  # секунды
```

### 🚰 Valve Control

**Расположение**: `valve_control/`

**Основные файлы**:
- `main.py` - основной контроллер
- `valve_controller.py` - логика управления
- `data_manager_integration.py` - интеграция

**Конфигурация**:
```python
# Переменные окружения
RELAY_PIN=17                    # GPIO пин реле
MAX_TEMP=55.0                   # Максимальная температура
MIN_TEMP=45.0                   # Минимальная температура
```

### 🖥️ GUI Interface

**Расположение**: `gui_interface/`

**Основные файлы**:
- `main_gui.py` - основное приложение
- `components/` - UI компоненты
- `styles/` - стили интерфейса

**Возможности**:
- Отображение температуры в реальном времени
- Настройка диапазонов температуры
- Статус системы
- Сенсорное управление

## ⚙️ Конфигурация

### Настройка ASIC подключения

```bash
# Редактирование конфигурации температурного мониторинга
nano get_temperature_from_asic/config.py
```

```python
# IP адрес ASIC майнера
ASIC_IP = "192.168.0.127"

# Порт API (обычно 4433)
ASIC_PORT = 4433

# Интервал обновления (секунды)
UPDATE_INTERVAL = 1.0

# Таймаут подключения
TIMEOUT = 10.0
```

### Настройка GPIO

```bash
# Редактирование конфигурации клапанов
nano valve_control/config.py
```

```python
# GPIO пин реле
RELAY_PIN = 17

# Состояния реле
RELAY_ON_STATE = True
RELAY_OFF_STATE = False

# Температурные пороги
MAX_TEMPERATURE = 55.0  # °C
MIN_TEMPERATURE = 45.0  # °C
HYSTERESIS = 2.0        # °C
```

### Переменные окружения

```bash
# Создание файла переменных окружения
nano .env
```

```bash
# ASIC Configuration
ASIC_IP=192.168.0.127
ASIC_PORT=4433

# GPIO Configuration  
RELAY_PIN=17
GPIO_MODE=BCM

# Temperature Settings
MAX_TEMP=55.0
MIN_TEMP=45.0
HYSTERESIS=2.0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/crypto-controller.log
```

## 🖥️ GUI Интерфейс

### Главный экран

```
┌─────────────────────────────────────────────────────────────┐
│  Температура охлаждающей жидкости        │    Управление    │
│                                          │                  │
│            52.3°C                        │   Настройка     │
│                                          │  диапазона      │
│    Диапазон: 45.0°C - 55.0°C           │ температуры     │
├─────────────────────────────────────────────────────────────┤
│  Статус системы                          │                  │
│                                          │                  │
│  Система: АКТИВНА                        │                  │
│  Статус: РАБОТАЕТ                        │                  │
│  Обновлено: 14:30:25                     │                  │
└─────────────────────────────────────────────────────────────┘
```

### Настройка температуры

- **Слайдеры** для установки min/max температуры
- **Валидация** настроек в реальном времени
- **Цветовая индикация** корректности настроек
- **Мгновенное сохранение** изменений

### Цветовая индикация

- 🟢 **Зеленый**: температура в норме
- 🔴 **Красный**: температура выше максимума
- 🔵 **Синий**: температура ниже минимума
- ⚫ **Серый**: нет данных

## 📡 API Документация

### Data Manager API

```python
from data_manager.core_system import *

# Запуск системы
start_core_system(temperature_ip="192.168.0.127")

# Получение данных
temperature = get_temperature_data()
system_data = get_core_instance().get_system_data()

# Настройка температуры
set_temperature_settings(max_temp=55.0, min_temp=45.0)
settings = get_temperature_settings()
```

### Temperature Monitor API

```python
from get_temperature_from_asic import *

# Запуск мониторинга
start_temperature_monitoring(ip_address="192.168.0.127")

# Получение данных
current_temp = get_current_temperature()
all_data = get_all_temperature_data()

# Остановка
stop_temperature_monitoring()
```

### Valve Control API

```python
from valve_control.main import ValveController

# Создание контроллера
controller = ValveController(temperature_callback=get_temperature)

# Запуск
controller.start()

# Получение статуса
status = controller.get_status()
```

## 📊 Мониторинг и логи

### Расположение логов

```bash
# Системные логи Data Manager
/home/user/CONTROLLER/logs/system.log

# Логи температурного мониторинга
/home/user/CONTROLLER/get_temperature_from_asic/logs/

# Логи управления клапанами
/home/user/CONTROLLER/valve_control/logs/

# Системные логи (если настроен systemd)
journalctl -u crypto-controller.service -f
```

### Мониторинг в реальном времени

```bash
# Просмотр основных логов
tail -f CONTROLLER/logs/system.log

# Мониторинг temperature модуля
tail -f CONTROLLER/get_temperature_from_asic/logs/monitor.log

# Мониторинг valve_control
tail -f CONTROLLER/valve_control/logs/controller.log
```

### Статистика системы

```python
# Получение статистики через Python
from data_manager.core_system import get_core_instance

core = get_core_instance()
stats = core.get_statistics()
print(stats)
```

## 🔧 Устранение неполадок

### Частые проблемы

#### 1. **Нет подключения к ASIC**

```bash
# Проверка сетевого подключения
ping 192.168.0.127

# Проверка доступности API порта
telnet 192.168.0.127 4433

# Проверка в логах
grep "connection" CONTROLLER/logs/system.log
```

**Решение**:
- Проверьте IP адрес ASIC
- Убедитесь что API включен на ASIC
- Проверьте файрвол

#### 2. **GUI не запускается**

```bash
# Проверка X server
echo $DISPLAY

# Запуск GUI с отладкой
KIVY_LOG_LEVEL=debug python3 gui_interface/main_gui.py
```

**Решение**:
- Убедитесь что запускаете из графической сессии
- Проверьте права доступа к /dev/input/*
- Установите пакет python3-kivy

#### 3. **GPIO не работает**

```bash
# Проверка прав доступа
groups $USER | grep gpio

# Добавление пользователя в группу gpio
sudo usermod -a -G gpio $USER
```

**Решение**:
- Перезайдите в систему после добавления в группу
- Проверьте что используете правильный пин
- Убедитесь что пин не используется другим процессом

#### 4. **Высокая нагрузка на CPU**

**Причины**:
- Слишком частое обновление (уменьшите интервал)
- Ошибки подключения к ASIC (проверьте сеть)
- Проблемы с GUI (уменьшите частоту обновления)

**Решение**:
```python
# Увеличение интервала обновления
# В config.py
UPDATE_INTERVAL = 2.0  # было 1.0
```

### Диагностические команды

```bash
# Проверка всех процессов
ps aux | grep python

# Использование CPU и памяти
htop

# Сетевая активность
sudo netstat -tulpn | grep python

# Проверка GPIO
gpio readall

# Проверка логов systemd
journalctl -xe
```

### Восстановление после сбоя

```bash
# Принудительная остановка всех процессов
pkill -f "python.*CONTROLLER"

# Очистка временных файлов
rm -f /tmp/crypto-controller.*

# Перезапуск
cd CONTROLLER && python3 start_all_modules.py
```

## 👨‍💻 Разработка

### Структура проекта

```
CONTROLLER/
├── start_all_modules.py          # Основной скрипт запуска
├── README.md                     # Документация
├── requirements.txt              # Зависимости
├── .env.example                  # Пример переменных окружения
│
├── data_manager/                 # Модуль управления данными
│   ├── __init__.py
│   ├── core_system.py           # Основная система
│   ├── data_manager.py          # Менеджер данных
│   └── requirements.txt
│
├── get_temperature_from_asic/   # Модуль мониторинга температуры
│   ├── __init__.py
│   ├── simple_api.py           # API для ASIC
│   ├── simple_monitor.py       # Мониторинг
│   ├── start_monitoring.py     # Точка входа
│   ├── config.py              # Конфигурация
│   └── requirements.txt
│
├── valve_control/              # Модуль управления клапанами
│   ├── __init__.py
│   ├── main.py                # Основной контроллер
│   ├── valve_controller.py    # Логика управления
│   ├── config.py             # Конфигурация
│   ├── data_manager_integration.py  # Интеграция
│   ├── temperature_regulator.py    # Регулятор температуры
│   └── requirements.txt
│
├── gui_interface/             # GUI интерфейс
│   ├── __init__.py
│   ├── main_gui.py           # Основное приложение
│   ├── components/           # UI компоненты
│   ├── styles/              # Стили
│   └── assets/              # Ресурсы
│
└── logs/                     # Логи системы
    └── system.log
```

### Добавление нового модуля

1. **Создайте директорию модуля**
2. **Добавьте `__init__.py`**
3. **Реализуйте интеграцию с Data Manager**
4. **Обновите `start_all_modules.py`**
5. **Добавьте тесты**

### Стиль кода

```python
# Следуйте PEP 8
# Используйте type hints
# Добавляйте docstrings

def process_temperature(temp: float) -> bool:
    """
    Обработка данных температуры
    
    Args:
        temp: Температура в градусах Цельсия
        
    Returns:
        True если температура в норме
    """
    return 45.0 <= temp <= 55.0
```

### Тестирование

```bash
# Проверка работы температурного мониторинга
cd get_temperature_from_asic
python3 simple_monitor.py

# Проверка valve_control
cd valve_control  
python3 main.py

# Тестирование интеграции через основной запуск
python3 start_all_modules.py
```

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

## 🤝 Вклад в проект

1. **Fork** репозитория
2. Создайте **feature branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit** изменения (`git commit -m 'Add some AmazingFeature'`)
4. **Push** в branch (`git push origin feature/AmazingFeature`)
5. Откройте **Pull Request**

## 📞 Поддержка

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Документация**: [Wiki](https://github.com/your-repo/wiki)
- **Email**: support@crypto-controller.com

## 🔄 Changelog

### v1.0.1 (2025-06-01)
- ✅ Оптимизация кодовой базы
- ✅ Удаление диагностических и тестовых файлов
- ✅ Улучшение стабильности системы
- ✅ Обновление документации

### v1.0.0 (2025-06-01)
- ✅ Первый релиз
- ✅ Полная интеграция модулей
- ✅ GUI интерфейс
- ✅ Автоматическое регулирование температуры
- ✅ Мониторинг ASIC майнеров

---

**🔥 Контроллер Криптокотла** - Надежное решение для автоматизации майнинг-фермы! 