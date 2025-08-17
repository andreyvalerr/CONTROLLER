#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'

# Re-exec as root if needed
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
	exec sudo -E bash "$0" "$@"
fi

print_usage() {
	cat <<'USAGE'
Установка и настройка VNC на Raspberry Pi OS.

Использование:
  sudo ./install.sh [--mode {wayland-mirror|service-x11|virtual}] [--reboot] [--install-viewer]

Режимы:
  wayland-mirror  Зеркалирование текущего Wayland-экрана через WayVNC (порт 5900). [по умолчанию на Wayland]
  service-x11     RealVNC Server в Service Mode (зеркалирование X11-экрана, порт 5900). Требует X11-сеанс.
  virtual         RealVNC Server в Virtual Mode (виртуальный рабочий стол, порт 5999).

Опции:
  --reboot         Для service-x11: сразу перезагрузить систему после настройки.
  --install-viewer Установить также RealVNC Viewer.

Примеры:
  sudo ./install.sh                        # Автовыбор: Wayland→wayland-mirror, X11→service-x11
  sudo ./install.sh --mode virtual         # Виртуальный рабочий стол RealVNC (порт 5999)
  sudo ./install.sh --mode service-x11 --reboot  # Переключение на X11 и RealVNC Service Mode с перезагрузкой
USAGE
}

log() {
	echo -e "[realVNC] $*"
}

get_codename() {
	. /etc/os-release
	echo "${VERSION_CODENAME:-bookworm}"
}

get_ip() {
	hostname -I 2>/dev/null | awk '{print $1}' || true
}

detect_session_type() {
	local t
	t=${XDG_SESSION_TYPE:-}
	if [[ -z "${t}" ]]; then
		local sid
		sid=$(loginctl 2>/dev/null | awk 'NR==2{print $1}') || true
		if [[ -n "${sid}" ]]; then
			t=$(loginctl show-session "${sid}" -p Type 2>/dev/null | cut -d= -f2)
		fi
	fi
	echo "${t:-tty}"
}

ensure_repos() {
	local codename
	codename=$(get_codename)
	if ! grep -Rqs "archive.raspberrypi.com" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null; then
		log "Добавляю репозиторий Raspberry Pi..."
		echo "deb http://archive.raspberrypi.com/debian/ ${codename} main" > /etc/apt/sources.list.d/raspi.list
	fi
}

apt_install() {
	DEBIAN_FRONTEND=noninteractive apt-get update
	DEBIAN_FRONTEND=noninteractive apt-get install -y "$@"
}

configure_wayland_mirror() {
	log "Настройка зеркалирования Wayland через WayVNC (порт 5900)..."
	apt_install wayvnc wayvnc-control || true
	# Отключить RealVNC сервисы (освободить 5900)
	systemctl disable --now vncserver-x11-serviced vncserver-virtuald 2>/dev/null || true
	# Сгенерировать ключи TLS (если не созданы)
	systemctl start wayvnc-generate-keys.service 2>/dev/null || true
	# Включить WayVNC
	systemctl enable --now wayvnc wayvnc-control
	log "WayVNC включён. Подключение: vnc://$(get_ip):5900 (логин/пароль системные)"
}

configure_virtual_mode() {
	log "Настройка RealVNC Virtual Mode (порт 5999)..."
	apt_install realvnc-vnc-server || true
	systemctl disable --now wayvnc wayvnc-control vncserver-x11-serviced 2>/dev/null || true
	systemctl enable --now vncserver-virtuald
	log "Virtual Mode активен. Подключение: vnc://$(get_ip):5999"
}

configure_service_x11() {
	log "Настройка RealVNC Service Mode (X11, порт 5900)..."
	apt_install realvnc-vnc-server lightdm || true
	systemctl disable --now wayvnc wayvnc-control vncserver-virtuald 2>/dev/null || true
	mkdir -p /etc/lightdm/lightdm.conf.d
	cat > /etc/lightdm/lightdm.conf.d/90-x11-session.conf <<'CONF'
[Seat:*]
user-session=LXDE-pi-x
autologin-session=LXDE-pi-x
greeter-session=lightdm-gtk-greeter
CONF
	systemctl enable vncserver-x11-serviced
	local stype
	stype=$(detect_session_type)
	if [[ "${stype}" != "x11" && "${stype}" != "xorg" ]]; then
		log "Текущий сеанс: ${stype}. Для Service Mode нужен X11. Требуется перезагрузка."
		return 10
	else
		systemctl restart lightdm || true
		sleep 3 || true
		systemctl restart vncserver-x11-serviced || true
		log "Service Mode включён. Подключение: vnc://$(get_ip):5900"
	fi
}

# ----------- Парсинг аргументов -----------
MODE=""
DO_REBOOT="no"
INSTALL_VIEWER="no"

while [[ $# -gt 0 ]]; do
	case "$1" in
		-m|--mode)
			MODE=${2:-}
			shift 2 ;;
		--reboot)
			DO_REBOOT="yes"
			shift ;;
		--install-viewer)
			INSTALL_VIEWER="yes"
			shift ;;
		-h|--help)
			print_usage; exit 0 ;;
		*)
			log "Неизвестный параметр: $1"; print_usage; exit 1 ;;
	 esac
done

# Определить режим по умолчанию
if [[ -z "${MODE}" ]]; then
	stype=$(detect_session_type)
	if [[ "${stype}" == "wayland" ]]; then
		MODE="wayland-mirror"
	else
		MODE="service-x11"
	fi
fi

ensure_repos || true

# Общие пакеты
COMMON_PKGS=(realvnc-vnc-server wayvnc wayvnc-control)
if [[ "${INSTALL_VIEWER}" == "yes" ]]; then
	COMMON_PKGS+=(realvnc-vnc-viewer)
fi
apt_install "${COMMON_PKGS[@]}" || true

rc=0
case "${MODE}" in
	wayland-mirror)
		configure_wayland_mirror || rc=$? ;;
	service-x11)
		configure_service_x11 || rc=$? ;;
	virtual)
		configure_virtual_mode || rc=$? ;;
	*)
		log "Неизвестный режим: ${MODE}"; print_usage; exit 2 ;;
esac

log "Порты VNC:" || true
ss -tulpn 2>/dev/null | awk 'NR==1 || /:(5900|5999)\b/' || true

if [[ ${rc} -eq 10 && "${DO_REBOOT}" == "yes" ]]; then
	log "Перезагрузка..."; sleep 2; systemctl reboot
elif [[ ${rc} -eq 10 ]]; then
	log "Перезагрузите систему для перехода на X11: sudo reboot"
fi

log "Готово. Текущий IP: $(get_ip)"


