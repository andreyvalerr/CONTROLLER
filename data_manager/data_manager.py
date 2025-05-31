#!/usr/bin/env python3
"""
Менеджер данных для ядра системы
Потокобезопасное хранение и обмен данными между модулями
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum


class DataType(Enum):
    """Типы данных в системе"""
    TEMPERATURE = "temperature"
    VALVE_POSITION = "valve_position"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"


@dataclass
class DataEntry:
    """Запись данных с метаинформацией"""
    value: Any
    timestamp: datetime
    data_type: DataType
    source_module: str
    metadata: Optional[Dict[str, Any]] = None


class DataManager:
    """Менеджер данных для централизованного хранения состояния системы"""
    
    def __init__(self, max_history_size: int = 1000):
        """
        Инициализация менеджера данных
        
        Args:
            max_history_size: Максимальный размер истории для каждого типа данных
        """
        self.max_history_size = max_history_size
        
        # Потокобезопасное хранилище
        self._data_lock = threading.RLock()
        self._current_data: Dict[DataType, DataEntry] = {}
        self._history: Dict[DataType, List[DataEntry]] = {data_type: [] for data_type in DataType}
        
        # Подписчики на изменения данных
        self._subscribers: Dict[DataType, List[Callable[[DataEntry], None]]] = {
            data_type: [] for data_type in DataType
        }
        
        # Статистика
        self._stats = {
            "total_updates": 0,
            "updates_by_type": {data_type: 0 for data_type in DataType},
            "updates_by_module": {},
            "start_time": datetime.now()
        }
    
    def set_data(self, data_type: DataType, value: Any, source_module: str, 
                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Установка данных
        
        Args:
            data_type: Тип данных
            value: Значение
            source_module: Модуль-источник
            metadata: Дополнительные метаданные
            
        Returns:
            bool: True если данные успешно установлены
        """
        try:
            entry = DataEntry(
                value=value,
                timestamp=datetime.now(),
                data_type=data_type,
                source_module=source_module,
                metadata=metadata or {}
            )
            
            with self._data_lock:
                # Обновление текущих данных
                self._current_data[data_type] = entry
                
                # Добавление в историю
                self._history[data_type].append(entry)
                
                # Ограничение размера истории
                if len(self._history[data_type]) > self.max_history_size:
                    self._history[data_type] = self._history[data_type][-self.max_history_size:]
                
                # Обновление статистики
                self._stats["total_updates"] += 1
                self._stats["updates_by_type"][data_type] += 1
                if source_module not in self._stats["updates_by_module"]:
                    self._stats["updates_by_module"][source_module] = 0
                self._stats["updates_by_module"][source_module] += 1
            
            # Уведомление подписчиков
            self._notify_subscribers(data_type, entry)
            
            return True
            
        except Exception as e:
            print(f"Ошибка при установке данных {data_type}: {e}")
            return False
    
    def get_data(self, data_type: DataType) -> Optional[DataEntry]:
        """
        Получение текущих данных
        
        Args:
            data_type: Тип данных
            
        Returns:
            DataEntry: Последняя запись данных или None
        """
        with self._data_lock:
            return self._current_data.get(data_type)
    
    def get_value(self, data_type: DataType) -> Any:
        """
        Получение только значения данных
        
        Args:
            data_type: Тип данных
            
        Returns:
            Any: Значение или None
        """
        entry = self.get_data(data_type)
        return entry.value if entry else None
    
    def get_history(self, data_type: DataType, limit: Optional[int] = None, 
                   since: Optional[datetime] = None) -> List[DataEntry]:
        """
        Получение истории данных
        
        Args:
            data_type: Тип данных
            limit: Ограничение количества записей
            since: Фильтр по времени (с какого момента)
            
        Returns:
            List[DataEntry]: Список записей истории
        """
        with self._data_lock:
            history = self._history[data_type].copy()
        
        # Фильтрация по времени
        if since:
            history = [entry for entry in history if entry.timestamp >= since]
        
        # Ограничение количества
        if limit:
            history = history[-limit:]
        
        return history
    
    def subscribe(self, data_type: DataType, callback: Callable[[DataEntry], None]):
        """
        Подписка на изменения данных
        
        Args:
            data_type: Тип данных
            callback: Функция обратного вызова
        """
        with self._data_lock:
            self._subscribers[data_type].append(callback)
    
    def unsubscribe(self, data_type: DataType, callback: Callable[[DataEntry], None]):
        """
        Отписка от изменений данных
        
        Args:
            data_type: Тип данных
            callback: Функция обратного вызова
        """
        with self._data_lock:
            if callback in self._subscribers[data_type]:
                self._subscribers[data_type].remove(callback)
    
    def _notify_subscribers(self, data_type: DataType, entry: DataEntry):
        """Уведомление подписчиков об изменении данных"""
        subscribers = []
        with self._data_lock:
            subscribers = self._subscribers[data_type].copy()
        
        for callback in subscribers:
            try:
                callback(entry)
            except Exception as e:
                print(f"Ошибка в callback для {data_type}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики работы
        
        Returns:
            Dict: Статистика
        """
        with self._data_lock:
            uptime = datetime.now() - self._stats["start_time"]
            
            return {
                "total_updates": self._stats["total_updates"],
                "updates_by_type": dict(self._stats["updates_by_type"]),
                "updates_by_module": dict(self._stats["updates_by_module"]),
                "uptime_seconds": uptime.total_seconds(),
                "current_data_types": list(self._current_data.keys()),
                "history_sizes": {
                    data_type.value: len(self._history[data_type]) 
                    for data_type in DataType
                },
                "subscribers_count": {
                    data_type.value: len(self._subscribers[data_type]) 
                    for data_type in DataType
                }
            }
    
    def is_data_fresh(self, data_type: DataType, max_age_seconds: float = 5.0) -> bool:
        """
        Проверка свежести данных
        
        Args:
            data_type: Тип данных
            max_age_seconds: Максимальный возраст в секундах
            
        Returns:
            bool: True если данные свежие
        """
        entry = self.get_data(data_type)
        if not entry:
            return False
        
        age = (datetime.now() - entry.timestamp).total_seconds()
        return age <= max_age_seconds
    
    def clear_history(self, data_type: Optional[DataType] = None):
        """
        Очистка истории данных
        
        Args:
            data_type: Тип данных для очистки (None для очистки всей истории)
        """
        with self._data_lock:
            if data_type:
                self._history[data_type].clear()
            else:
                for dt in DataType:
                    self._history[dt].clear()
    
    def get_all_current_data(self) -> Dict[str, Any]:
        """
        Получение всех текущих данных в удобном формате
        
        Returns:
            Dict: Словарь с текущими данными
        """
        with self._data_lock:
            result = {}
            for data_type, entry in self._current_data.items():
                result[data_type.value] = {
                    "value": entry.value,
                    "timestamp": entry.timestamp.isoformat(),
                    "source_module": entry.source_module,
                    "metadata": entry.metadata,
                    "age_seconds": (datetime.now() - entry.timestamp).total_seconds()
                }
            return result 