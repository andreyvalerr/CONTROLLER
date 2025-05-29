#!/usr/bin/env python3
"""
Контроллер релейного модуля для управления клапанами
Низкоуровневое управление GPIO Raspberry Pi
"""

import time
import logging
import atexit
from typing import Optional
from datetime import datetime, timedelta

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("ВНИМАНИЕ: RPi.GPIO недоступен. Работа в режиме эмуляции.")

from .config import RelayConfig, DEFAULT_RELAY_CONFIG

class RelayController:
    """
    Контроллер релейного модуля
    
    Управляет GPIO пином для включения/выключения реле
    Использует инвертированную логику (LOW = включено, HIGH = выключено)
    """
    
    def __init__(self, config: Optional[RelayConfig] = None):
        """
        Инициализация контроллера реле
        
        Args:
            config: Конфигурация реле (если None, используется конфигурация по умолчанию)
        """
        self.config = config or DEFAULT_RELAY_CONFIG
        self.logger = logging.getLogger(__name__)
        
        # Состояние реле
        self._is_initialized = False
        self._relay_state = False  # False = выключено, True = включено
        self._last_switch_time = None
        self._switch_count = 0
        self._start_time = datetime.now()
        
        # Статистика
        self._total_on_time = timedelta()
        self._last_on_time = None
        
        # Инициализация GPIO
        self._init_gpio()
        
        # Регистрация функции очистки при выходе
        if self.config.cleanup_on_exit:
            atexit.register(self.cleanup)
    
    def _init_gpio(self) -> bool:
        """
        Инициализация GPIO
        
        Returns:
            bool: True если инициализация успешна
        """
        if not GPIO_AVAILABLE:
            self.logger.warning("GPIO недоступен, работа в режиме эмуляции")
            self._is_initialized = True
            return True
        
        try:
            # Настройка режима GPIO
            if self.config.gpio_mode == "BCM":
                GPIO.setmode(GPIO.BCM)
            else:
                GPIO.setmode(GPIO.BOARD)
            
            # Отключение предупреждений
            GPIO.setwarnings(self.config.enable_warnings)
            
            # Настройка пина как выход
            GPIO.setup(self.config.relay_pin, GPIO.OUT)
            
            # Установка начального состояния (реле выключено)
            GPIO.output(self.config.relay_pin, self.config.relay_off_state)
            
            self._is_initialized = True
            self._relay_state = False
            
            self.logger.info(f"GPIO инициализирован: пин {self.config.relay_pin}, режим {self.config.gpio_mode}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации GPIO: {e}")
            self._is_initialized = False
            return False
    
    def is_initialized(self) -> bool:
        """Проверка инициализации GPIO"""
        return self._is_initialized
    
    def get_relay_state(self) -> bool:
        """
        Получение текущего состояния реле
        
        Returns:
            bool: True если реле включено, False если выключено
        """
        return self._relay_state
    
    def turn_on(self) -> bool:
        """
        Включение реле (охлаждения)
        
        Returns:
            bool: True если операция успешна
        """
        if not self._is_initialized:
            self.logger.error("GPIO не инициализирован")
            return False
        
        try:
            if GPIO_AVAILABLE:
                GPIO.output(self.config.relay_pin, self.config.relay_on_state)
            
            if not self._relay_state:  # Если реле было выключено
                self._relay_state = True
                self._last_switch_time = datetime.now()
                self._last_on_time = self._last_switch_time
                self._switch_count += 1
                
                self.logger.info("Реле включено (охлаждение запущено)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка включения реле: {e}")
            return False
    
    def turn_off(self) -> bool:
        """
        Выключение реле (охлаждения)
        
        Returns:
            bool: True если операция успешна
        """
        if not self._is_initialized:
            self.logger.error("GPIO не инициализирован")
            return False
        
        try:
            if GPIO_AVAILABLE:
                GPIO.output(self.config.relay_pin, self.config.relay_off_state)
            
            if self._relay_state:  # Если реле было включено
                self._relay_state = False
                self._last_switch_time = datetime.now()
                self._switch_count += 1
                
                # Обновление статистики времени работы
                if self._last_on_time:
                    self._total_on_time += self._last_switch_time - self._last_on_time
                    self._last_on_time = None
                
                self.logger.info("Реле выключено (охлаждение остановлено)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка выключения реле: {e}")
            return False
    
    def toggle(self) -> bool:
        """
        Переключение состояния реле
        
        Returns:
            bool: True если операция успешна
        """
        if self._relay_state:
            return self.turn_off()
        else:
            return self.turn_on()
    
    def emergency_off(self) -> bool:
        """
        Аварийное выключение реле
        
        Returns:
            bool: True если операция успешна
        """
        self.logger.warning("АВАРИЙНОЕ ВЫКЛЮЧЕНИЕ РЕЛЕ")
        return self.turn_off()
    
    def test_relay(self, duration: float = 2.0) -> bool:
        """
        Тестирование реле (включение на заданное время)
        
        Args:
            duration: Длительность теста в секундах
            
        Returns:
            bool: True если тест прошел успешно
        """
        if not self._is_initialized:
            self.logger.error("GPIO не инициализирован")
            return False
        
        try:
            self.logger.info(f"Начало теста реле на {duration} секунд")
            
            # Сохранение текущего состояния
            original_state = self._relay_state
            
            # Включение реле
            if not self.turn_on():
                return False
            
            # Ожидание
            time.sleep(duration)
            
            # Восстановление исходного состояния
            if original_state:
                result = self.turn_on()
            else:
                result = self.turn_off()
            
            self.logger.info("Тест реле завершен")
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка теста реле: {e}")
            return False
    
    def get_statistics(self) -> dict:
        """
        Получение статистики работы реле
        
        Returns:
            dict: Статистика работы
        """
        current_time = datetime.now()
        uptime = current_time - self._start_time
        
        # Расчет текущего времени работы
        current_on_time = self._total_on_time
        if self._relay_state and self._last_on_time:
            current_on_time += current_time - self._last_on_time
        
        # Расчет процента времени работы
        on_time_percentage = (current_on_time.total_seconds() / uptime.total_seconds() * 100) if uptime.total_seconds() > 0 else 0
        
        return {
            "relay_state": self._relay_state,
            "switch_count": self._switch_count,
            "total_on_time_seconds": current_on_time.total_seconds(),
            "uptime_seconds": uptime.total_seconds(),
            "on_time_percentage": round(on_time_percentage, 2),
            "last_switch_time": self._last_switch_time.isoformat() if self._last_switch_time else None,
            "gpio_pin": self.config.relay_pin,
            "is_initialized": self._is_initialized
        }
    
    def get_last_switch_time(self) -> Optional[datetime]:
        """Получение времени последнего переключения"""
        return self._last_switch_time
    
    def get_switch_count(self) -> int:
        """Получение количества переключений"""
        return self._switch_count
    
    def cleanup(self):
        """Очистка ресурсов GPIO"""
        if self._is_initialized and GPIO_AVAILABLE:
            try:
                # Выключение реле перед очисткой
                GPIO.output(self.config.relay_pin, self.config.relay_off_state)
                
                # Очистка GPIO
                GPIO.cleanup()
                
                self.logger.info("GPIO очищен")
                
            except Exception as e:
                self.logger.error(f"Ошибка очистки GPIO: {e}")
            
            finally:
                self._is_initialized = False
    
    def __enter__(self):
        """Контекстный менеджер - вход"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        self.cleanup()
    
    def __del__(self):
        """Деструктор"""
        if hasattr(self, '_is_initialized') and self._is_initialized:
            self.cleanup() 