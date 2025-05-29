#!/usr/bin/env python3
"""
Мониторинг температуры с использованием класса TemperatureAPI
"""

from simple_api import TemperatureAPI
import time
import signal
import sys

class TemperatureMonitorApp:
    """Приложение для мониторинга температуры"""
    
    def __init__(self, ip_address="192.168.0.127", update_interval=1.0):
        self.api = TemperatureAPI(ip_address, update_interval)
        self.running = False
        
    def signal_handler(self, sig, frame):
        """Обработчик сигнала для корректного завершения"""
        print('\n🛑 Остановка мониторинга...')
        self.stop()
        sys.exit(0)
        
    def start(self):
        """Запуск мониторинга"""
        print('🚀 Запуск мониторинга температуры (класс API)')
        print('=' * 50)
        
        # Установка обработчика сигналов
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Запуск API
        if self.api.start():
            print('✅ Мониторинг запущен успешно')
            print('📊 Нажмите Ctrl+C для остановки')
            print('-' * 50)
            
            self.running = True
            self.monitor_loop()
        else:
            print('❌ Не удалось запустить мониторинг')
            
    def monitor_loop(self):
        """Основной цикл мониторинга"""
        iteration = 0
        
        try:
            while self.running:
                iteration += 1
                
                # Получение данных
                temp = self.api.get_temperature()
                status = self.api.get_status()
                health = self.api.is_healthy()
                all_data = self.api.get_all_data()
                
                # Вывод основной информации
                health_icon = "💚" if health else "❤️"
                print(f'🌡️  Температура: {temp}°C | Статус: {status} | {health_icon}')
                
                # Дополнительная информация
                if all_data:
                    print(f'    PSU: {all_data["psu_temperature"]}°C | '
                          f'Вентилятор: {all_data["fan_speed"]} RPM')
                
                # Статистика каждые 10 итераций
                if iteration % 10 == 0:
                    print(f'📈 Итерация: {iteration} | Здоровье системы: {health}')
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            self.signal_handler(None, None)
            
    def stop(self):
        """Остановка мониторинга"""
        self.running = False
        self.api.stop()
        print('✅ Мониторинг остановлен')

def main():
    """Основная функция"""
    # Создание и запуск приложения
    app = TemperatureMonitorApp("192.168.0.91", update_interval=1.5)
    app.start()

if __name__ == "__main__":
    main() 