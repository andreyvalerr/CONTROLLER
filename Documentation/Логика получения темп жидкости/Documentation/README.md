# 🌡️ Whatsminer Liquid Temperature Monitor

## 📋 Описание проекта

Этот проект демонстрирует успешное получение температуры жидкости с майнера **Whatsminer M64_VL40** с жидкостным охлаждением через **API v3.0.1**.

## 🎯 Результаты

✅ **УСПЕШНО ПОЛУЧЕНА ТЕМПЕРАТУРА ЖИДКОСТИ: 49.6°C**

### 📊 Полученные данные:
- **💧 Температура жидкости:** `49.6°C` (отличный показатель)
- **🔥 Температура БП:** `55.9°C` (в норме)
- **🌪️ Скорость вентилятора:** `49.6%` (оптимальная)
- **🔌 Мощность:** `4144W`
- **⚡ Напряжение:** `230.75V`

## 📁 Структура проекта

```
📦 new_controller/
├── 📄 get_temperature.py          # Базовый скрипт получения температуры
├── 📄 get_temperature_v2.py       # Расширенный сканер API команд
├── 📄 liquid_temp_monitor.py      # Финальный монитор температуры
├── 📄 WHATSMINER_API_GUIDE.md     # Подробное руководство по API
├── 📄 TECHNICAL_DIAGRAMS.md       # Технические схемы и диаграммы
├── 📄 README.md                   # Этот файл
└── 📁 1729070366369python-whatsminer-api-3.0.0/  # Библиотека API
    ├── whatsminer_interface.py
    ├── whatsminer_trans.py
    └── whatsminer.py
```

## 🚀 Быстрый старт

### 1. Установка зависимостей
```bash
pip install passlib pycryptodome
```

### 2. Простое получение температуры
```bash
python liquid_temp_monitor.py
```

### 3. Полный анализ API
```bash
python get_temperature_v2.py
```

## 🔧 Технические детали

### Параметры подключения:
- **IP адрес:** `192.168.0.91`
- **Порт:** `4433`
- **Аккаунт:** `super`
- **Пароль:** `super`
- **API версия:** `3.0.1`

### Ключевая команда API:
```json
{
    "cmd": "get.device.info",
    "param": null
}
```

### Путь к данным температуры:
```python
liquid_temp = response['msg']['power']['liquid-temperature']
```

## 📈 Архитектура решения

```
Python Client ──TCP/IP──► Whatsminer M64_VL40
     │                         │
     │                    ┌────▼────┐
     │                    │ API v3  │
     │                    └────┬────┘
     │                         │
     │                    ┌────▼────┐
     │                    │Sensors  │
     │                    └────┬────┘
     │                         │
     └◄────JSON Response───────┘
       liquid-temperature: 49.6°C
```

## 🌡️ Логика получения температуры

### Шаг 1: Подключение
```python
whatsminer_tcp = WhatsminerTCP(ip, 4433, "super", "super")
whatsminer_tcp.connect()
```

### Шаг 2: Аутентификация
```python
req = whatsminer_api.get_request_cmds("get.device.info")
resp = whatsminer_tcp.send(req, len(req))
salt = resp['msg']['salt']
whatsminer_api.set_salt(salt)
```

### Шаг 3: Извлечение данных
```python
power_info = resp['msg']['power']
liquid_temp = power_info['liquid-temperature']  # 49.6°C
psu_temp = power_info['temp0']                  # 55.9°C
fan_speed = power_info['fanspeed']              # 49.6%
```

## 💡 Ключевые особенности

### ✅ Преимущества:
- **Прямой доступ** к температуре жидкости
- **Быстрый отклик** (< 1 секунды)
- **Надежная аутентификация** через salt
- **Минимальная нагрузка** на майнер
- **Дополнительные данные** (БП, вентиляторы, мощность)

### 🔐 Безопасность:
- AES шифрование команд
- Salt-based аутентификация
- Защищенное TCP соединение

### 📊 Мониторинг:
- Реальное время
- Кэширование данных
- Обработка ошибок
- Логирование

## 🎯 Применение в проектах

### 🏭 Промышленный мониторинг
```python
# Непрерывный мониторинг для дата-центра
monitor = WhatsminerTemperatureMonitor("192.168.0.91")
while True:
    temp = monitor.get_liquid_temperature()
    if temp > 60:
        send_alert("Критическая температура!")
    time.sleep(30)
```

### 📊 Система аналитики
```python
# Сбор данных для анализа
temperatures = []
for hour in range(24):
    temp = get_liquid_temperature("192.168.0.91")
    temperatures.append({
        'time': datetime.now(),
        'temperature': temp
    })
    time.sleep(3600)  # Каждый час
```

### ⚠️ Система предупреждений
```python
# Автоматические уведомления
def check_temperature():
    temp = get_liquid_temperature("192.168.0.91")
    if temp > 55:
        send_email("Повышенная температура: {}°C".format(temp))
    elif temp > 60:
        send_sms("КРИТИЧНО! Температура: {}°C".format(temp))
```

## 📚 Документация

- **[WHATSMINER_API_GUIDE.md](WHATSMINER_API_GUIDE.md)** - Полное руководство по API
- **[TECHNICAL_DIAGRAMS.md](TECHNICAL_DIAGRAMS.md)** - Технические схемы и диаграммы

## 🔍 Диагностика

### Проверка доступности:
```bash
telnet 192.168.0.91 4433
```

### Отладка:
```python
# Включить подробное логирование
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 Заключение

Проект успешно демонстрирует:

1. **✅ Подключение к Whatsminer API v3.0.1**
2. **✅ Получение температуры жидкости (49.6°C)**
3. **✅ Надежную аутентификацию и шифрование**
4. **✅ Обработку ошибок и мониторинг**
5. **✅ Готовые решения для промышленного применения**

Температура жидкости **49.6°C** - отличный показатель для майнера под нагрузкой, что подтверждает эффективность системы жидкостного охлаждения.

---

**Автор:** AI Assistant  
**Дата:** 2025-05-28  
**Версия:** 1.0  
**Статус:** ✅ Успешно завершено 