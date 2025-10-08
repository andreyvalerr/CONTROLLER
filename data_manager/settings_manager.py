#!/usr/bin/env python3
"""
Модуль управления настройками температуры
Сохранение и загрузка настроек в энергонезависимую память
"""

import json
import os
import shutil
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

class SettingsManager:
    """Класс для управления настройками температуры"""
    
    def __init__(self, config_dir: str = None):
        """
        Инициализация менеджера настроек
        
        Args:
            config_dir: Путь к папке конфигурации (по умолчанию auto-detect)
        """
        if config_dir is None:
            # Автоматическое определение пути к config
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_dir = os.path.join(current_dir, "config")
        
        self.config_dir = Path(config_dir)
        self.settings_file = self.config_dir / "gui_settings.json"
        self.defaults_file = self.config_dir / "defaults.json"
        self.backups_dir = self.config_dir / "backups"
        
        # Создание папок если не существуют
        self.config_dir.mkdir(exist_ok=True)
        self.backups_dir.mkdir(exist_ok=True)
        
        self._log_message(f"SettingsManager инициализирован с config_dir: {self.config_dir}")
    
    def save_settings(self, settings_dict: Dict[str, Any]) -> bool:
        """
        Сохранение словаря настроек в JSON файл
        
        Args:
            settings_dict: Словарь с настройками для сохранения
            
        Returns:
            bool: True если сохранение успешно
        """
        try:
            # Валидация температурных настроек (ожидается, что min/max будут переданы)
            if not self.validate_settings(settings_dict):
                self._log_error("Настройки не прошли валидацию, сохранение отменено")
                return False

            # Создание резервной копии если файл существует
            if self.settings_file.exists():
                if not self.create_backup(str(self.settings_file)):
                    self._log_error("Не удалось создать резервную копию, но продолжаем сохранение")

            # Загружаем существующие данные (для сохранения дополнительных полей, например IP и режим)
            existing_data: Dict[str, Any] = {}
            if self.settings_file.exists():
                try:
                    with open(self.settings_file, 'r', encoding='utf-8') as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            existing_data = loaded
                except Exception:
                    existing_data = {}

            # Базовая структура
            save_data: Dict[str, Any] = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "temperature_settings": {
                    "min_temp": settings_dict.get("min_temp", 45.0),
                    "max_temp": settings_dict.get("max_temp", 55.0)
                },
                "metadata": {
                    "device_id": "raspberry_pi_01",
                    "created_by": "core_system",
                    "backup_count": 3,
                    "source": settings_dict.get("source", "unknown")
                }
            }

            # Переносим дополнительные поля из существующих данных, если они не переопределяются
            # IP адрес ASIC
            if "ip_address_asic" in settings_dict and isinstance(settings_dict["ip_address_asic"], str):
                save_data["ip_address_asic"] = settings_dict["ip_address_asic"]
            elif isinstance(existing_data.get("ip_address_asic"), str):
                save_data["ip_address_asic"] = existing_data["ip_address_asic"]

            # Режим работы (mode_settings)
            incoming_mode = None
            if "mode" in settings_dict and isinstance(settings_dict["mode"], str):
                incoming_mode = settings_dict["mode"]
            elif isinstance(settings_dict.get("mode_settings"), dict) and isinstance(settings_dict["mode_settings"].get("mode"), str):
                incoming_mode = settings_dict["mode_settings"]["mode"]

            if incoming_mode is not None:
                save_data["mode_settings"] = {"mode": incoming_mode}
            elif isinstance(existing_data.get("mode_settings"), dict) and isinstance(existing_data["mode_settings"].get("mode"), str):
                save_data["mode_settings"] = {"mode": existing_data["mode_settings"]["mode"]}

            # Состояние охлаждения (cooling_settings)
            incoming_cooling = None
            if isinstance(settings_dict.get("cooling_settings"), dict) and isinstance(settings_dict["cooling_settings"].get("cooling_on"), bool):
                incoming_cooling = {"cooling_on": bool(settings_dict["cooling_settings"]["cooling_on"])}
            elif isinstance(settings_dict.get("cooling_on"), bool):
                incoming_cooling = {"cooling_on": bool(settings_dict["cooling_on"])}

            if incoming_cooling is not None:
                save_data["cooling_settings"] = incoming_cooling
            elif isinstance(existing_data.get("cooling_settings"), dict) and isinstance(existing_data["cooling_settings"].get("cooling_on"), bool):
                save_data["cooling_settings"] = {"cooling_on": existing_data["cooling_settings"]["cooling_on"]}

            # Сохраняем в файл
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            self._log_message(
                f"Настройки успешно сохранены: min_temp={save_data['temperature_settings']['min_temp']}, max_temp={save_data['temperature_settings']['max_temp']}"
            )
            if "mode_settings" in save_data:
                self._log_message(f"Режим работы сохранен: {save_data['mode_settings'].get('mode')}")
            return True

        except Exception as e:
            self._log_error(f"Ошибка при сохранении настроек: {e}")
            sys.exit(1)  # Аварийное завершение согласно инструкции

    def load_ip_address(self) -> Optional[str]:
        """
        Загрузка IP адреса ASIC из файла gui_settings.json
        
        Returns:
            Optional[str]: IP адрес или None, если не найден
        """
        try:
            if not self.settings_file.exists():
                return None
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            ip = data.get("ip_address_asic")
            if isinstance(ip, str) and ip:
                return ip
            # Возможная совместимость, если IP когда-то сохраняли внутри temperature_settings
            ts = data.get("temperature_settings", {})
            ip_alt = ts.get("ip_address_asic") if isinstance(ts, dict) else None
            return ip_alt if isinstance(ip_alt, str) and ip_alt else None
        except Exception as e:
            self._log_error(f"Ошибка загрузки IP адреса ASIC: {e}")
            return None

    def load_mode(self) -> Optional[str]:
        """
        Загрузка режима работы из gui_settings.json
        
        Returns:
            Optional[str]: Строка режима (например, 'auto' или 'manual') или None
        """
        try:
            if not self.settings_file.exists():
                return None
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            mode_settings = data.get("mode_settings")
            if isinstance(mode_settings, dict):
                mode_value = mode_settings.get("mode")
                if isinstance(mode_value, str) and mode_value:
                    return mode_value
            return None
        except Exception as e:
            self._log_error(f"Ошибка загрузки режима работы: {e}")
            return None

    def save_mode(self, mode_value: str) -> bool:
        """
        Сохранение режима работы в gui_settings.json с резервной копией.

        Args:
            mode_value: Строка режима ('auto' | 'manual' | 'predictive', допускаются 'Авто'/'Ручной'/'Авто (предиктивный)').

        Returns:
            bool: True если успешно сохранен
        """
        try:
            # Нормализация значения ('Авто'/'Ручной'/'Авто (предиктивный)' -> 'auto'/'manual'/'predictive')
            normalized = mode_value.strip().lower()
            if normalized in ("авто", "автоматический", "automatic"):
                normalized = "auto"
            elif normalized in ("авто (предиктивный)", "предиктивный", "predictive"):
                normalized = "predictive"
            elif normalized in ("ручной", "manual"):
                normalized = "manual"

            if normalized not in ("auto", "manual", "predictive"):
                self._log_error(f"Недопустимое значение режима: {mode_value}")
                return False

            # Подготовка данных: загружаем существующие либо базовую структуру
            data: Dict[str, Any]
            if self.settings_file.exists():
                try:
                    with open(self.settings_file, 'r', encoding='utf-8') as f:
                        loaded = json.load(f)
                        data = loaded if isinstance(loaded, dict) else {}
                except Exception:
                    data = {}
            else:
                # Если нет файла, создаем от defaults
                if self.defaults_file.exists():
                    with open(self.defaults_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if not isinstance(data, dict):
                            data = {}
                else:
                    data = {}

            # Базовые поля по умолчанию
            data.setdefault("version", "1.0")
            data["last_updated"] = datetime.now().isoformat()
            data.setdefault("temperature_settings", {"min_temp": 45.0, "max_temp": 55.0})
            data.setdefault("metadata", {})
            data["metadata"]["device_id"] = data.get("metadata", {}).get("device_id", "raspberry_pi_01")
            data["metadata"]["created_by"] = "settings_manager"
            data["metadata"]["backup_count"] = data.get("metadata", {}).get("backup_count", 3)
            data["metadata"]["source"] = "mode_update"

            # Обновляем режим
            data["mode_settings"] = {"mode": normalized}

            # Создаем резервную копию, если файл существует
            if self.settings_file.exists():
                self.create_backup(str(self.settings_file))

            # Сохраняем файл
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self._log_message(f"Режим работы сохранен: {normalized}")
            return True
        except Exception as e:
            self._log_error(f"Ошибка при сохранении режима работы: {e}")
            return False

    def save_ip_address(self, ip_address: str) -> bool:
        """
        Сохранение/обновление IP адреса ASIC в gui_settings.json
        
        Args:
            ip_address: IPv4 адрес ASIC
        
        Returns:
            bool: True если успешно сохранен
        """
        try:
            # Загружаем существующий файл или создаем базовую структуру
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
            else:
                data = {
                    "version": "1.0",
                    "temperature_settings": {
                        "min_temp": 45.0,
                        "max_temp": 55.0
                    },
                    "metadata": {
                        "device_id": "raspberry_pi_01",
                        "created_by": "settings_manager",
                        "backup_count": 3,
                        "source": "ip_update"
                    }
                }

            # Обновляем поля
            data["ip_address_asic"] = ip_address
            data["last_updated"] = datetime.now().isoformat()
            if "metadata" not in data or not isinstance(data["metadata"], dict):
                data["metadata"] = {}
            data["metadata"]["created_by"] = "settings_manager"
            data["metadata"]["source"] = "ip_update"

            # Создаем резервную копию, если файл есть
            if self.settings_file.exists():
                self.create_backup(str(self.settings_file))

            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._log_message(f"IP адрес ASIC сохранен в settings: {ip_address}")
            return True
        except Exception as e:
            self._log_error(f"Ошибка сохранения IP адреса ASIC: {e}")
            return False

    def load_cooling_state(self) -> Optional[bool]:
        """
        Загрузка состояния охлаждения из gui_settings.json
        
        Returns:
            Optional[bool]: True/False если сохранено, иначе None
        """
        try:
            if not self.settings_file.exists():
                return None
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            cooling = data.get("cooling_settings")
            if isinstance(cooling, dict) and isinstance(cooling.get("cooling_on"), bool):
                return bool(cooling["cooling_on"])
            return None
        except Exception as e:
            self._log_error(f"Ошибка загрузки состояния охлаждения: {e}")
            return None

    def save_cooling_state(self, cooling_on: bool) -> bool:
        """
        Сохранение состояния охлаждения (кнопки) в gui_settings.json с резервной копией.

        Args:
            cooling_on: Текущее состояние охлаждения (True/False)

        Returns:
            bool: True если успешно сохранено
        """
        try:
            # Загружаем существующий файл или создаем базовую структуру
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
            else:
                data = {
                    "version": "1.0",
                    "temperature_settings": {
                        "min_temp": 45.0,
                        "max_temp": 55.0
                    },
                    "metadata": {
                        "device_id": "raspberry_pi_01",
                        "created_by": "settings_manager",
                        "backup_count": 3,
                        "source": "cooling_update"
                    }
                }

            # Обновляем поля
            data["cooling_settings"] = {"cooling_on": bool(cooling_on)}
            data["last_updated"] = datetime.now().isoformat()
            if "metadata" not in data or not isinstance(data["metadata"], dict):
                data["metadata"] = {}
            data["metadata"]["created_by"] = "settings_manager"
            data["metadata"]["source"] = "cooling_update"

            # Создаем резервную копию, если файл есть
            if self.settings_file.exists():
                self.create_backup(str(self.settings_file))

            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._log_message(f"Состояние охлаждения сохранено: {'on' if cooling_on else 'off'}")
            return True
        except Exception as e:
            self._log_error(f"Ошибка сохранения состояния охлаждения: {e}")
            return False
    
    def load_settings(self) -> Optional[Dict[str, Any]]:
        """
        Загрузка настроек из JSON файла
        
        Returns:
            Optional[Dict]: Словарь с настройками или None при ошибке
        """
        try:
            # Если файл настроек не существует, используем defaults
            if not self.settings_file.exists():
                self._log_error(f"Файл настроек не найден: {self.settings_file}")
                sys.exit(1)  # Аварийное завершение согласно инструкции
            
            # Загрузка настроек
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверка корректности загруженных данных
            if not isinstance(data, dict) or "temperature_settings" not in data:
                self._log_error("Некорректная структура файла настроек")
                sys.exit(1)  # Аварийное завершение согласно инструкции
            
            settings = data["temperature_settings"]
            
            # Валидация загруженных настроек
            if not self.validate_settings(settings):
                self._log_error("Загруженные настройки не прошли валидацию")
                sys.exit(1)  # Аварийное завершение согласно инструкции
            
            self._log_message(f"Настройки успешно загружены: min_temp={settings['min_temp']}, max_temp={settings['max_temp']}")
            return settings
            
        except json.JSONDecodeError as e:
            self._log_error(f"Поврежденный JSON файл настроек: {e}")
            sys.exit(1)  # Аварийное завершение согласно инструкции
        except FileNotFoundError:
            self._log_error(f"Файл настроек не найден: {self.settings_file}")
            sys.exit(1)  # Аварийное завершение согласно инструкции
        except PermissionError:
            self._log_error(f"Нет прав доступа к файлу настроек: {self.settings_file}")
            sys.exit(1)  # Аварийное завершение согласно инструкции
        except Exception as e:
            self._log_error(f"Ошибка при загрузке настроек: {e}")
            sys.exit(1)  # Аварийное завершение согласно инструкции
    
    def validate_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Проверка корректности значений температуры
        
        Args:
            settings: Словарь с настройками для проверки
            
        Returns:
            bool: True если настройки корректны
        """
        try:
            # Проверка наличия обязательных полей
            if not isinstance(settings, dict):
                self._log_error("Настройки должны быть словарем")
                return False
            
            if "min_temp" not in settings or "max_temp" not in settings:
                self._log_error("Отсутствуют обязательные поля min_temp или max_temp")
                return False
            
            min_temp = settings["min_temp"]
            max_temp = settings["max_temp"]
            
            # Проверка типов
            if not isinstance(min_temp, (int, float)) or not isinstance(max_temp, (int, float)):
                self._log_error("Температуры должны быть числовыми значениями")
                return False
            
            # Проверка логической связности (min < max)
            if min_temp >= max_temp:
                self._log_error(f"Минимальная температура ({min_temp}) должна быть меньше максимальной ({max_temp})")
                return False
            
            # Проверка диапазонов (0°C < temp < 100°C)
            if min_temp < 0 or min_temp > 100:
                self._log_error(f"Минимальная температура ({min_temp}) вне допустимого диапазона 0-100°C")
                return False
            
            if max_temp < 0 or max_temp > 100:
                self._log_error(f"Максимальная температура ({max_temp}) вне допустимого диапазона 0-100°C")
                return False
            
            # Проверка разумности гистерезиса
            hysteresis = max_temp - min_temp
            if hysteresis < 0.1:
                self._log_error(f"Гистерезис ({hysteresis}) слишком мал, минимум 0.1°C")
                return False
            
            if hysteresis > 30.0:
                self._log_error(f"Гистерезис ({hysteresis}) слишком велик, максимум 30.0°C")
                return False
            
            return True
            
        except Exception as e:
            self._log_error(f"Ошибка при валидации настроек: {e}")
            return False
    
    def create_backup(self, file_path: str) -> bool:
        """
        Создание резервной копии с timestamp
        
        Args:
            file_path: Путь к файлу для резервного копирования
            
        Returns:
            bool: True если резервная копия создана успешно
        """
        try:
            if not os.path.exists(file_path):
                self._log_message("Файл для резервного копирования не существует")
                return True  # Не ошибка, просто нечего копировать
            
            # Создание имени резервной копии с timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_name = f"gui_settings_{timestamp}.json"
            backup_path = self.backups_dir / backup_name
            
            # Копирование файла
            shutil.copy2(file_path, backup_path)
            
            self._log_message(f"Создана резервная копия: {backup_path}")
            
            # Удаление старых резервных копий (хранить последние 5)
            self._cleanup_old_backups()
            
            return True
            
        except Exception as e:
            self._log_error(f"Ошибка при создании резервной копии: {e}")
            return False
    
    def _cleanup_old_backups(self):
        """Удаление старых резервных копий (хранить последние 5)"""
        try:
            # Получение всех файлов резервных копий (учитываем старые и новые имена)
            backup_files = (
                list(self.backups_dir.glob("gui_settings_*.json")) +
                list(self.backups_dir.glob("temperature_settings_*.json"))
            )
            
            if len(backup_files) > 5:
                # Сортировка по времени создания (старые первыми)
                backup_files.sort(key=lambda x: x.stat().st_mtime)
                
                # Удаление старых файлов
                for old_backup in backup_files[:-5]:  # Оставляем последние 5 суммарно
                    old_backup.unlink()
                    self._log_message(f"Удалена старая резервная копия: {old_backup}")
                    
        except Exception as e:
            self._log_error(f"Ошибка при очистке старых резервных копий: {e}")
    
    def get_settings_file_info(self) -> Dict[str, Any]:
        """
        Получение информации о файле настроек
        
        Returns:
            Dict: Информация о файле настроек
        """
        try:
            if not self.settings_file.exists():
                return {
                    "exists": False,
                    "path": str(self.settings_file),
                    "size": 0,
                    "modified": None
                }
            
            stat = self.settings_file.stat()
            return {
                "exists": True,
                "path": str(self.settings_file),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "readable": os.access(self.settings_file, os.R_OK),
                "writable": os.access(self.settings_file, os.W_OK)
            }
            
        except Exception as e:
            self._log_error(f"Ошибка при получении информации о файле: {e}")
            return {"exists": False, "error": str(e)}
    
    def copy_defaults_to_settings(self) -> bool:
        """
        Копирование defaults.json в gui_settings.json
        
        Returns:
            bool: True если копирование успешно
        """
        try:
            if not self.defaults_file.exists():
                self._log_error(f"Файл defaults.json не найден: {self.defaults_file}")
                sys.exit(1)  # Аварийное завершение согласно инструкции
            
            # Загрузка defaults
            with open(self.defaults_file, 'r', encoding='utf-8') as f:
                defaults_data = json.load(f)
            
            # Обновление timestamp
            defaults_data["last_updated"] = datetime.now().isoformat()
            defaults_data["metadata"]["created_by"] = "settings_manager"
            
            # Сохранение в settings файл
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(defaults_data, f, indent=2, ensure_ascii=False)
            
            self._log_message("Defaults скопированы в gui_settings.json")
            return True
            
        except Exception as e:
            self._log_error(f"Ошибка при копировании defaults: {e}")
            sys.exit(1)  # Аварийное завершение согласно инструкции
    
    def _log_message(self, message: str):
        """Логирование информационного сообщения"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] INFO: SettingsManager: {message}")
    
    def _log_error(self, message: str):
        """Логирование ошибки"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ERROR: SettingsManager: {message}")


# Глобальный экземпляр менеджера настроек
_global_settings_manager = None

def get_settings_manager() -> SettingsManager:
    """Получение глобального экземпляра менеджера настроек"""
    global _global_settings_manager
    if _global_settings_manager is None:
        _global_settings_manager = SettingsManager()
    return _global_settings_manager 