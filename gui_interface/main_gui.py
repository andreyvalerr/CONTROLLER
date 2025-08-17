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
    is_core_system_running,
    set_asic_ip,
    get_asic_ip
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

class CoolingButton(Button):
    """Большая кнопка 'ОХЛАЖДЕНИЕ' с кастомным стилем (красная, скруглённая, с обводкой)."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = 'ОХЛАЖДЕНИЕ'
        self.bold = True
        self.font_size = dp(28)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.color = (0, 0, 0, 1)  # чёрный текст
        self._radius = dp(20)
        # По умолчанию считаем, что охлаждение выключено (красный)
        self._fill_color = (0.95, 0.25, 0.25, 1)
        self._border_color = (0, 0, 0, 1)
        self._border_width = 3
        self.bind(size=self._update_canvas, pos=self._update_canvas)
        self._update_canvas()
    
    def _update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._fill_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self._radius])
        self.canvas.after.clear()
        with self.canvas.after:
            Color(*self._border_color)
            Line(rounded_rectangle=[self.x, self.y, self.width, self.height, self._radius], width=self._border_width)

    def set_cooling_state(self, is_on: bool):
        """Обновляет визуальный цвет: красный = выкл, зелёный = вкл."""
        # Зелёный для включенного охлаждения, красный — выключено
        self._fill_color = (0.30, 0.80, 0.30, 1) if is_on else (0.95, 0.25, 0.25, 1)
        self._update_canvas()

class NumericKeyboard(Popup):
    """Виртуальная клавиатура для ввода IP адреса"""
    
    def __init__(self, target_input, **kwargs):
        super().__init__(**kwargs)
        self.target_input = target_input
        self.title = 'Ввод IP адреса'
        self.size_hint = (0.85, 0.75)  # Уменьшаем размер для размещения на экране
        self.auto_dismiss = False
        
        # Основной контейнер
        main_layout = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(10))
        
        # Поле отображения вводимого текста
        self.display_input = TextInput(
            text=target_input.text,
            multiline=False,
            readonly=True,
            size_hint_y=None,
            height=dp(50),
            font_size=dp(24),
            background_color=(0.2, 0.2, 0.2, 1),
            foreground_color=(1, 1, 1, 1),
            halign='center'
        )
        main_layout.add_widget(self.display_input)
        
        # Клавиатура с цифрами (4 ряда по 3 кнопки)
        keyboard_layout = GridLayout(cols=3, spacing=dp(8), size_hint_y=None)
        keyboard_layout.bind(minimum_height=keyboard_layout.setter('height'))
        
        # Цифры 1-9
        for i in range(1, 10):
            btn = Button(
                text=str(i),
                font_size=dp(28),
                size_hint_y=None,
                height=dp(60),
                background_color=(0.4, 0.4, 0.4, 1)
            )
            btn.bind(on_press=lambda x, num=str(i): self.add_character(num))
            keyboard_layout.add_widget(btn)
        
        # Нижний ряд: точка, 0, backspace
        dot_btn = Button(
            text='.',
            font_size=dp(28),
            size_hint_y=None,
            height=dp(60),
            background_color=(0.4, 0.4, 0.4, 1)
        )
        dot_btn.bind(on_press=lambda x: self.add_character('.'))
        keyboard_layout.add_widget(dot_btn)
        
        zero_btn = Button(
            text='0',
            font_size=dp(28),
            size_hint_y=None,
            height=dp(60),
            background_color=(0.4, 0.4, 0.4, 1)
        )
        zero_btn.bind(on_press=lambda x: self.add_character('0'))
        keyboard_layout.add_widget(zero_btn)
        
        backspace_btn = Button(
            text='⌫',
            font_size=dp(28),
            size_hint_y=None,
            height=dp(60),
            background_color=(0.8, 0.4, 0.4, 1)
        )
        backspace_btn.bind(on_press=lambda x: self.backspace())
        keyboard_layout.add_widget(backspace_btn)
        
        main_layout.add_widget(keyboard_layout)
        
        # Кнопки управления (отдельно от цифровой клавиатуры)
        button_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(50))
        
        clear_btn = Button(
            text='Очистить',
            font_size=dp(16),
            background_color=(0.8, 0.6, 0.4, 1)
        )
        clear_btn.bind(on_press=lambda x: self.clear_input())
        
        cancel_btn = Button(
            text='Отмена',
            font_size=dp(16),
            background_color=(0.6, 0.6, 0.6, 1)
        )
        cancel_btn.bind(on_press=lambda x: self.dismiss())
        
        ok_btn = Button(
            text='ОК',
            font_size=dp(16),
            background_color=(0.3, 0.8, 1, 1)
        )
        ok_btn.bind(on_press=lambda x: self.confirm_input())
        
        button_layout.add_widget(clear_btn)
        button_layout.add_widget(cancel_btn)
        button_layout.add_widget(ok_btn)
        main_layout.add_widget(button_layout)
        
        self.content = main_layout
    
    def add_character(self, char):
        """Добавление символа к вводу"""
        current_text = self.display_input.text
        # Проверяем валидность для IP адреса
        new_text = current_text + char
        if self.is_valid_ip_partial(new_text):
            self.display_input.text = new_text
    
    def backspace(self):
        """Удаление последнего символа"""
        current_text = self.display_input.text
        if len(current_text) > 0:
            self.display_input.text = current_text[:-1]
    
    def clear_input(self):
        """Очистка поля ввода"""
        self.display_input.text = ''
    
    def confirm_input(self):
        """Подтверждение ввода"""
        ip_text = self.display_input.text
        if self.is_valid_ip(ip_text):
            self.target_input.text = ip_text
            self.dismiss()
        else:
            # Показываем ошибку
            error_popup = Popup(
                title='Ошибка',
                content=Label(text='Неверный формат IP адреса\nПример: 192.168.1.100'),
                size_hint=(0.6, 0.4),
                auto_dismiss=True
            )
            error_popup.open()
    
    def is_valid_ip_partial(self, text):
        """Проверка частично введенного IP адреса"""
        if len(text) > 15:  # Максимальная длина IP
            return False
        
        # Разрешаем только цифры и точки
        allowed_chars = set('0123456789.')
        if not all(c in allowed_chars for c in text):
            return False
        
        # Не более 3 точек
        if text.count('.') > 3:
            return False
        
        # Проверяем каждую часть
        parts = text.split('.')
        if len(parts) > 4:
            return False
        
        for part in parts:
            if part == '':
                continue  # Разрешаем пустые части во время ввода
            if len(part) > 3:
                return False
            if not part.isdigit():
                return False
            if int(part) > 255:
                return False
        
        return True
    
    def is_valid_ip(self, text):
        """Проверка полного IP адреса"""
        parts = text.split('.')
        if len(parts) != 4:
            return False
        
        for part in parts:
            if not part.isdigit():
                return False
            if int(part) > 255:
                return False
        
        return True

class SettingsPage(Popup):
    """Страница настроек"""
    
    # Переменные класса для сохранения между сессиями
    saved_asic_ip = '192.168.1.100'
    saved_temperature_method = 'Температура жидкости с ASIC'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.title = 'Настройки системы'
        self.size_hint = (0.95, 0.95)
        self.auto_dismiss = False
        
        # Переменные для повторяющегося изменения
        self.repeat_event = None
        self.repeat_temp_type = None
        self.repeat_change = None
        
        # Инициализация метода получения температуры из сохраненного значения
        self.temperature_method = SettingsPage.saved_temperature_method
        
        # Инициализация IP адреса ASIC: пробуем взять из data_manager или из файла настроек
        loaded_ip = None
        try:
            loaded_ip = get_asic_ip()
        except Exception:
            loaded_ip = None
        if not loaded_ip:
            try:
                from data_manager.settings_manager import get_settings_manager
                sm = get_settings_manager()
                loaded_ip = sm.load_ip_address()
            except Exception:
                loaded_ip = None
        if isinstance(loaded_ip, str) and loaded_ip:
            self.asic_ip = loaded_ip
            SettingsPage.saved_asic_ip = loaded_ip
        else:
            self.asic_ip = SettingsPage.saved_asic_ip
        
        # Получение текущих настроек температуры
        temp_settings = get_temperature_settings()
        if temp_settings:
            self.min_temp = temp_settings.get('min_temperature', 45.0)
            self.max_temp = temp_settings.get('max_temperature', 55.0)
        else:
            self.min_temp = 45.0
            self.max_temp = 55.0

        # Инициализация режима работы (Авто/Ручной) из файла настроек
        try:
            from data_manager.settings_manager import get_settings_manager
            sm = get_settings_manager()
            mode_value = sm.load_mode()  # 'auto' | 'manual' | None
        except Exception:
            mode_value = None
        if isinstance(mode_value, str) and mode_value.lower() == 'manual':
            self.mode_display = 'Ручной'
        else:
            # по умолчанию Авто
            self.mode_display = 'Авто'
        
        # Основной контейнер со скроллингом
        scroll = ScrollView()
        main_layout = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(20), size_hint_y=None)
        main_layout.bind(minimum_height=main_layout.setter('height'))
        
        # Секция температурных настроек
        temp_section = self._create_temperature_section()
        main_layout.add_widget(temp_section)
        
        # Секция метода получения температуры
        method_section = self._create_method_section()
        main_layout.add_widget(method_section)

        # Секция режима работы
        mode_section = self._create_mode_section()
        main_layout.add_widget(mode_section)
        
        # Секция IP адреса асика
        ip_section = self._create_ip_section()
        main_layout.add_widget(ip_section)
        
        # Секция полноэкранного режима
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
        
        # Контейнер для кнопок и значения верхнего порога
        max_control_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(40))
        
        max_minus_btn = Button(
            text='-',
            size_hint_x=None,
            width=dp(50),
            font_size=dp(24),
            background_color=(0.8, 0.3, 0.3, 1)
        )
        max_minus_btn.bind(on_press=lambda x: self.start_repeat_change('max', -0.1))
        max_minus_btn.bind(on_release=lambda x: self.stop_repeat_change())
        
        self.max_value_label = Label(
            text=f'{self.max_temp:.1f}°C',
            font_size=dp(18),
            color=(1, 0.6, 0.4, 1),
            bold=True
        )
        
        max_plus_btn = Button(
            text='+',
            size_hint_x=None,
            width=dp(50),
            font_size=dp(24),
            background_color=(0.3, 0.8, 0.3, 1)
        )
        max_plus_btn.bind(on_press=lambda x: self.start_repeat_change('max', 0.1))
        max_plus_btn.bind(on_release=lambda x: self.stop_repeat_change())
        
        max_control_layout.add_widget(max_minus_btn)
        max_control_layout.add_widget(self.max_value_label)
        max_control_layout.add_widget(max_plus_btn)
        
        max_layout.add_widget(max_control_layout)
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
        
        # Контейнер для кнопок и значения нижнего порога
        min_control_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(40))
        
        min_minus_btn = Button(
            text='-',
            size_hint_x=None,
            width=dp(50),
            font_size=dp(24),
            background_color=(0.8, 0.3, 0.3, 1)
        )
        min_minus_btn.bind(on_press=lambda x: self.start_repeat_change('min', -0.1))
        min_minus_btn.bind(on_release=lambda x: self.stop_repeat_change())
        
        self.min_value_label = Label(
            text=f'{self.min_temp:.1f}°C',
            font_size=dp(18),
            color=(0.4, 0.8, 1, 1),
            bold=True
        )
        
        min_plus_btn = Button(
            text='+',
            size_hint_x=None,
            width=dp(50),
            font_size=dp(24),
            background_color=(0.3, 0.8, 0.3, 1)
        )
        min_plus_btn.bind(on_press=lambda x: self.start_repeat_change('min', 0.1))
        min_plus_btn.bind(on_release=lambda x: self.stop_repeat_change())
        
        min_control_layout.add_widget(min_minus_btn)
        min_control_layout.add_widget(self.min_value_label)
        min_control_layout.add_widget(min_plus_btn)
        
        min_layout.add_widget(min_control_layout)
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
        """Создание секции метода получения температуры"""
        section = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(100))
        
        section.add_widget(self._create_section_header('Метод получения температуры'))
        
        self.method_spinner = Spinner(
            text=self.temperature_method,  # Используем сохраненное значение
            values=['Температура жидкости с ASIC', 'Внешний датчик температуры'],
            size_hint_y=None,
            height=dp(40),
            background_color=(0.3, 0.3, 0.3, 1)
        )
        # Привязываем обработчик изменения метода
        self.method_spinner.bind(text=self.on_method_change)
        
        section.add_widget(self.method_spinner)
        
        return section

    def _create_mode_section(self):
        """Создание секции выбора режима работы"""
        section = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(100))
        
        section.add_widget(self._create_section_header('Режим'))
        
        self.mode_spinner = Spinner(
            text=self.mode_display,
            values=['Авто', 'Ручной'],
            size_hint_y=None,
            height=dp(40),
            background_color=(0.3, 0.3, 0.3, 1)
        )
        section.add_widget(self.mode_spinner)
        
        return section
    
    def _create_ip_section(self):
        """Создание секции IP адреса асика"""
        section = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(100))
        
        section.add_widget(self._create_section_header('IP адрес ASIC устройства'))
        
        self.ip_input = TextInput(
            text=self.asic_ip,
            multiline=False,
            size_hint_y=None,
            height=dp(40),
            background_color=(0.3, 0.3, 0.3, 1),
            foreground_color=(1, 1, 1, 1),
            readonly=True,  # Делаем поле только для чтения
            font_size=dp(16)
        )
        # Привязываем открытие виртуальной клавиатуры при нажатии
        self.ip_input.bind(on_touch_down=self.on_ip_input_touch)
        
        section.add_widget(self.ip_input)
        
        return section
    
    def _create_fullscreen_section(self):
        """Создание секции полноэкранного режима"""
        section = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(120))
        
        # Заголовок секции
        section.add_widget(self._create_section_header('Полноэкранный режим'))
        
        # Контейнер для переключателя
        switch_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(50))
        
        label = Label(
            text='Полноэкранный режим',
            font_size=dp(16),
            color=(1, 1, 1, 1),
            size_hint_x=0.7
        )
        
        # Получаем текущее состояние полноэкранного режима
        # Обрабатываем различные возможные значения Window.fullscreen
        current_fullscreen = Window.fullscreen
        if isinstance(current_fullscreen, str):
            # Если fullscreen установлен как строка ('auto', 'fake', и т.д.), считаем это как True
            switch_active = True
        elif isinstance(current_fullscreen, bool):
            switch_active = current_fullscreen
        else:
            # Для любых других значений по умолчанию False
            switch_active = False
        
        self.fullscreen_switch = Switch(
            active=switch_active,
            size_hint_x=0.3
        )
        # Привязываем переключатель к методу обработки
        self.fullscreen_switch.bind(active=self.on_fullscreen_toggle)
        
        switch_layout.add_widget(label)
        switch_layout.add_widget(self.fullscreen_switch)
        section.add_widget(switch_layout)
        
        return section
    
    def on_min_button_change(self, change):
        """Изменение значения минимальной температуры кнопками"""
        new_value = self.min_temp + change
        # Ограничиваем диапазон от 0 до 100 градусов
        if new_value >= 0.0 and new_value <= 100.0:
            self.min_temp = round(new_value, 1)
            self.min_value_label.text = f'{self.min_temp:.1f}°C'
            self.validate_temperature_settings()
    
    def on_max_button_change(self, change):
        """Изменение значения максимальной температуры кнопками"""
        new_value = self.max_temp + change
        # Ограничиваем диапазон от 0 до 100 градусов
        if new_value >= 0.0 and new_value <= 100.0:
            self.max_temp = round(new_value, 1)
            self.max_value_label.text = f'{self.max_temp:.1f}°C'
            self.validate_temperature_settings()
    
    def on_min_slider_value(self, instance, value):
        """Обновление значения минимальной температуры (заглушка для совместимости)"""
        pass
    
    def on_max_slider_value(self, instance, value):
        """Обновление значения максимальной температуры (заглушка для совместимости)"""
        pass
    
    def start_repeat_change(self, temp_type, change):
        """Начало повторяющегося изменения температуры при зажатии кнопки"""
        # Сразу делаем первое изменение
        if temp_type == 'min':
            self.on_min_button_change(change)
        else:
            self.on_max_button_change(change)
        
        # Сохраняем параметры для повторения
        self.repeat_temp_type = temp_type
        self.repeat_change = change
        
        # Запускаем таймер повторения с интервалом 0.1 секунды
        self.repeat_event = Clock.schedule_interval(self.repeat_temperature_change, 0.1)
    
    def stop_repeat_change(self):
        """Остановка повторяющегося изменения при отпускании кнопки"""
        if self.repeat_event:
            self.repeat_event.cancel()
            self.repeat_event = None
            self.repeat_temp_type = None
            self.repeat_change = None
    
    def repeat_temperature_change(self, dt):
        """Повторяющееся изменение температуры"""
        if self.repeat_temp_type == 'min':
            self.on_min_button_change(self.repeat_change)
        elif self.repeat_temp_type == 'max':
            self.on_max_button_change(self.repeat_change)
        return True
    
    def validate_temperature_settings(self):
        """Валидация настроек температуры"""
        if self.min_temp >= self.max_temp:
            self.temp_error_label.text = 'Нижний порог должен быть меньше верхнего!'
            self.temp_error_label.color = (1, 0.3, 0.3, 1)
        else:
            difference = self.max_temp - self.min_temp
            self.temp_error_label.text = f'Диапазон: {difference:.1f}°C'
            self.temp_error_label.color = (0.4, 1, 0.4, 1)
    
    def on_method_change(self, instance, text):
        """Обработка изменения метода получения температуры"""
        self.temperature_method = text
        print(f"Выбран метод получения температуры: {text}")
        
        # Можно добавить дополнительную логику в зависимости от метода
        if text == 'Температура жидкости с ASIC':
            print("Будет использоваться температура с ASIC")
        elif text == 'Внешний датчик температуры':
            print("Будет использоваться внешний датчик температуры")

    def save_settings(self, instance):
        """Сохранение настроек"""
        # Сохраняем температурные настройки
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
        
        # Сохраняем метод получения температуры в переменную класса
        SettingsPage.saved_temperature_method = self.temperature_method
        print(f"Метод получения температуры сохранен: {self.temperature_method}")
        
        # Сохраняем IP адрес ASIC в переменную класса
        self.asic_ip = self.ip_input.text
        SettingsPage.saved_asic_ip = self.asic_ip
        print(f"IP адрес ASIC устройства сохранен: {self.asic_ip}")

        # Сохраняем режим работы в gui_settings.json
        try:
            from data_manager.settings_manager import get_settings_manager
            sm = get_settings_manager()
            selected_text = getattr(self, 'mode_spinner', None).text if hasattr(self, 'mode_spinner') else 'Авто'
            normalized = 'auto' if selected_text.strip().lower().startswith('авто') else 'manual'
            if sm.save_mode(normalized):
                print(f"Режим работы сохранен: {selected_text} ({normalized})")
                # Применяем режим к модулю valve_control немедленно
                try:
                    if normalized == 'manual':
                        from valve_control.data_manager_integration import set_manual_mode
                        if set_manual_mode():
                            print("valve_control переведён в ручной режим (охлаждение выключено)")
                        else:
                            print("Не удалось перевести valve_control в ручной режим")
                    else:
                        from valve_control.data_manager_integration import set_auto_mode
                        if set_auto_mode():
                            print("valve_control переведён в автоматический режим")
                        else:
                            print("Не удалось перевести valve_control в авто режим")
                except Exception as e:
                    print(f"Ошибка применения режима в valve_control: {e}")
                # Обновляем локально состояние режима в главном приложении и применяем видимость кнопки
                try:
                    app = App.get_running_app()
                    if app:
                        setattr(app, 'current_mode', normalized)
                        if hasattr(app, '_apply_mode_visibility'):
                            app._apply_mode_visibility()
                except Exception:
                    pass
            else:
                print("Не удалось сохранить режим работы")
        except Exception as e:
            print(f"Ошибка сохранения режима работы: {e}")

        # Немедленно передаем IP адрес ASIC в data_manager
        try:
            if set_asic_ip(self.asic_ip, source_module="gui_interface"):
                print(f"IP адрес ASIC передан в data_manager: {self.asic_ip}")
            else:
                print("Не удалось передать IP адрес ASIC в data_manager")
        except Exception as e:
            print(f"Ошибка передачи IP адреса ASIC в data_manager: {e}")
        
        print("Настройки сохранены успешно!")
        self.dismiss()

    def on_fullscreen_toggle(self, instance, value):
        """Обработка переключения полноэкранного режима"""
        try:
            if value:
                # Включаем полноэкранный режим (используем 'auto' для лучшей совместимости)
                Window.fullscreen = 'auto'
                print("Включен полноэкранный режим (auto)")
            else:
                # Выключаем полноэкранный режим
                Window.fullscreen = False
                print("Выключен полноэкранный режим")
        except Exception as e:
            print(f"Ошибка при переключении полноэкранного режима: {e}")
            # Возвращаем переключатель в исходное состояние при ошибке
            instance.active = not value

    def on_ip_input_touch(self, instance, touch):
        """Обработка нажатия на поле ввода IP"""
        if instance.collide_point(touch.x, touch.y):
            keyboard = NumericKeyboard(instance)
            keyboard.open()
            return True
        return False

class TemperatureControllerGUI(App):
    """Главное приложение GUI"""
    
    def build(self):
        """Построение интерфейса"""
        # Настройка окна для полноэкранного режима
        # Window.fullscreen = False  # ЗАКОММЕНТИРОВАНО: Эта строка принудительно отключала полноэкранный режим.
                                     # Теперь приложение будет использовать аргументы командной строки (--auto-fullscreen).
        Window.size = (800, 480)  # Типичный размер для 7" дисплея
        
        # Привязка обработки клавиш для переключения полноэкранного режима
        Window.bind(on_key_down=self.on_key_down)
        
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

        # Кнопка 'ОХЛАЖДЕНИЕ' (по умолчанию скрыта, показывается в ручном режиме)
        self.cooling_button = CoolingButton(
            size_hint=(None, None),
            size=(dp(240), dp(130)),
            pos_hint={'right': 0.88, 'center_y': 0.56}
        )
        self.cooling_button.bind(on_press=self.on_cooling_button_press)
        root_layout.add_widget(self.cooling_button)
        self.current_mode = self._get_current_mode()
        # Устанавливаем начальный цвет кнопки по фактическому состоянию охлаждения
        try:
            from valve_control.data_manager_integration import get_cooling_state
            current = get_cooling_state()
            if current is None:
                # Фолбэк к сохраненному состоянию в settings
                try:
                    from data_manager.settings_manager import get_settings_manager
                    sm = get_settings_manager()
                    saved = sm.load_cooling_state()
                    if isinstance(saved, bool):
                        self.cooling_button.set_cooling_state(saved)
                    else:
                        self.cooling_button.set_cooling_state(False)
                except Exception:
                    self.cooling_button.set_cooling_state(False)
            else:
                self.cooling_button.set_cooling_state(bool(current))
        except Exception:
            self.cooling_button.set_cooling_state(False)
        self._apply_mode_visibility()
        
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
        
        # Обновление карточки температуры (скрываем при ошибке/устаревших данных)
        display_temp = system_data.temperature
        try:
            hide_temp = False
            # Скрываем при статусе ошибки
            if system_data.temperature_status == "error":
                hide_temp = True
            # Скрываем при устаревших данных (>10 сек)
            elif system_data.last_update is None:
                hide_temp = True
            else:
                age_sec = (datetime.now() - system_data.last_update).total_seconds()
                if age_sec > 10:
                    hide_temp = True
            if hide_temp:
                display_temp = None
        except Exception:
            display_temp = None

        self.temp_card.update_data(display_temp)
        
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
            
            # Обновление карточки температуры (скрываем при ошибке/устаревших данных)
            display_temp = system_data.temperature
            try:
                hide_temp = False
                if system_data.temperature_status == "error":
                    hide_temp = True
                elif system_data.last_update is None:
                    hide_temp = True
                else:
                    age_sec = (datetime.now() - system_data.last_update).total_seconds()
                    if age_sec > 10:
                        hide_temp = True
                if hide_temp:
                    display_temp = None
            except Exception:
                display_temp = None

            self.temp_card.update_data(display_temp)
            
            # Проверяем изменения режима и обновляем видимость кнопки
            new_mode = self._get_current_mode()
            if new_mode != getattr(self, 'current_mode', None):
                self.current_mode = new_mode
                self._apply_mode_visibility()
            # В ручном режиме периодически подтягиваем состояние охлаждения
            if self.current_mode == 'manual':
                try:
                    from valve_control.data_manager_integration import get_cooling_state
                    current = get_cooling_state()
                    if current is not None:
                        self.cooling_button.set_cooling_state(bool(current))
                    else:
                        # Фолбэк к сохраненному состоянию
                        try:
                            from data_manager.settings_manager import get_settings_manager
                            sm = get_settings_manager()
                            saved = sm.load_cooling_state()
                            if isinstance(saved, bool):
                                self.cooling_button.set_cooling_state(saved)
                        except Exception:
                            pass
                except Exception:
                    pass
            
        except Exception as e:
            print(f"Ошибка обновления интерфейса: {e}")
    
    def open_settings_page(self, instance=None):
        """Открытие страницы настроек"""
        popup = SettingsPage()
        popup.open()

    def on_key_down(self, instance, keycode, *args):
        """Обработка нажатия клавиш"""
        # F11 для переключения полноэкранного режима
        if keycode[1] == 'f11':
            self.toggle_fullscreen()
            return True
        return False

    def toggle_fullscreen(self):
        """Переключение полноэкранного режима"""
        try:
            # Определяем текущее состояние
            current_fullscreen = Window.fullscreen
            is_fullscreen = current_fullscreen not in [False, 0]
            
            if is_fullscreen:
                # Выключаем полноэкранный режим
                Window.fullscreen = False
                print("Выключен полноэкранный режим (F11)")
            else:
                # Включаем полноэкранный режим
                Window.fullscreen = 'auto'
                print("Включен полноэкранный режим (F11)")
        except Exception as e:
            print(f"Ошибка при переключении полноэкранного режима: {e}")

    def _get_current_mode(self):
        """Чтение текущего режима из gui_settings.json (auto/manual)."""
        try:
            from data_manager.settings_manager import get_settings_manager
            sm = get_settings_manager()
            mode_value = sm.load_mode()
            if isinstance(mode_value, str) and mode_value.lower() in ('manual', 'auto'):
                return mode_value.lower()
        except Exception:
            pass
        return 'auto'

    def _apply_mode_visibility(self):
        """Показывает кнопку охлаждения только в ручном режиме."""
        try:
            is_manual = (self.current_mode == 'manual')
            if hasattr(self, 'cooling_button') and self.cooling_button is not None:
                self.cooling_button.opacity = 1.0 if is_manual else 0.0
                self.cooling_button.disabled = not is_manual
                # При появлении кнопки обновляем цвет по фактическому состоянию
                if is_manual:
                    try:
                        from valve_control.data_manager_integration import get_cooling_state
                        current = get_cooling_state()
                        if current is not None:
                            self.cooling_button.set_cooling_state(bool(current))
                        else:
                            # Фолбэк к сохраненному состоянию
                            try:
                                from data_manager.settings_manager import get_settings_manager
                                sm = get_settings_manager()
                                saved = sm.load_cooling_state()
                                if isinstance(saved, bool):
                                    self.cooling_button.set_cooling_state(saved)
                            except Exception:
                                pass
                    except Exception:
                        pass
        except Exception as e:
            print(f"Ошибка применения режима отображения кнопки: {e}")

    def on_cooling_button_press(self, instance):
        """Обработка нажатия на кнопку 'ОХЛАЖДЕНИЕ' — переключение охлаждения в valve_control."""
        try:
            if self.current_mode != 'manual':
                return
            from valve_control.data_manager_integration import toggle_manual_cooling
            if toggle_manual_cooling():
                # После удачного переключения узнаём актуальное состояние и меняем цвет
                try:
                    from valve_control.data_manager_integration import get_cooling_state
                    current = get_cooling_state()
                    if current is not None:
                        self.cooling_button.set_cooling_state(bool(current))
                        # Сохраняем состояние в gui_settings.json
                        try:
                            from data_manager.settings_manager import get_settings_manager
                            sm = get_settings_manager()
                            sm.save_cooling_state(bool(current))
                        except Exception as e:
                            print(f"Ошибка сохранения состояния охлаждения: {e}")
                except Exception:
                    pass
                print("Переключение охлаждения отправлено в valve_control")
            else:
                print("Не удалось переключить охлаждение (valve_control)")
        except Exception as e:
            print(f"Ошибка при переключении охлаждения: {e}")

def main():
    """Запуск GUI приложения"""
    try:
        app = TemperatureControllerGUI()
        app.run()
    except Exception as e:
        print(f"Ошибка запуска GUI: {e}")

if __name__ == '__main__':
    main() 