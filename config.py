import os
import json

DEFAULT_CONFIG = {
    "keybindings": {
        "quit": [":q"],
        "search": ["/"],
        "next": ["n"],
        "prev": ["p"],
        "play_pause": [" "],
        "down": ["KEY_DOWN"],
        "up": ["KEY_UP"],
        "enter": ["KEY_ENTER", 10, 13],
        "add_folder": [":a"],
        "shuffle": ["s"],
        "repeat": ["r"],
        "volume_up": ["+", "="],
        "volume_down": ["-"],
        "fadeout": ["f"],
        "queue": ["e"],
        "seek_forward": ["KEY_RIGHT"],
        "seek_backward": ["KEY_LEFT"],
        "clear_queue": [":clear"],
        "remove_queue": [":remove"]
    },
    "music_folder": "",
    "seek_seconds": 5,
    "shuffle": False,
    "repeat": False,
    "volume": 1.0,
    "default_view": 1
}

def load_config(path="config.json"):
    path = os.path.expanduser(path)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
        for k in DEFAULT_CONFIG:
            if k not in config:
                config[k] = DEFAULT_CONFIG[k]
        for k in DEFAULT_CONFIG["keybindings"]:
            if k not in config["keybindings"]:
                config["keybindings"][k] = DEFAULT_CONFIG["keybindings"][k]
        if "music_folder" in config:
            config["music_folder"] = os.path.expanduser(config["music_folder"])
        return config
    return DEFAULT_CONFIG.copy()

def save_config(config, path="config.json"):
    path = os.path.expanduser(path)
    config_to_save = config.copy()
    if "music_folder" in config_to_save:
        home = os.path.expanduser("~")
        if config_to_save["music_folder"].startswith(home):
            config_to_save["music_folder"] = config_to_save["music_folder"].replace(home, "~", 1)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config_to_save, f, indent=2)