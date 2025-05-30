#!/usr/bin/env python3
"""
Модели данных для системы управления температурой
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
import json

@dataclass
class TemperatureData:
    """Данные о температуре"""
    current_temp: float
    target_temp: float
    min_temp: float
    timestamp: datetime
    source: str = "whatsminer"  # источник данных
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для JSON"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemperatureData':
        """Создание объекта из словаря"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

@dataclass
class SystemStatus:
    """Статус системы"""
    valve_state: bool
    system_mode: str  # "auto", "manual", "emergency"
    last_update: datetime
    errors: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для JSON"""
        data = asdict(self)
        data['last_update'] = self.last_update.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemStatus':
        """Создание объекта из словаря"""
        data['last_update'] = datetime.fromisoformat(data['last_update'])
        return cls(**data)

@dataclass
class SystemSettings:
    """Настройки системы"""
    max_temperature: float = 52.0
    min_temperature: float = 51.9
    hysteresis: float = 0.1
    control_interval: float = 1.0
    critical_temp: float = 65.0
    emergency_temp: float = 70.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для JSON"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemSettings':
        """Создание объекта из словаря"""
        return cls(**data)
    
    def validate(self) -> bool:
        """Проверка корректности настроек"""
        if self.max_temperature <= self.min_temperature:
            return False
        if self.critical_temp <= self.max_temperature:
            return False
        if self.emergency_temp <= self.critical_temp:
            return False
        return True

@dataclass
class SystemData:
    """Полные данные системы для обмена"""
    temperature: TemperatureData
    status: SystemStatus
    settings: SystemSettings
    
    def to_json(self) -> str:
        """Преобразование в JSON"""
        return json.dumps({
            'temperature': self.temperature.to_dict(),
            'status': self.status.to_dict(),
            'settings': self.settings.to_dict()
        }, ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SystemData':
        """Создание объекта из JSON"""
        data = json.loads(json_str)
        return cls(
            temperature=TemperatureData.from_dict(data['temperature']),
            status=SystemStatus.from_dict(data['status']),
            settings=SystemSettings.from_dict(data['settings'])
        ) 