#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работоспособности GUI и API системы
"""

import time
import threading
import requests
import json
from core.shared_state import system_state
from core.api_server import api_server

def test_shared_state():
    """Тест общего состояния системы"""
    print("🧪 Тест SharedState...")
    
    # Тест обновления температуры
    system_state.update_temperature(51.5, "test")
    temp_data = system_state.get_temperature_data()
    assert temp_data.current_temp == 51.5
    print("✅ Обновление температуры работает")
    
    # Тест обновления целевой температуры
    success = system_state.update_target_temperature(53.0)
    assert success == True
    settings = system_state.get_settings()
    assert settings.max_temperature == 53.0
    print("✅ Обновление целевой температуры работает")
    
    # Тест обновления состояния клапана
    system_state.update_valve_state(True)
    status = system_state.get_system_status()
    assert status.valve_state == True
    print("✅ Обновление состояния клапана работает")
    
    print("✅ Все тесты SharedState прошли успешно\n")

def test_api_server():
    """Тест API сервера"""
    print("🧪 Тест API сервера...")
    
    # Запуск API сервера
    if not api_server.start():
        print("❌ Не удалось запустить API сервер")
        return False
    
    # Даем время на запуск
    time.sleep(2)
    
    try:
        # Тест health check
        response = requests.get("http://localhost:5000/api/health")
        assert response.status_code == 200
        print("✅ Health check работает")
        
        # Тест получения статуса
        response = requests.get("http://localhost:5000/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        print("✅ Получение статуса работает")
        
        # Тест установки температуры
        response = requests.post(
            "http://localhost:5000/api/temperature/target",
            json={"target_temp": 54.0}
        )
        assert response.status_code == 200
        print("✅ Установка температуры через API работает")
        
        # Проверяем, что температура действительно изменилась
        response = requests.get("http://localhost:5000/api/status")
        data = response.json()
        temp = data["data"]["settings"]["max_temperature"]
        assert temp == 54.0
        print("✅ Температура изменилась корректно")
        
        print("✅ Все тесты API сервера прошли успешно\n")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования API: {e}")
        return False
    finally:
        api_server.stop()

def test_gui_import():
    """Тест импорта GUI модулей"""
    print("🧪 Тест импорта GUI...")
    
    try:
        from gui_interface.main_gui import TemperatureControllerGUI
        print("✅ GUI модули импортируются корректно")
        
        # Попытка создать приложение (без запуска)
        app = TemperatureControllerGUI()
        print("✅ GUI приложение создается корректно")
        
        print("✅ Все тесты GUI прошли успешно\n")
        return True
        
    except ImportError as e:
        print(f"⚠️ GUI недоступен: {e}")
        print("   Возможно, не установлен Kivy")
        return False
    except Exception as e:
        print(f"❌ Ошибка GUI: {e}")
        return False

def test_data_models():
    """Тест моделей данных"""
    print("🧪 Тест моделей данных...")
    
    from core.data_models import SystemSettings, TemperatureData, SystemStatus, SystemData
    from datetime import datetime
    
    # Тест SystemSettings
    settings = SystemSettings(max_temperature=55.0, min_temperature=54.9)
    assert settings.validate() == True
    print("✅ SystemSettings работает")
    
    # Тест сериализации
    settings_dict = settings.to_dict()
    settings_restored = SystemSettings.from_dict(settings_dict)
    assert settings_restored.max_temperature == settings.max_temperature
    print("✅ Сериализация настроек работает")
    
    # Тест TemperatureData
    temp_data = TemperatureData(
        current_temp=52.1,
        target_temp=52.0,
        min_temp=51.9,
        timestamp=datetime.now()
    )
    temp_dict = temp_data.to_dict()
    temp_restored = TemperatureData.from_dict(temp_dict)
    assert temp_restored.current_temp == temp_data.current_temp
    print("✅ TemperatureData работает")
    
    print("✅ Все тесты моделей данных прошли успешно\n")

def main():
    """Запуск всех тестов"""
    print("🚀 ЗАПУСК ТЕСТОВ СИСТЕМЫ GUI И API")
    print("=" * 50)
    
    all_passed = True
    
    # Тест моделей данных
    try:
        test_data_models()
    except Exception as e:
        print(f"❌ Тест моделей данных провален: {e}")
        all_passed = False
    
    # Тест SharedState
    try:
        test_shared_state()
    except Exception as e:
        print(f"❌ Тест SharedState провален: {e}")
        all_passed = False
    
    # Тест API сервера
    try:
        if not test_api_server():
            all_passed = False
    except Exception as e:
        print(f"❌ Тест API сервера провален: {e}")
        all_passed = False
    
    # Тест GUI (опциональный)
    try:
        test_gui_import()
    except Exception as e:
        print(f"❌ Тест GUI провален: {e}")
        # GUI не критичен для общей работоспособности
    
    print("=" * 50)
    if all_passed:
        print("✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("🎉 Система готова к использованию")
        print("\nДля запуска с GUI:")
        print("python3 start_system_with_gui.py")
        print("\nДля тестирования API:")
        print("curl http://localhost:5000/api/health")
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        print("Проверьте ошибки выше")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 