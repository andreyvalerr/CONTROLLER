#!/bin/bash
# Скрипт установки зависимостей для модуля получения температуры

echo "🌡️ Установка модуля получения температуры Whatsminer"
echo "=================================================="

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.7+"
    exit 1
fi

echo "✅ Python найден: $(python3 --version)"

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
    
    if [ $? -eq 0 ]; then
        echo "✅ Виртуальное окружение создано"
    else
        echo "❌ Ошибка создания виртуального окружения"
        exit 1
    fi
else
    echo "✅ Виртуальное окружение уже существует"
fi

# Активация виртуального окружения
echo "🔄 Активация виртуального окружения..."
source venv/bin/activate

# Обновление pip
echo "⬆️ Обновление pip..."
pip install --upgrade pip

# Установка зависимостей
echo "📦 Установка зависимостей..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Зависимости установлены успешно"
else
    echo "❌ Ошибка установки зависимостей"
    exit 1
fi

# Проверка установки
echo "🔍 Проверка установки..."
python -c "
try:
    from Crypto.Cipher import AES
    print('✅ pycryptodome установлен')
except ImportError:
    print('❌ pycryptodome не установлен')
    exit(1)

try:
    import requests
    print('✅ requests установлен')
except ImportError:
    print('❌ requests не установлен')
    exit(1)

print('✅ Все зависимости установлены корректно')
"

echo ""
echo "🚀 Установка завершена!"
echo ""
echo "Для использования модуля:"
echo "  source venv/bin/activate    # Активация окружения"
echo ""
echo "Для тестирования запустите:"
echo "  python main.py --test       # Тест подключения"
echo "  python main.py --config     # Показать конфигурацию"
echo "  python main.py --single     # Одно измерение"
echo "  python main.py              # Запуск мониторинга"
echo ""
echo "Для настройки IP адреса майнера:"
echo "  export MINER_IP='192.168.0.127'"
echo "  или отредактируйте config.py"
echo ""
echo "Для деактивации окружения:"
echo "  deactivate" 