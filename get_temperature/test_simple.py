#!/usr/bin/env python3
"""
Простой тест API Whatsminer на основе документации
"""

from whatsminer_transport import WhatsminerTCP
from whatsminer_interface import WhatsminerAPIv3

def get_liquid_temp_simple(ip):
    """Простое получение температуры жидкости"""
    
    # Инициализация
    api = WhatsminerAPIv3("super", "super")
    tcp = WhatsminerTCP(ip, 4433, "super", "super")
    
    try:
        print(f"🔍 Подключение к {ip}...")
        
        # Подключение
        if not tcp.connect():
            print("❌ Не удалось подключиться")
            return None
        
        print("✅ Подключение установлено")
        
        # Аутентификация
        print("🔐 Аутентификация...")
        req = api.get_request_cmds("get.device.info")
        resp = tcp.send(req, len(req), api)
        
        if resp and resp.get('code') == 0:
            print("✅ Аутентификация успешна")
            
            # Установка salt
            salt = resp['msg']['salt']
            api.set_salt(salt)
            print(f"🔑 Salt установлен: {salt}")
            
            # Извлечение температуры из первого ответа
            power_data = resp['msg'].get('power', {})
            liquid_temp = power_data.get('liquid-temperature')
            psu_temp = power_data.get('temp0')
            fan_speed = power_data.get('fanspeed')
            
            print(f"🌡️ Температура жидкости: {liquid_temp}°C")
            print(f"🌡️ Температура PSU: {psu_temp}°C")
            print(f"🌀 Скорость вентилятора: {fan_speed} RPM")
            
            tcp.close()
            return liquid_temp
        else:
            print(f"❌ Ошибка аутентификации: {resp}")
            return None
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None
    finally:
        tcp.close()

if __name__ == "__main__":
    # Тест
    temp = get_liquid_temp_simple("192.168.0.91")
    if temp:
        print(f"\n✅ Результат: {temp}°C")
    else:
        print("\n❌ Не удалось получить температуру") 