#!/bin/bash

# Быстрый запуск мониторинга температуры
echo "🚀 Быстрый запуск мониторинга температуры асика"
echo "================================================"

# Переход в директорию проекта
cd "$(dirname "$0")"

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "💡 Запустите: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Активация виртуального окружения
echo "🔄 Активация виртуального окружения..."
source venv/bin/activate

# Проверка зависимостей
echo "🔍 Проверка зависимостей..."
python -c "import Crypto, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Зависимости не установлены!"
    echo "💡 Установка зависимостей..."
    pip install -r requirements.txt
fi

echo "✅ Все готово к запуску!"
echo ""

# Меню выбора
echo "Выберите способ запуска:"
echo "1) Простой мониторинг (API функции)"
echo "2) Мониторинг через класс API"
echo "3) Однократное получение температуры"
echo "4) Выход"
echo ""

read -p "Ваш выбор (1-4): " choice

case $choice in
    1)
        echo "🚀 Запуск простого мониторинга..."
        python start_monitoring.py
        ;;
    2)
        echo "🚀 Запуск мониторинга через класс..."
        python monitor_class.py
        ;;
    3)
        echo "🌡️ Получение температуры..."
        python test_simple.py
        ;;
    4)
        echo "👋 До свидания!"
        exit 0
        ;;
    *)
        echo "❌ Неверный выбор!"
        exit 1
        ;;
esac 