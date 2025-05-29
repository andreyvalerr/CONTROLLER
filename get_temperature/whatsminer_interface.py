#!/usr/bin/env python3
"""
Интерфейс для работы с API Whatsminer v3.0.1
Обеспечивает формирование команд и обработку ответов
"""

import json
import hashlib
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad


class WhatsminerAPIv3:
    """Класс для работы с API Whatsminer версии 3.0.1"""
    
    def __init__(self, account="super", password="super"):
        """
        Инициализация API клиента
        
        Args:
            account (str): Учетная запись (super/admin/user1)
            password (str): Пароль
        """
        self.account = account
        self.password = password
        self.salt = None
        self.aes_cipher = None
        
    def set_salt(self, salt):
        """
        Установка salt для шифрования команд
        
        Args:
            salt (str): Salt полученный от майнера
        """
        self.salt = salt
        
        # Создание ключа шифрования
        key_string = f"{self.account}{self.password}{salt}"
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        key = key_hash[:16].encode()
        
        # Инициализация AES шифрования
        self.aes_cipher = AES.new(key, AES.MODE_ECB)
        
    def get_request_cmds(self, command, param=None):
        """
        Формирование команды для отправки
        
        Args:
            command (str): Команда API (например, "get.device.info")
            param: Параметры команды (по умолчанию None)
            
        Returns:
            bytes: Сформированная команда для отправки
        """
        # Создание JSON команды
        cmd_data = {
            "cmd": command,
            "param": param
        }
        
        json_str = json.dumps(cmd_data, separators=(',', ':'))
        
        # Если salt установлен, шифруем команду
        if self.salt and self.aes_cipher:
            # Дополняем до кратности 16 байт
            padded_data = pad(json_str.encode(), 16)
            encrypted_data = self.aes_cipher.encrypt(padded_data)
            return encrypted_data
        else:
            # Первый запрос без шифрования
            return json_str.encode()
    
    def decrypt_response(self, encrypted_data):
        """
        Расшифровка ответа от майнера
        
        Args:
            encrypted_data (bytes): Зашифрованные данные
            
        Returns:
            dict: Расшифрованный JSON ответ
        """
        if self.aes_cipher:
            try:
                decrypted_data = self.aes_cipher.decrypt(encrypted_data)
                unpadded_data = unpad(decrypted_data, 16)
                json_str = unpadded_data.decode()
                return json.loads(json_str)
            except Exception as e:
                print(f"Ошибка расшифровки: {e}")
                return None
        else:
            # Если шифрование не настроено, пробуем как обычный JSON
            try:
                return json.loads(encrypted_data.decode())
            except:
                return None 