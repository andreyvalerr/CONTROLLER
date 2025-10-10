#!/usr/bin/env python3
"""
Интеграция модуля управления клапанами с менеджером данных
Получение температурных данных каждую секунду через data_manager
"""

import threading
import time
import sys
import os
from typing import Optional, Callable
from datetime import datetime

# Добавляем путь к data_manager
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from data_manager.core_system import get_temperature_data, get_core_instance
    from data_manager.data_manager import DataType
    DATA_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Предупреждение: Модуль data_manager недоступен: {e}")
    DATA_MANAGER_AVAILABLE = False


class TemperatureDataProvider:
    """
    Поставщик температурных данных через data_manager
    Обеспечивает получение температуры каждую секунду
    """
    
    def __init__(self, update_interval: float = 1.0):
        """
        Инициализация поставщика данных
        
        Args:
            update_interval: Интервал обновления в секундах (по умолчанию 1 секунда)
        """
        self.update_interval = update_interval
        self._current_temperature = None
        self._last_update = None
        self._is_running = False
        self._update_thread = None
        self._lock = threading.Lock()
        
        # Статистика
        self._stats = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "last_error": None
        }
    
    def start(self) -> bool:
        """
        Запуск поставщика данных
        
        Returns:
            bool: True если запуск успешен
        """
        if not DATA_MANAGER_AVAILABLE:
            print("Ошибка: data_manager недоступен")
            return False
        
        with self._lock:
            if self._is_running:
                return True
            
            self._is_running = True
            self._update_thread = threading.Thread(
                target=self._update_loop,
                daemon=True
            )
            self._update_thread.start()
            
            print(f"TemperatureDataProvider запущен (интервал: {self.update_interval}с)")
            return True
    
    def stop(self):
        """Остановка поставщика данных"""
        with self._lock:
            if not self._is_running:
                return
            
            self._is_running = False
            print("TemperatureDataProvider остановлен")
    
    def get_current_temperature(self) -> Optional[float]:
        """
        Получение текущей температуры
        
        Returns:
            Optional[float]: Температура в градусах Цельсия или None
        """
        with self._lock:
            return self._current_temperature
    
    def get_last_update_time(self) -> Optional[datetime]:
        """
        Получение времени последнего обновления
        
        Returns:
            Optional[datetime]: Время последнего обновления
        """
        with self._lock:
            return self._last_update
    
    def is_data_fresh(self, max_age_seconds: float = 5.0) -> bool:
        """
        Проверка свежести данных
        
        Args:
            max_age_seconds: Максимальный возраст данных в секундах
            
        Returns:
            bool: True если данные свежие
        """
        with self._lock:
            if self._last_update is None:
                return False
            
            age = (datetime.now() - self._last_update).total_seconds()
            return age <= max_age_seconds
    
    def get_statistics(self) -> dict:
        """
        Получение статистики работы
        
        Returns:
            dict: Статистика
        """
        with self._lock:
            success_rate = 0.0
            if self._stats["total_updates"] > 0:
                success_rate = (self._stats["successful_updates"] / self._stats["total_updates"]) * 100
            
            return {
                "is_running": self._is_running,
                "current_temperature": self._current_temperature,
                "last_update": self._last_update.isoformat() if self._last_update else None,
                "update_interval": self.update_interval,
                "total_updates": self._stats["total_updates"],
                "successful_updates": self._stats["successful_updates"],
                "failed_updates": self._stats["failed_updates"],
                "success_rate": success_rate,
                "last_error": self._stats["last_error"],
                "data_fresh": self.is_data_fresh()
            }
    
    def _update_loop(self):
        """Основной цикл обновления температурных данных"""
        while self._is_running:
            try:
                # Получение температуры через data_manager
                temperature = get_temperature_data()
                
                with self._lock:
                    self._stats["total_updates"] += 1
                    
                    if temperature is not None:
                        self._current_temperature = temperature
                        self._last_update = datetime.now()
                        self._stats["successful_updates"] += 1
                    else:
                        self._stats["failed_updates"] += 1
                        self._stats["last_error"] = "Температура недоступна"
                
            except Exception as e:
                with self._lock:
                    self._stats["total_updates"] += 1
                    self._stats["failed_updates"] += 1
                    self._stats["last_error"] = str(e)
                
                print(f"Ошибка получения температуры: {e}")
            
            time.sleep(self.update_interval)


