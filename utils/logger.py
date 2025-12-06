"""
日志模块（data_next）

基于 mock_server 中的日志实现，提供多等级文件日志和基础的 Windows 兼容处理。
"""

import logging
import os
from logging.handlers import RotatingFileHandler


class SafeRotatingFileHandler(RotatingFileHandler):
    """
    安全的日志轮转处理器

    在 Windows 上，如果日志文件被其他进程占用，轮转可能会失败。
    这个类会捕获轮转异常，避免程序崩溃。
    """

    def doRollover(self) -> None:
        """
        执行日志轮转。

        如果轮转失败（例如文件被占用），会捕获异常并继续使用当前日志文件。
        """
        try:
            super().doRollover()
        except (PermissionError, OSError):
            # 在 Windows 上，如果文件被其他进程占用，轮转会失败。
            # 这种情况下，我们忽略错误，继续使用当前日志文件。
            # 这样可以避免程序崩溃，但日志文件可能会继续增长。
            pass
        except Exception:
            # 其他异常也忽略，避免影响程序运行。
            pass


class Logger:
    """
    日志管理器。

    - 按等级输出到不同日志文件（debug/info/warning/error）。
    - 统一 logger 名称前缀为 "data_next"。
    """

    def __init__(self, log_dir: str = "logs", name: str = "data_next") -> None:
        """
        初始化日志管理器。

        Args:
            log_dir: 日志输出目录，默认 "logs"。
            name: 日志名称前缀，默认 "data_next"。
        """
        self.log_dir = log_dir
        self.name = name

        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)

        # 创建 logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 避免重复添加 handler
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self) -> None:
        """设置不同级别的日志处理器。"""
        # DEBUG 级别日志
        debug_handler = SafeRotatingFileHandler(
            os.path.join(self.log_dir, f"{self.name}_debug.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
        debug_handler.setFormatter(debug_formatter)

        # INFO 级别日志
        info_handler = SafeRotatingFileHandler(
            os.path.join(self.log_dir, f"{self.name}_info.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        info_handler.setLevel(logging.INFO)
        info_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        info_handler.setFormatter(info_formatter)

        # WARNING 级别日志
        warning_handler = SafeRotatingFileHandler(
            os.path.join(self.log_dir, f"{self.name}_warning.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        warning_handler.setLevel(logging.WARNING)
        warning_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        warning_handler.setFormatter(warning_formatter)

        # ERROR 级别日志
        error_handler = SafeRotatingFileHandler(
            os.path.join(self.log_dir, f"{self.name}_error.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
        error_handler.setFormatter(error_formatter)

        # 添加所有 handler
        self.logger.addHandler(debug_handler)
        self.logger.addHandler(info_handler)
        self.logger.addHandler(warning_handler)
        self.logger.addHandler(error_handler)

    def get_logger(self) -> logging.Logger:
        """获取底层 logger 实例。"""
        return self.logger

    def close(self) -> None:
        """
        关闭所有日志处理器。

        在程序退出前调用，确保日志文件被正确关闭，避免 Windows 上的文件占用问题。
        """
        # 先刷新所有日志，确保日志都被写入
        for handler in self.logger.handlers[:]:
            try:
                handler.flush()
            except Exception:
                pass

        # 再关闭所有 handler
        handlers_to_close = list(self.logger.handlers)
        for handler in handlers_to_close:
            try:
                if hasattr(handler, "stream") and handler.stream:
                    try:
                        handler.stream.close()
                    except Exception:
                        pass
                handler.close()
                self.logger.removeHandler(handler)
            except Exception:
                # 忽略关闭时的错误，避免影响程序退出
                pass


_LOGGER_INSTANCE: Logger | None = None


def get_logger(log_dir: str = "logs", name: str = "data_next") -> logging.Logger:
    """
    获取全局 logger 实例（单例）。

    Args:
        log_dir: 日志输出目录。
        name: 日志名称前缀。
    """
    global _LOGGER_INSTANCE
    if _LOGGER_INSTANCE is None:
        _LOGGER_INSTANCE = Logger(log_dir, name)
    return _LOGGER_INSTANCE.get_logger()


def close_logger() -> None:
    """
    关闭全局 logger 实例。

    在长时间运行的进程退出前调用，确保日志文件句柄释放。
    """
    global _LOGGER_INSTANCE
    if _LOGGER_INSTANCE is not None:
        _LOGGER_INSTANCE.close()
        _LOGGER_INSTANCE = None


