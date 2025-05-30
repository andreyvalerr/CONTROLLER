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
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp

# Добавляем путь к core модулю
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.shared_state import system_state
from core.data_models import SystemData

class TemperatureCard(BoxLayout):
    """Карточка отображения температуры"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = dp(10)
        self.padding = dp(15)
        
        # Фон карточки
        with self.canvas.before:
            Color(0.2, 0.2, 0.2, 1)  # Темно-серый фон
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(15)])
        
        self.bind(size=self._update_rect, pos=self._update_rect)
        
        # Заголовок
        self.title_label = Label(
            text='Температура охлаждающей жидкости',
            font_size=dp(18),
            color=(1, 1, 1, 1),
            size_hint_y=0.3
        )
        self.add_widget(self.title_label)
        
        # Текущая температура
        self.temp_label = Label(
            text='--°C',
            font_size=dp(48),
            color=(0.3, 0.8, 1, 1),  # Голубой цвет
            size_hint_y=0.5,
            bold=True
        )
        self.add_widget(self.temp_label)
        
        # Целевая температура
        self.target_label = Label(
            text='Целевая: --°C',
            font_size=dp(16),
            color=(0.8, 0.8, 0.8, 1),
            size_hint_y=0.2
        )
        self.add_widget(self.target_label)
    
    def _update_rect(self, instance, value):
        """Обновление размера фона"""
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def update_data(self, temp_data):
        """Обновление данных температуры"""
        self.temp_label.text = f'{temp_data.current_temp:.1f}°C'
        self.target_label.text = f'Целевая: {temp_data.target_temp:.1f}°C'
        
        # Изменение цвета в зависимости от температуры
        if temp_data.current_temp > temp_data.target_temp:
            self.temp_label.color = (1, 0.4, 0.4, 1)  # Красный
        elif temp_data.current_temp < temp_data.min_temp:
            self.temp_label.color = (0.4, 0.8, 1, 1)  # Голубой
        else:
            self.temp_label.color = (0.4, 1, 0.4, 1)  # Зеленый

class StatusCard(BoxLayout):
    """Карточка статуса системы"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = dp(10)
        self.padding = dp(15)
        
        # Фон карточки
        with self.canvas.before:
            Color(0.2, 0.2, 0.2, 1)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(15)])
        
        self.bind(size=self._update_rect, pos=self._update_rect)
        
        # Заголовок
        self.title_label = Label(
            text='Статус системы',
            font_size=dp(18),
            color=(1, 1, 1, 1),
            size_hint_y=0.25
        )
        self.add_widget(self.title_label)
        
        # Статус клапана
        self.valve_label = Label(
            text='Клапан: ЗАКРЫТ',
            font_size=dp(20),
            color=(1, 0.4, 0.4, 1),
            size_hint_y=0.35,
            bold=True
        )
        self.add_widget(self.valve_label)
        
        # Режим работы
        self.mode_label = Label(
            text='Режим: АВТО',
            font_size=dp(16),
            color=(0.8, 0.8, 0.8, 1),
            size_hint_y=0.25
        )
        self.add_widget(self.mode_label)
        
        # Время обновления
        self.update_label = Label(
            text='Обновлено: --:--',
            font_size=dp(14),
            color=(0.6, 0.6, 0.6, 1),
            size_hint_y=0.15
        )
        self.add_widget(self.update_label)
    
    def _update_rect(self, instance, value):
        """Обновление размера фона"""
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def update_data(self, status_data):
        """Обновление данных статуса"""
        # Статус клапана
        valve_text = 'ОТКРЫТ' if status_data.valve_state else 'ЗАКРЫТ'
        valve_color = (0.4, 1, 0.4, 1) if status_data.valve_state else (1, 0.4, 0.4, 1)
        self.valve_label.text = f'Клапан: {valve_text}'
        self.valve_label.color = valve_color
        
        # Режим работы
        mode_text = {
            'auto': 'АВТО',
            'manual': 'РУЧНОЙ',
            'emergency': 'АВАРИЙНЫЙ'
        }.get(status_data.system_mode, status_data.system_mode.upper())
        
        self.mode_label.text = f'Режим: {mode_text}'
        
        # Время обновления
        update_time = status_data.last_update.strftime('%H:%M:%S')
        self.update_label.text = f'Обновлено: {update_time}'

