#!/usr/bin/env bash
set -euo pipefail

# Инсталлятор и конфигуратор CONTROLLER по шагам из раздела "## 🚀 Установка" README
# Делает:
#  1) Обновление системы и установка пакетов GUI/LightDM/X и Python зависимостей (apt)
#  2) Установку Python-зависимостей из requirements.txt (pip или в venv при --venv)
#  3) Настройку автологина LightDM
#  4) Установку и включение systemd-сервиса cryptoboiler.service
#  5) Настройку киоск-режима в оконном виде (курсор виден, есть рамка окна)

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
REQ_FILE="$PROJECT_DIR/requirements.txt"
SERVICE_SRC="$PROJECT_DIR/start/cryptoboiler.service"
SERVICE_DST="/etc/systemd/system/cryptoboiler.service"
LIGHTDM_DIR="/etc/lightdm/lightdm.conf.d"
AUTOLOGIN_CONF="$LIGHTDM_DIR/11-autologin.conf"
KIVY_CONFIG_DIR="$HOME/.kivy"
KIVY_CONFIG="$KIVY_CONFIG_DIR/config.ini"
LXSESSION_AUTOSTART_DIR="$HOME/.config/lxsession/LXDE-pi"
LXSESSION_AUTOSTART="$LXSESSION_AUTOSTART_DIR/autostart"
START_SH="$PROJECT_DIR/start/start_controller.sh"

usage() {
	echo "Usage: $0 [--venv <path>] [--check] [--user <name>] [--no-systemd] [--no-lightdm] [--no-kiosk] [--no-vnc] [--no-upgrade] [--reboot]" >&2
	echo "  --venv <path>    Установить Python-пакеты в указанный venv через pip" >&2
	echo "  --check          Проверить импорты после установки" >&2
	echo "  --user <name>    Пользователь для автологина LightDM (по умолчанию SUDO_USER/USER)" >&2
	echo "  --no-systemd     Пропустить установку/включение systemd-сервиса" >&2
	echo "  --no-lightdm     Пропустить настройку автологина LightDM" >&2
	echo "  --no-kiosk       Пропустить настройку киоск-режима (оконного)" >&2
	echo "  --no-vnc         Пропустить настройку VNC" >&2
	echo "  --no-upgrade     Пропустить apt upgrade (оставить только install)" >&2
	echo "  --reboot         Перезагрузить систему в конце" >&2
}

VENV_PATH=""
DO_CHECK=false
SKIP_SYSTEMD=false
SKIP_LIGHTDM=false
SKIP_KIOSK=false
SKIP_VNC=false
SKIP_UPGRADE=false
DO_REBOOT=false
AUTOLOGIN_USER="${SUDO_USER:-${USER}}"

while [[ $# -gt 0 ]]; do
	case "$1" in
		--venv)
			shift
			VENV_PATH="${1:-}"
			[[ -z "$VENV_PATH" ]] && { echo "error: --venv требует путь" >&2; exit 1; }
			shift
			;;
		--check)
			DO_CHECK=true; shift;
			;;
		--user)
			shift
			AUTOLOGIN_USER="${1:-}"
			[[ -z "$AUTOLOGIN_USER" ]] && { echo "error: --user требует имя" >&2; exit 1; }
			shift
			;;
		--no-systemd)
			SKIP_SYSTEMD=true; shift;
			;;
		--no-lightdm)
			SKIP_LIGHTDM=true; shift;
			;;
		--no-kiosk)
			SKIP_KIOSK=true; shift;
			;;
		--no-vnc)
			SKIP_VNC=true; shift;
			;;
		--no-upgrade)
			SKIP_UPGRADE=true; shift;
			;;
		--reboot)
			DO_REBOOT=true; shift;
			;;
		-h|--help)
			usage; exit 0;
			;;
		*)
			echo "error: неизвестный аргумент: $1" >&2
			usage; exit 1
			;;
	esac
done

log() { echo "[+] $*"; }
warn() { echo "[warn] $*"; }
ok() { echo "[ok] $*"; }

