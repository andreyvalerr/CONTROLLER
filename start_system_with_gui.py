#!/usr/bin/env python3
"""
Запуск системы контроля температуры с GUI интерфейсом и API сервером
"""

import signal
import sys
import threading
import time
from valve_control.valve_controller import ValveController
from core.api_server import api_server
from core.shared_state import system_state

# Опциональный запуск GUI
GUI_ENABLED = True
try:
    from gui_interface.main_gui import TemperatureControllerGUI
except ImportError:
    GUI_ENABLED = False
    print("⚠️ GUI недоступен (отсутствует Kivy)")

class SystemManager:
    """Менеджер всей системы"""
    
    def __init__(self):
        self.valve_controller = None
        self.gui_app = None
        self.running = False
        
        # Настройка обработчиков сигналов
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Обработчик сигналов остановки"""
        print(f"\n🛑 Получен сигнал {sig}...")
        self.stop()
        sys.exit(0)
    
    def _valve_controller_worker(self):
        """Рабочий поток контроллера клапанов"""
        try:
            # Создание и запуск контроллера
            self.valve_controller = ValveController()
            
            # Подключение к общему состоянию системы
            self._setup_valve_controller_integration()
            
            if self.valve_controller.start():
                print("✅ Контроллер клапанов запущен")
                self.valve_controller.run_forever()
            else:
                print("❌ Ошибка запуска контроллера клапанов")
                system_state.set_error("Ошибка запуска контроллера клапанов")
                
        except Exception as e:
            print(f"❌ Критическая ошибка контроллера клапанов: {e}")
            system_state.set_error(f"Критическая ошибка: {e}")
    
    def _setup_valve_controller_integration(self):
        """Настройка интеграции контроллера клапанов с общим состоянием"""
        if not self.valve_controller:
            return
        
        # Подписка на изменения настроек из GUI/API
        def on_settings_update(system_data):
            try:
                settings = system_data.settings
                # Обновляем настройки в контроллере клапанов
                if hasattr(self.valve_controller, 'temperature_regulator'):
                    regulator = self.valve_controller.temperature_regulator
                    regulator.config.max_temperature = settings.max_temperature
                    regulator.config.min_temperature = settings.min_temperature
                    regulator.config.hysteresis = settings.hysteresis
                    print(f"📝 Настройки контроллера обновлены: {settings.max_temperature}°C")
            except Exception as e:
                print(f"Ошибка обновления настроек контроллера: {e}")
        
        system_state.subscribe(on_settings_update)
        
        # Обновление данных в shared_state из контроллера
        def update_system_state():
            while self.running:
                try:
                    if hasattr(self.valve_controller, 'current_temperature'):
                        temp = getattr(self.valve_controller, 'current_temperature', 0.0)
                        system_state.update_temperature(temp, "whatsminer")
                    
                    if hasattr(self.valve_controller, 'relay_controller'):
                        valve_state = getattr(self.valve_controller.relay_controller, 'is_on', False)
                        system_state.update_valve_state(valve_state)
                        
                except Exception as e:
                    print(f"Ошибка синхронизации состояния: {e}")
                
                time.sleep(1.0)
        
        update_thread = threading.Thread(target=update_system_state, daemon=True)
        update_thread.start()
    
    def start(self):
        """Запуск всей системы"""
        print("🚀 ЗАПУСК СИСТЕМЫ КОНТРОЛЯ ТЕМПЕРАТУРЫ")
        print("=" * 50)
        
        self.running = True
        
        # 1. Запуск API сервера
        print("🌐 Запуск API сервера...")
        if api_server.start():
            print("✅ API сервер запущен на порту 5000")
        else:
            print("❌ Ошибка запуска API сервера")
            return False
        
        # Настройка удаленного сервера (если нужно)
        # api_server.set_remote_server("https://your-remote-server.com", 30)
        
        # 2. Запуск контроллера клапанов в отдельном потоке
        print("🔧 Запуск контроллера клапанов...")
        controller_thread = threading.Thread(
            target=self._valve_controller_worker,
            daemon=True
        )
        controller_thread.start()
        
        # Ждем немного для инициализации
        time.sleep(2)
        
        # 3. Запуск GUI (если доступен)
        if GUI_ENABLED:
            print("🖥️ Запуск GUI интерфейса...")
            try:
                self.gui_app = TemperatureControllerGUI()
                
                # Имитация данных для демонстрации
                self._setup_demo_data()
                
                print("✅ Система полностью запущена!")
                print("📊 GUI интерфейс активен")
                print("🌐 API доступен на http://localhost:5000/api/status")
                print("\nЗакройте окно GUI для остановки системы")
                
                # Запуск GUI в главном потоке
                self.gui_app.run()
                
            except Exception as e:
                print(f"❌ Ошибка запуска GUI: {e}")
                return False
        else:
            print("✅ Система запущена без GUI")
            print("🌐 API доступен на http://localhost:5000/api/status")
            print("Нажмите Ctrl+C для остановки")
            
            # Простое ожидание в случае отсутствия GUI
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        
        return True
    
    def _setup_demo_data(self):
        """Настройка демонстрационных данных"""
        # Имитация получения температуры
        def demo_temperature_update():
            import random
            while self.running:
                # Симуляция колебаний температуры
                base_temp = 51.5
                current_temp = base_temp + random.uniform(-1.0, 2.0)
                system_state.update_temperature(current_temp, "demo")
                time.sleep(2)
        
        demo_thread = threading.Thread(target=demo_temperature_update, daemon=True)
        demo_thread.start()
    
    def stop(self):
        """Остановка системы"""
        print("🛑 Остановка системы...")
        self.running = False
        
        # Остановка API сервера
        api_server.stop()
        
        # Остановка контроллера клапанов
        if self.valve_controller:
            self.valve_controller.stop()
        
        # Остановка GUI
        if self.gui_app:
            self.gui_app.stop()
        
        print("✅ Система остановлена")

def main():
    """Главная функция запуска"""
    try:
        manager = SystemManager()
        
        if manager.start():
            print("👋 Система завершена")
            return 0
        else:
            print("❌ Ошибка запуска системы")
            return 1
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 