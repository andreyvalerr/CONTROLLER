#!/usr/bin/env python3
"""
API сервер для обмена данными с удаленным веб-сервисом
"""

import json
import time
import requests
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from flask import Flask, request, jsonify
from .shared_state import system_state
from .data_models import SystemSettings, SystemData

class APIServer:
    """
    REST API сервер для обмена данными между Raspberry Pi и удаленным веб-сервисом
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5000):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.running = False
        self.server_thread: Optional[threading.Thread] = None
        
        # Настройки для отправки данных на удаленный сервер
        self.remote_server_url: Optional[str] = None
        self.data_sender_thread: Optional[threading.Thread] = None
        self.send_interval = 10  # интервал отправки данных в секундах
        
        self._setup_routes()
        
        # Подписка на изменения системы
        system_state.subscribe(self._on_system_update)
    
    def _setup_routes(self):
        """Настройка маршрутов API"""
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """Получение статуса системы"""
            try:
                data = system_state.get_system_data()
                return jsonify({
                    "status": "success",
                    "data": {
                        "temperature": data.temperature.to_dict(),
                        "system_status": data.status.to_dict(),
                        "settings": data.settings.to_dict()
                    }
                })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/temperature', methods=['GET'])
        def get_temperature():
            """Получение данных о температуре"""
            try:
                temp_data = system_state.get_temperature_data()
                return jsonify({
                    "status": "success",
                    "data": temp_data.to_dict()
                })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/settings', methods=['GET'])
        def get_settings():
            """Получение настроек системы"""
            try:
                settings = system_state.get_settings()
                return jsonify({
                    "status": "success",
                    "data": settings.to_dict()
                })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/settings', methods=['POST'])
        def update_settings():
            """Обновление настроек системы"""
            try:
                data = request.get_json()
                
                if not data:
                    return jsonify({
                        "status": "error",
                        "message": "Отсутствуют данные"
                    }), 400
                
                # Создание объекта настроек из полученных данных
                settings = SystemSettings.from_dict(data)
                
                if system_state.update_settings(settings):
                    return jsonify({
                        "status": "success",
                        "message": "Настройки обновлены"
                    })
                else:
                    return jsonify({
                        "status": "error",
                        "message": "Некорректные настройки"
                    }), 400
                    
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/temperature/target', methods=['POST'])
        def set_target_temperature():
            """Быстрое обновление целевой температуры"""
            try:
                data = request.get_json()
                
                if not data or 'target_temp' not in data:
                    return jsonify({
                        "status": "error",
                        "message": "Отсутствует параметр target_temp"
                    }), 400
                
                target_temp = float(data['target_temp'])
                
                if system_state.update_target_temperature(target_temp):
                    return jsonify({
                        "status": "success",
                        "message": f"Целевая температура установлена: {target_temp}°C"
                    })
                else:
                    return jsonify({
                        "status": "error",
                        "message": "Некорректное значение температуры"
                    }), 400
                    
            except (ValueError, TypeError) as e:
                return jsonify({
                    "status": "error",
                    "message": "Некорректный формат температуры"
                }), 400
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/valve', methods=['POST'])
        def control_valve():
            """Ручное управление клапаном (только в ручном режиме)"""
            try:
                data = request.get_json()
                
                if not data or 'state' not in data:
                    return jsonify({
                        "status": "error",
                        "message": "Отсутствует параметр state"
                    }), 400
                
                # Проверка режима системы
                status = system_state.get_system_status()
                if status.system_mode != "manual":
                    return jsonify({
                        "status": "error",
                        "message": "Ручное управление доступно только в ручном режиме"
                    }), 403
                
                valve_state = bool(data['state'])
                system_state.update_valve_state(valve_state)
                
                return jsonify({
                    "status": "success",
                    "message": f"Клапан {'открыт' if valve_state else 'закрыт'}"
                })
                    
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/mode', methods=['POST'])
        def set_mode():
            """Установка режима системы"""
            try:
                data = request.get_json()
                
                if not data or 'mode' not in data:
                    return jsonify({
                        "status": "error",
                        "message": "Отсутствует параметр mode"
                    }), 400
                
                mode = data['mode']
                
                if system_state.update_system_mode(mode):
                    return jsonify({
                        "status": "success",
                        "message": f"Режим установлен: {mode}"
                    })
                else:
                    return jsonify({
                        "status": "error",
                        "message": "Некорректный режим. Доступны: auto, manual, emergency"
                    }), 400
                    
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Проверка работоспособности API"""
            return jsonify({
                "status": "success",
                "message": "API сервер работает",
                "timestamp": datetime.now().isoformat()
            })
    
    def _on_system_update(self, system_data: SystemData):
        """Обработчик изменений в системе"""
        # Здесь можно добавить логику для немедленной отправки
        # критических изменений на удаленный сервер
        pass
    
    def set_remote_server(self, url: str, send_interval: int = 10):
        """Настройка удаленного сервера для отправки данных"""
        self.remote_server_url = url
        self.send_interval = send_interval
    
    def _data_sender_worker(self):
        """Рабочий поток для отправки данных на удаленный сервер"""
        while self.running and self.remote_server_url:
            try:
                # Получаем текущие данные системы
                system_data = system_state.get_system_data()
                
                # Отправляем на удаленный сервер
                response = requests.post(
                    f"{self.remote_server_url}/api/update",
                    json={
                        "device_id": "raspberry_pi_controller",
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "temperature": system_data.temperature.to_dict(),
                            "status": system_data.status.to_dict(),
                            "settings": system_data.settings.to_dict()
                        }
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    print(f"✅ Данные отправлены на удаленный сервер: {datetime.now()}")
                else:
                    print(f"⚠️ Ошибка отправки данных: {response.status_code}")
                    
            except requests.RequestException as e:
                print(f"❌ Ошибка соединения с удаленным сервером: {e}")
            except Exception as e:
                print(f"❌ Ошибка отправки данных: {e}")
            
            # Ждем до следующей отправки
            time.sleep(self.send_interval)
    
    def start(self) -> bool:
        """Запуск API сервера"""
        try:
            self.running = True
            
            # Запуск Flask сервера в отдельном потоке
            self.server_thread = threading.Thread(
                target=lambda: self.app.run(
                    host=self.host, 
                    port=self.port, 
                    debug=False,
                    use_reloader=False
                ),
                daemon=True
            )
            self.server_thread.start()
            
            # Запуск отправщика данных если настроен удаленный сервер
            if self.remote_server_url:
                self.data_sender_thread = threading.Thread(
                    target=self._data_sender_worker,
                    daemon=True
                )
                self.data_sender_thread.start()
            
            print(f"🌐 API сервер запущен на {self.host}:{self.port}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка запуска API сервера: {e}")
            self.running = False
            return False
    
    def stop(self):
        """Остановка API сервера"""
        self.running = False
        print("🛑 API сервер остановлен")

# Глобальный экземпляр API сервера
api_server = APIServer() 