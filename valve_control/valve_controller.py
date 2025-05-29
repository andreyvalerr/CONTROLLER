#!/usr/bin/env python3
"""
Основной контроллер клапанов
Высокоуровневый API для управления температурой криптокотла
"""

import sys
import os
import logging
import signal
from typing import Optional
from dataclasses import dataclass

# Добавление пути к модулю get_temperature
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'get_temperature'))

try:
    from get_temperature import get_current_temperature, TemperatureAPI
except ImportError:
    print("ВНИМАНИЕ: Модуль get_temperature недоступен. Работа в режиме эмуляции.")
    
    def get_current_temperature() -> Optional[float]:
        """Эмуляция получения температуры"""
        import random
        return round(random.uniform(30.0, 50.0), 1)
    
    class TemperatureAPI:
        def __init__(self, *args, **kwargs):
            pass
        def start(self):
            return True
        def stop(self):
            pass
        def get_temperature(self):
            return get_current_temperature()

from .relay_controller import RelayController
from .temperature_regulator import TemperatureRegulator, RegulatorConfig
from .config import (
    RelayConfig, TemperatureConfig, MonitoringConfig, SafetyConfig,
    load_config_from_env, validate_config
)

@dataclass
class ValveControllerConfig:
    """Полная конфигурация контроллера клапанов"""
    relay_config: RelayConfig
    temperature_config: TemperatureConfig
    monitoring_config: MonitoringConfig
    safety_config: SafetyConfig

