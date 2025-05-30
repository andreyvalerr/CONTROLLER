#!/usr/bin/env python3
"""
Запуск системы контроля температуры с GUI интерфейсом
"""

import signal
import sys
import threading
import time
from core.shared_state import system_state

# Опциональный запуск GUI
GUI_ENABLED = True
try:
    from gui_interface.main_gui import TemperatureControllerGUI
except ImportError:
    GUI_ENABLED = False
    print("⚠️ GUI недоступен (отсутствует Kivy)")

# Импорт температурного API напрямую
try:
    from get_temperature import get_current_temperature, TemperatureAPI
    TEMPERATURE_API_AVAILABLE = True
except ImportError:
    TEMPERATURE_API_AVAILABLE = False
    print("⚠️ API температуры недоступен")

class SystemManager:
    """Менеджер всей системы"""
    
    def __init__(self):
        self.temperature_api = None
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
    
    def _setup_temperature_monitoring(self):
        """Настройка мониторинга температуры асика"""
        if not TEMPERATURE_API_AVAILABLE:
            print("❌ API температуры недоступен")
            return False
            
        try:
            # Создание температурного API
            self.temperature_api = TemperatureAPI(
                ip_address="192.168.0.127",  # IP асика
                update_interval=1.0
            )
            
            if self.temperature_api.start():
                print("✅ Мониторинг температуры асика запущен")
                
                # Запуск обновления данных в shared_state
                def temperature_update_worker():
                    while self.running:
                        try:
                            current_temp = self.temperature_api.get_temperature()
                            if current_temp is not None:
                                system_state.update_temperature(current_temp, "whatsminer")
                            else:
                                print("⚠️ Не удалось получить температуру асика")
                        except Exception as e:
                            print(f"Ошибка получения температуры: {e}")
                        
                        time.sleep(1.0)
                
                temp_thread = threading.Thread(target=temperature_update_worker, daemon=True)
                temp_thread.start()
                return True
            else:
                print("❌ Не удалось запустить мониторинг температуры")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка настройки мониторинга температуры: {e}")
            return False
    
    def start(self):
        """Запуск всей системы"""
        print("🚀 ЗАПУСК СИСТЕМЫ КОНТРОЛЯ ТЕМПЕРАТУРЫ")
        print("=" * 50)
        
        self.running = True
        
        # 1. Настройка мониторинга температуры асика
        print("🌡️ Настройка мониторинга температуры асика...")
        if not self._setup_temperature_monitoring():
            print("⚠️ Продолжаем без мониторинга температуры")
        
        # Ждем немного для инициализации
        time.sleep(2)
        
        # 2. Запуск GUI (если доступен)
        if GUI_ENABLED:
            print("🖥️ Запуск GUI интерфейса...")
            try:
                self.gui_app = TemperatureControllerGUI()
                
                print("✅ Система полностью запущена!")
                print("📊 GUI интерфейс активен")
                print("🌡️ Отображается реальная температура асика")
                print("\nЗакройте окно GUI для остановки системы")
                
                # Запуск GUI в главном потоке
                self.gui_app.run()
                
            except Exception as e:
                print(f"❌ Ошибка запуска GUI: {e}")
                return False
        else:
            print("✅ Система запущена без GUI")
            print("🌡️ Мониторинг температуры асика активен")
            print("Нажмите Ctrl+C для остановки")
            
            # Простое ожидание в случае отсутствия GUI
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        
        return True
    
    def stop(self):
        """Остановка системы"""
        print("🛑 Остановка системы...")
        self.running = False
        
        # Остановка мониторинга температуры
        if self.temperature_api:
            self.temperature_api.stop()
        
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