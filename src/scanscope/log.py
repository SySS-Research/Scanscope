import logging
from typing import Any

grey = "\x1b[38m"
yellow = "\x1b[33m"
green = "\x1b[32m"
red = "\x1b[31m"
bold_red = "\x1b[31;1m"
reset = "\x1b[0m"

# add success level
logging.SUCCESS = 25  # type: ignore[attr-defined]  # between WARNING and INFO
logging.addLevelName(logging.SUCCESS, "SUCCESS")  # type: ignore[attr-defined]


def color_map(_format: str) -> dict[int, str]:
    formats = {
        logging.DEBUG: grey + _format + reset,
        logging.INFO: _format,
        logging.WARNING: yellow + _format + reset,
        logging.ERROR: red + _format + reset,
        logging.CRITICAL: bold_red + _format + reset,
        logging.SUCCESS: green + _format + reset,  # type: ignore[attr-defined]
    }
    return formats


class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors"""

    fields = [
        #  '%(asctime)s',
        "%(levelname)s",
        "%(message)s",
    ]
    _format = " - ".join(fields)

    FORMATS = color_map(_format)

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, "%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class CustomFormatterDebug(CustomFormatter):
    fields = ["%(asctime)s", "%(filename)s:%(lineno)d", "%(levelname)s", "%(message)s"]
    _format = " - ".join(fields)
    FORMATS = color_map(_format)


def init_logging(loglevel: str | int = logging.INFO, logfile: str | None = None) -> None:
    # create logger
    logger = logging.getLogger()
    logger.setLevel(loglevel)

    # add success level
    def success(self: logging.Logger, message: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.SUCCESS, message, args, **kwargs)  # type: ignore[attr-defined]

    logging.Logger.success = success  # type: ignore[attr-defined]

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(loglevel)

    # create formatter and add it to the handlers
    if loglevel in ["DEBUG", logging.DEBUG]:
        formatter = CustomFormatterDebug()
    else:
        formatter = CustomFormatter()
    ch.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(ch)

    if logfile:
        # create file handler which logs even debug messages
        fh = logging.FileHandler(logfile)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
