# 🚀 ЗАПУСК СИСТЕМЫ КОНТРОЛЯ ТЕМПЕРАТУРЫ

## Способы запуска

### 1. 🧪 Тестовый запуск (ручной)

```bash
cd CONTROLLER
python3 start_system.py
```

**Особенности:**
- Запуск в текущем терминале
- Остановка по Ctrl+C
- Подходит для тестирования и отладки

### 2. 🔧 Запуск как системный сервис

#### Установка сервиса:
```bash
cd CONTROLLER
chmod +x install_service.sh
sudo ./install_service.sh
```

#### Управление сервисом:
```bash
# Запуск
sudo systemctl start crypto-boiler

# Остановка
sudo systemctl stop crypto-boiler

# Статус
sudo systemctl status crypto-boiler

# Просмотр логов в реальном времени
sudo journalctl -u crypto-boiler -f

# Отключение автозапуска
sudo systemctl disable crypto-boiler
```

### 3. 🏃‍♂️ Запуск в фоне

```bash
cd CONTROLLER
nohup python3 start_system.py > system.log 2>&1 &
```

## 📊 Мониторинг системы

### Проверка статуса:
```python
from valve_control.valve_controller import ValveController
controller = ValveController()
status = controller.get_status()
print(status)
```

### Просмотр логов:
```bash
# Логи сервиса
sudo journalctl -u crypto-boiler --since "1 hour ago"

# Логи файла (если запущено через nohup)
tail -f system.log
```

## ⚙️ Настройки

### Переменные окружения:
- `GPIO_PIN` - номер GPIO пина для реле (по умолчанию: 17)
- `ASIC_IP` - IP адрес ASIC (по умолчанию: 192.168.0.91)
- `MAX_TEMP` - максимальная температура (по умолчанию: 40.0°C)
- `MIN_TEMP` - минимальная температура (по умолчанию: 35.0°C)
- `CRITICAL_TEMP` - критическая температура (по умолчанию: 50.0°C)

### Пример с настройками:
```bash
export GPIO_PIN=18
export MAX_TEMP=45.0
python3 start_system.py
```

## 🚨 Безопасность

### Важные моменты:
1. **GPIO доступ**: Убедитесь, что пользователь входит в группу `gpio`
2. **Сетевой доступ**: ASIC должен быть доступен по сети
3. **Автозапуск**: Сервис автоматически перезапускается при сбоях
4. **Логирование**: Все события записываются в журнал

### Добавление пользователя в группу gpio:
```bash
sudo usermod -a -G gpio $USER
# Перелогиньтесь после выполнения команды
```

## 🔍 Диагностика

### Проверка подключения к ASIC:
```bash
cd CONTROLLER
python3 -c "
from get_temperature.simple_monitor import SimpleTemperatureMonitor
monitor = SimpleTemperatureMonitor('192.168.0.91')
data = monitor.get_temperature_reading()
print(f'Температура: {data.liquid_temperature}°C' if data and data.liquid_temperature else 'Ошибка подключения')
"
```

### Проверка GPIO:
```bash
# Проверка доступности GPIO
ls -la /dev/gpiomem

# Проверка группы пользователя
groups $USER
```

## 📈 Рекомендации

1. **Для продакшена**: Используйте systemd сервис
2. **Для разработки**: Используйте ручной запуск
3. **Мониторинг**: Настройте регулярную проверку логов
4. **Резервное копирование**: Сохраняйте конфигурацию системы 