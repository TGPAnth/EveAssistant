from src.config import configurator, ConfigurationError, ConfigContainer


@configurator(path='communicators.telegram')
def conf(config,
         bot_token=None,
         ):
    return ConfigContainer({
        'bot_token': bot_token,
    })
