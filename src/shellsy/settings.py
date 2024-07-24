import json
import os
from appdirs import user_data_dir


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


data_dir = user_data_dir("shellsy", "ken-morel")
if not os.path.exists(data_dir):
    os.mkdir(data_dir)

settings = SettingsFile(os.path.join(data_dir, "settings.json"), {

})
history = os.path.join(data_dir, "history.log")