# Глобальный экземпляр поставщика данных
_global_temperature_provider = None
_provider_lock = threading.Lock()

# Глобальная ссылка на инстанс ValveController и управление режимом
_controller_instance = None
_controller_lock = threading.Lock()
_is_manual_mode = False

# Слушатель режима/охлаждения
_listener_running = False
_listener_lock = threading.Lock()
_mode_callback_ref = None
_cooling_callback_ref = None


def start_temperature_data_provider(update_interval: float = 1.0) -> bool:
    """
    Запуск глобального поставщика температурных данных
    
    Args:
        update_interval: Интервал обновления в секундах
        
    Returns:
        bool: True если запуск успешен
    """
    global _global_temperature_provider
    
    with _provider_lock:
        if _global_temperature_provider is not None:
            return True  # Уже запущен
        
        _global_temperature_provider = TemperatureDataProvider(update_interval)
        return _global_temperature_provider.start()


def register_valve_controller_instance(controller) -> None:
    """Регистрация экземпляра ValveController для внешнего управления из GUI."""
    global _controller_instance
    with _controller_lock:
        _controller_instance = controller


def _get_controller():
    """Получение текущего зарегистрированного контроллера (или None)."""
    global _controller_instance
    with _controller_lock:
        return _controller_instance


def set_manual_mode() -> bool:
    """
    Переводит контроллер клапанов в ручной режим и выключает охлаждение по умолчанию.
    """
    global _is_manual_mode
    controller = _get_controller()
    if controller is None:
        print("[valve_control] Невозможно включить ручной режим: контроллер не зарегистрирован")
        return False
    try:
        ok = controller.manual_cooling_off()
        _is_manual_mode = True if ok else _is_manual_mode
        return ok
    except Exception as e:
        print(f"[valve_control] Ошибка установки ручного режима: {e}")
        return False


def set_auto_mode(algorithm: object = None) -> bool:
    """Переводит контроллер в автоматический режим (возобновляет регулятор).
    Можно указать алгоритм: 'predictive' | 'hysteresis' (или Enum).
    """
    global _is_manual_mode
    controller = _get_controller()
    if controller is None:
        print("[valve_control] Невозможно включить авто режим: контроллер не зарегистрирован")
        return False
    try:
        ok = controller.resume_automatic_control(algorithm)
        if ok:
            _is_manual_mode = False
        return ok
    except Exception as e:
        print(f"[valve_control] Ошибка установки авто режима: {e}")
        return False


def is_manual_mode() -> bool:
    """Возвращает текущий локальный флаг ручного режима."""
    return _is_manual_mode


def start_mode_cooling_listener() -> bool:
    """
    Подписывается на изменения MODE и COOLING_STATE в DataManager,
    применяя их к зарегистрированному контроллеру.
    """
    global _listener_running, _mode_callback_ref, _cooling_callback_ref
    if not DATA_MANAGER_AVAILABLE:
        print("[valve_control] Нельзя запустить listener: data_manager недоступен")
        return False
    with _listener_lock:
        if _listener_running:
            return True
        core = get_core_instance()
        if core is None or not core.is_running:
            print("[valve_control] Нельзя запустить listener: core_system не запущен")
            return False
        dm = core.data_manager

        def on_mode_change(entry):
            try:
                mode_val = str(entry.value).strip().lower() if entry and entry.value is not None else None
                if mode_val in ("авто", "automatic"):
                    mode_val = "auto"
                if mode_val in ("авто (предиктивный)", "предиктивный", "predictive"):
                    mode_val = "predictive"
                if mode_val in ("ручной", "manual"):
                    mode_val = "manual"
                if mode_val == "manual":
                    set_manual_mode()
                elif mode_val in ("auto", "predictive"):
                    alg = "predictive" if mode_val == "predictive" else "hysteresis"
                    set_auto_mode(alg)
            except Exception as e:
                print(f"[valve_control] Ошибка обработчика MODE: {e}")

        def on_cooling_change(entry):
            try:
                if not is_manual_mode():
                    return
                desired = bool(entry.value) if entry and entry.value is not None else False
                set_manual_cooling(desired)
            except Exception as e:
                print(f"[valve_control] Ошибка обработчика COOLING_STATE: {e}")

        # Сохраняем ссылки для отписки
        _mode_callback_ref = on_mode_change
        _cooling_callback_ref = on_cooling_change

        # Подписка
        dm.subscribe(DataType.MODE, _mode_callback_ref)
        dm.subscribe(DataType.COOLING_STATE, _cooling_callback_ref)

        # Немедленно применяем текущие значения, если есть
        try:
            current_mode = core.data_manager.get_value(DataType.MODE)
            if isinstance(current_mode, str):
                on_mode_change(type('E', (), {'value': current_mode}))
            current_cooling = core.data_manager.get_value(DataType.COOLING_STATE)
            if current_cooling is not None:
                on_cooling_change(type('E', (), {'value': current_cooling}))
        except Exception:
            pass

        _listener_running = True
        print("[valve_control] Listener режима/охлаждения запущен")
        return True


