from src.config import configurator, ConfigurationError, ConfigContainer


@configurator(path='communicators.voice')
def conf(config,
         # sample=None,
         ):
    return ConfigContainer({
        # 'sample': sample,
    })
