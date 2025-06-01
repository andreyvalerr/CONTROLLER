#!/usr/bin/env python3
"""
Регулятор температуры с гистерезисом
Управляет включением/выключением охлаждения на основе температуры жидкости
"""

import time
import logging
import threading
from typing import Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .relay_controller import RelayController
from .config import TemperatureConfig, SafetyConfig, DEFAULT_TEMPERATURE_CONFIG, DEFAULT_SAFETY_CONFIG

class RegulatorState(Enum):
    """Состояния регулятора"""
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"

@dataclass
class RegulatorConfig:
    """Конфигурация регулятора температуры"""
    temperature_config: TemperatureConfig
    safety_config: SafetyConfig
    # Пороги температуры (получаются из data_manager)
    min_temperature: float = 45.0  # По умолчанию, будет обновлено из data_manager
    max_temperature: float = 50.0  # По умолчанию, будет обновлено из data_manager

class TemperatureRegulator:
    """
    Регулятор температуры с гистерезисом
    
    Алгоритм работы:
    1. Если температура >= max_threshold И охлаждение выключено → ВКЛЮЧИТЬ охлаждение
    2. Если температура <= min_threshold И охлаждение включено → ВЫКЛЮЧИТЬ охлаждение
    3. В остальных случаях состояние не меняется
    """
    
    def __init__(self, 
                 relay_controller: RelayController,
                 temperature_callback: Callable[[], Optional[float]],
                 config: Optional[RegulatorConfig] = None,
                 temperature_settings_callback: Optional[Callable[[], Optional[dict]]] = None):
        """
        Инициализация регулятора температуры
        
        Args:
            relay_controller: Контроллер реле
            temperature_callback: Функция получения температуры
            config: Конфигурация регулятора
            temperature_settings_callback: Функция получения настроек температуры из data_manager
        """
        self.relay_controller = relay_controller
        self.temperature_callback = temperature_callback
        self.temperature_settings_callback = temperature_settings_callback
        
        # Конфигурация
        if config is None:
            config = RegulatorConfig(
                temperature_config=DEFAULT_TEMPERATURE_CONFIG,
                safety_config=DEFAULT_SAFETY_CONFIG
            )
        self.config = config
        
        self.logger = logging.getLogger(__name__)
        
        # Состояние регулятора
        self.state = RegulatorState.STOPPED
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()
        
        # Статистика
        self._start_time = None
        self._last_temperature = None
        self._last_temperature_time = None
        
        # Счетчики
        self._total_cycles = 0
        self._cooling_cycles = 0
        
        # Отслеживание обновлений настроек
        self._last_settings_check = None
        self._settings_check_interval = 1.0  # Проверять настройки каждую секунду
        self._settings_update_count = 0
        
    def start(self) -> bool:
        """
        Запуск регулятора температуры
        
        Returns:
            bool: True если запуск успешен
        """
        if self._running:
            self.logger.warning("Регулятор уже запущен")
            return True
        
        if not self.relay_controller.is_initialized():
            self.logger.error("Релейный контроллер не инициализирован")
            return False
        
        try:
            self._running = True
            self._stop_event.clear()
            self.state = RegulatorState.RUNNING
            self._start_time = datetime.now()
            
            # Запуск потока регулирования
            self._thread = threading.Thread(target=self._regulation_loop, daemon=True)
            self._thread.start()
            
            self.logger.info("Регулятор температуры запущен")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска регулятора: {e}")
            self._running = False
            self.state = RegulatorState.ERROR
            return False
    
    def stop(self):
        """Остановка регулятора температуры"""
        if not self._running:
            return
        
        self.logger.info("Остановка регулятора температуры")
        
        self._running = False
        self._stop_event.set()
        
        # Ожидание завершения потока
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        
        # Выключение охлаждения при остановке
        self.relay_controller.turn_off()
        
        self.state = RegulatorState.STOPPED
        self.logger.info("Регулятор температуры остановлен")
    
    def _regulation_loop(self):
        """Основной цикл регулирования температуры"""
        self.logger.info("Запуск цикла регулирования температуры")
        
        while self._running and not self._stop_event.is_set():
            try:
                # Периодическая проверка обновлений настроек температуры
                self._check_and_update_temperature_settings()
                
                # Получение температуры
                temperature = self._get_temperature_safe()
                
                if temperature is None:
                    self.logger.warning("Не удалось получить температуру")
                    continue
                
                # Обновление статистики
                self._last_temperature = temperature
                self._last_temperature_time = datetime.now()
                
                # Основная логика регулирования
                self._regulate_temperature(temperature)
                
                self._total_cycles += 1
                
            except Exception as e:
                self.logger.error(f"Ошибка в цикле регулирования: {e}")
                self.state = RegulatorState.ERROR
            
            # Ожидание следующего цикла
            self._stop_event.wait(self.config.temperature_config.control_interval)
        
        self.logger.info("Цикл регулирования температуры завершен")
    
    def _get_temperature_safe(self) -> Optional[float]:
        """
        Безопасное получение температуры с таймаутом
        
        Returns:
            float: Температура или None при ошибке
        """
        try:
            return self.temperature_callback()
        except Exception as e:
            self.logger.error(f"Ошибка получения температуры: {e}")
            return None
    
    def _regulate_temperature(self, temperature: float):
        """
        Основная логика регулирования температуры с гистерезисом
        
        Args:
            temperature: Текущая температура
        """
        cooling_active = self.relay_controller.get_relay_state()
        max_temp = self.config.max_temperature
        min_temp = self.config.min_temperature
        
        # Подробное логирование для диагностики
        self.logger.debug(f"Регулирование: T={temperature:.1f}°C, охлаждение={'ВКЛ' if cooling_active else 'ВЫКЛ'}, "
                         f"пороги=[{min_temp:.1f}°C - {max_temp:.1f}°C]")
        
        if not cooling_active and temperature >= max_temp:
            # Включить охлаждение при достижении максимальной температуры
            self.logger.info(f"🔥 ПОПЫТКА ВКЛЮЧЕНИЯ: T={temperature:.1f}°C >= {max_temp:.1f}°C")
            if self.relay_controller.turn_on():
                self._cooling_cycles += 1
                self.logger.info(f"✅ Охлаждение включено: {temperature}°C >= {max_temp}°C")
            else:
                self.logger.error(f"❌ НЕ УДАЛОСЬ ВКЛЮЧИТЬ охлаждение при T={temperature:.1f}°C")
        
        elif cooling_active and temperature <= min_temp:
            # Выключить охлаждение при достижении минимальной температуры
            self.logger.info(f"❄️ ПОПЫТКА ВЫКЛЮЧЕНИЯ: T={temperature:.1f}°C <= {min_temp:.1f}°C")
            if self.relay_controller.turn_off():
                self.logger.info(f"✅ Охлаждение выключено: {temperature}°C <= {min_temp}°C")
            else:
                self.logger.error(f"❌ НЕ УДАЛОСЬ ВЫКЛЮЧИТЬ охлаждение при T={temperature:.1f}°C")
        
        else:
            # Логирование состояния когда нет действий
            if cooling_active:
                self.logger.debug(f"⏳ Охлаждение активно, ожидание снижения до {min_temp:.1f}°C (текущая: {temperature:.1f}°C)")
            else:
                self.logger.debug(f"⏳ Охлаждение неактивно, ожидание повышения до {max_temp:.1f}°C (текущая: {temperature:.1f}°C)")
    
    def _check_and_update_temperature_settings(self):
        """
        Проверка и обновление настроек температуры из data_manager
        """
        current_time = datetime.now()
        
        # Проверяем настройки только если прошло достаточно времени
        if (self._last_settings_check is None or 
            (current_time - self._last_settings_check).total_seconds() >= self._settings_check_interval):
            
            self._last_settings_check = current_time
            
            if self.temperature_settings_callback:
                try:
                    settings = self.temperature_settings_callback()
                    
                    if settings and 'max_temperature' in settings and 'min_temperature' in settings:
                        new_max_temp = settings['max_temperature']
                        new_min_temp = settings['min_temperature']
                        
                        # Проверяем, изменились ли настройки
                        current_max = self.config.max_temperature
                        current_min = self.config.min_temperature
                        
                        if new_max_temp != current_max or new_min_temp != current_min:
                            # Обновляем настройки в RegulatorConfig
                            self.config.max_temperature = new_max_temp
                            self.config.min_temperature = new_min_temp
                            self._settings_update_count += 1
                            
                            self.logger.info(f"Настройки температуры обновлены из data_manager: "
                                           f"{new_min_temp}°C - {new_max_temp}°C (обновление #{self._settings_update_count})")
                    
                except Exception as e:
                    self.logger.error(f"Ошибка при проверке настроек температуры: {e}")
    
    def get_status(self) -> dict:
        """
        Получение статуса регулятора
        
        Returns:
            dict: Текущий статус регулятора
        """
        current_time = datetime.now()
        
        # Время работы
        uptime = None
        if self._start_time:
            uptime = current_time - self._start_time
        
        # Время с последнего обновления температуры
        temp_age = None
        if self._last_temperature_time:
            temp_age = current_time - self._last_temperature_time
        
        # Время с последней проверки настроек
        settings_check_age = None
        if self._last_settings_check:
            settings_check_age = current_time - self._last_settings_check
        
        return {
            # Основной статус
            "state": self.state.value,
            "is_running": self._running,
            "cooling_active": self.relay_controller.get_relay_state(),
            
            # Температура
            "current_temperature": self._last_temperature,
            "temperature_age_seconds": temp_age.total_seconds() if temp_age else None,
            "last_temperature_time": self._last_temperature_time.isoformat() if self._last_temperature_time else None,
            
            # Пороги
            "max_temperature": self.config.max_temperature,
            "min_temperature": self.config.min_temperature,
            "hysteresis": self.config.temperature_config.hysteresis,
            
            # Статистика
            "total_cycles": self._total_cycles,
            "cooling_cycles": self._cooling_cycles,
            "settings_updates": self._settings_update_count,
            "uptime_seconds": uptime.total_seconds() if uptime else None,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            
            # Проверки настроек
            "last_settings_check": self._last_settings_check.isoformat() if self._last_settings_check else None,
            "settings_check_age_seconds": settings_check_age.total_seconds() if settings_check_age else None,
            "settings_check_interval": self._settings_check_interval,
            
            # Конфигурация
            "control_interval": self.config.temperature_config.control_interval
        }
    
    def update_config(self, config: RegulatorConfig):
        """
        Обновление конфигурации регулятора
        
        Args:
            config: Новая конфигурация
        """
        self.config = config
        self.logger.info("Конфигурация регулятора обновлена")
    
    def is_running(self) -> bool:
        """Проверка работы регулятора"""
        return self._running
    
    def get_last_temperature(self) -> Optional[float]:
        """Получение последней измеренной температуры"""
        return self._last_temperature
    
    def __enter__(self):
        """Поддержка контекстного менеджера"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера"""
        self.stop() 