class ControlPanel(BoxLayout):
    """Панель управления"""
    
    def __init__(self, main_app, **kwargs):
        super().__init__(**kwargs)
        self.main_app = main_app
        self.orientation = 'vertical'
        self.spacing = dp(15)
        self.padding = dp(15)
        
        # Фон панели
        with self.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(15)])
        
        self.bind(size=self._update_rect, pos=self._update_rect)
        
        # Заголовок
        title = Label(
            text='Управление',
            font_size=dp(20),
            color=(1, 1, 1, 1),
            size_hint_y=0.2,
            bold=True
        )
        self.add_widget(title)
        
        # Кнопка настройки температуры
        temp_btn = Button(
            text='Настройка температуры',
            font_size=dp(16),
            size_hint_y=0.3,
            background_color=(0.3, 0.7, 1, 1)
        )
        temp_btn.bind(on_press=self.open_temperature_settings)
        self.add_widget(temp_btn)
        
        # Кнопка переключения режима
        self.mode_btn = Button(
            text='Переключить в РУЧНОЙ',
            font_size=dp(16),
            size_hint_y=0.3,
            background_color=(1, 0.7, 0.3, 1)
        )
        self.mode_btn.bind(on_press=self.toggle_mode)
        self.add_widget(self.mode_btn)
        
        # Кнопка аварийного отключения
        emergency_btn = Button(
            text='АВАРИЙНОЕ ОТКЛЮЧЕНИЕ',
            font_size=dp(16),
            size_hint_y=0.2,
            background_color=(1, 0.3, 0.3, 1)
        )
        emergency_btn.bind(on_press=self.emergency_stop)
        self.add_widget(emergency_btn)
    
    def _update_rect(self, instance, value):
        """Обновление размера фона"""
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def open_temperature_settings(self, instance):
        """Открытие настроек температуры"""
        self.main_app.open_temperature_popup()
    
    def toggle_mode(self, instance):
        """Переключение режима системы"""
        current_status = system_state.get_system_status()
        if current_status.system_mode == 'auto':
            system_state.update_system_mode('manual')
            self.mode_btn.text = 'Переключить в АВТО'
            self.mode_btn.background_color = (0.3, 1, 0.3, 1)
        else:
            system_state.update_system_mode('auto')
            self.mode_btn.text = 'Переключить в РУЧНОЙ'
            self.mode_btn.background_color = (1, 0.7, 0.3, 1)
    
    def emergency_stop(self, instance):
        """Аварийное отключение"""
        system_state.update_system_mode('emergency')
        system_state.update_valve_state(False)
    
    def update_mode_button(self, mode):
        """Обновление кнопки режима"""
        if mode == 'auto':
            self.mode_btn.text = 'Переключить в РУЧНОЙ'
            self.mode_btn.background_color = (1, 0.7, 0.3, 1)
        elif mode == 'manual':
            self.mode_btn.text = 'Переключить в АВТО'
            self.mode_btn.background_color = (0.3, 1, 0.3, 1)
        else:  # emergency
            self.mode_btn.text = 'АВАРИЙНЫЙ РЕЖИМ'
            self.mode_btn.background_color = (1, 0.3, 0.3, 1)

