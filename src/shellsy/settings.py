import json
import os
from appdirs import user_data_dir
from . import __author__ as author, __version__ as version, __name__ as name

data_dir = user_data_dir(name, author, version, True)
history = os.path.join(data_dir, "history.log")


class SettingsFile(dict):
    """
    Creates a json settings file at path
    """

    def __init__(self, path: str, default: dict = {}):
        """
        :param path: the path to the settings file
        """
        self.path = path
        super().__init__(default)
        try:
            self.load()
        except OSError:
            self.save()

    def load(self):
        with open(self.path) as f:
            self.update(json.loads(f.read()))

    def save(self):
        with open(self.path, "w") as f:
            f.write(json.dumps(self, indent=2))


_settings = None


def init():
    global _settings
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    if not _settings:
        _settings = SettingsFile(os.path.join(data_dir, "settings.json"), {})


def get_setting(name, default=None):
    _settings.load()
    return _settings.get(name, default)


def set_setting(name, val):
    _settings[name] = val
    _settings.save()


def settings():
    return _settings
