import logging

from src.config import configurator, check_file_path, ConfigurationError, ConfigContainer

levels = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}


@configurator(path='core.logger')
def conf(config,
         console_level='WARNING',
         file_level='DEBUG',
         max_file_size=1024 * 1024 * 10,
         entry_log_date=True,
         entry_log_task=True,
         entry_log_module=True,
         log_filename='runtime.log',
         error_filename='error.log',
         ):
    if log_filename and not check_file_path(log_filename, 'a'):
        raise ConfigurationError('Invalid file path in option log_filename')

    if error_filename and not check_file_path(error_filename, 'a'):
        raise ConfigurationError('Invalid file path in option error_filename')

    return ConfigContainer({
        'console_level': levels[console_level.upper()],
        'file_level': levels[file_level.upper()],
        'max_file_size': int(max_file_size),
        'entry_log_date': bool(int(entry_log_date)),
        'entry_log_task': bool(int(entry_log_task)),
        'entry_log_module': bool(int(entry_log_module)),
        'log_filename': log_filename,
        'error_filename': error_filename,
    })
