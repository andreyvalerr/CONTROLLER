#!/usr/bin/env python3
"""
Регулятор температуры с гистерезисом
Управляет включением/выключением охлаждения на основе температуры жидкости
"""

import time
import logging
import threading
from typing import Optional, Callable
from collections import deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from .relay_controller import RelayController
from .config import TemperatureConfig, SafetyConfig, DEFAULT_TEMPERATURE_CONFIG, DEFAULT_SAFETY_CONFIG

class RegulatorState(Enum):
    """Состояния регулятора"""
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"


class RegulatorAlgorithm(Enum):
    """Алгоритм работы регулятора"""
    HYSTERESIS = "hysteresis"
    PREDICTIVE = "predictive"

@dataclass
class RegulatorConfig:
    """Конфигурация регулятора температуры"""
    temperature_config: TemperatureConfig
    safety_config: SafetyConfig
    # Пороги температуры (получаются из data_manager)
    min_temperature: float = 47.0  # По умолчанию, будет обновлено из data_manager
    max_temperature: float = 55.0  # По умолчанию, будет обновлено из data_manager
    # Параметры предиктивного алгоритма
    predictive_lookahead_s: float = 5.0          # горизонт прогноза, сек
    predictive_min_rate_c_per_s: float = 0.05    # минимальная скорость изменения T для предиктивных действий
    predictive_pre_on_margin_c: float = 0.5      # досрочное включение, запас по порогу (°C)
    predictive_pre_off_margin_c: float = 0.5     # досрочное выключение, запас по порогу (°C)
    predictive_slope_window_s: float = 5.0      # окно усреднения скорости (сек)
    predictive_reverse_rate_c_per_s: float = 0.02 # требуемая скорость разворота тренда (°C/с)
    predictive_reverse_temp_margin_c: float = 0.10 # требуемый отскок от экстремума (°C)

