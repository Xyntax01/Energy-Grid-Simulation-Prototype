import logging
import logging.config
import logging.handlers
import os
from typing import Any, Optional


def valid_log_threshold(threshold: Any) -> Optional[int]:
    """Check if a threshold is valid and return its level if it is.

    Args:
        threshold: either an integer or a string denoting a standard logging level."""
    if threshold in logging._nameToLevel:
        return logging._nameToLevel[threshold]
    if isinstance(threshold, int) and 0 < threshold <= 50:
        return threshold
    return None


class LoggerFactory:
    def __init__(
        self, logfile: Optional[str] = None, default_log_threshold: Optional[int] = None
    ):
        self.logfile = logfile
        default_log_threshold = valid_log_threshold(default_log_threshold)
        if default_log_threshold is None:
            self.default_log_threshold = logging.INFO
        else:
            self.default_log_threshold = default_log_threshold

        self.formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        if self.logfile is not None and not os.path.exists(
            os.path.dirname(os.path.abspath(self.logfile))
        ):
            raise FileNotFoundError(f"Could not open log file at path {self.logfile}")

    def get_logger(
        self, logger_name: str, log_threshold: Optional[int] = None
    ) -> logging.Logger:
        log_threshold = valid_log_threshold(log_threshold)
        if log_threshold is None:
            log_threshold = self.default_log_threshold

        logger = logging.getLogger(logger_name)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.formatter)

        logger.propagate = False
        logger.addHandler(console_handler)

        logger.setLevel(log_threshold)
        if self.logfile is not None:
            file_handler = logging.handlers.RotatingFileHandler(
                self.logfile, maxBytes=100000, backupCount=2
            )
            file_handler.setFormatter(self.formatter)

            logger.addHandler(file_handler)
        else:
            logger.warning("Can't write to logfile as none was configured!")

        return logger