step_apt_prepare() {
	log "Обновляю индексы пакетов (apt update)"
	sudo DEBIAN_FRONTEND=noninteractive apt-get update
	if ! $SKIP_UPGRADE; then
		log "Обновляю установленные пакеты (apt upgrade)"
		sudo DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
	else
		warn "Пропускаю apt upgrade (задан --no-upgrade)"
	fi
}

step_apt_install() {
	log "Устанавливаю GUI/LightDM/X и Python-зависимости (apt install)"
	sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
		raspberrypi-ui-mods \
		lightdm \
		x11-xserver-utils \
		curl \
		rsync \
		python3-pip \
		python3-kivy \
		python3-pycryptodome \
		python3-rpi.gpio || true
}

ensure_venv() {
	if [[ -n "$VENV_PATH" ]]; then
		log "Создаю/активирую venv: $VENV_PATH"
		python3 -m venv "$VENV_PATH"
		source "$VENV_PATH/bin/activate"
		python -m pip install --upgrade pip
	fi
}

step_python_requirements() {
	if [[ -n "$VENV_PATH" ]]; then
		log "Устанавливаю зависимости из requirements.txt в venv"
		pip install -r "$REQ_FILE"
	else
		log "Устанавливаю зависимости из requirements.txt в системную среду (--break-system-packages)"
		pip3 install -r "$REQ_FILE" --break-system-packages || warn "При ошибке используйте --venv <path>"
	fi
}

step_lightdm_autologin() {
	$SKIP_LIGHTDM && { warn "Пропускаю настройку LightDM (задан --no-lightdm)"; return; }
	log "Настраиваю автологин LightDM для пользователя: $AUTOLOGIN_USER"
	sudo mkdir -p "$LIGHTDM_DIR"
	printf "[Seat:*]\nautologin-user=%s\nautologin-user-timeout=0\n" "$AUTOLOGIN_USER" | sudo tee "$AUTOLOGIN_CONF" >/dev/null
}

step_add_user_gpio() {
	log "Добавляю пользователя $AUTOLOGIN_USER в группу gpio"
	if id "$AUTOLOGIN_USER" >/dev/null 2>&1; then
		sudo usermod -a -G gpio "$AUTOLOGIN_USER" || warn "Не удалось добавить пользователя в группу gpio"
	else
		warn "Пользователь $AUTOLOGIN_USER не найден — пропускаю добавление в gpio"
	fi
}

step_systemd_service() {
	$SKIP_SYSTEMD && { warn "Пропускаю установку systemd-сервиса (задан --no-systemd)"; return; }
	log "Устанавливаю systemd-сервис cryptoboiler"
	sudo cp "$SERVICE_SRC" "$SERVICE_DST"
	sudo systemctl daemon-reload
	sudo systemctl enable cryptoboiler.service
	log "Включаю графический таргет по умолчанию"
	sudo systemctl set-default graphical.target
}

step_kiosk_windowed() {
	$SKIP_KIOSK && { warn "Пропускаю настройку киоск-режима (задан --no-kiosk)"; return; }
	log "Создаю конфиг Kivy (полноэкранный киоск, курсор включен)"
	mkdir -p "$KIVY_CONFIG_DIR"
	cat > "$KIVY_CONFIG" << 'EOF'
[graphics]
fullscreen = 1
borderless = 1
show_cursor = 1
width = 800
height = 480
EOF
	log "Отключаю бланкинг/DPMS через автозапуск LXDE"
	mkdir -p "$LXSESSION_AUTOSTART_DIR"
	cat > "$LXSESSION_AUTOSTART" << 'EOF'
@xset s off
@xset -dpms
@xset s noblank
EOF
	if [[ ! -f "$START_SH" ]]; then
		warn "Скрипт запуска не найден: $START_SH"
	fi
}

step_vnc_setup() {
	$SKIP_VNC && { warn "Пропускаю настройку VNC (задан --no-vnc)"; return; }
	if [[ -x "$PROJECT_DIR/install_libs/install_realVNC.sh" ]]; then
		log "Настраиваю VNC (как на текущем устройстве)"
		bash "$PROJECT_DIR/install_libs/install_realVNC.sh" || warn "Скрипт VNC завершился с предупреждением"
	else
		warn "Скрипт VNC не найден: $PROJECT_DIR/install_libs/install_realVNC.sh"
	fi
}

