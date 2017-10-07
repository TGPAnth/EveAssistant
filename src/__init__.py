"""
Modules stucture

Activator - check that this plugin should be activated
Requester - gwts request and processed it, returns response `future` object 
Responser - returns data to user


"""

from src.core import Core

if __name__ == "__main__":
    config_path = '../config.yaml'
    core = Core(config_path)
    core.run()
