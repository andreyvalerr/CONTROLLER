# Интеграция Valve Control с Data Manager

## Описание

Данная интеграция позволяет модулю `valve_control` получать данные температуры ASIC каждую секунду через модуль `data_manager`, который в свою очередь получает их от модуля `get_temperature_from_asic`.

**ОБНОВЛЕНИЕ**: Теперь модуль также получает настройки температуры (`max_temperature` и `min_temperature`) из `data_manager`, что обеспечивает централизованное управление всеми температурными параметрами.

## Архитектура

```
get_temperature_from_asic → data_manager → valve_control
                                ↑
                    temperature_settings ←
```

1. **get_temperature_from_asic** - получает текущую температуру от ASIC
2. **data_manager** - централизованное хранение температурных данных И настроек
3. **valve_control** - управление клапанами на основе данных из data_manager

## Новая функциональность настроек температуры

### Получение настроек температуры из data_manager

Модуль `valve_control` теперь получает `max_temperature` и `min_temperature` из `data_manager` вместо локального `config.py`:

- `get_temperature_settings_for_valve_controller()` - получение настроек
- `set_temperature_settings_from_valve_controller()` - установка настроек  
- `is_temperature_settings_available()` - проверка доступности

### Преимущества централизованных настроек

1. **Единый источник истины** - все настройки температуры в одном месте
2. **Динамическое изменение** - настройки можно изменять без перезапуска
3. **Синхронизация** - автоматическая синхронизация между модулями
4. **Строгая зависимость** - модуль не работает без data_manager, что обеспечивает целостность системы

### Новые файлы и изменения

#### Новые тестовые файлы
- `test_temperature_settings_integration.py` - тестирование настроек температуры

#### Изменения в data_manager
- Добавлен тип данных `TEMPERATURE_SETTINGS`
- Новые функции управления настройками в `core_system.py`

#### Изменения в valve_control
- `config.py` - убраны max/min temperature из TemperatureConfig
- `data_manager_integration.py` - добавлены функции работы с настройками
- `valve_controller.py` - новые методы синхронизации с data_manager
- `main.py` - автоматическая инициализация настроек при запуске

## Использование новой функциональности

### Автоматический режим (рекомендуется)
```bash
cd /home/user/CONTROLLER/valve_control
python3 main.py
```

При запуске автоматически:
1. Запускается интеграция с data_manager
2. Инициализируются настройки температуры
3. Происходит синхронизация с существующими настройками
4. Контроллер использует централизованные настройки

### Ручное управление настройками

```python
from valve_control.data_manager_integration import (
    get_temperature_settings_for_valve_controller,
    set_temperature_settings_from_valve_controller,
    is_temperature_settings_available
)

# Проверка доступности настроек
if is_temperature_settings_available():
    # Получение текущих настроек
    settings = get_temperature_settings_for_valve_controller()
    print(f"Max: {settings['max_temperature']}°C, Min: {settings['min_temperature']}°C")
    
    # Обновление настроек
    set_temperature_settings_from_valve_controller(53.0, 52.5)
```

### Работа с ValveController

```python
from valve_control.valve_controller import ValveController

# Создание контроллера
controller = ValveController(temperature_callback=get_temperature_for_valve_controller)

# Синхронизация настроек с data_manager
controller.sync_temperature_settings_with_data_manager()

# Получение настроек из data_manager
dm_config = controller.get_temperature_settings_from_data_manager()
print(f"Источник настроек: {dm_config.source}")
print(f"Доступны в data_manager: {dm_config.is_available}")

# Обновление настроек в data_manager
controller.update_temperature_settings_to_data_manager(54.0, 53.5)
```

## Тестирование

### Тест интеграции настроек температуры
```bash
cd /home/user/CONTROLLER/valve_control
python3 test_temperature_settings_integration.py
```

Тест проверяет:
- Создание и получение настроек
- Обновление настроек
- Синхронизацию данных
- Обработку некорректных значений

### Тест полной интеграции
```bash
cd /home/user/CONTROLLER/valve_control
python3 test_data_manager_integration.py
```

## Конфигурация

### Обязательные требования
- data_manager core_system ДОЛЖЕН быть запущен
- Настройки температуры ДОЛЖНЫ быть установлены в data_manager
- Модуль НЕ работает без data_manager

### Настройки температуры в data_manager
- `max_temperature`: Максимальная температура для включения охлаждения
- `min_temperature`: Минимальная температура для выключения охлаждения
- `hysteresis`: Автоматически вычисляется как (max_temperature - min_temperature)

## Миграция с локальной конфигурации

⚠️ **ВАЖНО**: После рефакторинга модуль valve_control НЕ создает настройки температуры автоматически.

### Ручная установка настроек
Перед первым запуском ОБЯЗАТЕЛЬНО установите настройки температуры в data_manager:

```python
from data_manager.core_system import set_temperature_settings

# Установка настроек температуры
set_temperature_settings(
    max_temp=52.0,  # Максимальная температура
    min_temp=51.9,  # Минимальная температура
    source_module="manual_setup"
)
```

### Проверка настроек
```python
from data_manager.core_system import get_temperature_settings
settings = get_temperature_settings()
print(f"Настройки: {settings}")
```

## Диагностика проблем

### Если настройки не синхронизируются:
1. Проверьте работу data_manager core_system
2. Убедитесь в доступности модуля data_manager
3. Проверьте логи valve_controller на ошибки синхронизации
4. Запустите тест настроек: `python3 test_temperature_settings_integration.py`

### Проверка текущих настроек:
```python
from data_manager.core_system import get_temperature_settings
settings = get_temperature_settings()
print(f"Настройки в data_manager: {settings}")
```

## Требования к запуску

Перед запуском valve_control убедитесь, что:
1. Запущен data_manager core_system
2. Модуль data_manager доступен и функционирует
3. ASIC доступен для получения температуры
4. Нет конфликтов настроек между модулями 