def stop_mode_cooling_listener() -> None:
    """Отписка от изменений MODE/COOLING_STATE в DataManager."""
    global _listener_running, _mode_callback_ref, _cooling_callback_ref
    if not DATA_MANAGER_AVAILABLE:
        return
    with _listener_lock:
        if not _listener_running:
            return
        core = get_core_instance()
        if core is not None and core.is_running:
            dm = core.data_manager
            try:
                if _mode_callback_ref is not None:
                    dm.unsubscribe(DataType.MODE, _mode_callback_ref)
                if _cooling_callback_ref is not None:
                    dm.unsubscribe(DataType.COOLING_STATE, _cooling_callback_ref)
            except Exception:
                pass
        _mode_callback_ref = None
        _cooling_callback_ref = None
        _listener_running = False
        print("[valve_control] Listener режима/охлаждения остановлен")


def set_manual_cooling(state: bool) -> bool:
    """Вручную включает/выключает охлаждение. Требуется ручной режим."""
    controller = _get_controller()
    if controller is None:
        print("[valve_control] Невозможно управлять охлаждением: контроллер не зарегистрирован")
        return False
    if not _is_manual_mode:
        print("[valve_control] Игнор: ручное управление доступно только в ручном режиме")
        return False
    try:
        return controller.manual_cooling_on() if state else controller.manual_cooling_off()
    except Exception as e:
        print(f"[valve_control] Ошибка ручного управления охлаждением: {e}")
        return False


def toggle_manual_cooling() -> bool:
    """Переключает состояние охлаждения в ручном режиме."""
    controller = _get_controller()
    if controller is None:
        print("[valve_control] Невозможно переключить охлаждение: контроллер не зарегистрирован")
        return False
    if not _is_manual_mode:
        print("[valve_control] Игнор: переключение доступно только в ручном режиме")
        return False
    try:
        return controller.relay_controller.toggle()
    except Exception as e:
        print(f"[valve_control] Ошибка переключения охлаждения: {e}")
        return False


def get_cooling_state() -> Optional[bool]:
    """Возвращает текущее состояние охлаждения (True/False) или None."""
    controller = _get_controller()
    if controller is None:
        return None
    try:
        return controller.is_cooling_active()
    except Exception:
        return None


def initialize_mode_from_settings() -> bool:
    """
    Инициализирует режим работы на основании настроек GUI.
    Если в настройках 'manual' — ручной режим (охлаждение выкл), иначе авто.
    """
    try:
        from data_manager.settings_manager import get_settings_manager
        sm = get_settings_manager()
        mode = sm.load_mode()
        saved_cooling = sm.load_cooling_state()
        mv = None
        if isinstance(mode, str):
            mv = mode.strip().lower()
        if mv == 'manual':
            ok = set_manual_mode()
            # Если удалось перейти в ручной режим и есть сохранённое состояние — применим его
            if ok and isinstance(saved_cooling, bool):
                try:
                    set_manual_cooling(saved_cooling)
                    print(f"[valve_control] Применено сохранённое состояние охлаждения: {'ON' if saved_cooling else 'OFF'}")
                except Exception:
                    pass
            return ok
        else:
            alg = 'predictive' if mv == 'predictive' else 'hysteresis'
            return set_auto_mode(alg)
    except Exception as e:
        print(f"[valve_control] Не удалось инициализировать режим из настроек: {e}")
        return False


def stop_temperature_data_provider():
    """Остановка глобального поставщика данных"""
    global _global_temperature_provider
    
    with _provider_lock:
        if _global_temperature_provider is not None:
            _global_temperature_provider.stop()
            _global_temperature_provider = None