step_install_updater() {
	local updater="/usr/local/bin/cryptoboiler-update"
	log "Устанавливаю скрипт обновления через GitHub Releases: $updater"
	sudo bash -c "cat > '$updater' <<'UPD'
#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/${SUDO_USER:-$USER}/CONTROLLER"

# Параметр: --repo-url=https://github.com/<owner>/<repo>
REPO_URL=""
for arg in "$@"; do
  case "$arg" in
    --repo-url=*) REPO_URL="${arg#*=}" ;;
  esac
done

if [[ -z "$REPO_URL" ]]; then
  if command -v git >/dev/null 2>&1 && [[ -d "$PROJECT_DIR/.git" ]]; then
    REPO_URL=$(git -C "$PROJECT_DIR" remote get-url origin || true)
  fi
fi

if [[ -z "$REPO_URL" ]]; then
  echo "error: не удалось определить репозиторий. Запустите с --repo-url=https://github.com/<owner>/<repo>" >&2
  exit 1
fi

# Извлекаем owner/repo
OWNER=""
REPO=""
if [[ "$REPO_URL" =~ github.com[:/]+([^/]+)/([^/.]+) ]]; then
  OWNER="${BASH_REMATCH[1]}"
  REPO="${BASH_REMATCH[2]}"
else
  echo "error: нераспознанный URL репозитория: $REPO_URL" >&2
  exit 1
fi

echo "[+] Проверяю последнюю версию Releases для $OWNER/$REPO"
TARBALL_URL=$(curl -s https://api.github.com/repos/$OWNER/$REPO/releases/latest | grep -m1 '"tarball_url"' | cut -d '"' -f4 || true)
if [[ -z "$TARBALL_URL" ]]; then
  echo "error: не удалось получить tarball_url" >&2
  exit 1
fi

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
echo "[+] Скачиваю: $TARBALL_URL"
curl -L "$TARBALL_URL" -o "$TMPDIR/release.tar.gz"

echo "[+] Распаковываю архив"
tar -xzf "$TMPDIR/release.tar.gz" -C "$TMPDIR"
SRCDIR=$(tar -tzf "$TMPDIR/release.tar.gz" | head -1 | cut -d/ -f1)
if [[ -z "$SRCDIR" || ! -d "$TMPDIR/$SRCDIR" ]]; then
  echo "error: не найден исходный каталог после распаковки" >&2
  exit 1
fi

echo "[+] Обновляю файлы проекта (с сохранением пользовательских настроек GUI)"
sudo apt-get install -y rsync >/dev/null 2>&1 || true
rsync -a --delete \
  --exclude 'data_manager/config/gui_settings.json' \
  --exclude 'data_manager/config/backups/' \
  "$TMPDIR/$SRCDIR/" "$PROJECT_DIR/"

echo "[+] Перезапускаю сервис"
sudo systemctl restart cryptoboiler.service || true
echo "[ok] Обновление завершено"
UPD"
	sudo chmod +x "$updater"
}

run_checks() {
	log "Проверяю импорты основных Python-библиотек"
	set +e
	python3 - <<'PY'
try:
	import kivy
	print("kivy", getattr(kivy, "__version__", "installed"))
except Exception as e:
	print("kivy: FAIL", e)

try:
	from Cryptodome.Cipher import AES
	from Cryptodome.Util.Padding import pad, unpad
	import Cryptodome
	print("pycryptodome(Cryptodome)", getattr(Cryptodome, "__version__", "installed"))
except Exception as e:
	print("pycryptodome: FAIL", e)

try:
	import RPi.GPIO as GPIO
	print("RPi.GPIO", getattr(GPIO, "VERSION", "installed"))
except Exception as e:
	print("RPi.GPIO: FAIL", e)
PY
	set -e
}

# Выполнение шагов
step_apt_prepare
step_apt_install
ensure_venv
step_python_requirements
step_lightdm_autologin
step_add_user_gpio
step_systemd_service
step_kiosk_windowed
step_vnc_setup
step_install_updater

$DO_CHECK && run_checks || true

ok "Установка и настройка завершены. При необходимости перезагрузите систему."
if $DO_REBOOT; then
	log "Перезагрузка..."
	sudo reboot
