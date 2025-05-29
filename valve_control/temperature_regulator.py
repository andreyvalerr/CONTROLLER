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
    EMERGENCY = "emergency"

@dataclass
class RegulatorConfig:
    """Конфигурация регулятора температуры"""
    temperature_config: TemperatureConfig
    safety_config: SafetyConfig
    
    def __post_init__(self):
        # Автоматический расчет min_temperature на основе гистерезиса
        if self.temperature_config.min_temperature >= self.temperature_config.max_temperature:
            self.temperature_config.min_temperature = (
                self.temperature_config.max_temperature - self.temperature_config.hysteresis
            )

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
                 config: Optional[RegulatorConfig] = None):
        """
        Инициализация регулятора температуры
        
        Args:
            relay_controller: Контроллер реле
            temperature_callback: Функция получения температуры
            config: Конфигурация регулятора
        """
        self.relay_controller = relay_controller
        self.temperature_callback = temperature_callback
        
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
        
        # Статистика и безопасность
        self._start_time = None
        self._last_temperature = None
        self._last_temperature_time = None
        self._cooling_start_time = None
        self._switch_history = []  # История переключений для контроля частоты
        self._emergency_count = 0
        
        # Счетчики
        self._total_cycles = 0
        self._cooling_cycles = 0
        self._emergency_stops = 0
        
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
    
    def emergency_stop(self):
        """Аварийная остановка регулятора"""
        self.logger.warning("АВАРИЙНАЯ ОСТАНОВКА РЕГУЛЯТОРА")
        
        self._emergency_stops += 1
        self.state = RegulatorState.EMERGENCY
        
        # Аварийное выключение реле
        self.relay_controller.emergency_off()
        
        # Остановка регулятора
        self.stop()
    
    def _regulation_loop(self):
        """Основной цикл регулирования температуры"""
        self.logger.info("Запуск цикла регулирования температуры")
        
        while self._running and not self._stop_event.is_set():
            try:
                # Получение температуры
                temperature = self._get_temperature_safe()
                
                if temperature is None:
                    self._handle_temperature_error()
                    continue
                
                # Обновление статистики
                self._last_temperature = temperature
                self._last_temperature_time = datetime.now()
                
                # Проверка критических значений
                if self._check_critical_temperature(temperature):
                    continue
                
                # Основная логика регулирования
                self._regulate_temperature(temperature)
                
                # Проверка безопасности
                self._check_safety_limits()
                
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
    
    def _handle_temperature_error(self):
        """Обработка ошибки получения температуры"""
        if self._last_temperature_time:
            time_since_last = datetime.now() - self._last_temperature_time
            
            if time_since_last.total_seconds() > self.config.safety_config.emergency_timeout:
                self.logger.error("Превышен таймаут получения температуры - аварийная остановка")
                self.emergency_stop()
                return
        
        self.logger.warning("Не удалось получить температуру, пропуск цикла")
        self.state = RegulatorState.ERROR
    
    def _check_critical_temperature(self, temperature: float) -> bool:
        """
        Проверка критических значений температуры
        
        Args:
            temperature: Текущая температура
            
        Returns:
            bool: True если обнаружена критическая ситуация
        """
        # Аварийная температура
        if temperature >= self.config.temperature_config.emergency_temp:
            self.logger.critical(f"АВАРИЙНАЯ ТЕМПЕРАТУРА: {temperature}°C >= {self.config.temperature_config.emergency_temp}°C")
            self.emergency_stop()
            return True
        
        # Критическая температура
        if temperature >= self.config.temperature_config.critical_max_temp:
            self.logger.warning(f"КРИТИЧЕСКАЯ ТЕМПЕРАТУРА: {temperature}°C >= {self.config.temperature_config.critical_max_temp}°C")
            # Принудительное включение охлаждения
            if not self.relay_controller.get_relay_state():
                self.relay_controller.turn_on()
                self._cooling_start_time = datetime.now()
                self._add_switch_to_history()
            return False
        
        return False
    
    def _regulate_temperature(self, temperature: float):
        """
        Основная логика регулирования температуры с гистерезисом
        
        Args:
            temperature: Текущая температура
        """
        current_cooling = self.relay_controller.get_relay_state()
        
        # Логика с гистерезисом
        if temperature >= self.config.temperature_config.max_temperature and not current_cooling:
            # Включение охлаждения
            if self._can_switch():
                self.relay_controller.turn_on()
                self._cooling_start_time = datetime.now()
                self._cooling_cycles += 1
                self._add_switch_to_history()
                self.logger.info(f"Охлаждение включено: {temperature}°C >= {self.config.temperature_config.max_temperature}°C")
        
        elif temperature <= self.config.temperature_config.min_temperature and current_cooling:
            # Выключение охлаждения
            if self._can_switch():
                self.relay_controller.turn_off()
                self._cooling_start_time = None
                self._add_switch_to_history()
                self.logger.info(f"Охлаждение выключено: {temperature}°C <= {self.config.temperature_config.min_temperature}°C")
    
    def _can_switch(self) -> bool:
        """
        Проверка возможности переключения реле (защита от частых переключений)
        
        Returns:
            bool: True если переключение разрешено
        """
        now = datetime.now()
        
        # Проверка минимального времени между переключениями
        last_switch = self.relay_controller.get_last_switch_time()
        if last_switch:
            time_since_switch = now - last_switch
            if time_since_switch.total_seconds() < self.config.safety_config.min_cycle_time:
                return False
        
        # Проверка максимального количества переключений в час
        hour_ago = now - timedelta(hours=1)
        recent_switches = [t for t in self._switch_history if t > hour_ago]
        
        if len(recent_switches) >= self.config.safety_config.max_switches_per_hour:
            self.logger.warning(f"Превышено максимальное количество переключений в час: {len(recent_switches)}")
            return False
        
        return True
    
    def _add_switch_to_history(self):
        """Добавление переключения в историю"""
        now = datetime.now()
        self._switch_history.append(now)
        
        # Очистка старых записей (старше 24 часов)
        day_ago = now - timedelta(days=1)
        self._switch_history = [t for t in self._switch_history if t > day_ago]
    
    def _check_safety_limits(self):
        """Проверка ограничений безопасности"""
        if not self.relay_controller.get_relay_state():
            return
        
        # Проверка максимального времени работы охлаждения
        if self._cooling_start_time:
            cooling_duration = datetime.now() - self._cooling_start_time
            max_duration = timedelta(minutes=self.config.safety_config.max_cooling_time)
            
            if cooling_duration > max_duration:
                self.logger.warning(f"Превышено максимальное время работы охлаждения: {cooling_duration}")
                self.relay_controller.turn_off()
                self._cooling_start_time = None
                self._add_switch_to_history()
    
    def get_status(self) -> dict:
        """
        Получение статуса регулятора
        
        Returns:
            dict: Статус регулятора
        """
        now = datetime.now()
        
        # Время работы охлаждения
        cooling_time = None
        if self._cooling_start_time and self.relay_controller.get_relay_state():
            cooling_time = (now - self._cooling_start_time).total_seconds()
        
        # Время с последней температуры
        time_since_temp = None
        if self._last_temperature_time:
            time_since_temp = (now - self._last_temperature_time).total_seconds()
        
        # Статистика переключений за час
        hour_ago = now - timedelta(hours=1)
        switches_last_hour = len([t for t in self._switch_history if t > hour_ago])
        
        return {
            "state": self.state.value,
            "is_running": self._running,
            "current_temperature": self._last_temperature,
            "time_since_temperature": time_since_temp,
            "cooling_active": self.relay_controller.get_relay_state(),
            "cooling_time_seconds": cooling_time,
            "total_cycles": self._total_cycles,
            "cooling_cycles": self._cooling_cycles,
            "emergency_stops": self._emergency_stops,
            "switches_last_hour": switches_last_hour,
            "max_temperature": self.config.temperature_config.max_temperature,
            "min_temperature": self.config.temperature_config.min_temperature,
            "critical_temperature": self.config.temperature_config.critical_max_temp,
            "emergency_temperature": self.config.temperature_config.emergency_temp,
            "uptime_seconds": (now - self._start_time).total_seconds() if self._start_time else 0
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
        """Получение последней температуры"""
        return self._last_temperature
    
    def __enter__(self):
        """Контекстный менеджер - вход"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        self.stop() 