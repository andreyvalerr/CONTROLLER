#!/usr/bin/env python3
"""
Главный GUI интерфейс для сенсорного дисплея
Современный интерфейс управления системой контроля температуры
"""

import os
import sys
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.slider import Slider
from kivy.uix.switch import Switch
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.metrics import dp

# Добавляем путь к модулю data_manager
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Импорты из data_manager вместо core
from data_manager.core_system import (
    SystemData, 
    set_temperature_settings, 
    get_temperature_settings, 
    is_temperature_settings_available, 
    get_temperature_data,
    get_core_instance,
    start_core_system,
    is_core_system_running
)

class TemperatureCard(BoxLayout):
    """Карточка отображения температуры"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = dp(30)
        self.padding = dp(30)
        
        # Фон карточки на всё окно
        with self.canvas.before:
            Color(0.2, 0.2, 0.2, 1)  # Темно-серый фон
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(25)])
        
        self.bind(size=self._update_rect, pos=self._update_rect)
        
        # Отступ сверху для лого (еще меньше)
        top_spacer = Label(
            text='',
            size_hint_y=None,
            height=dp(100)  # Еще меньший отступ для поднятия температуры
        )
        self.add_widget(top_spacer)
        
        # Текущая температура (очень большой размер шрифта)
        self.temp_label = Label(
            text='--°C',
            font_size=dp(120),  # Увеличен размер шрифта
            color=(0.3, 0.8, 1, 1),  # Голубой цвет
            size_hint_y=0.6,
            bold=True,
            font_name='DejaVuSans'  # Более округлый шрифт
        )
        self.add_widget(self.temp_label)
        
        # Целевая температура
        self.range_label = Label(
            text='Целевая температура: --°C - --°C',
            font_size=dp(24),  # Увеличен размер шрифта
            color=(0.8, 0.8, 0.8, 1),
            size_hint_y=0.4,
            font_name='DejaVuSans'  # Более округлый шрифт
        )
        self.add_widget(self.range_label)
    
    def _update_rect(self, instance, value):
        """Обновление размера фона"""
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def update_data(self, current_temp):
        """Обновление данных температуры"""
        # Получение настроек температуры
        temp_settings = get_temperature_settings()
        
        # Обновление текущей температуры
        if current_temp is not None:
            self.temp_label.text = f'{current_temp:.1f}°C'
            
            # Определение цвета в зависимости от диапазона
            if temp_settings:
                min_temp = temp_settings.get('min_temperature', 45.0)
                max_temp = temp_settings.get('max_temperature', 55.0)
                
                if current_temp > max_temp:
                    self.temp_label.color = (1, 0.4, 0.4, 1)  # Красный - выше максимума
                elif current_temp < min_temp:
                    self.temp_label.color = (0.4, 0.8, 1, 1)  # Голубой - ниже минимума
                else:
                    self.temp_label.color = (0.4, 1, 0.4, 1)  # Зеленый - в диапазоне
            else:
                self.temp_label.color = (0.8, 0.8, 0.8, 1)  # Серый - нет настроек
        else:
            self.temp_label.text = '--°C'
            self.temp_label.color = (0.6, 0.6, 0.6, 1)
        
        # Обновление целевой температуры
        if temp_settings:
            min_temp = temp_settings.get('min_temperature', 45.0)
            max_temp = temp_settings.get('max_temperature', 55.0)
            self.range_label.text = f'Целевая температура: {min_temp:.1f}°C - {max_temp:.1f}°C'
        else:
            self.range_label.text = 'Целевая температура: не настроена'

class GearIcon(Button):
    """Кликабельная иконка шестеренки"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(60), dp(60))  # Немного увеличил размер
        self.background_color = (0, 0, 0, 0)  # Прозрачный фон
        self.background_normal = ''
        
        # Привязываем обновление графики к изменениям размера и позиции
        self.bind(size=self._update_graphics, pos=self._update_graphics)
        self._update_graphics()
    
    def _update_graphics(self, *args):
        """Обновление графики шестеренки"""
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)  # Белый цвет
            # Внешний круг шестеренки
            outer_size = (dp(45), dp(45))
            outer_pos = (self.pos[0] + dp(7.5), self.pos[1] + dp(7.5))
            self.outer_circle = Ellipse(pos=outer_pos, size=outer_size)
            
            # Внутренний круг
            inner_size = (dp(25), dp(25))
            inner_pos = (self.pos[0] + dp(17.5), self.pos[1] + dp(17.5))
            Color(0.1, 0.1, 0.1, 1)  # Цвет фона
            self.inner_circle = Ellipse(pos=inner_pos, size=inner_size)
            
            # Зубчики шестеренки
            Color(1, 1, 1, 1)
            center_x = self.pos[0] + dp(30)
            center_y = self.pos[1] + dp(30)
            
            # 8 зубцов вокруг центра
            import math
            for i in range(8):
                angle = i * math.pi / 4
                x1 = center_x + dp(17) * math.cos(angle)
                y1 = center_y + dp(17) * math.sin(angle)
                x2 = center_x + dp(22) * math.cos(angle)
                y2 = center_y + dp(22) * math.sin(angle)
                Line(points=[x1, y1, x2, y2], width=3)

