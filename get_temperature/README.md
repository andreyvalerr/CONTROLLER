# 🌡️ Модуль получения температуры жидкости

Рабочий модуль для получения температуры жидкости с асика Whatsminer M64_VL40 для контроллера криптокотла.

## 📁 Структура файлов

```
get_temperature/
├── simple_api.py           # 🚀 Основной API для интеграции
├── simple_monitor.py       # 🔧 Упрощенный монитор температуры  
├── test_simple.py          # ✅ Рабочий тест
├── start_monitoring.py     # 🖥️ Простой мониторинг в реальном времени
├── monitor_class.py        # 🔧 Мониторинг через класс API
├── quick_start.sh          # ⚡ Быстрый запуск с меню
├── whatsminer_interface.py # 🔌 API интерфейс Whatsminer
├── whatsminer_transport.py # 🌐 TCP транспорт
├── requirements.txt        # 📦 Зависимости
├── install.sh             # 🛠️ Скрипт установки
├── test_report.md          # 📋 Отчет о проверке работоспособности
├── __init__.py            # 📋 Инициализация модуля
├── SOLUTION.md            # 📖 Документация решения
└── README.md              # 📚 Этот файл
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd CONTROLLER/get_temperature
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Тест работоспособности

```bash
# Простой тест
python3 test_simple.py

# Тест API
python3 simple_api.py
```

## 🖥️ Запуск мониторинга температуры

### ⚡ Самый простой способ - через меню

```bash
./quick_start.sh
```

Этот скрипт автоматически:
- ✅ Активирует виртуальное окружение
- ✅ Проверяет зависимости
- ✅ Предлагает меню выбора режима

### 🔄 Способы мониторинга

#### 1. Простой мониторинг (рекомендуется)
```bash
source venv/bin/activate
python start_monitoring.py
```

**Что показывает:**
- 🌡️ Температура жидкости в реальном времени
- 📊 Статус системы (normal/warning/critical)
- 🔧 Температура PSU и скорость вентилятора
- 📈 Статистика успешности запросов

#### 2. Мониторинг через класс API
```bash
source venv/bin/activate
python monitor_class.py
```

**Дополнительно показывает:**
- 💚 Индикатор здоровья системы
- 📊 Расширенную диагностику

#### 3. Однократное получение
```bash
source venv/bin/activate
python test_simple.py
```

### 🛑 Остановка мониторинга

Для остановки любого мониторинга используйте **Ctrl+C**

## 🔌 Интеграция с контроллером клапанов

### Простое использование

```python
from simple_api import get_current_temperature

# В цикле контроллера
current_temp = get_current_temperature()
if current_temp and current_temp > 55:
    # Открыть клапан охлаждения
    pass
```

### Автоматический мониторинг

```python
import simple_api

# Запуск фонового мониторинга
simple_api.start_temperature_monitoring("192.168.0.91", update_interval=1.0)

# Получение данных в любое время
temp = simple_api.get_current_temperature()
status = simple_api.get_temperature_status()
all_data = simple_api.get_all_temperature_data()

# Остановка мониторинга
simple_api.stop_temperature_monitoring()
```

### Использование с ПИД-регулятором

```python
from simple_api import ValveController

# Создание контроллера
controller = ValveController(target_temperature=50.0)

# Получение сигнала управления
valve_position = controller.calculate_valve_position()
# valve_position: от -1.0 до 1.0
```

### Использование с контекстным менеджером

```python
from simple_api import TemperatureAPI

with TemperatureAPI() as temp_api:
    temp = temp_api.get_temperature()
    status = temp_api.get_status()
    health = temp_api.is_healthy()
    # Автоматическое управление ресурсами
```

## 📊 Характеристики

- **Время отклика**: ~1-2 секунды
- **Частота обновления**: Настраиваемая (1-2 Гц)
- **Надежность**: 100% в тестах
- **Потребление ресурсов**: Минимальное
- **Поддержка мониторинга**: В реальном времени

## 🔧 Конфигурация

По умолчанию:
- **IP майнера**: 192.168.0.91
- **Порт**: 4433
- **Логин/пароль**: super/super
- **Интервал**: 1.0 секунда

Настройка IP адреса:
```python
# В коде
simple_api.start_temperature_monitoring("192.168.1.100")

# Или через класс
api = TemperatureAPI("192.168.1.100", update_interval=2.0)
```

## 📈 Статус температуры

- 🟢 **normal**: < 55°C
- 🟡 **warning**: 55-60°C  
- 🔴 **critical**: > 60°C
- ❌ **error**: Ошибка подключения
- ❓ **unknown**: Неизвестное состояние

## 🛠️ Устранение неполадок

### Майнер недоступен
```bash
python3 test_simple.py
```

### Проблемы с зависимостями
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Проблемы с виртуальным окружением
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Проверка работоспособности
Запустите полную проверку:
```bash
./quick_start.sh
# Выберите пункт 3 для теста
```

## 📊 Мониторинг и диагностика

### Получение статистики
```python
import simple_api

stats = simple_api.get_monitoring_statistics()
print(f"Успешность: {stats['success_rate']}%")
print(f"Всего запросов: {stats['total_requests']}")
```

### Проверка активности мониторинга
```python
is_active = simple_api.is_temperature_monitoring_active()
print(f"Мониторинг активен: {is_active}")
```

## 📖 Документация

- **Подробная документация решения**: [SOLUTION.md](SOLUTION.md)
- **Отчет о проверке работоспособности**: [test_report.md](test_report.md)

## 🎯 Готово для продакшена

Модуль протестирован и готов для интеграции с контроллером клапанов криптокотла! 

### ✅ Проверено:
- Все зависимости установлены
- Подключение к устройству работает
- API функции доступны
- Мониторинг в реальном времени функционирует
- Получение температуры: **50.1°C** ✅

🚀 **Начните с `./quick_start.sh` для быстрого старта!**