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
        
        # Диапазон температуры
        self.range_label = Label(
            text='Диапазон: --°C - --°C',
            font_size=dp(16),
            color=(0.8, 0.8, 0.8, 1),
            size_hint_y=0.2
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
        
        # Обновление диапазона
        if temp_settings:
            min_temp = temp_settings.get('min_temperature', 45.0)
            max_temp = temp_settings.get('max_temperature', 55.0)
            self.range_label.text = f'Диапазон: {min_temp:.1f}°C - {max_temp:.1f}°C'
        else:
            self.range_label.text = 'Диапазон: не настроен'

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
    
    def update_data(self, system_data: SystemData):
        """Обновление данных статуса"""
        # Поскольку у нас нет valve_state в SystemData, используем system_status для вывода
        if system_data.system_status == "running":
            valve_text = 'АКТИВНА'
            valve_color = (0.4, 1, 0.4, 1)
        else:
            valve_text = 'НЕАКТИВНА'
            valve_color = (1, 0.4, 0.4, 1)
        
        self.valve_label.text = f'Система: {valve_text}'
        self.valve_label.color = valve_color
        
        # Режим работы
        mode_text = {
            'running': 'РАБОТАЕТ',
            'starting': 'ЗАПУСК',
            'stopped': 'ОСТАНОВЛЕНА',
            'unknown': 'НЕИЗВЕСТНО'
        }.get(system_data.system_status, system_data.system_status.upper())
        
        self.mode_label.text = f'Статус: {mode_text}'
        
        # Время обновления
        if system_data.last_update:
            update_time = system_data.last_update.strftime('%H:%M:%S')
            self.update_label.text = f'Обновлено: {update_time}'
        else:
            self.update_label.text = 'Обновлено: --:--'

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
            size_hint_y=0.4,
            bold=True
        )
        self.add_widget(title)
        
        # Кнопка настройки температуры
        temp_btn = Button(
            text='Настройка диапазона температуры',
            font_size=dp(16),
            size_hint_y=0.6,
            background_color=(0.3, 0.7, 1, 1)
        )
        temp_btn.bind(on_press=self.open_temperature_settings)
        self.add_widget(temp_btn)
    
    def _update_rect(self, instance, value):
        """Обновление размера фона"""
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def open_temperature_settings(self, instance):
        """Открытие настроек температуры"""
        self.main_app.open_temperature_popup()

