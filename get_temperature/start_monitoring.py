#!/usr/bin/env python3
"""
Простой запуск мониторинга температуры
"""

import simple_api
import time
import signal
import sys

def signal_handler(sig, frame):
    """Обработчик сигнала для корректного завершения"""
    print('\n🛑 Остановка мониторинга...')
    simple_api.stop_temperature_monitoring()
    print('✅ Мониторинг остановлен')
    sys.exit(0)

def main():
    """Основная функция мониторинга"""
    print('🚀 Запуск мониторинга температуры жидкости асика')
    print('=' * 50)
    
    # Установка обработчика сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Запуск мониторинга
    print('🔄 Запуск мониторинга...')
    if simple_api.start_temperature_monitoring("192.168.0.91", update_interval=1.0):
        print('✅ Мониторинг запущен успешно')
        print('📊 Нажмите Ctrl+C для остановки')
        print('-' * 50)
        
        try:
            while True:
                # Получение данных
                temp = simple_api.get_current_temperature()
                status = simple_api.get_temperature_status()
                data = simple_api.get_all_temperature_data()
                
                if temp is not None:
                    print(f'🌡️  Температура жидкости: {temp}°C | Статус: {status}')
                    
                    if data:
                        print(f'    PSU: {data["psu_temperature"]}°C | '
                              f'Вентилятор: {data["fan_speed"]} RPM | '
                              f'Время: {data["timestamp"]}')
                else:
                    print('❌ Ошибка получения данных')
                
                # Статистика каждые 10 итераций
                stats = simple_api.get_monitoring_statistics()
                if stats['total_requests'] % 10 == 0 and stats['total_requests'] > 0:
                    print(f'📈 Статистика: {stats["successful_requests"]}/{stats["total_requests"]} '
                          f'({stats["success_rate"]}% успех)')
                
                time.sleep(2)  # Обновление каждые 2 секунды
                
        except KeyboardInterrupt:
            signal_handler(None, None)
    else:
        print('❌ Не удалось запустить мониторинг')

if __name__ == "__main__":
    main() 