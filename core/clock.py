"""
统一时钟模块

核心设计：
- 维护周期计数（cycle_count）作为核心状态，模拟时间（sim_time）由计算得出
- step() 方法内部根据模式决定是否等待，调用方无需关心
- 支持执行周期（cycle_time）与采样间隔（sample_interval）分离

运行模式：
- REALTIME: 实时模式，每个周期都会 sleep，适合在线运行/联调
- GENERATOR: 生成器模式，不 sleep，用于批量数据生成
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Union, Tuple

from utils.logger import get_logger


logger = get_logger()

# 常量定义
EXECUTION_TIME_WARNING_THRESHOLD = 0.6  # 执行时间警告阈值（占周期的百分比）
LAG_SAFETY_MARGIN = 1.5  # 历史数据安全余量（用于计算 record_length）
MIN_RECORD_LENGTH = 10  # 最小历史记录长度


class ClockMode(Enum):
    """时钟运行模式。"""

    REALTIME = auto()  # 实时模式，每个周期 sleep
    GENERATOR = auto()  # 生成器模式，不 sleep


@dataclass
class ClockConfig:
    """
    时钟配置。

    Attributes:
        cycle_time: PLC执行周期（秒），例如 0.5 表示 500ms
        start_time: 起始时间，可以是 float（时间戳）或 datetime 对象，默认 0.0
        mode: 时钟模式（实时/生成器）
        sample_interval: 采样间隔（秒），如果为 None 则等于 cycle_time（每个周期都采样）
                        例如：cycle_time=0.5, sample_interval=5.0 表示每 0.5 秒执行一次，
                        但每 5 秒采样一次数据（每 10 个周期采样一次）
        time_format: 时间字符串格式化模板，使用 strftime 格式，例如：
                     - "%Y%m%d" -> "20241202"
                     - "%Y-%m-%d %H:%M:%S" -> "2024-12-02 10:30:45"
                     - "%y%m" -> "2412"
                     如果为 None，则返回 ISO 格式字符串
    """

    cycle_time: float = 0.5
    start_time: Union[float, datetime] = 0.0
    mode: ClockMode = ClockMode.REALTIME
    sample_interval: float | None = None
    time_format: str | None = None

    def __post_init__(self) -> None:
        """验证配置有效性。"""
        if self.cycle_time <= 0:
            raise ValueError(f"cycle_time must be positive, got {self.cycle_time}")
        if self.sample_interval is not None and self.sample_interval <= 0:
            raise ValueError(
                f"sample_interval must be positive, got {self.sample_interval}"
            )
        if (
            self.sample_interval is not None
            and self.sample_interval < self.cycle_time
        ):
            raise ValueError(
                f"sample_interval ({self.sample_interval}) must be >= cycle_time ({self.cycle_time})"
            )


class Clock:
    """
    统一时钟。

    核心状态：
    - cycle_count: 周期计数（核心状态）
    - sim_time: 模拟时间（计算属性，由 start_time + cycle_count * cycle_time 得出）

    行为：
    - step(): 步进一个周期，根据模式决定是否等待，返回 (周期计数, 是否需要采样, 当前时间字符串)
    """

    def __init__(self, config: ClockConfig) -> None:
        """
        初始化时钟。

        Args:
            config: 时钟配置
        """
        self.config = config

        # 核心状态：周期计数
        self.cycle_count: int = 0

        # 计算起始时间戳
        if isinstance(config.start_time, datetime):
            self._start_timestamp: float = config.start_time.timestamp()
        else:
            self._start_timestamp: float = float(config.start_time)

        # 运行状态
        self._real_start_time: float | None = None
        self._is_running: bool = False
        
        # 当前周期的开始时间戳（用于计算执行时间和剩余 sleep 时间）
        self._current_cycle_start_time: float | None = None

        # 计算采样周期数（如果指定了采样间隔）
        if config.sample_interval is not None:
            self._sample_cycles: int = int(
                config.sample_interval / config.cycle_time
            )
            if self._sample_cycles < 1:
                self._sample_cycles = 1
        else:
            self._sample_cycles = 1  # 每个周期都采样

        logger.info(
            "Clock initialized: cycle_time=%.3f, mode=%s, "
            "start_time=%.3f, sample_interval=%s (every %d cycles), time_format=%s",
            self.config.cycle_time,
            self.config.mode.name,
            self._start_timestamp,
            self.config.sample_interval,
            self._sample_cycles,
            self.config.time_format,
        )

    @property
    def sim_time(self) -> float:
        """
        当前模拟时间（计算属性）。

        Returns:
            模拟时间（秒）：start_time + cycle_count * cycle_time
        """
        return self._start_timestamp + self.cycle_count * self.config.cycle_time

    def start(self) -> None:
        """启动时钟。"""
        if not self._is_running:
            self._real_start_time = time.time()
            # 第一个周期的开始时间
            self._current_cycle_start_time = self._real_start_time
            self._is_running = True
            logger.info(
                "Clock started: cycle_count=%d, sim_time=%.3f",
                self.cycle_count,
                self.sim_time,
            )

    def stop(self) -> None:
        """停止时钟。"""
        if self._is_running:
            self._is_running = False
            logger.info(
                "Clock stopped: cycle_count=%d, sim_time=%.3f",
                self.cycle_count,
                self.sim_time,
            )

    def step(self) -> Tuple[int, bool, str, float]:
        """
        步进一个周期（单一对外 API）。

        注意：
        - REALTIME 模式：在此方法内部根据执行时间计算剩余时间并 sleep
        - GENERATOR 模式：不 sleep，直接步进

        Returns:
            (周期计数, 是否需要采样, 当前时间字符串, 执行时间百分比)
            - 周期计数：当前的 cycle_count
            - 是否需要采样：根据 sample_interval 判断
            - 当前时间字符串：根据 time_format 格式化后的时间字符串
            - 执行时间百分比：本周期算法执行时间占周期的百分比（0.0 ~ 1.0），
                            在 GENERATOR 模式下恒为 0
        """
        if not self._is_running:
            self.start()

        # 计算本周期执行时间（从上一次记录的开始时间到现在）
        execution_time = 0.0
        now = time.time()
        if self._current_cycle_start_time is not None:
            execution_time = now - self._current_cycle_start_time

        exec_ratio = 0.0

        # 在 REALTIME 模式下，根据执行时间计算剩余时间并 sleep，同时计算执行时间占比
        if self.config.mode is ClockMode.REALTIME and self.config.cycle_time > 0:
            exec_ratio = min(execution_time / self.config.cycle_time, 1.0)

            threshold = self.config.cycle_time * EXECUTION_TIME_WARNING_THRESHOLD
            if execution_time > threshold:
                logger.warning(
                    "Cycle execution time (%.3fs) exceeds 60%% of cycle_time (%.3fs * 0.6 = %.3fs), "
                    "cycle_count=%d, execution_time=%.3fs, cycle_time=%.3fs",
                    execution_time,
                    self.config.cycle_time,
                    threshold,
                    self.cycle_count,
                    execution_time,
                    self.config.cycle_time,
                )

            remaining_time = self.config.cycle_time - execution_time
            if remaining_time > 0:
                time.sleep(remaining_time)
            else:
                logger.warning(
                    "Cycle execution time (%.3fs) >= cycle_time (%.3fs), no time left for sleep, "
                    "cycle_count=%d",
                    execution_time,
                    self.config.cycle_time,
                    self.cycle_count,
                )

        # REALTIME 模式下 sleep 完成、或 GENERATOR 模式下直接进入下一周期：
        # 更新下一周期的开始时间戳
        self._current_cycle_start_time = time.time()

        # 更新周期计数
        self.cycle_count += 1

        # 判断是否需要采样
        need_sample = self.cycle_count % self._sample_cycles == 0

        # 格式化时间字符串
        current_dt = datetime.fromtimestamp(self.sim_time)
        if self.config.time_format:
            time_str = current_dt.strftime(self.config.time_format)
        else:
            # 默认使用 ISO 格式
            time_str = current_dt.isoformat()

        return (self.cycle_count, need_sample, time_str, exec_ratio)

    def reset(self, cycle_count: int = 0) -> None:
        """
        重置时钟（重置周期计数）。

        Args:
            cycle_count: 重置到的周期计数，默认 0
        """
        self.cycle_count = cycle_count
        logger.info("Clock reset: cycle_count=%d, sim_time=%.3f", cycle_count, self.sim_time)

