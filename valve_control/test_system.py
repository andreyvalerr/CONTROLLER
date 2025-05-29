#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работоспособности системы контроллера клапанов
"""

import sys
import os
import time

def test_imports():
    """Тестирование импортов модулей"""
    print("=== ТЕСТИРОВАНИЕ ИМПОРТОВ ===")
    
    try:
        from . import config
        print("✓ Модуль config импортирован")
    except Exception as e:
        print(f"✗ Ошибка импорта config: {e}")
        return False
    
    try:
        from .config import RelayConfig, TemperatureConfig, MonitoringConfig, SafetyConfig
        print("✓ Классы конфигурации импортированы")
    except Exception as e:
        print(f"✗ Ошибка импорта классов конфигурации: {e}")
        return False
    
    try:
        from . import relay_controller
        print("✓ Модуль relay_controller импортирован")
    except Exception as e:
        print(f"✗ Ошибка импорта relay_controller: {e}")
        return False
    
    try:
        from . import temperature_regulator
        print("✓ Модуль temperature_regulator импортирован")
    except Exception as e:
        print(f"✗ Ошибка импорта temperature_regulator: {e}")
        return False
    
    try:
        from . import valve_controller
        print("✓ Модуль valve_controller импортирован")
    except Exception as e:
        print(f"✗ Ошибка импорта valve_controller: {e}")
        return False
    
    return True

def test_config():
    """Тестирование системы конфигурации"""
    print("\n=== ТЕСТИРОВАНИЕ КОНФИГУРАЦИИ ===")
    
    try:
        from .config import RelayConfig, TemperatureConfig, load_config_from_env, validate_config
        
        # Создание конфигураций по умолчанию
        relay_config = RelayConfig()
        temp_config = TemperatureConfig()
        
        print(f"✓ Конфигурация реле: GPIO {relay_config.relay_pin}")
        print(f"✓ Температурные пороги: {temp_config.min_temperature}°C - {temp_config.max_temperature}°C")
        
        # Валидация конфигурации
        errors = validate_config(relay_config, temp_config)
        if errors:
            print(f"✗ Ошибки валидации: {errors}")
            return False
        else:
            print("✓ Валидация конфигурации прошла успешно")
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка тестирования конфигурации: {e}")
        return False

def test_relay_controller():
    """Тестирование контроллера реле"""
    print("\n=== ТЕСТИРОВАНИЕ КОНТРОЛЛЕРА РЕЛЕ ===")
    
    try:
        from .relay_controller import RelayController
        from .config import RelayConfig
        
        # Создание контроллера
        config = RelayConfig()
        relay = RelayController(config)
        
        print(f"✓ Контроллер реле создан для GPIO {config.relay_pin}")
        print(f"✓ Инициализация: {'успешна' if relay.is_initialized() else 'неуспешна'}")
        
        # Получение статистики
        stats = relay.get_statistics()
        print(f"✓ Текущее состояние: {'включено' if stats['relay_state'] else 'выключено'}")
        print(f"✓ Количество переключений: {stats['switch_count']}")
        
        # Очистка
        relay.cleanup()
        print("✓ Очистка GPIO выполнена")
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка тестирования контроллера реле: {e}")
        return False

def test_temperature_regulator():
    """Тестирование регулятора температуры"""
    print("\n=== ТЕСТИРОВАНИЕ РЕГУЛЯТОРА ТЕМПЕРАТУРЫ ===")
    
    try:
        from .temperature_regulator import TemperatureRegulator, RegulatorConfig
        from .relay_controller import RelayController
        from .config import RelayConfig, TemperatureConfig, SafetyConfig
        
        # Функция эмуляции температуры
        def mock_temperature():
            return 38.5
        
        # Создание компонентов
        relay_config = RelayConfig()
        temp_config = TemperatureConfig()
        safety_config = SafetyConfig()
        
        relay = RelayController(relay_config)
        regulator_config = RegulatorConfig(temp_config, safety_config)
        regulator = TemperatureRegulator(relay, mock_temperature, regulator_config)
        
        print("✓ Регулятор температуры создан")
        print(f"✓ Пороги: {temp_config.min_temperature}°C - {temp_config.max_temperature}°C")
        
        # Получение статуса
        status = regulator.get_status()
        print(f"✓ Состояние регулятора: {status['state']}")
        print(f"✓ Работает: {'да' if status['is_running'] else 'нет'}")
        
        # Очистка
        relay.cleanup()
        print("✓ Очистка выполнена")
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка тестирования регулятора: {e}")
        return False

def test_valve_controller():
    """Тестирование основного контроллера клапанов"""
    print("\n=== ТЕСТИРОВАНИЕ КОНТРОЛЛЕРА КЛАПАНОВ ===")
    
    try:
        from .valve_controller import ValveController, ValveControllerConfig
        from .config import RelayConfig, TemperatureConfig, MonitoringConfig, SafetyConfig
        
        # Создание конфигурации
        config = ValveControllerConfig(
            relay_config=RelayConfig(),
            temperature_config=TemperatureConfig(),
            monitoring_config=MonitoringConfig(),
            safety_config=SafetyConfig()
        )
        
        # Создание контроллера
        controller = ValveController(config)
        print("✓ Контроллер клапанов создан")
        
        # Получение статуса без запуска
        status = controller.get_status()
        print(f"✓ Статус получен: работает = {status['controller']['is_running']}")
        
        # Проверка методов
        temp = controller.get_current_temperature()
        print(f"✓ Получение температуры: {temp if temp is not None else 'недоступно'}")
        
        cooling = controller.is_cooling_active()
        print(f"✓ Состояние охлаждения: {'включено' if cooling else 'выключено'}")
        
        print("✓ Все методы контроллера работают")
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка тестирования контроллера клапанов: {e}")
        return False

def test_get_temperature_integration():
    """Тестирование интеграции с модулем get_temperature"""
    print("\n=== ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ GET_TEMPERATURE ===")
    
    try:
        # Добавление пути к модулю get_temperature
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'get_temperature'))
        
        try:
            from get_temperature import get_current_temperature
            print("✓ Модуль get_temperature найден")
            
            # Попытка получить температуру
            temp = get_current_temperature()
            if temp is not None:
                print(f"✓ Температура получена: {temp}°C")
            else:
                print("⚠ Температура не получена (возможно, асик недоступен)")
            
        except ImportError:
            print("⚠ Модуль get_temperature недоступен, будет использоваться эмуляция")
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка тестирования интеграции: {e}")
        return False

def test_manual_control():
    """Тестирование ручного управления"""
    print("\n=== ТЕСТИРОВАНИЕ РУЧНОГО УПРАВЛЕНИЯ ===")
    
    try:
        from . import manual_control
        print("✓ Модуль manual_control импортирован")
        
        # Проверка функции ручного управления
        from .manual_control import manual_valve_control
        print("✓ Функция manual_valve_control доступна")
        
        return True
        
    except Exception as e:
        print(f"✗ Ошибка тестирования ручного управления: {e}")
        return False

def main():
    """Главная функция тестирования"""
    print("ТЕСТИРОВАНИЕ СИСТЕМЫ КОНТРОЛЛЕРА КЛАПАНОВ")
    print("=" * 50)
    
    tests = [
        ("Импорты модулей", test_imports),
        ("Система конфигурации", test_config),
        ("Контроллер реле", test_relay_controller),
        ("Регулятор температуры", test_temperature_regulator),
        ("Контроллер клапанов", test_valve_controller),
        ("Интеграция get_temperature", test_get_temperature_integration),
        ("Ручное управление", test_manual_control),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✓ {test_name}: ПРОЙДЕН")
            else:
                print(f"\n✗ {test_name}: ПРОВАЛЕН")
        except Exception as e:
            print(f"\n✗ {test_name}: ОШИБКА - {e}")
    
    print("\n" + "=" * 50)
    print(f"РЕЗУЛЬТАТ: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print("⚠ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 