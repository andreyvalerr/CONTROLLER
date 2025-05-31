#!/usr/bin/env python3
"""
Конфигурация модуля получения температуры
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class TemperatureConfig:
    """Конфигурация температурного мониторинга"""
    # Настройки подключения
    ip_address: str = "192.168.0.127"
    port: int = 4433
    account: str = "super"
    password: str = "super"
    
    # Интервалы
    update_interval: float = 1.0
    connection_timeout: float = 10.0
    
    # Пороги температуры
    normal_temp_max: float = 40.0
    warning_temp_max: float = 50.0
    critical_temp_max: float = 60.0
    
    # Логирование
    log_level: str = "INFO"
    log_file: Optional[str] = None
    enable_console_log: bool = True

# Конфигурация по умолчанию
DEFAULT_CONFIG = TemperatureConfig()

def load_config_from_env() -> TemperatureConfig:
    """
    Загрузка конфигурации из переменных окружения
    
    Returns:
        TemperatureConfig: Конфигурация
    """
    return TemperatureConfig(
        ip_address=os.getenv("ASIC_IP", DEFAULT_CONFIG.ip_address),
        port=int(os.getenv("ASIC_PORT", DEFAULT_CONFIG.port)),
        account=os.getenv("ASIC_ACCOUNT", DEFAULT_CONFIG.account),
        password=os.getenv("ASIC_PASSWORD", DEFAULT_CONFIG.password),
        update_interval=float(os.getenv("UPDATE_INTERVAL", DEFAULT_CONFIG.update_interval)),
        connection_timeout=float(os.getenv("CONNECTION_TIMEOUT", DEFAULT_CONFIG.connection_timeout)),
        normal_temp_max=float(os.getenv("NORMAL_TEMP_MAX", DEFAULT_CONFIG.normal_temp_max)),
        warning_temp_max=float(os.getenv("WARNING_TEMP_MAX", DEFAULT_CONFIG.warning_temp_max)),
        critical_temp_max=float(os.getenv("CRITICAL_TEMP_MAX", DEFAULT_CONFIG.critical_temp_max)),
        log_level=os.getenv("LOG_LEVEL", DEFAULT_CONFIG.log_level),
        log_file=os.getenv("LOG_FILE", DEFAULT_CONFIG.log_file),
        enable_console_log=os.getenv("CONSOLE_LOG", "true").lower() == "true"
    ) 