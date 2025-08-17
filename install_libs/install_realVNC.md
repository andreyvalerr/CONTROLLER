Создаю исполняемый скрипт `realVNC` с установкой и автонастройкой в режимах: зеркалирование Wayland (по умолчанию), Service Mode (X11) и Virtual Mode. Затем сделаю файл исполняемым.
Ran tool

Создам исполняемый скрипт установки/настройки VNC в `\`/home/user/CONTROLLER/realVNC/install.sh\`` и затем помечу его как исполняемый.
Ran tool
```bash
chmod +x /home/user/CONTROLLER/realVNC/install.sh
```
Скрипт готов и отмечен как исполняемый.

Как запускать
- Зеркалирование экрана на Wayland (по умолчанию):
```bash
sudo /home/user/CONTROLLER/realVNC/install.sh
```
- Явно указать режим:
```bash
# Wayland зеркалирование (порт 5900)
sudo /home/user/CONTROLLER/realVNC/install.sh --mode wayland-mirror

# Service Mode (X11, порт 5900). Если сейчас Wayland, добавьте перезагрузку:
sudo /home/user/CONTROLLER/realVNC/install.sh --mode service-x11 --reboot

# Virtual Mode (виртуальный рабочий стол, порт 5999)
sudo /home/user/CONTROLLER/realVNC/install.sh --mode virtual
```
- Установить также Viewer:
```bash
sudo /home/user/CONTROLLER/realVNC/install.sh --install-viewer
```

Что делает
- Автообнаруживает тип сессии и выбирает подходящий режим.
- Устанавливает нужные пакеты, включает соответствующие службы.
- Для X11 создаёт `LightDM` drop-in `90-x11-session.conf` с `LXDE-pi-x`.
- Показывает, какие порты слушают: 5900 (зеркалирование) или 5999 (виртуальный).

Если нужно другое имя/расположение скрипта — скажи, перенесу.