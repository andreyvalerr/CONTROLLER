#!/bin/bash

# Скрипт запуска valve_control с интеграцией data_manager
# Убедитесь, что data_manager core_system уже запущен

echo "=== ЗАПУСК VALVE_CONTROL С DATA_MANAGER ИНТЕГРАЦИЕЙ ==="
echo ""

# Переход в директорию модуля
cd /home/user/CONTROLLER/valve_control

echo "Проверка доступности модулей..."

# Проверка data_manager
python3 -c "
try:
    from data_manager.core_system import get_temperature_data
    print('✓ data_manager модуль доступен')
except ImportError as e:
    print('✗ data_manager модуль недоступен:', e)
    exit(1)
" || exit 1

# Проверка get_temperature_from_asic
python3 -c "
try:
    from get_temperature_from_asic import get_current_temperature
    print('✓ get_temperature_from_asic модуль доступен')
except ImportError as e:
    print('✗ get_temperature_from_asic модуль недоступен:', e)
    exit(1)
" || exit 1

echo ""
echo "Все модули доступны. Запуск valve_control..."
echo "Нажмите Ctrl+C для остановки"
echo ""

# Запуск основного модуля
python3 main.py "$@" 