"""Preference file helpers."""

import os
from json import dumps, loads


PREFERENCES_FILE = "./fd_preferences.json"


def load_preferences(defaults=None, filename=PREFERENCES_FILE):
    """Load preferences from disk, creating the file from defaults if needed."""
    if os.path.exists(filename):
        with open(filename, "rt", encoding="utf-8") as file_descriptor:
            return loads(file_descriptor.read())

    preferences = defaults.copy() if defaults else {}
    save_preferences(preferences, filename)
    return preferences


def save_preferences(preferences, filename=PREFERENCES_FILE):
    """Write preferences to disk."""
    with open(filename, "wt", encoding="utf-8") as file_descriptor:
        file_descriptor.write(dumps(preferences, indent=4))