fi

#!/usr/bin/env bash
set -euo pipefail

# Установщик библиотек для CONTROLLER
# По умолчанию использует системные пакеты (apt) на Raspberry Pi.
# Опционально можно установить в отдельное виртуальное окружение: --venv /path/to/venv
# Дополнительно: флаг --check для проверки импортов после установки.

REQ_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)/requirements.txt"

usage() {
	echo "Usage: $0 [--venv <path>] [--check]" >&2
	echo "  --venv <path>   Установить пакеты в указанное venv через pip" >&2
	echo "  --check         Проверить импорты после установки" >&2
}

VENV_PATH=""
DO_CHECK=false

while [[ $# -gt 0 ]]; do
	case "$1" in
		--venv)
			shift
			VENV_PATH="${1:-}"
			[[ -z "$VENV_PATH" ]] && { echo "error: --venv требует путь" >&2; exit 1; }
			shift
			;;
		--check)
			DO_CHECK=true
			shift
			;;
		-h|--help)
			usage; exit 0;
			;;
		*)
			echo "error: неизвестный аргумент: $1" >&2
			usage; exit 1
			;;
	esac
done

install_with_apt() {
	echo "[+] Обновляю индексы пакетов..."
	sudo DEBIAN_FRONTEND=noninteractive apt-get update
	echo "[+] Устанавливаю системные пакеты: python3-kivy, python3-pycryptodome, RPi.GPIO (apt)"
	# python3-pycryptodome даёт пространство имён Cryptodome
	sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
		python3-kivy \
		python3-pycryptodome \
		python3-rpi.gpio || true

	# На некоторых системах пакет называется python3-rpi.gpio, на других RPi.GPIO уже предустановлен
	if python3 -c "import RPi.GPIO as GPIO; print(GPIO.VERSION)" >/dev/null 2>&1; then
		echo "[ok] RPi.GPIO доступен"
	else
		echo "[warn] RPi.GPIO не найден через apt. Попробую альтернативные имена пакетов..."
		sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-rpi.gpio RPi.GPIO || true
	fi
}

ensure_venv() {
	if [[ -n "$VENV_PATH" ]]; then
		echo "[+] Создаю venv: $VENV_PATH (если отсутствует)"
		python3 -m venv "$VENV_PATH"
		source "$VENV_PATH/bin/activate"
		python -m pip install --upgrade pip
		# На Debian/PEP 668 может потребоваться ключ
		PIP_FLAGS=""
		python -c "import sys; print(int(sys.version_info[:2] >= (3,11)))" >/dev/null 2>&1 || true
	fi
}

install_with_pip() {
	# Если активен venv — ставим строго по requirements.txt
	if [[ -n "${VENV_PATH}" ]]; then
		echo "[+] Устанавливаю зависимости из requirements.txt в venv"
		pip install -r "$REQ_FILE"
	else
		# В системную среду pip блокируется (PEP 668). Можно подсказать пользователю.
		echo "[warn] Установка через pip в системную среду может быть заблокирована (PEP 668)."
		echo "[i] Рекомендуется использовать --venv <path> для установки через pip."
	fi
}

run_checks() {
	echo "[+] Проверяю импорты..."
	set +e
	python3 - <<'PY'
try:
	import kivy
	print("kivy", getattr(kivy, "__version__", "installed"))
except Exception as e:
	print("kivy: FAIL", e)

try:
	from Cryptodome.Cipher import AES
	from Cryptodome.Util.Padding import pad, unpad
	import Cryptodome
	print("pycryptodome(Cryptodome)", getattr(Cryptodome, "__version__", "installed"))
except Exception as e:
	print("pycryptodome: FAIL", e)

try:
	import RPi.GPIO as GPIO
	print("RPi.GPIO", getattr(GPIO, "VERSION", "installed"))
except Exception as e:
	print("RPi.GPIO: FAIL", e)
PY
	set -e
}

if [[ -n "$VENV_PATH" ]]; then
	ensure_venv
	install_with_pip
else
	install_with_apt
fi

if $DO_CHECK; then
	run_checks
fi

echo "[done] Установка завершена"


