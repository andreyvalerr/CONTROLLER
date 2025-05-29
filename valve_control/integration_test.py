#!/usr/bin/env python3
"""
Тест полной интеграции системы контроллера клапанов
"""

import time
from .valve_controller import ValveController

def main():
    print('=== ТЕСТ ПОЛНОЙ ИНТЕГРАЦИИ СИСТЕМЫ ===')

    # Создание контроллера
    controller = ValveController()
    print('✓ Контроллер создан')

    try:
        # Запуск контроллера
        if controller.start():
            print('✓ Контроллер запущен')
            
            # Работа в течение 10 секунд
            for i in range(10):
                status = controller.get_status()
                temp = status['temperature']['current']
                cooling = status['regulator']['cooling_active']
                cycles = status['regulator']['total_cycles']
                state = status['regulator']['state']
                
                temp_str = f"{temp}°C" if temp is not None else "недоступна"
                print(f'Цикл {i+1}: Температура={temp_str}, Охлаждение={cooling}, Циклов={cycles}, Состояние={state}')
                time.sleep(1)
            
            # Остановка
            controller.stop()
            print('✓ Контроллер остановлен')
            print('✓ Тест полной интеграции завершен успешно!')
            return True
        else:
            print('✗ Не удалось запустить контроллер')
            return False
            
    except Exception as e:
        print(f'✗ Ошибка во время теста: {e}')
        controller.stop()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 