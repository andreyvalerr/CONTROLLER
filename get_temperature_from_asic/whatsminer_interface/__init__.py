#!/usr/bin/env python3
"""
Интерфейс для работы с Whatsminer
Модули для TCP транспорта и API взаимодействия
"""

from .whatsminer_transport import WhatsminerTCP
from .whatsminer_interface import WhatsminerAPIv3

__all__ = ["WhatsminerTCP", "WhatsminerAPIv3"] 