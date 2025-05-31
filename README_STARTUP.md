# 🚀 ЗАПУСК СИСТЕМЫ КОНТРОЛЯ ТЕМПЕРАТУРЫ С GUI

## 🖥️ Важное изменение
**Система теперь работает только с GUI интерфейсом!**
Консольная версия (start_system.py) была удалена.

## Способы запуска

### 1. 🧪 Тестовый запуск (ручной)

```bash
cd CONTROLLER
python3 start_system_with_gui.py
```

**Особенности:**
- Запуск с графическим интерфейсом
- Отображение на подключенном дисплее
- Остановка по закрытию окна GUI или Ctrl+C
- Подходит для тестирования и отладки

**Требования:**
- Установленная библиотека Kivy
- Подключенный дисплей (HDMI/DSI)
- Доступ к X-серверу (DISPLAY=:0)

### 2. 🔧 Запуск как системный сервис (рекомендуется)

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

### 3. 🏃‍♂️ Запуск в фоне с GUI

```bash
cd CONTROLLER
DISPLAY=:0 nohup python3 start_system_with_gui.py > system.log 2>&1 &
```

## 🖥️ GUI Интерфейс

### Особенности GUI:
- **Карточка температуры**: Отображение текущей и целевой температуры
- **Статус системы**: Состояние клапанов и режим работы
- **Панель управления**: Настройки температуры и ручное управление
- **Реальное время**: Обновление данных каждую секунду
- **Цветовая индикация**: Зеленый/красный/синий для разных состояний

### Требования для GUI:
```bash
# Проверка Kivy
python3 -c "import kivy; print('Kivy доступен')"

# Проверка дисплея
echo $DISPLAY
```

## 📊 Мониторинг системы

### Проверка статуса:
```python
# Через core модуль
from core.shared_state import system_state
status = system_state.get_current_data()
print(f"Температура: {status.temperature}°C")
print(f"Клапан: {'ОТКРЫТ' if status.valve_state else 'ЗАКРЫТ'}")
```

### Просмотр логов:
```bash
# Логи сервиса с GUI
sudo journalctl -u crypto-boiler --since "1 hour ago"

# Логи файла (если запущено через nohup)
tail -f system.log
```

## ⚙️ Настройки

### Переменные окружения:
- `DISPLAY` - дисплей для GUI (по умолчанию: :0)
- `GPIO_PIN` - номер GPIO пина для реле (по умолчанию: 17)
- `ASIC_IP` - IP адрес ASIC (по умолчанию: 192.168.0.127)
- `MAX_TEMP` - максимальная температура (по умолчанию: 52.0°C)
- `MIN_TEMP` - минимальная температура (по умолчанию: 51.9°C)

### Пример с настройками:
```bash
export DISPLAY=:0
export GPIO_PIN=18
export MAX_TEMP=45.0
python3 start_system_with_gui.py
```

## 🚨 Безопасность

### Важные моменты:
1. **GUI доступ**: Убедитесь, что переменная DISPLAY установлена
2. **GPIO доступ**: Убедитесь, что пользователь входит в группу `gpio`
3. **Сетевой доступ**: ASIC должен быть доступен по сети
4. **Автозапуск**: Сервис автоматически перезапускается при сбоях
5. **Логирование**: Все события записываются в журнал

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
from get_temperature_from_asic.simple_monitor import SimpleTemperatureMonitor
monitor = SimpleTemperatureMonitor('192.168.0.127')
data = monitor.get_temperature_reading()
print(f'Температура: {data.liquid_temperature}°C' if data and data.liquid_temperature else 'Ошибка подключения')
"
```

### Проверка GUI зависимостей:
```bash
# Проверка Kivy
python3 -c "import kivy; print('✅ Kivy установлен')"

# Проверка дисплея
echo "DISPLAY: $DISPLAY"

# Проверка X-сервера
xdpyinfo | head -5
```

### Проверка GPIO:
```bash
# Проверка доступности GPIO
ls -la /dev/gpiomem

# Проверка группы пользователя
groups $USER
```

## 📈 Рекомендации

1. **Для продакшена**: Используйте systemd сервис с автозапуском
2. **Для разработки**: Используйте ручной запуск с GUI
3. **Дисплей**: Подключите HDMI или DSI дисплей для отображения GUI
4. **Мониторинг**: Настройте регулярную проверку логов через journalctl
5. **Резервное копирование**: Сохраняйте конфигурацию системы

## 🎯 Системные файлы

- **Основной запуск**: `start_system_with_gui.py`
- **Сервис**: `crypto-boiler.service`
- **Установка**: `install_service.sh`
- **GUI интерфейс**: `gui_interface/main_gui.py` 