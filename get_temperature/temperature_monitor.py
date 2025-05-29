#!/usr/bin/env python3
"""
Алиас для simple_monitor.py для совместимости
"""

from .simple_monitor import SimpleTemperatureMonitor as TemperatureMonitor, TemperatureData

__all__ = ["TemperatureMonitor", "TemperatureData"] 