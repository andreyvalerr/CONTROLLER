# Ядро системы контроллера криптокотла

Централизованная система для управления данными и координации работы модулей контроллера криптокотла.

## Описание

Ядро системы (`data_manager`) предоставляет:

- **Централизованное хранение данных** - потокобезопасный менеджер данных для обмена информацией между модулями
- **Интеграцию с модулем температуры** - автоматическое получение и обновление данных температуры асика
- **API для других модулей** - простой интерфейс для получения актуальных данных
- **Мониторинг системы** - контроль состояния и статистика работы
- **Обработку ошибок** - централизованное логирование и обработка сбоев

## Архитектура

```
┌─────────────────────────────────────────────┐
│              ЯДРО СИСТЕМЫ                   │
├─────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐   │
│  │  CoreSystem     │  │  DataManager    │   │
│  │  - координация  │  │  - данные       │   │
│  │  - мониторинг   │  │  - история      │   │
│  │  - API          │  │  - подписки     │   │
│  └─────────────────┘  └─────────────────┘   │
└─────────────────┬───────────────────────────┘
                  │
       ┌──────────┼──────────┐
       │          │          │
┌──────▼────┐ ┌───▼────┐ ┌───▼────┐
│  Модуль   │ │ Модуль │ │ Другие │
│температуры│ │клапанов│ │модули  │
└───────────┘ └────────┘ └────────┘
```

## Быстрый старт

### 1. Запуск ядра системы

```python
from data_manager import start_core_system, stop_core_system

# Запуск с настройками по умолчанию
success = start_core_system()

# Запуск с кастомными настройками
success = start_core_system(
    temperature_ip="192.168.0.127",
    temperature_update_interval=2.0
)

# Остановка
stop_core_system()
```

### 2. Получение данных (для других модулей)

```python
from data_manager import get_temperature_data, get_system_status

# Получение текущей температуры
temperature = get_temperature_data()  # Возвращает float или None
print(f"Температура: {temperature}°C")

# Проверка статуса системы
status = get_system_status()  # "healthy", "warning", "degraded", "stopped"
print(f"Статус: {status}")
```

### 3. Расширенное использование

```python
from data_manager import get_core_instance, DataType

# Получение полного доступа к ядру
core = get_core_instance()

if core:
    # Получение данных с метаинформацией
    temp_entry = core.data_manager.get_data(DataType.TEMPERATURE)
    if temp_entry:
        print(f"Температура: {temp_entry.value}°C")
        print(f"Время: {temp_entry.timestamp}")
        print(f"Источник: {temp_entry.source_module}")
    
    # Получение истории
    history = core.data_manager.get_history(DataType.TEMPERATURE, limit=10)
    
    # Подписка на изменения
    def on_temperature_change(entry):
        print(f"Новая температура: {entry.value}°C")
    
    core.data_manager.subscribe(DataType.TEMPERATURE, on_temperature_change)
```

## API ядра

### Основные функции

| Функция | Описание | Возвращает |
|---------|----------|------------|
| `start_core_system()` | Запуск ядра системы | `bool` |
| `stop_core_system()` | Остановка ядра | `None` |
| `is_core_system_running()` | Проверка активности | `bool` |
| `get_temperature_data()` | Текущая температура | `float` или `None` |
| `get_system_status()` | Статус системы | `str` |
| `get_core_instance()` | Доступ к ядру | `CoreSystem` или `None` |

### Типы данных

```python
from data_manager import DataType

DataType.TEMPERATURE     # Данные температуры
DataType.VALVE_POSITION  # Положение клапанов
DataType.SYSTEM_STATUS   # Статус системы
DataType.ERROR          # Ошибки
```

### Статусы системы

- **`healthy`** - Все системы работают нормально
- **`warning`** - Есть предупреждения (например, устаревшие данные)
- **`degraded`** - Снижена функциональность (модуль недоступен)
- **`stopped`** - Система остановлена

## Интеграция с модулем температуры

Ядро автоматически:

1. **Запускает мониторинг** температуры при старте системы
2. **Синхронизирует данные** каждые 1-2 секунды
3. **Сохраняет историю** измерений
4. **Обрабатывает ошибки** модуля температуры
5. **Предоставляет актуальные данные** другим модулям

### Поток данных

```
Асик → Модуль температуры → Ядро → Другие модули
```

## Примеры использования

### Пример 1: Простой мониторинг

```python
import time
from data_manager import start_core_system, get_temperature_data

# Запуск системы
start_core_system()

# Мониторинг
for i in range(10):
    temp = get_temperature_data()
    if temp:
        print(f"Температура: {temp:.1f}°C")
    time.sleep(5)
```

### Пример 2: Модуль с подпиской на изменения

```python
from data_manager import get_core_instance, DataType

def my_module():
    core = get_core_instance()
    if not core:
        print("Ядро недоступно")
        return
    
    def on_temp_change(entry):
        temp = entry.value
        if temp > 60:
            print(f"ВНИМАНИЕ: Высокая температура {temp}°C!")
        elif temp < 30:
            print(f"ВНИМАНИЕ: Низкая температура {temp}°C!")
    
    # Подписка на изменения температуры
    core.data_manager.subscribe(DataType.TEMPERATURE, on_temp_change)
    
    print("Модуль запущен и следит за температурой")
```

### Пример 3: Модуль с историческими данными

```python
from data_manager import get_core_instance, DataType
from datetime import datetime, timedelta

def analyze_temperature_trend():
    core = get_core_instance()
    if not core:
        return
    
    # Получение данных за последние 5 минут
    since = datetime.now() - timedelta(minutes=5)
    history = core.data_manager.get_history(DataType.TEMPERATURE, since=since)
    
    if len(history) > 1:
        temps = [entry.value for entry in history]
        avg_temp = sum(temps) / len(temps)
        trend = "растет" if temps[-1] > temps[0] else "падает"
        
        print(f"Средняя температура: {avg_temp:.1f}°C")
        print(f"Тренд: {trend}")
```

## Тестирование

Запуск тестового скрипта:

```bash
# Полный тест интеграции
python3 test_core_integration.py

# Демонстрация использования другим модулем
python3 test_core_integration.py demo
```

## Конфигурация

### Параметры запуска

```python
start_core_system(
    temperature_ip="192.168.0.127",        # IP асика
    temperature_update_interval=1.0        # Интервал обновления (сек)
)
```

### DataManager настройки

```python
from data_manager.data_manager import DataManager

# Создание с кастомными настройками
data_manager = DataManager(max_history_size=2000)
```

## Логирование и диагностика

### Получение статистики

```python
core = get_core_instance()
if core:
    stats = core.get_statistics()
    print(f"Время работы: {stats['system']['uptime_seconds']} сек")
    print(f"Обновлений температуры: {stats['modules']['temperature']['updates']}")
    print(f"Ошибок: {stats['errors']['system_errors']}")
```

### Проверка свежести данных

```python
core = get_core_instance()
if core:
    is_fresh = core.data_manager.is_data_fresh(DataType.TEMPERATURE, max_age_seconds=5.0)
    print(f"Данные свежие: {is_fresh}")
```

## Безопасность потоков

Все компоненты ядра потокобезопасны:

- **DataManager** использует `threading.RLock()`
- **CoreSystem** защищен блокировками
- **Глобальные функции** синхронизированы

## Планы развития

- [ ] Веб-интерфейс для мониторинга
- [ ] Система алертов и уведомлений
- [ ] Интеграция с базой данных
- [ ] REST API для внешних систем
- [ ] Конфигурационные файлы 