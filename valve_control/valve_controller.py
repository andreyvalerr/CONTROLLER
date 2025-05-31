#!/usr/bin/env python3
"""
Основной контроллер клапанов
Высокоуровневый API для управления температурой криптокотла
"""

import logging
import signal
from typing import Optional, Callable
from dataclasses import dataclass

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
    """
    
    def __init__(self, 
                 temperature_callback: Callable[[], Optional[float]],
                 config: Optional[ValveControllerConfig] = None):
        """
        Инициализация контроллера клапанов
        
        Args:
            temperature_callback: Функция для получения температуры
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
        self.temperature_callback = temperature_callback
        
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
        
        # Регулятор температуры
        regulator_config = RegulatorConfig(
            temperature_config=self.config.temperature_config,
            safety_config=self.config.safety_config
        )
        
        self.temperature_regulator = TemperatureRegulator(
            relay_controller=self.relay_controller,
            temperature_callback=self.temperature_callback,
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
            
            # Запуск регулятора температуры
            if not self.temperature_regulator.start():
                self.logger.error("Не удалось запустить регулятор температуры")
                return False
            
            self._is_running = True
            self.logger.info("Контроллер клапанов успешно запущен")
            
            # Вывод конфигурации
            self._log_configuration()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска контроллера: {e}")
            return False
    
    def stop(self):
        """Остановка контроллера клапанов"""
        if not self._is_running:
            return
        
        self.logger.info("Остановка контроллера клапанов")
        
        # Остановка регулятора температуры
        self.temperature_regulator.stop()
        
        # Очистка ресурсов реле
        self.relay_controller.cleanup()
        
        self._is_running = False
        self.logger.info("Контроллер клапанов остановлен")
    
    def get_status(self) -> dict:
        """
        Получение полного статуса контроллера
        
        Returns:
            dict: Полный статус системы
        """
        # Статус контроллера
        controller_status = {
            "is_running": self._is_running,
            "shutdown_requested": self._shutdown_requested
        }
        
        # Статус температуры
        temperature_status = {
            "current": self.temperature_callback()
        }
        
        # Статус регулятора
        regulator_status = self.temperature_regulator.get_status()
        
        # Статус реле
        relay_status = self.relay_controller.get_statistics()
        
        # Конфигурация
        config_status = {
            "max_temp": self.config.temperature_config.max_temperature,
            "min_temp": self.config.temperature_config.min_temperature,
            "gpio_pin": self.config.relay_config.relay_pin
        }
        
        return {
            "controller": controller_status,
            "temperature": temperature_status,
            "regulator": regulator_status,
            "relay": relay_status,
            "config": config_status
        }
    
    def get_current_temperature(self) -> Optional[float]:
        """Получение текущей температуры"""
        return self.temperature_callback()
    
    def is_cooling_active(self) -> bool:
        """Проверка активности охлаждения"""
        return self.relay_controller.get_relay_state()
    
    def is_running(self) -> bool:
        """Проверка работы контроллера"""
        return self._is_running
    
    def manual_cooling_on(self) -> bool:
        """
        Ручное включение охлаждения
        
        Returns:
            bool: True если операция успешна
        """
        if not self._is_running:
            self.logger.error("Контроллер не запущен")
            return False
        
        # Остановка автоматического регулирования
        self.temperature_regulator.stop()
        
        # Включение реле
        result = self.relay_controller.turn_on()
        if result:
            self.logger.info("Ручное включение охлаждения")
        
        return result
    
    def manual_cooling_off(self) -> bool:
        """
        Ручное выключение охлаждения
        
        Returns:
            bool: True если операция успешна
        """
        if not self._is_running:
            self.logger.error("Контроллер не запущен")
            return False
        
        # Остановка автоматического регулирования
        self.temperature_regulator.stop()
        
        # Выключение реле
        result = self.relay_controller.turn_off()
        if result:
            self.logger.info("Ручное выключение охлаждения")
        
        return result
    
    def resume_automatic_control(self) -> bool:
        """
        Возобновление автоматического управления
        
        Returns:
            bool: True если операция успешна
        """
        if not self._is_running:
            self.logger.error("Контроллер не запущен")
            return False
        
        # Запуск регулятора температуры
        result = self.temperature_regulator.start()
        if result:
            self.logger.info("Автоматическое управление возобновлено")
        
        return result
    
    def test_relay(self, duration: float = 2.0) -> bool:
        """
        Тестирование реле
        
        Args:
            duration: Длительность теста в секундах
            
        Returns:
            bool: True если тест успешен
        """
        if not self._is_running:
            self.logger.error("Контроллер не запущен")
            return False
        
        # Временная остановка автоматического регулирования
        was_regulator_running = self.temperature_regulator.is_running()
        if was_regulator_running:
            self.temperature_regulator.stop()
        
        try:
            # Тестирование реле
            result = self.relay_controller.test_relay(duration)
            
            # Возобновление регулирования если было активно
            if was_regulator_running:
                self.temperature_regulator.start()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка тестирования реле: {e}")
            
            # Возобновление регулирования при ошибке
            if was_regulator_running:
                self.temperature_regulator.start()
            
            return False
    
    def update_temperature_thresholds(self, max_temp: float, min_temp: Optional[float] = None):
        """
        Обновление порогов температуры
        
        Args:
            max_temp: Максимальная температура
            min_temp: Минимальная температура (если None, рассчитывается автоматически)
        """
        if min_temp is None:
            min_temp = max_temp - self.config.temperature_config.hysteresis
        
        # Обновление конфигурации
        self.config.temperature_config.max_temperature = max_temp
        self.config.temperature_config.min_temperature = min_temp
        
        # Обновление конфигурации регулятора
        regulator_config = RegulatorConfig(
            temperature_config=self.config.temperature_config,
            safety_config=self.config.safety_config
        )
        self.temperature_regulator.update_config(regulator_config)
        
        self.logger.info(f"Пороги температуры обновлены: {min_temp}°C - {max_temp}°C")
    
    def _log_configuration(self):
        """Вывод текущей конфигурации"""
        self.logger.info("=== КОНФИГУРАЦИЯ КОНТРОЛЛЕРА ===")
        self.logger.info(f"GPIO пин: {self.config.relay_config.relay_pin}")
        self.logger.info(f"Пороги температуры: {self.config.temperature_config.min_temperature}°C - {self.config.temperature_config.max_temperature}°C")
        self.logger.info(f"Интервал контроля: {self.config.temperature_config.control_interval} сек")
        self.logger.info("================================")
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов системы"""
        self.logger.info(f"Получен сигнал {signum}, остановка контроллера")
        self._shutdown_requested = True
        self.stop()
    
    def run_forever(self):
        """
        Запуск контроллера в бесконечном цикле
        
        Блокирует выполнение до получения сигнала остановки
        """
        if not self.start():
            self.logger.error("Не удалось запустить контроллер")
            return
        
        try:
            self.logger.info("Контроллер запущен, ожидание сигнала остановки...")
            
            # Ожидание до получения сигнала остановки
            import time
            while self._is_running and not self._shutdown_requested:
                time.sleep(1.0)
                
        except KeyboardInterrupt:
            self.logger.info("Получен сигнал KeyboardInterrupt")
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка: {e}")
        finally:
            self.stop()
    
    def __enter__(self):
        """Поддержка контекстного менеджера"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера"""
        self.stop() 