class ValveController:
    """
    Основной контроллер клапанов для управления температурой криптокотла
    
    Объединяет:
    - RelayController: управление GPIO реле
    - TemperatureRegulator: логика регулирования с гистерезисом
    - TemperatureAPI: получение температуры от асика
    """
    
    def __init__(self, config: Optional[ValveControllerConfig] = None):
        """
        Инициализация контроллера клапанов
        
        Args:
            config: Конфигурация контроллера (если None, загружается из переменных окружения)
        """
        # Загрузка конфигурации
        if config is None:
            relay_config, temp_config, monitoring_config, safety_config = load_config_from_env()
            config = ValveControllerConfig(
                relay_config=relay_config,
                temperature_config=temp_config,
                monitoring_config=monitoring_config,
                safety_config=safety_config
            )
        
        self.config = config
        
        # Настройка логирования
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Валидация конфигурации
        errors = validate_config(self.config.relay_config, self.config.temperature_config)
        if errors:
            for error in errors:
                self.logger.error(f"Ошибка конфигурации: {error}")
            raise ValueError(f"Некорректная конфигурация: {'; '.join(errors)}")
        
        # Инициализация компонентов
        self.relay_controller = RelayController(self.config.relay_config)
        self.temperature_api = TemperatureAPI(
            ip_address=self.config.monitoring_config.asic_ip,
            update_interval=self.config.monitoring_config.update_interval
        )
        
        # Регулятор температуры
        regulator_config = RegulatorConfig(
            temperature_config=self.config.temperature_config,
            safety_config=self.config.safety_config
        )
        
        self.temperature_regulator = TemperatureRegulator(
            relay_controller=self.relay_controller,
            temperature_callback=self._get_temperature,
            config=regulator_config
        )
        
        # Состояние контроллера
        self._is_running = False
        self._shutdown_requested = False
        
        # Регистрация обработчиков сигналов
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("Контроллер клапанов инициализирован")
    
    def _setup_logging(self):
        """Настройка системы логирования"""
        log_level = getattr(logging, self.config.monitoring_config.log_level.upper(), logging.INFO)
        
        # Формат логов
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Настройка корневого логгера
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Очистка существующих обработчиков
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Консольный вывод
        if self.config.monitoring_config.enable_console_log:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # Файловый вывод
        if self.config.monitoring_config.log_file:
            file_handler = logging.FileHandler(self.config.monitoring_config.log_file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
    
    def _get_temperature(self) -> Optional[float]:
        """
        Получение температуры через API
        
        Returns:
            float: Температура в градусах Цельсия или None при ошибке
        """
        try:
            return self.temperature_api.get_temperature()
        except Exception as e:
            self.logger.error(f"Ошибка получения температуры: {e}")
            return None
    
    def start(self) -> bool:
        """
        Запуск контроллера клапанов
        
        Returns:
            bool: True если запуск успешен
        """
        if self._is_running:
            self.logger.warning("Контроллер уже запущен")
            return True
        
        try:
            self.logger.info("Запуск контроллера клапанов")
            
            # Проверка инициализации реле
            if not self.relay_controller.is_initialized():
                self.logger.error("Релейный контроллер не инициализирован")
                return False
            
            # Запуск мониторинга температуры
            if not self.temperature_api.start():
                self.logger.error("Не удалось запустить мониторинг температуры")
                return False
            
            # Запуск регулятора температуры
            if not self.temperature_regulator.start():
                self.logger.error("Не удалось запустить регулятор температуры")
                self.temperature_api.stop()
                return False
            
            self._is_running = True
            self.logger.info("Контроллер клапанов успешно запущен")
            
            # Вывод конфигурации
            self._log_configuration()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска контроллера: {e}")
            self.stop()
            return False
    
    def stop(self):
        """Остановка контроллера клапанов"""
        if not self._is_running:
            return
        
        self.logger.info("Остановка контроллера клапанов")
        
        try:
            # Остановка регулятора температуры
            self.temperature_regulator.stop()
            
            # Остановка мониторинга температуры
            self.temperature_api.stop()
            
            # Выключение реле
            self.relay_controller.turn_off()
            
            self._is_running = False
            self.logger.info("Контроллер клапанов остановлен")
            
        except Exception as e:
            self.logger.error(f"Ошибка остановки контроллера: {e}")
    
    def emergency_stop(self):
        """Аварийная остановка контроллера"""
        self.logger.warning("АВАРИЙНАЯ ОСТАНОВКА КОНТРОЛЛЕРА КЛАПАНОВ")
        
        try:
            # Аварийная остановка регулятора
            self.temperature_regulator.emergency_stop()
            
            # Аварийное выключение реле
            self.relay_controller.emergency_off()
            
            # Остановка мониторинга
            self.temperature_api.stop()
            
            self._is_running = False
            
        except Exception as e:
            self.logger.error(f"Ошибка аварийной остановки: {e}")
    
    def get_status(self) -> dict:
        """
        Получение полного статуса контроллера
        
        Returns:
            dict: Статус всех компонентов
        """
        try:
            # Статус регулятора
            regulator_status = self.temperature_regulator.get_status()
            
            # Статус реле
            relay_stats = self.relay_controller.get_statistics()
            
            # Общий статус
            return {
                "controller": {
                    "is_running": self._is_running,
                    "shutdown_requested": self._shutdown_requested
                },
                "temperature": {
                    "current": regulator_status.get("current_temperature"),
                    "time_since_update": regulator_status.get("time_since_temperature"),
                    "status": "ok" if regulator_status.get("current_temperature") is not None else "error"
                },
                "regulator": regulator_status,
                "relay": relay_stats,
                "config": {
                    "max_temp": self.config.temperature_config.max_temperature,
                    "min_temp": self.config.temperature_config.min_temperature,
                    "critical_temp": self.config.temperature_config.critical_max_temp,
                    "emergency_temp": self.config.temperature_config.emergency_temp,
                    "gpio_pin": self.config.relay_config.relay_pin,
                    "asic_ip": self.config.monitoring_config.asic_ip
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения статуса: {e}")
            return {"error": str(e)}
    
    def get_current_temperature(self) -> Optional[float]:
        """Получение текущей температуры"""
        return self.temperature_regulator.get_last_temperature()
    
    def is_cooling_active(self) -> bool:
        """Проверка активности охлаждения"""
        return self.relay_controller.get_relay_state()
    
    def is_running(self) -> bool:
        """Проверка работы контроллера"""
        return self._is_running
    
    def manual_cooling_on(self) -> bool:
        """
        Ручное включение охлаждения (остановка автоматического регулирования)
        
        Returns:
            bool: True если операция успешна
        """
        self.logger.info("Ручное включение охлаждения")
        
        # Остановка автоматического регулирования
        if self.temperature_regulator.is_running():
            self.temperature_regulator.stop()
        
        # Включение реле
        return self.relay_controller.turn_on()
    
    def manual_cooling_off(self) -> bool:
        """
        Ручное выключение охлаждения (остановка автоматического регулирования)
        
        Returns:
            bool: True если операция успешна
        """
        self.logger.info("Ручное выключение охлаждения")
        
        # Остановка автоматического регулирования
        if self.temperature_regulator.is_running():
            self.temperature_regulator.stop()
        
        # Выключение реле
        return self.relay_controller.turn_off()
    
    def resume_automatic_control(self) -> bool:
        """
        Возобновление автоматического регулирования
        
        Returns:
            bool: True если операция успешна
        """
        self.logger.info("Возобновление автоматического регулирования")
        
        if not self._is_running:
            self.logger.error("Контроллер не запущен")
            return False
        
        return self.temperature_regulator.start()
    
    def test_relay(self, duration: float = 2.0) -> bool:
        """
        Тестирование реле
        
        Args:
            duration: Длительность теста в секундах
            
        Returns:
            bool: True если тест прошел успешно
        """
        self.logger.info(f"Тестирование реле на {duration} секунд")
        
        # Временная остановка регулятора
        was_running = self.temperature_regulator.is_running()
        if was_running:
            self.temperature_regulator.stop()
        
        try:
            result = self.relay_controller.test_relay(duration)
            
            # Восстановление регулятора
            if was_running:
                self.temperature_regulator.start()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка тестирования реле: {e}")
            
            # Восстановление регулятора
            if was_running:
                self.temperature_regulator.start()
            
            return False
    
    def update_temperature_thresholds(self, max_temp: float, min_temp: Optional[float] = None):
        """
        Обновление температурных порогов
        
        Args:
            max_temp: Максимальная температура
            min_temp: Минимальная температура (если None, рассчитывается автоматически)
        """
        if min_temp is None:
            min_temp = max_temp - self.config.temperature_config.hysteresis
        
        self.config.temperature_config.max_temperature = max_temp
        self.config.temperature_config.min_temperature = min_temp
        
        # Обновление конфигурации регулятора
        regulator_config = RegulatorConfig(
            temperature_config=self.config.temperature_config,
            safety_config=self.config.safety_config
        )
        self.temperature_regulator.update_config(regulator_config)
        
        self.logger.info(f"Обновлены температурные пороги: max={max_temp}°C, min={min_temp}°C")
    
    def _log_configuration(self):
        """Вывод текущей конфигурации в лог"""
        self.logger.info("=== КОНФИГУРАЦИЯ КОНТРОЛЛЕРА КЛАПАНОВ ===")
        self.logger.info(f"GPIO пин реле: {self.config.relay_config.relay_pin}")
        self.logger.info(f"IP адрес асика: {self.config.monitoring_config.asic_ip}")
        self.logger.info(f"Максимальная температура: {self.config.temperature_config.max_temperature}°C")
        self.logger.info(f"Минимальная температура: {self.config.temperature_config.min_temperature}°C")
        self.logger.info(f"Критическая температура: {self.config.temperature_config.critical_max_temp}°C")
        self.logger.info(f"Аварийная температура: {self.config.temperature_config.emergency_temp}°C")
        self.logger.info(f"Интервал контроля: {self.config.temperature_config.control_interval}с")
        self.logger.info("==========================================")
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов завершения"""
        self.logger.info(f"Получен сигнал {signum}, завершение работы...")
        self._shutdown_requested = True
        self.stop()
    
    def run_forever(self):
        """
        Запуск контроллера в бесконечном цикле
        Блокирует выполнение до получения сигнала завершения
        """
        if not self.start():
            self.logger.error("Не удалось запустить контроллер")
            return False
        
        try:
            self.logger.info("Контроллер клапанов работает. Нажмите Ctrl+C для остановки.")
            
            while self._is_running and not self._shutdown_requested:
                import time
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Получен сигнал прерывания")
        
        finally:
            self.stop()
            self.logger.info("Контроллер клапанов завершил работу")
        
        return True
    
    def __enter__(self):
        """Контекстный менеджер - вход"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        self.stop() 