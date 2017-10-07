from src.config import configurator, ConfigurationError, ConfigContainer


@configurator(path='plugins.weather')
def conf(config,
         default_city=1,
         openweathermap_appid="Moscow",
         ):
    return ConfigContainer({
        'default_city': default_city,
        'openweathermap_appid': openweathermap_appid,
    })
