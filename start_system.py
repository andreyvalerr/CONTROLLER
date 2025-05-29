#!/usr/bin/env python3
"""
Простой запуск системы контроля температуры
"""

from valve_control.valve_controller import ValveController
import signal
import sys

def main():
    print("🚀 ЗАПУСК СИСТЕМЫ КОНТРОЛЯ ТЕМПЕРАТУРЫ")
    print("=" * 50)
    
    # Создание контроллера
    controller = ValveController()
    
    def signal_handler(sig, frame):
        print("\n🛑 Получен сигнал остановки...")
        controller.stop()
        print("✅ Система остановлена")
        sys.exit(0)
    
    # Регистрация обработчика сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Запуск системы
        if controller.start():
            print("✅ Система запущена успешно!")
            print("📊 Мониторинг температуры активен")
            print("🔧 Автоматическое управление клапанами включено")
            print("\nНажмите Ctrl+C для остановки системы")
            
            # Запуск в бесконечном цикле
            controller.run_forever()
        else:
            print("❌ Ошибка запуска системы")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Остановка по запросу пользователя...")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return 1
    finally:
        controller.stop()
        print("✅ Система корректно остановлена")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 