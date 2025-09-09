#!/bin/bash
# Скрипт для запуска контроллера криптокотла

# Установка переменной DISPLAY для GUI
# Предполагается, что основной дисплей :0. При необходимости измените.
export DISPLAY=:0
# Если требуется, можно также установить XAUTHORITY, хотя это часто не нужно при запуске от имени вошедшего пользователя.
# export XAUTHORITY=/home/user/.Xauthority

# Переход в директорию проекта
cd /home/user/CONTROLLER

# Запуск основного скрипта приложения с аргументом для полноэкранного режима
# Гарантированный авто‑перезапуск при штатном закрытии GUI
# Убедитесь, что python3 указывает на нужную версию Python.

# Задержка перед повторным запуском (секунды). Можно переопределить переменной окружения RESTART_DELAY
RESTART_DELAY="${RESTART_DELAY:-5}"

# Корректно завершаем цикл по сигналу (остановка сервиса)
trap 'echo "[start_controller] Получен сигнал остановки, выходим"; exit 0' SIGTERM SIGINT

while true; do
    /usr/bin/python3 start_all_modules.py --auto-fullscreen
    exit_code=$?
    echo "[start_controller] Приложение завершилось с кодом ${exit_code}. Перезапуск через ${RESTART_DELAY}с..."
    sleep "$RESTART_DELAY"
done