class SettingsPage(Popup):
    """Страница настроек"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.title = 'Настройки системы'
        self.size_hint = (0.95, 0.95)
        self.auto_dismiss = False
        
        # Получение текущих настроек температуры
        temp_settings = get_temperature_settings()
        if temp_settings:
            self.min_temp = temp_settings.get('min_temperature', 45.0)
            self.max_temp = temp_settings.get('max_temperature', 55.0)
        else:
            self.min_temp = 45.0
            self.max_temp = 55.0
        
        # Основной контейнер со скроллингом
        scroll = ScrollView()
        main_layout = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(20), size_hint_y=None)
        main_layout.bind(minimum_height=main_layout.setter('height'))
        
        # Секция температурных настроек
        temp_section = self._create_temperature_section()
        main_layout.add_widget(temp_section)
        
        # Секция метода получения температуры (заглушка)
        method_section = self._create_method_section()
        main_layout.add_widget(method_section)
        
        # Секция IP адреса асика (заглушка)
        ip_section = self._create_ip_section()
        main_layout.add_widget(ip_section)
        
        # Секция темы (заглушка)
        theme_section = self._create_theme_section()
        main_layout.add_widget(theme_section)
        
        # Секция полноэкранного режима (заглушка)
        fullscreen_section = self._create_fullscreen_section()
        main_layout.add_widget(fullscreen_section)
        
        # Кнопки управления
        button_layout = BoxLayout(orientation='horizontal', spacing=dp(20), size_hint_y=None, height=dp(50))
        
        close_btn = Button(
            text='Закрыть',
            size_hint_x=0.5,
            background_color=(0.6, 0.6, 0.6, 1)
        )
        close_btn.bind(on_press=self.dismiss)
        
        save_btn = Button(
            text='Сохранить',
            size_hint_x=0.5,
            background_color=(0.3, 0.8, 1, 1)
        )
        save_btn.bind(on_press=self.save_settings)
        
        button_layout.add_widget(close_btn)
        button_layout.add_widget(save_btn)
        main_layout.add_widget(button_layout)
        
        scroll.add_widget(main_layout)
        self.content = scroll
    
    def _create_section_header(self, title):
        """Создание заголовка секции"""
        header = Label(
            text=title,
            font_size=dp(20),
            size_hint_y=None,
            height=dp(40),
            color=(0.3, 0.8, 1, 1),
            bold=True,
            halign='left'
        )
        header.bind(size=header.setter('text_size'))
        return header
    
    def _create_temperature_section(self):
        """Создание секции температурных настроек"""
        section = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(300))
        
        # Заголовок секции
        section.add_widget(self._create_section_header('Температурные пороги'))
        
        # Верхний порог температуры
        max_layout = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_y=None, height=dp(120))
        
        max_title = Label(
            text='Верхний порог температуры',
            font_size=dp(16),
            size_hint_y=None,
            height=dp(30),
            color=(1, 0.6, 0.4, 1)
        )
        max_layout.add_widget(max_title)
        
        self.max_slider = Slider(
            min=35.0,
            max=70.0,
            value=self.max_temp,
            step=0.1,
            size_hint_y=None,
            height=dp(40)
        )
        
        self.max_value_label = Label(
            text=f'{self.max_temp:.1f}°C',
            font_size=dp(18),
            size_hint_y=None,
            height=dp(30),
            color=(1, 0.6, 0.4, 1),
            bold=True
        )
        
        self.max_slider.bind(value=self.on_max_slider_value)
        
        max_layout.add_widget(self.max_slider)
        max_layout.add_widget(self.max_value_label)
        section.add_widget(max_layout)
        
        # Нижний порог температуры
        min_layout = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_y=None, height=dp(120))
        
        min_title = Label(
            text='Нижний порог температуры',
            font_size=dp(16),
            size_hint_y=None,
            height=dp(30),
            color=(0.4, 0.8, 1, 1)
        )
        min_layout.add_widget(min_title)
        
        self.min_slider = Slider(
            min=20.0,
            max=60.0,
            value=self.min_temp,
            step=0.1,
            size_hint_y=None,
            height=dp(40)
        )
        
        self.min_value_label = Label(
            text=f'{self.min_temp:.1f}°C',
            font_size=dp(18),
            size_hint_y=None,
            height=dp(30),
            color=(0.4, 0.8, 1, 1),
            bold=True
        )
        
        self.min_slider.bind(value=self.on_min_slider_value)
        
        min_layout.add_widget(self.min_slider)
        min_layout.add_widget(self.min_value_label)
        section.add_widget(min_layout)
        
        # Сообщение о валидации
        self.temp_error_label = Label(
            text='',
            font_size=dp(14),
            size_hint_y=None,
            height=dp(30),
            color=(1, 0.3, 0.3, 1)
        )
        section.add_widget(self.temp_error_label)
        
        self.validate_temperature_settings()
        
        return section
    
    def _create_method_section(self):
        """Создание секции метода получения температуры (заглушка)"""
        section = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(100))
        
        section.add_widget(self._create_section_header('Метод получения температуры'))
        
        method_spinner = Spinner(
            text='DS18B20 (по умолчанию)',
            values=['DS18B20 (по умолчанию)', 'Термопара K-типа', 'Цифровой датчик'],
            size_hint_y=None,
            height=dp(40),
            background_color=(0.3, 0.3, 0.3, 1)
        )
        
        section.add_widget(method_spinner)
        
        return section
    
    def _create_ip_section(self):
        """Создание секции IP адреса асика (заглушка)"""
        section = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(100))
        
        section.add_widget(self._create_section_header('IP адрес ASIC устройства'))
        
        ip_input = TextInput(
            text='192.168.1.100',
            multiline=False,
            size_hint_y=None,
            height=dp(40),
            background_color=(0.3, 0.3, 0.3, 1),
            foreground_color=(1, 1, 1, 1)
        )
        
        section.add_widget(ip_input)
        
        return section
    
    def _create_theme_section(self):
        """Создание секции темы (заглушка)"""
        section = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(100))
        
        section.add_widget(self._create_section_header('Тема интерфейса'))
        
        theme_spinner = Spinner(
            text='Темная (по умолчанию)',
            values=['Темная (по умолчанию)', 'Светлая', 'Синяя', 'Зеленая'],
            size_hint_y=None,
            height=dp(40),
            background_color=(0.3, 0.3, 0.3, 1)
        )
        
        section.add_widget(theme_spinner)
        
        return section
    
    def _create_fullscreen_section(self):
        """Создание секции полноэкранного режима (заглушка)"""
        section = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(80))
        
        label = Label(
            text='Полноэкранный режим',
            font_size=dp(18),
            color=(1, 1, 1, 1),
            size_hint_x=0.7
        )
        
        fullscreen_switch = Switch(
            active=False,
            size_hint_x=0.3
        )
        
        section.add_widget(label)
        section.add_widget(fullscreen_switch)
        
        return section
    
    def on_min_slider_value(self, instance, value):
        """Обновление значения минимальной температуры"""
        self.min_temp = value
        self.min_value_label.text = f'{value:.1f}°C'
        self.validate_temperature_settings()
    
    def on_max_slider_value(self, instance, value):
        """Обновление значения максимальной температуры"""
        self.max_temp = value
        self.max_value_label.text = f'{value:.1f}°C'
        self.validate_temperature_settings()
    
    def validate_temperature_settings(self):
        """Валидация настроек температуры"""
        if self.min_temp >= self.max_temp:
            self.temp_error_label.text = 'Нижний порог должен быть меньше верхнего!'
            self.temp_error_label.color = (1, 0.3, 0.3, 1)
        else:
            difference = self.max_temp - self.min_temp
            self.temp_error_label.text = f'Диапазон: {difference:.1f}°C'
            self.temp_error_label.color = (0.4, 1, 0.4, 1)
    
    def save_settings(self, instance):
        """Сохранение настроек"""
        # Сохраняем только температурные настройки (остальные - заглушки)
        if self.min_temp < self.max_temp:
            success = set_temperature_settings(
                max_temp=self.max_temp,
                min_temp=self.min_temp,
                source_module="gui_interface"
            )
            
            if success:
                print(f"Температурные настройки сохранены: {self.min_temp:.1f}°C - {self.max_temp:.1f}°C")
            else:
                print("Ошибка при сохранении температурных настроек")
        
        print("Остальные настройки пока недоступны (заглушки)")
        self.dismiss()

class TemperatureControllerGUI(App):
    """Главное приложение GUI"""
    
    def build(self):
        """Построение интерфейса"""
        # Настройка окна для полноэкранного режима
        Window.fullscreen = False  # Можно изменить на True для реального использования
        Window.size = (800, 480)  # Типичный размер для 7" дисплея
        
        # Основной контейнер с наложением (FloatLayout для размещения элементов)
        root_layout = FloatLayout()
        
        # Карточка температуры на весь экран
        self.temp_card = TemperatureCard(
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        root_layout.add_widget(self.temp_card)
        
        # Лого в верхней части экрана по центру
        logo_path = '/home/user/CONTROLLER/gui_interface/images/Transparent Logo.png'
        self.logo = Image(
            source=logo_path,
            size_hint=(None, None),
            size=(dp(400), dp(240)),  # Фиксированный размер
            pos_hint={'center_x': 0.5, 'top': 1.1},  # Еще выше
            allow_stretch=True,
            keep_ratio=True
        )
        root_layout.add_widget(self.logo)
        
        # Шестеренка в правом верхнем углу
        self.gear_icon = GearIcon(
            pos_hint={'right': 0.95, 'top': 0.95}
        )
        self.gear_icon.bind(on_press=self.open_settings_page)
        root_layout.add_widget(self.gear_icon)
        
        # НЕ запускаем core system из GUI - он должен быть уже запущен из start_all_modules.py
        # Проверяем только что система доступна
        if not is_core_system_running():
            print("⚠️ ПРЕДУПРЕЖДЕНИЕ: Core system не запущен!")
            print("   GUI запущен изолированно. Запустите систему через start_all_modules.py")
        
        # Получение данных из core_system вместо отдельного вызова
        core_instance = get_core_instance()
        if core_instance:
            system_data = core_instance.get_system_data()
        else:
            # Создаем данные по умолчанию если core system недоступен
            current_temp = get_temperature_data()
            system_data = SystemData(
                temperature=current_temp,
                system_status="unknown" if current_temp is None else "running",
                last_update=datetime.now() if current_temp is not None else None
            )
        
        # Обновление карточки температуры
        self.temp_card.update_data(system_data.temperature)
        
        # Запуск таймера обновления
        Clock.schedule_interval(self.update_interface, 1.0)
        
        # Установка темного фона
        with root_layout.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            self.bg_rect = Rectangle(size=Window.size, pos=(0, 0))
        
        return root_layout
    
    def update_interface(self, dt):
        """Обновление интерфейса"""
        try:
            # Получение системных данных через core instance
            core_instance = get_core_instance()
            if core_instance:
                system_data = core_instance.get_system_data()
            else:
                # Fallback если core system недоступен
                current_temp = get_temperature_data()
                system_data = SystemData(
                    temperature=current_temp,
                    system_status="unknown" if current_temp is None else "running",
                    last_update=datetime.now() if current_temp is not None else None
                )
            
            # Обновление карточки температуры
            self.temp_card.update_data(system_data.temperature)
            
        except Exception as e:
            print(f"Ошибка обновления интерфейса: {e}")
    
    def open_settings_page(self, instance=None):
        """Открытие страницы настроек"""
        popup = SettingsPage()
        popup.open()

def main():
    """Запуск GUI приложения"""
    try:
        app = TemperatureControllerGUI()
        app.run()
    except Exception as e:
        print(f"Ошибка запуска GUI: {e}")

if __name__ == '__main__':
    main() 