class TemperatureSettingsPopup(Popup):
    """Попап настройки температуры"""
    
    def __init__(self, current_temp, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Настройка температуры'
        self.size_hint = (0.8, 0.6)
        self.auto_dismiss = False
        
        # Основной контейнер
        main_layout = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(20))
        
        # Текущая температура
        current_label = Label(
            text=f'Текущая целевая температура: {current_temp:.1f}°C',
            font_size=dp(16),
            size_hint_y=0.2,
            color=(1, 1, 1, 1)
        )
        main_layout.add_widget(current_label)
        
        # Слайдер температуры
        slider_layout = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=0.4)
        
        self.temp_slider = Slider(
            min=45.0,
            max=60.0,
            value=current_temp,
            step=0.1,
            size_hint_y=0.6
        )
        
        self.value_label = Label(
            text=f'{current_temp:.1f}°C',
            font_size=dp(20),
            size_hint_y=0.4,
            color=(0.3, 0.8, 1, 1),
            bold=True
        )
        
        self.temp_slider.bind(value=self.on_slider_value)
        
        slider_layout.add_widget(self.temp_slider)
        slider_layout.add_widget(self.value_label)
        main_layout.add_widget(slider_layout)
        
        # Кнопки
        button_layout = BoxLayout(orientation='horizontal', spacing=dp(20), size_hint_y=0.3)
        
        cancel_btn = Button(
            text='Отмена',
            size_hint_x=0.5,
            background_color=(0.6, 0.6, 0.6, 1)
        )
        cancel_btn.bind(on_press=self.dismiss)
        
        save_btn = Button(
            text='Сохранить',
            size_hint_x=0.5,
            background_color=(0.3, 0.8, 1, 1)
        )
        save_btn.bind(on_press=self.save_temperature)
        
        button_layout.add_widget(cancel_btn)
        button_layout.add_widget(save_btn)
        main_layout.add_widget(button_layout)
        
        self.content = main_layout
    
    def on_slider_value(self, instance, value):
        """Обновление значения при движении слайдера"""
        self.value_label.text = f'{value:.1f}°C'
    
    def save_temperature(self, instance):
        """Сохранение новой температуры"""
        new_temp = self.temp_slider.value
        system_state.update_target_temperature(new_temp)
        self.dismiss()

class TemperatureControllerGUI(App):
    """Главное приложение GUI"""
    
    def build(self):
        """Построение интерфейса"""
        # Настройка окна для полноэкранного режима
        Window.fullscreen = False  # Можно изменить на True для реального использования
        Window.size = (800, 480)  # Типичный размер для 7" дисплея
        
        # Основной контейнер
        main_layout = BoxLayout(orientation='horizontal', spacing=dp(10), padding=dp(10))
        
        # Левая панель с данными
        data_panel = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_x=0.7)
        
        # Карточка температуры
        self.temp_card = TemperatureCard(size_hint_y=0.6)
        data_panel.add_widget(self.temp_card)
        
        # Карточка статуса
        self.status_card = StatusCard(size_hint_y=0.4)
        data_panel.add_widget(self.status_card)
        
        main_layout.add_widget(data_panel)
        
        # Правая панель управления
        self.control_panel = ControlPanel(self, size_hint_x=0.3)
        main_layout.add_widget(self.control_panel)
        
        # Подписка на обновления системы
        system_state.subscribe(self.on_system_update)
        
        # Запуск таймера обновления
        Clock.schedule_interval(self.update_interface, 1.0)
        
        # Установка темного фона
        with main_layout.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            self.bg_rect = Rectangle(size=Window.size, pos=(0, 0))
        
        return main_layout
    
    def on_system_update(self, system_data: SystemData):
        """Обработчик обновления данных системы"""
        # Обновление происходит через таймер
        pass
    
    def update_interface(self, dt):
        """Обновление интерфейса"""
        try:
            system_data = system_state.get_system_data()
            
            # Обновление карточек
            self.temp_card.update_data(system_data.temperature)
            self.status_card.update_data(system_data.status)
            self.control_panel.update_mode_button(system_data.status.system_mode)
            
        except Exception as e:
            print(f"Ошибка обновления интерфейса: {e}")
    
    def open_temperature_popup(self):
        """Открытие попапа настройки температуры"""
        current_temp = system_state.get_temperature_data().target_temp
        popup = TemperatureSettingsPopup(current_temp)
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