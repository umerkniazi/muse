def keybinding_helper_row(keybindings):
    mapping = {
        "up": "↑",
        "down": "↓",
        "enter": "Play",
        "play_pause": "Pause/Play",
        "next": "Next",
        "prev": "Prev",
        "shuffle": "Shuffle",
        "repeat": "Repeat",
        "search": "Search",
        "quit": "Quit",
        "volume_up": "Vol+",
        "volume_down": "Vol-",
        "queue": "Queue"
    }
    order = [
        "up", "down", "enter", "play_pause", "next", "prev",
        "shuffle", "repeat", "search", "volume_up", "volume_down", "queue", "quit"
    ]
    parts = []
    for k in order:
        if k in keybindings:
            keys = []
            for v in keybindings[k]:
                if isinstance(v, str):
                    if v.startswith("KEY_"):
                        keys.append(v.replace("KEY_", "").replace("_", "").title())
                    elif v == " ":
                        keys.append("Space")
                    elif v.startswith(":"):
                        continue
                    else:
                        keys.append(v.upper())
                else:
                    keys.append(str(v))
            if keys:
                keys_str = keys[0]
                label = mapping.get(k, k)
                parts.append(f"{keys_str}:{label}")
    return "  ".join(parts)

def help_text(keybindings):
    mapping = {
        "up": "Move up",
        "down": "Move down",
        "enter": "Play selected",
        "play_pause": "Play/Pause",
        "next": "Next track",
        "prev": "Previous track",
        "shuffle": "Toggle shuffle",
        "repeat": "Toggle repeat",
        "search": "Search",
        "quit": "Quit",
        "volume_up": "Increase volume",
        "volume_down": "Decrease volume",
        "fadeout": "Fade out",
        "queue": "Add to queue",
        "seek_forward": "Seek forward",
        "seek_backward": "Seek backward",
        "clear_queue": "Clear queue",
        "remove_queue": "Remove from queue",
        "add_folder": "Add folder"
    }
    lines = ["Muse Help - Keybindings:"]
    for k, v in keybindings.items():
        keys = []
        for key in v:
            if isinstance(key, str):
                if key.startswith("KEY_"):
                    keys.append(key.replace("KEY_", "").replace("_", " ").title())
                elif key == " ":
                    keys.append("Space")
                else:
                    keys.append(key)
            else:
                keys.append(str(key))
        desc = mapping.get(k, k)
        lines.append(f"{'/'.join(keys)}: {desc}")
    lines.append("")
    lines.append("Other commands:")
    lines.append(":a <folder> - Add/change music folder")
    lines.append(":refresh - Rescan music folder and update library")
    lines.append(":clear - Clear queue")
    lines.append(":remove <n> - Remove nth song from queue")
    lines.append(":q - Quit Muse")
    lines.append(":v or :version - Show version")
    lines.append(":help - Show this help")
    return "\n".join(lines)