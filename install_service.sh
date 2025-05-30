#!/bin/bash

echo "🔧 УСТАНОВКА СЕРВИСА CRYPTO BOILER С GUI"
echo "========================================"

# Проверка прав root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с правами root: sudo ./install_service.sh"
    exit 1
fi

# Копирование файла сервиса
echo "📁 Копирование файла сервиса..."
cp crypto-boiler.service /etc/systemd/system/

# Установка прав доступа
chmod 644 /etc/systemd/system/crypto-boiler.service

# Перезагрузка systemd
echo "🔄 Перезагрузка systemd..."
systemctl daemon-reload

# Включение автозапуска
echo "🚀 Включение автозапуска..."
systemctl enable crypto-boiler.service

echo "✅ Сервис с GUI установлен успешно!"
echo ""
echo "📋 КОМАНДЫ УПРАВЛЕНИЯ СЕРВИСОМ:"
echo "  Запуск:    sudo systemctl start crypto-boiler"
echo "  Остановка: sudo systemctl stop crypto-boiler"
echo "  Статус:    sudo systemctl status crypto-boiler"
echo "  Логи:      sudo journalctl -u crypto-boiler -f"
echo "  Отключить: sudo systemctl disable crypto-boiler"
echo ""
echo "🖥️ ВНИМАНИЕ: Теперь система запускается с GUI интерфейсом!"
echo "📊 GUI будет отображаться на подключенном дисплее"
echo ""
echo "🔥 Для запуска сервиса выполните:"
echo "   sudo systemctl start crypto-boiler" 