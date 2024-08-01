import json
import os
import sys

from pathlib import Path


data_dir = Path.home() / ".shellsy"
history = os.path.join(data_dir, "history.log")
plugin_dir = os.path.join(data_dir, "plugins")


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
    os.environ.setdefault("SHELLSYPATH", plugin_dir)
    for p in os.environ.get("SHELLSYPATH").split(";"):
        sys.path.append(p)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    if not os.path.exists(plugin_dir):
        os.makedirs(plugin_dir)
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
