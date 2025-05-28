# 🌡️ Руководство по получению температуры жидкости Whatsminer API v3.0.0

## 📋 Оглавление
1. [Архитектура системы](#архитектура-системы)
2. [Протокол связи](#протокол-связи)
3. [Процесс аутентификации](#процесс-аутентификации)
4. [Структура команд API](#структура-команд-api)
5. [Получение температурных данных](#получение-температурных-данных)
6. [Обработка ошибок](#обработка-ошибок)
7. [Практические примеры](#практические-примеры)
8. [Оптимизация и лучшие практики](#оптимизация-и-лучшие-практики)

---

## 🏗️ Архитектура системы

### Компоненты системы:
```
┌─────────────────┐    TCP/IP     ┌─────────────────┐
│   Python Client │ ◄──────────► │  Whatsminer     │
│                 │   Port 4433   │  M64_VL40       │
│ - API Interface │               │ - Liquid Cooling│
│ - TCP Transport │               │ - Temperature   │
│ - Crypto Module │               │   Sensors       │
└─────────────────┘               └─────────────────┘
```

### Основные модули:
- **`WhatsminerAPIv3`** - Интерфейс API, формирование команд
- **`WhatsminerTCP`** - TCP транспорт, сетевое взаимодействие
- **Crypto (AES)** - Шифрование данных для безопасности

---

## 🔌 Протокол связи

### Параметры подключения:
```python
IP_ADDRESS = "192.168.0.91"    # IP адрес майнера
PORT = 4433                    # Стандартный порт API v3
ACCOUNT = "super"              # Учетная запись (super/admin/user1)
PASSWORD = "super"             # Пароль
```

### Структура TCP пакета:
```
┌──────────────┬──────────────┬──────────────┐
│   Header     │   Length     │    Data      │
│   (4 bytes)  │   (4 bytes)  │  (variable)  │
└──────────────┴──────────────┴──────────────┘
```

---

## 🔐 Процесс аутентификации

### Шаг 1: Установка соединения
```python
whatsminer_tcp = WhatsminerTCP(ip_address, port, account, password)
whatsminer_tcp.connect()
```

### Шаг 2: Получение salt для шифрования
```python
# Отправляем команду get.device.info
req_info = whatsminer_api.get_request_cmds("get.device.info")
rsp_info = whatsminer_tcp.send(req_info, len(req_info))

# Извлекаем salt из ответа
if rsp_info['code'] == 0:
    miner_salt = rsp_info['msg']['salt']
    whatsminer_api.set_salt(miner_salt)
```

### Шаг 3: Настройка шифрования
```python
# Salt используется для AES шифрования последующих команд
# Это обеспечивает безопасность передачи данных
```

---

## 📡 Структура команд API

### Формат запроса:
```json
{
    "cmd": "get.device.info",
    "param": null
}
```

### Формат ответа:
```json
{
    "code": 0,                    // 0 = успех, -1/-2 = ошибка
    "when": 1748425808,          // Unix timestamp
    "msg": {                     // Данные ответа
        "power": {
            "liquid-temperature": 49.7,
            "temp0": 55.9,
            "fanspeed": 49.7
        },
        "salt": "BQ5hoXV9"       // Salt для шифрования
    }
}
```

### Коды ошибок:
- **0** - Успешное выполнение
- **-1** - Неверные параметры (invalid param)
- **-2** - Неизвестная команда (invalid command)

---

## 🌡️ Получение температурных данных

### Основная команда: `get.device.info`

Эта команда возвращает полную информацию об устройстве, включая температурные данные:

```python
def get_temperature_data(whatsminer_tcp, whatsminer_api):
    # Формируем запрос
    req_info = whatsminer_api.get_request_cmds("get.device.info")
    
    # Отправляем запрос
    rsp_info = whatsminer_tcp.send(req_info, len(req_info))
    
    if rsp_info['code'] == 0:
        device_info = rsp_info['msg']
        power_info = device_info.get('power', {})
        
        # Извлекаем температурные данные
        liquid_temp = power_info.get('liquid-temperature')  # Температура жидкости
        psu_temp = power_info.get('temp0')                 # Температура БП
        fan_speed = power_info.get('fanspeed')             # Скорость вентилятора
        
        return liquid_temp, psu_temp, fan_speed
```

### Структура данных температуры:

```json
{
    "power": {
        "type": "P738B",                    // Тип блока питания
        "liquid-temperature": 49.7,         // 🌡️ ТЕМПЕРАТУРА ЖИДКОСТИ
        "temp0": 55.9,                      // Температура БП
        "fanspeed": 49.7,                   // Скорость вентилятора %
        "iin": 18.28,                       // Входной ток
        "vin": 230.75,                      // Входное напряжение
        "vout": 1936,                       // Выходное напряжение
        "pin": 4144                         // Входная мощность
    }
}
```

---

## ⚠️ Обработка ошибок

### Типы ошибок и их обработка:

```python
def handle_api_errors(response):
    """Обработка ошибок API"""
    
    if response['code'] == 0:
        return True, "Успех"
    
    elif response['code'] == -1:
        return False, "Неверные параметры команды"
    
    elif response['code'] == -2:
        return False, "Неизвестная команда API"
    
    else:
        return False, f"Неизвестная ошибка: {response['code']}"

def handle_network_errors():
    """Обработка сетевых ошибок"""
    try:
        # Код подключения
        pass
    except ConnectionRefusedError:
        return "Майнер недоступен или API отключен"
    except TimeoutError:
        return "Таймаут подключения"
    except Exception as e:
        return f"Сетевая ошибка: {e}"
```

---

## 💻 Практические примеры

### Пример 1: Простое получение температуры

```python
#!/usr/bin/env python3
import sys
sys.path.append('1729070366369python-whatsminer-api-3.0.0')

from whatsminer_trans import WhatsminerTCP
from whatsminer_interface import WhatsminerAPIv3

def get_liquid_temp_simple(ip):
    """Простое получение температуры жидкости"""
    
    # Инициализация
    api = WhatsminerAPIv3("super", "super")
    tcp = WhatsminerTCP(ip, 4433, "super", "super")
    
    try:
        # Подключение
        tcp.connect()
        
        # Аутентификация
        req = api.get_request_cmds("get.device.info")
        resp = tcp.send(req, len(req))
        
        if resp['code'] == 0:
            # Установка salt
            api.set_salt(resp['msg']['salt'])
            
            # Извлечение температуры
            liquid_temp = resp['msg']['power']['liquid-temperature']
            
            tcp.close()
            return liquid_temp
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

# Использование
temp = get_liquid_temp_simple("192.168.0.91")
print(f"Температура жидкости: {temp}°C")
```

### Пример 2: Мониторинг с логированием

```python
import datetime
import json

def monitor_with_logging(ip, duration_minutes=60):
    """Мониторинг с сохранением в файл"""
    
    log_data = []
    start_time = datetime.datetime.now()
    end_time = start_time + datetime.timedelta(minutes=duration_minutes)
    
    while datetime.datetime.now() < end_time:
        temp = get_liquid_temp_simple(ip)
        
        if temp:
            log_entry = {
                'timestamp': datetime.datetime.now().isoformat(),
                'liquid_temperature': temp,
                'status': 'normal' if temp < 55 else 'warning' if temp < 60 else 'critical'
            }
            
            log_data.append(log_entry)
            print(f"{log_entry['timestamp']}: {temp}°C ({log_entry['status']})")
        
        time.sleep(60)  # Измерение каждую минуту
    
    # Сохранение в файл
    with open(f'temperature_log_{start_time.strftime("%Y%m%d_%H%M")}.json', 'w') as f:
        json.dump(log_data, f, indent=2)
```

### Пример 3: Класс для работы с температурой

```python
class WhatsminerTemperatureMonitor:
    """Класс для мониторинга температуры Whatsminer"""
    
    def __init__(self, ip_address, account="super", password="super"):
        self.ip = ip_address
        self.account = account
        self.password = password
        self.api = WhatsminerAPIv3(account, password)
        
    def connect(self):
        """Установка соединения"""
        self.tcp = WhatsminerTCP(self.ip, 4433, self.account, self.password)
        self.tcp.connect()
        
        # Аутентификация
        req = self.api.get_request_cmds("get.device.info")
        resp = self.tcp.send(req, len(req))
        
        if resp['code'] == 0:
            self.api.set_salt(resp['msg']['salt'])
            return True
        return False
    
    def get_temperatures(self):
        """Получение всех температурных данных"""
        req = self.api.get_request_cmds("get.device.info")
        resp = self.tcp.send(req, len(req))
        
        if resp['code'] == 0:
            power = resp['msg']['power']
            return {
                'liquid_temp': power.get('liquid-temperature'),
                'psu_temp': power.get('temp0'),
                'fan_speed': power.get('fanspeed'),
                'timestamp': datetime.datetime.now()
            }
        return None
    
    def disconnect(self):
        """Закрытие соединения"""
        if hasattr(self, 'tcp'):
            self.tcp.close()

# Использование класса
monitor = WhatsminerTemperatureMonitor("192.168.0.91")
if monitor.connect():
    temps = monitor.get_temperatures()
    print(f"Температура жидкости: {temps['liquid_temp']}°C")
    monitor.disconnect()
```

---

## 🚀 Оптимизация и лучшие практики

### 1. Управление соединениями

```python
# ❌ Плохо - создание нового соединения для каждого запроса
def bad_approach():
    for i in range(100):
        tcp = WhatsminerTCP(ip, port, account, password)
        tcp.connect()
        # ... запрос
        tcp.close()

# ✅ Хорошо - переиспользование соединения
def good_approach():
    tcp = WhatsminerTCP(ip, port, account, password)
    tcp.connect()
    
    for i in range(100):
        # ... запросы
        pass
    
    tcp.close()
```

### 2. Обработка исключений

```python
def robust_temperature_reading(ip):
    """Надежное чтение температуры с повторными попытками"""
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # Попытка получения данных
            temp = get_liquid_temp_simple(ip)
            if temp is not None:
                return temp
                
        except Exception as e:
            print(f"Попытка {attempt + 1} неудачна: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    return None
```

### 3. Кэширование и оптимизация

```python
class CachedTemperatureReader:
    """Чтение температуры с кэшированием"""
    
    def __init__(self, ip, cache_duration=30):
        self.ip = ip
        self.cache_duration = cache_duration
        self.last_reading = None
        self.last_time = None
    
    def get_temperature(self):
        now = datetime.datetime.now()
        
        # Проверяем кэш
        if (self.last_reading and self.last_time and 
            (now - self.last_time).seconds < self.cache_duration):
            return self.last_reading
        
        # Получаем новые данные
        temp = get_liquid_temp_simple(self.ip)
        if temp:
            self.last_reading = temp
            self.last_time = now
        
        return temp
```

### 4. Мониторинг производительности

```python
import time

def performance_monitor():
    """Мониторинг производительности API"""
    
    start_time = time.time()
    
    # Выполнение запроса
    temp = get_liquid_temp_simple("192.168.0.91")
    
    end_time = time.time()
    response_time = end_time - start_time
    
    print(f"Время ответа: {response_time:.2f} сек")
    print(f"Температура: {temp}°C")
    
    return response_time
```

---

## 📊 Структура данных майнера

### Полная структура ответа `get.device.info`:

```json
{
  "network": {
    "ip": "192.168.0.91",
    "proto": "dhcp",
    "netmask": "255.255.255.0",
    "dns": "192.168.0.1",
    "mac": "A0:53:0A:00:00:2A",
    "gateway": "192.168.0.1",
    "hostname": "WhatsMiner"
  },
  "miner": {
    "working": "true",
    "type": "M64_VL40",              // Модель с жидкостным охлаждением
    "hash-board": "L40",
    "cointype": "BTC",
    "board-num": "4",
    "miner-sn": "HTM40X40HR25041019880203044H48181"
  },
  "system": {
    "api": "3.0.1",                 // Версия API
    "platform": "H616",
    "fwversion": "20250409.15.REL",
    "control-board-version": "CB6V5"
  },
  "power": {
    "type": "P738B",                // Тип блока питания
    "liquid-temperature": 49.7,     // 🌡️ ТЕМПЕРАТУРА ЖИДКОСТИ
    "temp0": 55.9,                  // Температура БП
    "fanspeed": 49.7,               // Скорость вентилятора
    "iin": 18.28,                   // Входной ток (A)
    "vin": 230.75,                  // Входное напряжение (V)
    "vout": 1936,                   // Выходное напряжение (mV)
    "pin": 4144                     // Входная мощность (W)
  },
  "salt": "BQ5hoXV9",              // Salt для шифрования
  "error-code": []                 // Коды ошибок
}
```

---

## 🔧 Диагностика и отладка

### Проверка доступности API:

```python
def check_api_availability(ip):
    """Проверка доступности API"""
    
    import socket
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, 4433))
        sock.close()
        
        if result == 0:
            print("✅ Порт 4433 открыт")
            return True
        else:
            print("❌ Порт 4433 закрыт")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
        return False
```

### Логирование для отладки:

```python
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('whatsminer_debug.log'),
        logging.StreamHandler()
    ]
)

def debug_temperature_request(ip):
    """Отладочная версия запроса температуры"""
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Подключение к {ip}:4433")
        
        api = WhatsminerAPIv3("super", "super")
        tcp = WhatsminerTCP(ip, 4433, "super", "super")
        
        tcp.connect()
        logger.info("Соединение установлено")
        
        req = api.get_request_cmds("get.device.info")
        logger.debug(f"Отправка команды: {req}")
        
        resp = tcp.send(req, len(req))
        logger.debug(f"Получен ответ: {resp}")
        
        if resp['code'] == 0:
            temp = resp['msg']['power']['liquid-temperature']
            logger.info(f"Температура жидкости: {temp}°C")
            return temp
        else:
            logger.error(f"Ошибка API: {resp}")
            return None
            
    except Exception as e:
        logger.exception(f"Исключение: {e}")
        return None
    finally:
        tcp.close()
        logger.info("Соединение закрыто")
```

---

## 📈 Заключение

### Ключевые моменты:

1. **API v3.0.1** - Современная версия с поддержкой жидкостного охлаждения
2. **Команда `get.device.info`** - Основной источник температурных данных
3. **Поле `power.liquid-temperature`** - Прямое значение температуры жидкости
4. **TCP порт 4433** - Стандартный порт для API v3
5. **Аутентификация через salt** - Безопасность передачи данных

### Преимущества данного подхода:

- ✅ Прямой доступ к температуре жидкости
- ✅ Надежная аутентификация
- ✅ Минимальная нагрузка на майнер
- ✅ Быстрый отклик (< 1 секунды)
- ✅ Дополнительные данные (БП, вентиляторы)

### Применение в проектах:

- 🏭 **Промышленный мониторинг** - Контроль температуры в дата-центрах
- 📊 **Системы аналитики** - Сбор данных для оптимизации
- ⚠️ **Системы предупреждений** - Автоматические уведомления о перегреве
- 🔧 **Автоматизация** - Управление системами охлаждения

Этот механизм обеспечивает надежный и эффективный способ мониторинга температуры жидкостного охлаждения Whatsminer для любых промышленных и исследовательских проектов. 