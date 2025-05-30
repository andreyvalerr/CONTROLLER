#!/usr/bin/env python3
"""
Общее состояние системы для обмена данными между компонентами
"""

import threading
from datetime import datetime
from typing import Optional, Callable, List
from .data_models import TemperatureData, SystemStatus, SystemSettings, SystemData

class SharedSystemState:
    """
    Потокобезопасное хранилище состояния системы
    Используется для обмена данными между GUI, API и контроллером
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        
        # Инициализация настроек по умолчанию
        self._settings = SystemSettings()
        
        # Инициализация данных
        self._temperature_data = TemperatureData(
            current_temp=0.0,
            target_temp=self._settings.max_temperature,
            min_temp=self._settings.min_temperature,
            timestamp=datetime.now()
        )
        
        self._system_status = SystemStatus(
            valve_state=False,
            system_mode="auto",
            last_update=datetime.now()
        )
        
        # Подписчики на изменения
        self._subscribers: List[Callable] = []
    
    def subscribe(self, callback: Callable):
        """Подписка на изменения состояния"""
        with self._lock:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable):
        """Отписка от изменений состояния"""
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
    
    def _notify_subscribers(self):
        """Уведомление подписчиков об изменениях"""
        for callback in self._subscribers:
            try:
                callback(self.get_system_data())
            except Exception as e:
                print(f"Ошибка уведомления подписчика: {e}")
    
    # Методы для работы с температурными данными
    def update_temperature(self, temp: float, source: str = "whatsminer"):
        """Обновление текущей температуры"""
        with self._lock:
            self._temperature_data = TemperatureData(
                current_temp=temp,
                target_temp=self._temperature_data.target_temp,
                min_temp=self._temperature_data.min_temp,
                timestamp=datetime.now(),
                source=source
            )
            self._notify_subscribers()
    
    def get_temperature_data(self) -> TemperatureData:
        """Получение данных о температуре"""
        with self._lock:
            return self._temperature_data
    
    # Методы для работы с настройками
    def update_settings(self, settings: SystemSettings):
        """Обновление настроек системы"""
        with self._lock:
            if settings.validate():
                old_max = self._settings.max_temperature
                old_min = self._settings.min_temperature
                
                self._settings = settings
                
                # Обновляем целевые температуры если они изменились
                if (old_max != settings.max_temperature or 
                    old_min != settings.min_temperature):
                    self._temperature_data = TemperatureData(
                        current_temp=self._temperature_data.current_temp,
                        target_temp=settings.max_temperature,
                        min_temp=settings.min_temperature,
                        timestamp=datetime.now(),
                        source=self._temperature_data.source
                    )
                
                self._notify_subscribers()
                return True
            return False
    
    def get_settings(self) -> SystemSettings:
        """Получение настроек системы"""
        with self._lock:
            return self._settings
    
    def update_target_temperature(self, target_temp: float):
        """Быстрое обновление целевой температуры"""
        with self._lock:
            if self._settings.min_temperature <= target_temp <= self._settings.critical_temp:
                # Обновляем настройки
                self._settings.max_temperature = target_temp
                self._settings.min_temperature = target_temp - self._settings.hysteresis
                
                # Обновляем данные о температуре
                self._temperature_data = TemperatureData(
                    current_temp=self._temperature_data.current_temp,
                    target_temp=target_temp,
                    min_temp=self._settings.min_temperature,
                    timestamp=datetime.now(),
                    source=self._temperature_data.source
                )
                
                self._notify_subscribers()
                return True
            return False
    
    # Методы для работы со статусом системы
    def update_valve_state(self, valve_state: bool):
        """Обновление состояния клапана"""
        with self._lock:
            self._system_status = SystemStatus(
                valve_state=valve_state,
                system_mode=self._system_status.system_mode,
                last_update=datetime.now(),
                errors=self._system_status.errors
            )
            self._notify_subscribers()
    
    def update_system_mode(self, mode: str):
        """Обновление режима системы"""
        with self._lock:
            if mode in ["auto", "manual", "emergency"]:
                self._system_status = SystemStatus(
                    valve_state=self._system_status.valve_state,
                    system_mode=mode,
                    last_update=datetime.now(),
                    errors=self._system_status.errors
                )
                self._notify_subscribers()
                return True
            return False
    
    def set_error(self, error_message: Optional[str]):
        """Установка сообщения об ошибке"""
        with self._lock:
            self._system_status = SystemStatus(
                valve_state=self._system_status.valve_state,
                system_mode=self._system_status.system_mode,
                last_update=datetime.now(),
                errors=error_message
            )
            self._notify_subscribers()
    
    def get_system_status(self) -> SystemStatus:
        """Получение статуса системы"""
        with self._lock:
            return self._system_status
    
    # Общие методы
    def get_system_data(self) -> SystemData:
        """Получение полных данных системы"""
        with self._lock:
            return SystemData(
                temperature=self._temperature_data,
                status=self._system_status,
                settings=self._settings
            )
    
    def update_system_data(self, system_data: SystemData) -> bool:
        """Обновление полных данных системы"""
        with self._lock:
            try:
                if system_data.settings.validate():
                    self._settings = system_data.settings
                    self._temperature_data = system_data.temperature
                    self._system_status = system_data.status
                    self._notify_subscribers()
                    return True
            except Exception as e:
                print(f"Ошибка обновления данных системы: {e}")
            return False

# Глобальный экземпляр для использования во всем приложении
system_state = SharedSystemState() 