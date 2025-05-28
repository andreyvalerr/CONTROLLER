#!/usr/bin/env python3
"""
TCP транспорт для связи с Whatsminer
Обеспечивает сетевое взаимодействие по протоколу TCP
"""

import socket
import struct
import json
import time
from typing import Optional, Dict, Any


class WhatsminerTCP:
    """Класс для TCP соединения с Whatsminer"""
    
    def __init__(self, ip_address: str, port: int = 4433, account: str = "super", password: str = "super"):
        """
        Инициализация TCP клиента
        
        Args:
            ip_address (str): IP адрес майнера
            port (int): Порт подключения (по умолчанию 4433)
            account (str): Учетная запись
            password (str): Пароль
        """
        self.ip_address = ip_address
        self.port = port
        self.account = account
        self.password = password
        self.socket = None
        self.connected = False
        
    def connect(self, timeout: int = 10) -> bool:
        """
        Установка соединения с майнером
        
        Args:
            timeout (int): Таймаут подключения в секундах
            
        Returns:
            bool: True если соединение установлено
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            self.socket.connect((self.ip_address, self.port))
            self.connected = True
            print(f"✅ Подключение к {self.ip_address}:{self.port} установлено")
            return True
            
        except ConnectionRefusedError:
            print(f"❌ Соединение отклонено {self.ip_address}:{self.port}")
            return False
        except socket.timeout:
            print(f"❌ Таймаут подключения к {self.ip_address}:{self.port}")
            return False
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    def send(self, data: bytes, length: int, api_instance=None) -> Optional[Dict[Any, Any]]:
        """
        Отправка данных и получение ответа
        
        Args:
            data (bytes): Данные для отправки
            length (int): Длина данных
            api_instance: Экземпляр API для расшифровки ответов
            
        Returns:
            dict: Ответ от майнера или None при ошибке
        """
        if not self.connected or not self.socket:
            print("❌ Соединение не установлено")
            return None
            
        try:
            # Формирование заголовка пакета
            header = struct.pack('<I', length)
            
            # Отправка заголовка и данных
            self.socket.sendall(header + data)
            
            # Получение заголовка ответа
            response_header = self._receive_exact(4)
            if not response_header:
                return None
                
            response_length = struct.unpack('<I', response_header)[0]
            
            # Получение данных ответа
            response_data = self._receive_exact(response_length)
            if not response_data:
                return None
            
            # Парсинг JSON ответа
            try:
                # Сначала пробуем как обычный JSON
                response_json = json.loads(response_data.decode())
                return response_json
            except json.JSONDecodeError:
                # Если не получилось, пробуем расшифровать
                if api_instance and hasattr(api_instance, 'decrypt_response'):
                    decrypted_response = api_instance.decrypt_response(response_data)
                    if decrypted_response:
                        return decrypted_response
                
                # Возможно данные зашифрованы, возвращаем как есть
                return {"encrypted_data": response_data}
                
        except socket.timeout:
            print("❌ Таймаут при отправке/получении данных")
            return None
        except Exception as e:
            print(f"❌ Ошибка при отправке данных: {e}")
            return None
    
    def _receive_exact(self, length: int) -> Optional[bytes]:
        """
        Получение точного количества байт
        
        Args:
            length (int): Количество байт для получения
            
        Returns:
            bytes: Полученные данные или None при ошибке
        """
        data = b''
        start_time = time.time()
        print(f"🔍 Ожидание {length} байт...")
        
        while len(data) < length:
            try:
                chunk = self.socket.recv(length - len(data))
                if not chunk:
                    print("❌ Соединение закрыто удаленной стороной")
                    return None
                data += chunk
                print(f"📥 Получено {len(chunk)} байт, всего: {len(data)}/{length}")
            except socket.timeout:
                elapsed = time.time() - start_time
                print(f"❌ Таймаут при получении данных (прошло {elapsed:.1f}с)")
                return None
            except Exception as e:
                print(f"❌ Ошибка при получении данных: {e}")
                return None
        
        elapsed = time.time() - start_time
        print(f"✅ Получено {len(data)} байт за {elapsed:.1f}с")
        return data
    
    def close(self):
        """Закрытие соединения"""
        if self.socket:
            try:
                self.socket.close()
                self.connected = False
                print(f"✅ Соединение с {self.ip_address}:{self.port} закрыто")
            except Exception as e:
                print(f"❌ Ошибка при закрытии соединения: {e}")
    
    def is_connected(self) -> bool:
        """
        Проверка состояния соединения
        
        Returns:
            bool: True если соединение активно
        """
        return self.connected and self.socket is not None
    
    def test_connection(self) -> bool:
        """
        Тестирование доступности майнера
        
        Returns:
            bool: True если майнер доступен
        """
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(5)
            result = test_socket.connect_ex((self.ip_address, self.port))
            test_socket.close()
            
            if result == 0:
                print(f"✅ Майнер {self.ip_address}:{self.port} доступен")
                return True
            else:
                print(f"❌ Майнер {self.ip_address}:{self.port} недоступен")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка тестирования соединения: {e}")
            return False 