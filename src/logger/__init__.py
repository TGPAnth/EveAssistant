# -*- coding: utf-8 -*-
import os
import logging

COLORS = {
    "critical": '\x1b[0;31m',  # red
    "error": '\x1b[0;31m',  # red
    "warning": '\x1b[0;33m',  # yellow
    "info": '\x1b[0;34m',  # blue
    "debug": '\x1b[2;49;37m',  # light gray

    "reset": '\x1b[0m',  # default
    # "module": '\x1b[2;49;37m',  # gray
}

FMT_DEFAULT = None
FMT_TIME = "%H:%M:%S"


def color(name="reset"):
    if os.environ.get("SHELL", "unknown").endswith("sh"):
        return COLORS.get(name.lower(), "")
    return ""


class LogFormatter(logging.Formatter):
    def __init__(self,
                 log_date=True,
                 log_task=True,
                 log_module=True,
                 is_file_log=False):

        self.log_task = log_task

        if log_date:
            self._datefmt = FMT_DEFAULT
            date_token = '%(asctime)-25s'
        else:
            self._datefmt = FMT_TIME
            date_token = '%(asctime)-8s'

        if log_module:
            name_token = "[%(name)s] "
        else:
            name_token = ""

        process_token = "%(processName)-10s - "

        self.use_colors = not is_file_log
        if self.use_colors:
            # may use colors
            format = date_token + ' - '
            format += '%(levelcolor)-s' + '%(levelname)-8s' + color() + ' - '
            format += process_token
            format += color('module') + name_token + color()
            format += '%(message)s'
        else:
            # dont use colors
            format = date_token + ' - '
            format += '%(levelname)-8s - '
            format += process_token
            format += name_token
            format += '%(message)s'

        super(LogFormatter, self).__init__(format)

    def format(self, record):
        record.levelcolor = ""
        if self.use_colors:
            record.levelcolor = color(record.levelname)
        return super(LogFormatter, self).format(record)

    def formatTime(self, record, datefmt=None):
        if datefmt is None:
            datefmt = self._datefmt
        return super(LogFormatter, self).formatTime(record, datefmt)


def logger_init(config):
    formatter_kwargs = {
        'log_date': config.entry_log_date,
        'log_task': config.entry_log_task,
        'log_module': config.entry_log_module,
        'is_file_log': False
    }

    console_formatter = LogFormatter(**formatter_kwargs)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(config.console_level)

    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)


def get_logger(name):
    """Get logger instance with specified name
    @param name (str) - logger name"""
    # TODO: for now this is just a stub for a standard Python logsystem
    log = logging.getLogger(name)
    return log