def get_temperature_for_valve_controller() -> Optional[float]:
    """
    Функция-callback для получения температуры в valve_controller
    Автоматически запускает поставщик данных если необходимо
    
    Returns:
        Optional[float]: Температура в градусах Цельсия
    """
    global _global_temperature_provider
    
    with _provider_lock:
        if _global_temperature_provider is None:
            # Автоматический запуск поставщика данных
            if not start_temperature_data_provider():
                return None
        
        return _global_temperature_provider.get_current_temperature()


def is_temperature_provider_running() -> bool:
    """
    Проверка работы поставщика данных
    
    Returns:
        bool: True если поставщик работает
    """
    global _global_temperature_provider
    
    with _provider_lock:
        return _global_temperature_provider is not None and _global_temperature_provider._is_running


def get_temperature_provider_statistics() -> dict:
    """
    Получение статистики поставщика температурных данных
    
    Returns:
        dict: Статистика работы поставщика
    """
    global _global_temperature_provider
    
    with _provider_lock:
        if _global_temperature_provider is None:
            return {
                "is_running": False,
                "current_temperature": None,
                "last_update": None,
                "update_interval": 0.0,
                "total_updates": 0,
                "successful_updates": 0,
                "failed_updates": 0,
                "success_rate": 0.0,
                "last_error": "Поставщик не инициализирован",
                "data_fresh": False
            }
        
        return _global_temperature_provider.get_statistics()


# Новые функции для работы с настройками температуры
def get_temperature_settings_for_valve_controller() -> Optional[dict]:
    """
    Получение настроек температуры для valve_controller из data_manager
    
    Returns:
        Optional[dict]: Словарь с настройками {max_temperature, min_temperature} или None если data_manager недоступен
    """
    if not DATA_MANAGER_AVAILABLE:
        print("ОШИБКА: data_manager недоступен. Модуль valve_control не может работать без data_manager.")
        return None
    
    try:
        from data_manager.core_system import get_temperature_settings
        settings = get_temperature_settings()
        
        if settings is None:
            print("ОШИБКА: Настройки температуры отсутствуют в data_manager.")
            return None
            
        return settings
    except Exception as e:
        print(f"ОШИБКА получения настроек температуры: {e}")
        return None


def set_temperature_settings_from_valve_controller(max_temp: float, min_temp: float) -> bool:
    """Отключено: изменение уставок из valve_controller запрещено по политике SSOT."""
    print("[valve_control] Изменение уставок запрещено: используйте GUI для изменения gui_settings.json")
    return False


def is_temperature_settings_available() -> bool:
    """
    Проверка доступности настроек температуры в data_manager
    
    Returns:
        bool: True если настройки доступны
    """
    if not DATA_MANAGER_AVAILABLE:
        return False
    
    try:
        from data_manager.core_system import is_temperature_settings_available
        return is_temperature_settings_available()
    except Exception as e:
        print(f"ОШИБКА проверки доступности настроек температуры: {e}")
        return False


def validate_data_manager_availability() -> bool:
    """
    Валидация доступности data_manager для работы valve_control
    
    Returns:
        bool: True если data_manager доступен и готов к работе
    """
    if not DATA_MANAGER_AVAILABLE:
        print("КРИТИЧЕСКАЯ ОШИБКА: Модуль data_manager недоступен.")
        print("Модуль valve_control не может работать без data_manager.")
        return False
    
    try:
        from data_manager.core_system import is_core_system_running
        if not is_core_system_running():
            print("КРИТИЧЕСКАЯ ОШИБКА: data_manager core_system не запущен.")
            print("Запустите data_manager перед использованием valve_control.")
            return False
        
        return True
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА проверки data_manager: {e}")
        return False


def get_temperature_configuration_for_valve_controller() -> dict:
    """
    Получение полной конфигурации температуры для valve_controller
    Комбинирует текущую температуру и настройки
    
    Returns:
        dict: Полная информация о температуре и настройках
    """
    result = {
        "current_temperature": get_temperature_for_valve_controller(),
        "settings_available": is_temperature_settings_available(),
        "settings": get_temperature_settings_for_valve_controller(),
        "provider_running": is_temperature_provider_running(),
        "timestamp": datetime.now().isoformat()
    }
    
    return result 