class TemperatureRegulator:
    """
    Регулятор температуры с гистерезисом
    
    Алгоритм работы:
    1. Если температура >= max_threshold И охлаждение выключено → ВКЛЮЧИТЬ охлаждение
    2. Если температура <= min_threshold И охлаждение включено → ВЫКЛЮЧИТЬ охлаждение
    3. В остальных случаях состояние не меняется
    """
    
    def __init__(self, 
                 relay_controller: RelayController,
                 temperature_callback: Callable[[], Optional[float]],
                 config: Optional[RegulatorConfig] = None,
                 temperature_settings_callback: Optional[Callable[[], Optional[dict]]] = None,
                 relay_controller_low: Optional[RelayController] = None):
        """
        Инициализация регулятора температуры
        
        Args:
            relay_controller: Контроллер реле
            temperature_callback: Функция получения температуры
            config: Конфигурация регулятора
            temperature_settings_callback: Функция получения настроек температуры из data_manager
        """
        self.relay_controller = relay_controller
        self.temperature_callback = temperature_callback
        self.temperature_settings_callback = temperature_settings_callback
        # Дополнительный релейный канал для нижнего порога (GPIO22)
        self.relay_controller_low = relay_controller_low
        
        # Конфигурация
        if config is None:
            config = RegulatorConfig(
                temperature_config=DEFAULT_TEMPERATURE_CONFIG,
                safety_config=DEFAULT_SAFETY_CONFIG
            )
        self.config = config
        
        self.logger = logging.getLogger(__name__)
        
        # Состояние регулятора
        self.state = RegulatorState.STOPPED
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()
        
        # Статистика
        self._start_time = None
        self._last_temperature = None
        self._last_temperature_time = None
        
        # Счетчики
        self._total_cycles = 0
        self._cooling_cycles = 0
        
        # Отслеживание обновлений настроек
        self._last_settings_check = None
        self._settings_check_interval = 1.0  # Проверять настройки каждую секунду
        self._settings_update_count = 0

        # Режим (алгоритм) регулятора
        self._algorithm = RegulatorAlgorithm.HYSTERESIS

        # История температур и расчёт производной
        self._history = deque(maxlen=600)  # хранить до ~10 минут при интервале 1с
        self._last_slope_c_per_s: Optional[float] = None
        self._last_pred_high: Optional[float] = None
        self._last_pred_low: Optional[float] = None
        # Экстремумы с момента включения каналов для контроля разворота
        self._high_since_on_min_temp: Optional[float] = None
        self._low_since_on_max_temp: Optional[float] = None
        
    def start(self) -> bool:
        """
        Запуск регулятора температуры
        
        Returns:
            bool: True если запуск успешен
        """
        if self._running:
            self.logger.warning("Регулятор уже запущен")
            return True
        
        if not self.relay_controller.is_initialized():
            self.logger.error("Релейный контроллер (верхний порог) не инициализирован")
            return False
        if self.relay_controller_low is not None and not self.relay_controller_low.is_initialized():
            self.logger.error("Релейный контроллер (нижний порог) не инициализирован")
            return False
        
        try:
            self._running = True
            self._stop_event.clear()
            self.state = RegulatorState.RUNNING
            self._start_time = datetime.now()
            
            # Запуск потока регулирования
            self._thread = threading.Thread(target=self._regulation_loop, daemon=True)
            self._thread.start()
            
            self.logger.info("Регулятор температуры запущен")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска регулятора: {e}")
            self._running = False
            self.state = RegulatorState.ERROR
            return False
    
    def stop(self):
        """Остановка регулятора температуры"""
        if not self._running:
            return
        
        self.logger.info("Остановка регулятора температуры")
        
        self._running = False
        self._stop_event.set()
        
        # Ожидание завершения потока
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        
        # Выключение реле при остановке
        self.relay_controller.turn_off()
        if self.relay_controller_low is not None:
            self.relay_controller_low.turn_off()
        
        self.state = RegulatorState.STOPPED
        self.logger.info("Регулятор температуры остановлен")
    
    def _regulation_loop(self):
        """Основной цикл регулирования температуры"""
        self.logger.info("Запуск цикла регулирования температуры")
        
        while self._running and not self._stop_event.is_set():
            try:
                # Периодическая проверка обновлений настроек температуры
                self._check_and_update_temperature_settings()
                
                # Получение температуры
                temperature = self._get_temperature_safe()
                
                if temperature is None:
                    self.logger.warning("Не удалось получить температуру")
                    continue
                
                # Обновление статистики
                self._last_temperature = temperature
                self._last_temperature_time = datetime.now()

                # Обновление истории для расчёта тренда температуры
                self._update_temperature_history(self._last_temperature_time, temperature)
                
                # Основная логика регулирования
                if self._algorithm == RegulatorAlgorithm.PREDICTIVE:
                    self._regulate_temperature_predictive(temperature)
                else:
                    self._regulate_temperature(temperature)
                
                self._total_cycles += 1
                
            except Exception as e:
                self.logger.error(f"Ошибка в цикле регулирования: {e}")
                self.state = RegulatorState.ERROR
            
            # Ожидание следующего цикла
            self._stop_event.wait(self.config.temperature_config.control_interval)
        
        self.logger.info("Цикл регулирования температуры завершен")
    
    def _get_temperature_safe(self) -> Optional[float]:
        """
        Безопасное получение температуры с таймаутом
        
        Returns:
            float: Температура или None при ошибке
        """
        try:
            return self.temperature_callback()
        except Exception as e:
            self.logger.error(f"Ошибка получения температуры: {e}")
            return None
    
    def _regulate_temperature(self, temperature: float):
        """
        Основная логика регулирования температуры с гистерезисом
        
        Args:
            temperature: Текущая температура
        """
        # Состояния и пороги
        high_active = self.relay_controller.get_relay_state()
        low_active = self.relay_controller_low.get_relay_state() if self.relay_controller_low is not None else False
        max_temp = self.config.max_temperature
        min_temp = self.config.min_temperature
        hysteresis = self.config.temperature_config.hysteresis if self.config and self.config.temperature_config else 0.1
        
        # Подробное логирование для диагностики
        self.logger.debug(
            f"Регулирование: T={temperature:.2f}°C, "
            f"HIGH={'ON' if high_active else 'OFF'}, LOW={'ON' if low_active else 'OFF'}, "
            f"пороги=[{min_temp:.2f}°C - {max_temp:.2f}°C], hyst={hysteresis:.2f}°C"
        )
        
        # ЛОГИКА ДЛЯ ВЕРХНЕГО ПОРОГА (GPIO17):
        # Включить при достижении max_temp, выключить когда температура станет МЕНЬШЕ (max_temp - 0.1)
        if not high_active and temperature >= max_temp:
            self.logger.info(f"🔥 HIGH ON: T={temperature:.2f}°C >= {max_temp:.2f}°C")
            if self._safe_turn_on(self.relay_controller, channel_name="HIGH"):
                self._cooling_cycles += 1
                self.logger.info(f"✅ HIGH включено (GPIO17)")
            else:
                self.logger.error(f"❌ Не удалось включить HIGH при T={temperature:.2f}°C")
        elif high_active and temperature < (max_temp - hysteresis):
            self.logger.info(f"❄️ HIGH OFF: T={temperature:.2f}°C < {max_temp - hysteresis:.2f}°C")
            if self._safe_turn_off(self.relay_controller, channel_name="HIGH"):
                self.logger.info(f"✅ HIGH выключено (GPIO17)")
            else:
                self.logger.error(f"❌ Не удалось выключить HIGH при T={temperature:.2f}°C")

        # ЛОГИКА ДЛЯ НИЖНЕГО ПОРОГА (GPIO22):
        if self.relay_controller_low is not None:
            if not low_active and temperature < min_temp:
                self.logger.info(f"🧊 LOW ON: T={temperature:.2f}°C < {min_temp:.2f}°C")
                if self._safe_turn_on(self.relay_controller_low, channel_name="LOW"):
                    self._cooling_cycles += 1
                    self.logger.info(f"✅ LOW включено (GPIO22)")
                else:
                    self.logger.error(f"❌ Не удалось включить LOW при T={temperature:.2f}°C")
            elif low_active and temperature > (min_temp + hysteresis):
                self.logger.info(f"🌡️ LOW OFF: T={temperature:.2f}°C > {min_temp + hysteresis:.2f}°C")
                if self._safe_turn_off(self.relay_controller_low, channel_name="LOW"):
                    self.logger.info(f"✅ LOW выключено (GPIO22)")
                else:
                    self.logger.error(f"❌ Не удалось выключить LOW при T={temperature:.2f}°C")
        
        # Иначе — без действий
    
    def _regulate_temperature_predictive(self, temperature: float):
        """Предиктивная логика регулирования температуры.
        Работает как авто (гистерезис), но с упреждающим включением/выключением, чтобы точнее держать заданный диапазон.
        """
        # Текущее состояние и базовые пороги
        high_active = self.relay_controller.get_relay_state()
        low_active = self.relay_controller_low.get_relay_state() if self.relay_controller_low is not None else False
        max_temp = self.config.max_temperature
        min_temp = self.config.min_temperature
        hysteresis = self.config.temperature_config.hysteresis if self.config and self.config.temperature_config else 0.1

        # Параметры предиктивного алгоритма
        lookahead = max(0.0, float(getattr(self.config, 'predictive_lookahead_s', 5.0)))
        min_rate = max(0.0, float(getattr(self.config, 'predictive_min_rate_c_per_s', 0.05)))
        pre_on_margin = max(0.0, float(getattr(self.config, 'predictive_pre_on_margin_c', 2.0)))
        pre_off_margin = max(0.0, float(getattr(self.config, 'predictive_pre_off_margin_c', 2.0)))
        slope = self._compute_temperature_slope()

        # Прогноз температуры через lookahead секунд
        predicted = None if slope is None else (temperature + slope * lookahead)
        self._last_slope_c_per_s = slope
        self._last_pred_high = predicted
        self._last_pred_low = predicted

        self.logger.debug(
            f"PREDICTIVE: T={temperature:.2f}°C, slope={slope if slope is not None else 'NA'} °C/s, "
            f"pred(+{lookahead:.1f}s)={predicted if predicted is not None else 'NA'}°C, "
            f"range=[{min_temp:.2f}°C - {max_temp:.2f}°C], hyst={hysteresis:.2f}°C"
        )

        # ВЕРХНИЙ ПОРОГ (ОХЛАЖДЕНИЕ, GPIO17)
        should_high_on = False
        should_high_off = False

        # Базовая гистерезисная логика
        if not high_active and temperature >= max_temp:
            should_high_on = True
        elif high_active and temperature < (max_temp - hysteresis):
            should_high_off = True

        # Предиктивные условия: упреждающее включение/выключение
        if predicted is not None:
            # Упреждающее включение охлаждения, если тренд вверх и достигнем порога в ближайшее время
            if not high_active and slope is not None and slope > min_rate and predicted >= (max_temp - pre_on_margin):
                should_high_on = True
                self.logger.debug(
                    f"PREDICTIVE HIGH ON trigger: slope={slope:.3f}, predicted={predicted:.2f}°C >= {max_temp - pre_on_margin:.2f}°C"
                )
            # Выключение только после разворота тренда вверх с отскоком от минимума
            reverse_rate = float(getattr(self.config, 'predictive_reverse_rate_c_per_s', 0.02))
            reverse_margin = float(getattr(self.config, 'predictive_reverse_temp_margin_c', 0.10))
            if high_active and slope is not None and slope >= reverse_rate:
                if self._high_since_on_min_temp is not None and temperature >= (self._high_since_on_min_temp + reverse_margin):
                    # Разрешаем выключение HIGH по развороту только если температура уже
                    # опустилась ниже (max_temp - pre_off_margin)
                    if temperature <= (max_temp - pre_off_margin):
                        should_high_off = True
                        self.logger.debug(
                            f"PREDICTIVE HIGH OFF (reversal + below max-pre_off): slope={slope:.3f}>= {reverse_rate:.3f}, "
                            f"T={temperature:.2f}°C <= {max_temp - pre_off_margin:.2f}°C"
                        )
                    else:
                        self.logger.debug(
                            f"PREDICTIVE HIGH OFF blocked: T={temperature:.2f}°C > {max_temp - pre_off_margin:.2f}°C (max_temp - pre_off_margin)"
                        )

        # Применяем решения по верхнему порогу
        if should_high_on and not high_active:
            # Взаимоисключение: если низкий канал активен, пытаемся его выключить.
            if low_active and self.relay_controller_low is not None:
                off_ok = self._safe_turn_off(self.relay_controller_low, channel_name="LOW")
                # Перепроверка состояния после попытки
                try:
                    low_active = self.relay_controller_low.get_relay_state()
                except Exception:
                    pass
                if not off_ok and low_active:
                    # Блокируем включение HIGH до окончания min_cycle_time
                    self.logger.debug("PREDICTIVE HIGH ON blocked: LOW still ON (min_cycle_time)")
                    should_high_on = False
            if should_high_on:
                self.logger.info(f"🔮 HIGH ON (predictive): T={temperature:.2f}°C")
                if self._safe_turn_on(self.relay_controller, channel_name="HIGH"):
                    self._cooling_cycles += 1
                    # Сброс и фиксация минимума после включения
                    self._high_since_on_min_temp = temperature
        elif should_high_off and high_active:
            self.logger.info(f"🔮 HIGH OFF (predictive): T={temperature:.2f}°C")
            self._safe_turn_off(self.relay_controller, channel_name="HIGH")
            # Сброс трекинга минимума
            self._high_since_on_min_temp = None

        # НИЖНИЙ ПОРОГ (ОТОПЛЕНИЕ/ЗАКРЫТИЕ КЛАПАНА, GPIO22)
        if self.relay_controller_low is not None:
            should_low_on = False
            should_low_off = False

            # Базовая гистерезисная логика
            if not low_active and temperature < min_temp:
                should_low_on = True
            elif low_active and temperature > (min_temp + hysteresis):
                should_low_off = True

            # Предиктивные условия
            if predicted is not None:
                # Упреждающее включение нижнего канала, если тренд вниз и скоро пересечём минимум
                if not low_active and slope is not None and slope < -min_rate and predicted <= (min_temp + pre_on_margin):
                    should_low_on = True
                    self.logger.debug(
                        f"PREDICTIVE LOW ON trigger: slope={slope:.3f}, predicted={predicted:.2f}°C <= {min_temp + pre_on_margin:.2f}°C"
                    )
                # Выключение только после разворота тренда вниз с отскоком от максимума
                reverse_rate = float(getattr(self.config, 'predictive_reverse_rate_c_per_s', 0.02))
                reverse_margin = float(getattr(self.config, 'predictive_reverse_temp_margin_c', 0.10))
                if low_active and slope is not None and (-slope) >= reverse_rate:
                    if self._low_since_on_max_temp is not None and temperature <= (self._low_since_on_max_temp - reverse_margin):
                        should_low_off = True
                        self.logger.debug(
                            f"PREDICTIVE LOW OFF (reversal) trigger: -slope={-slope:.3f}>= {reverse_rate:.3f}, "
                            f"T={temperature:.2f}°C <= max_since_on-{reverse_margin:.2f} ({self._low_since_on_max_temp - reverse_margin:.2f}°C)"
                        )

            # Применяем решения по нижнему порогу
            if should_low_on and not low_active:
                if high_active:
                    off_ok = self._safe_turn_off(self.relay_controller, channel_name="HIGH")
                    try:
                        high_active = self.relay_controller.get_relay_state()
                    except Exception:
                        pass
                    if not off_ok and high_active:
                        self.logger.debug("PREDICTIVE LOW ON blocked: HIGH still ON (min_cycle_time)")
                        should_low_on = False
                if should_low_on:
                    self.logger.info(f"🔮 LOW ON (predictive): T={temperature:.2f}°C")
                    if self._safe_turn_on(self.relay_controller_low, channel_name="LOW"):
                        # Сброс и фиксация максимума после включения
                        self._low_since_on_max_temp = temperature
            elif should_low_off and low_active:
                self.logger.info(f"🔮 LOW OFF (predictive): T={temperature:.2f}°C")
                self._safe_turn_off(self.relay_controller_low, channel_name="LOW")
                # Сброс трекинга максимума
                self._low_since_on_max_temp = None

    def _can_switch_now(self, controller: RelayController) -> tuple[bool, float, float]:
        """Проверяет, можно ли переключить данный канал с учётом min_cycle_time.
        Returns: (allowed, elapsed_s, min_cycle_s)
        """
        try:
            min_cycle = float(self.config.safety_config.min_cycle_time) if self.config and self.config.safety_config else 0.0
        except Exception:
            min_cycle = 0.0
        last_sw = None
        try:
            last_sw = controller.get_last_switch_time()
        except Exception:
            last_sw = None
        if last_sw is None or min_cycle <= 0.0:
            return True, 0.0, max(0.0, min_cycle)
        elapsed = (datetime.now() - last_sw).total_seconds()
        return elapsed >= min_cycle, elapsed, min_cycle

    def _safe_turn_on(self, controller: RelayController, channel_name: str = "") -> bool:
        allowed, elapsed, min_cycle = self._can_switch_now(controller)
        if not allowed:
            self.logger.debug(
                f"BLOCK {channel_name} ON: прошло {elapsed:.1f}s < min_cycle_time {min_cycle:.1f}s"
            )
            return False
        return controller.turn_on()

    def _safe_turn_off(self, controller: RelayController, channel_name: str = "") -> bool:
        allowed, elapsed, min_cycle = self._can_switch_now(controller)
        if not allowed:
            self.logger.debug(
                f"BLOCK {channel_name} OFF: прошло {elapsed:.1f}s < min_cycle_time {min_cycle:.1f}s"
            )
            return False
        return controller.turn_off()

    def _update_temperature_history(self, timestamp: datetime, temperature: float) -> None:
        """Добавляет точку в историю температур."""
        try:
            self._history.append((timestamp, temperature))
        except Exception:
            # Защита от редких ошибок деки
            pass

    def _compute_temperature_slope(self) -> Optional[float]:
        """Вычисляет усреднённую скорость изменения температуры (°C/сек) за окно времени."""
        window = max(1.0, float(getattr(self.config, 'predictive_slope_window_s', 10.0)))
        if not self._history or len(self._history) < 2:
            return None
        newest_t, newest_v = self._history[-1]
        # Ищем самую старую точку в пределах окна
        cutoff = newest_t.timestamp() - window
        oldest_idx = None
        for i in range(len(self._history) - 2, -1, -1):
            t_i, _ = self._history[i]
            if t_i.timestamp() <= cutoff:
                oldest_idx = i
                break
        if oldest_idx is None:
            # Нет достаточно старой точки — возьмём самую первую
            oldest_idx = 0
        oldest_t, oldest_v = self._history[oldest_idx]
        dt = (newest_t - oldest_t).total_seconds()
        if dt <= 0:
            return None
        return (newest_v - oldest_v) / dt

    def set_algorithm(self, algorithm: "RegulatorAlgorithm | str") -> None:
        """Устанавливает алгоритм регулирования (hysteresis | predictive)."""
        try:
            if isinstance(algorithm, RegulatorAlgorithm):
                self._algorithm = algorithm
            else:
                normalized = str(algorithm).strip().lower()
                if normalized in ("predictive", "предиктивный", "авто (предиктивный)"):
                    self._algorithm = RegulatorAlgorithm.PREDICTIVE
                else:
                    self._algorithm = RegulatorAlgorithm.HYSTERESIS
            self.logger.info(f"Алгоритм регулятора установлен: {self._algorithm.value}")
        except Exception as e:
            self.logger.error(f"Ошибка установки алгоритма: {e}")

    def get_algorithm(self) -> str:
        """Возвращает текущий алгоритм регулирования ('hysteresis'|'predictive')."""
        return self._algorithm.value
    def _check_and_update_temperature_settings(self):
        """
        Проверка и обновление настроек температуры из data_manager
        """
        current_time = datetime.now()
        
        # Проверяем настройки только если прошло достаточно времени
        if (self._last_settings_check is None or 
            (current_time - self._last_settings_check).total_seconds() >= self._settings_check_interval):
            
            self._last_settings_check = current_time
            
            if self.temperature_settings_callback:
                try:
                    settings = self.temperature_settings_callback()
                    
                    if settings and 'max_temperature' in settings and 'min_temperature' in settings:
                        new_max_temp = settings['max_temperature']
                        new_min_temp = settings['min_temperature']
                        
                        # Проверяем, изменились ли настройки
                        current_max = self.config.max_temperature
                        current_min = self.config.min_temperature
                        
                        if new_max_temp != current_max or new_min_temp != current_min:
                            # Обновляем настройки в RegulatorConfig
                            self.config.max_temperature = new_max_temp
                            self.config.min_temperature = new_min_temp
                            self._settings_update_count += 1
                            
                            self.logger.info(f"Настройки температуры обновлены из data_manager: "
                                           f"{new_min_temp}°C - {new_max_temp}°C (обновление #{self._settings_update_count})")
                    
                except Exception as e:
                    self.logger.error(f"Ошибка при проверке настроек температуры: {e}")
    
    def get_status(self) -> dict:
        """
        Получение статуса регулятора
        
        Returns:
            dict: Текущий статус регулятора
        """
        current_time = datetime.now()
        
        # Время работы
        uptime = None
        if self._start_time:
            uptime = current_time - self._start_time
        
        # Время с последнего обновления температуры
        temp_age = None
        if self._last_temperature_time:
            temp_age = current_time - self._last_temperature_time
        
        # Время с последней проверки настроек
        settings_check_age = None
        if self._last_settings_check:
            settings_check_age = current_time - self._last_settings_check
        
        return {
            # Основной статус
            "state": self.state.value,
            "is_running": self._running,
            "cooling_active": self.relay_controller.get_relay_state(),
            "algorithm": self.get_algorithm(),
            
            # Температура
            "current_temperature": self._last_temperature,
            "temperature_age_seconds": temp_age.total_seconds() if temp_age else None,
            "last_temperature_time": self._last_temperature_time.isoformat() if self._last_temperature_time else None,
            "temperature_slope_c_per_s": self._last_slope_c_per_s,
            "predicted_temperature_in_lookahead": self._last_pred_high,
            
            # Пороги
            "max_temperature": self.config.max_temperature,
            "min_temperature": self.config.min_temperature,
            "hysteresis": self.config.temperature_config.hysteresis,
            
            # Статистика
            "total_cycles": self._total_cycles,
            "cooling_cycles": self._cooling_cycles,
            "settings_updates": self._settings_update_count,
            "uptime_seconds": uptime.total_seconds() if uptime else None,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            
            # Проверки настроек
            "last_settings_check": self._last_settings_check.isoformat() if self._last_settings_check else None,
            "settings_check_age_seconds": settings_check_age.total_seconds() if settings_check_age else None,
            "settings_check_interval": self._settings_check_interval,
            
            # Конфигурация
            "control_interval": self.config.temperature_config.control_interval
        }
    
    def update_config(self, config: RegulatorConfig):
        """
        Обновление конфигурации регулятора
        
        Args:
            config: Новая конфигурация
        """
        self.config = config
        self.logger.info("Конфигурация регулятора обновлена")
    
    def is_running(self) -> bool:
        """Проверка работы регулятора"""
        return self._running
    
    def get_last_temperature(self) -> Optional[float]:
        """Получение последней измеренной температуры"""
        return self._last_temperature
    
    def __enter__(self):
        """Поддержка контекстного менеджера"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера"""
        self.stop() 