class TemperatureSettingsPopup(Popup):
    """Попап настройки минимальной и максимальной температуры"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = 'Настройка температуры'
        self.size_hint = (0.8, 0.8)
        self.auto_dismiss = False
        
        # Получение текущих настроек
        current_settings = get_temperature_settings()
        self.min_temp = current_settings.get('min_temperature', 45.0) if current_settings else 45.0
        self.max_temp = current_settings.get('max_temperature', 55.0) if current_settings else 55.0
        
        # Основной контейнер
        main_layout = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(20))
        
        # Заголовок с текущими настройками
        header_label = Label(
            text='Настройка диапазона температуры',
            font_size=dp(18),
            size_hint_y=0.1,
            color=(1, 1, 1, 1),
            bold=True
        )
        main_layout.add_widget(header_label)
        
        # Секция минимальной температуры
        min_section = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=0.35)
        
        min_title = Label(
            text='Минимальная температура',
            font_size=dp(16),
            size_hint_y=0.2,
            color=(0.8, 0.8, 0.8, 1)
        )
        min_section.add_widget(min_title)
        
        self.min_slider = Slider(
            min=30.0,
            max=65.0,
            value=self.min_temp,
            step=0.1,
            size_hint_y=0.5
        )
        
        self.min_value_label = Label(
            text=f'{self.min_temp:.1f}°C',
            font_size=dp(20),
            size_hint_y=0.3,
            color=(0.4, 0.8, 1, 1),
            bold=True
        )
        
        self.min_slider.bind(value=self.on_min_slider_value)
        
        min_section.add_widget(self.min_slider)
        min_section.add_widget(self.min_value_label)
        main_layout.add_widget(min_section)
        
        # Секция максимальной температуры
        max_section = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=0.35)
        
        max_title = Label(
            text='Максимальная температура',
            font_size=dp(16),
            size_hint_y=0.2,
            color=(0.8, 0.8, 0.8, 1)
        )
        max_section.add_widget(max_title)
        
        self.max_slider = Slider(
            min=35.0,
            max=70.0,
            value=self.max_temp,
            step=0.1,
            size_hint_y=0.5
        )
        
        self.max_value_label = Label(
            text=f'{self.max_temp:.1f}°C',
            font_size=dp(20),
            size_hint_y=0.3,
            color=(1, 0.6, 0.4, 1),
            bold=True
        )
        
        self.max_slider.bind(value=self.on_max_slider_value)
        
        max_section.add_widget(self.max_slider)
        max_section.add_widget(self.max_value_label)
        main_layout.add_widget(max_section)
        
        # Сообщение об ошибке валидации
        self.error_label = Label(
            text='',
            font_size=dp(14),
            size_hint_y=0.05,
            color=(1, 0.3, 0.3, 1)
        )
        main_layout.add_widget(self.error_label)
        
        # Кнопки
        button_layout = BoxLayout(orientation='horizontal', spacing=dp(20), size_hint_y=0.15)
        
        cancel_btn = Button(
            text='Отмена',
            size_hint_x=0.5,
            background_color=(0.6, 0.6, 0.6, 1)
        )
        cancel_btn.bind(on_press=self.dismiss)
        
        self.save_btn = Button(
            text='Сохранить',
            size_hint_x=0.5,
            background_color=(0.3, 0.8, 1, 1)
        )
        self.save_btn.bind(on_press=self.save_temperature_settings)
        
        button_layout.add_widget(cancel_btn)
        button_layout.add_widget(self.save_btn)
        main_layout.add_widget(button_layout)
        
        self.content = main_layout
        
        # Начальная валидация
        self.validate_settings()
    
    def on_min_slider_value(self, instance, value):
        """Обновление значения минимальной температуры"""
        self.min_temp = value
        self.min_value_label.text = f'{value:.1f}°C'
        self.validate_settings()
    
    def on_max_slider_value(self, instance, value):
        """Обновление значения максимальной температуры"""
        self.max_temp = value
        self.max_value_label.text = f'{value:.1f}°C'
        self.validate_settings()
    
    def validate_settings(self):
        """Валидация настроек температуры"""
        if self.min_temp >= self.max_temp:
            self.error_label.text = 'Минимальная температура должна быть меньше максимальной!'
            self.save_btn.background_color = (0.6, 0.6, 0.6, 1)
            self.save_btn.disabled = True
        else:
            difference = self.max_temp - self.min_temp
            self.error_label.text = f'Диапазон: {difference:.1f}°C'
            self.error_label.color = (0.4, 1, 0.4, 1)
            self.save_btn.background_color = (0.3, 0.8, 1, 1)
            self.save_btn.disabled = False
    
    def save_temperature_settings(self, instance):
        """Сохранение новых настроек температуры"""
        if self.min_temp >= self.max_temp:
            return  # Не сохраняем некорректные настройки
        
        success = set_temperature_settings(
            max_temp=self.max_temp,
            min_temp=self.min_temp,
            source_module="gui_interface"
        )
        
        if success:
            print(f"Настройки температуры сохранены: {self.min_temp:.1f}°C - {self.max_temp:.1f}°C")
        else:
            print("Ошибка при сохранении настроек температуры")
        
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
        
        # Обновление карточек
        self.temp_card.update_data(system_data.temperature)
        self.status_card.update_data(system_data)
        
        # Запуск таймера обновления
        Clock.schedule_interval(self.update_interface, 1.0)
        
        # Установка темного фона
        with main_layout.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            self.bg_rect = Rectangle(size=Window.size, pos=(0, 0))
        
        return main_layout
    
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
            
            # Обновление карточек
            self.temp_card.update_data(system_data.temperature)
            self.status_card.update_data(system_data)
            
        except Exception as e:
            print(f"Ошибка обновления интерфейса: {e}")
    
    def open_temperature_popup(self):
        """Открытие попапа настройки температуры"""
        popup = TemperatureSettingsPopup()
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