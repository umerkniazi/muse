import os
import sys
if sys.platform == "win32":
    os.system("title Muse")
else:
    print("\33]0;Muse\a", end="", flush=True)

import json
try:
    import curses
except ImportError:
    if sys.platform.startswith("win"):
        print("Missing 'windows-curses'. Please run: pip install windows-curses")
        sys.exit(1)
    else:
        raise

import glob
import time
import difflib
import random
from music_player import MusicPlayer
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

DEFAULT_CONFIG = {
    "keybindings": {
        "quit": [":q"],
        "search": ["/"],
        "next": ["n", "KEY_RIGHT"],
        "prev": ["p", "KEY_LEFT"],
        "play_pause": [" "],
        "down": ["KEY_DOWN"],
        "up": ["KEY_UP"],
        "enter": ["KEY_ENTER", 10, 13],
        "add_folder": [":a"],
        "shuffle": ["s"],
        "repeat": ["r"]
    },
    "music_folder": "D:\\Music"
}

def load_config(path="config.json"):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
        for k in DEFAULT_CONFIG:
            if k not in config:
                config[k] = DEFAULT_CONFIG[k]
        return config
    return DEFAULT_CONFIG

def save_config(config, path="config.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def key_match(key, options, buffer=None):
    for opt in options:
        if isinstance(opt, int) and key == opt:
            return True
        if isinstance(opt, str):
            if opt.startswith("KEY_"):
                if hasattr(curses, opt) and key == getattr(curses, opt):
                    return True
            elif len(opt) == 1 and key == ord(opt):
                return True
            elif buffer is not None and buffer == opt:
                return True
    return False

def keybinding_helper_row(keybindings):
    mapping = {
        "up": "Up",
        "down": "Down",
        "enter": "Play",
        "play_pause": "Play/Pause",
        "next": "Next",
        "prev": "Prev",
        "shuffle": "Shuffle",
        "repeat": "Repeat",
        "search": "Search",
        "quit": "Quit (:q)"
    }
    order = ["up", "down", "enter", "play_pause", "next", "prev", "shuffle", "repeat", "search", "quit"]
    parts = []
    for k in order:
        if k in keybindings:
            keys = []
            for v in keybindings[k]:
                if isinstance(v, str):
                    if v.startswith("KEY_"):
                        keys.append(v.replace("KEY_", ""))
                    elif v == " ":
                        keys.append("SPACE")
                    elif v.startswith(":"):
                        keys.append(v)
                    else:
                        keys.append(v)
            if keys:
                keys_str = "/".join(keys)
                parts.append(f"{keys_str}: {mapping.get(k, k)}")
    return " | ".join(parts)

class CLI:
    def __init__(self, stdscr, config):
        self.player = MusicPlayer()
        self.stdscr = stdscr
        self.config = config
        self.keybindings = config["keybindings"]
        self.music_folder = config["music_folder"]
        self.playlist = []
        self.display_names = []
        self.durations = []
        self.current_index = None
        self.selected_index = 0
        self.scroll_offset = 0
        self.shuffle = False
        self.repeat = False
        self.last_top_bar = ""
        self.last_command_input = ""
        self.last_status = ""
        self.last_selected = -1
        self.last_display_names = []
        self.last_scroll_offset = -1

    def get_display_name_and_duration(self, filepath):
        try:
            audio = MP3(filepath, ID3=EasyID3)
            title = audio.get('title', [None])[0]
            artist = audio.get('artist', [None])[0]
            duration = int(audio.info.length)
            minutes = duration // 60
            seconds = duration % 60
            timestamp = f"{minutes:02}:{seconds:02}"
            if title and artist:
                name = f"{artist} - {title}"
            elif title:
                name = title
            elif artist:
                name = artist
            else:
                name = os.path.basename(filepath)
            return name, timestamp
        except Exception:
            return os.path.basename(filepath), "--:--"

    def display_menu(self, display_names=None, command_input="", force_redraw=False):
        max_y, max_x = self.stdscr.getmaxyx()
        max_songs = max_y - 4

        if not hasattr(self, 'colors_initialized'):
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
            self.colors_initialized = True

        now_playing = ""
        playback_pos = ""
        if (
            self.current_index is not None
            and self.playlist
            and 0 <= self.current_index < len(self.playlist)
        ):
            name = self.display_names[self.current_index]
            timestamp = self.durations[self.current_index]
            try:
                pos_seconds = int(self.player.get_pos())
            except Exception:
                pos_seconds = 0
            pos_min = pos_seconds // 60
            pos_sec = pos_seconds % 60
            playback_pos = f"{pos_min:02}:{pos_sec:02}"
            now_playing = f" | Now Playing: {name} [{playback_pos} / {timestamp}]"
        
        top_bar = f" Library{now_playing} | Shuffle: {'On' if self.shuffle else 'Off'} | Repeat: {'On' if self.repeat else 'Off'}"
        
        if top_bar != self.last_top_bar or force_redraw:
            self.stdscr.attron(curses.color_pair(1))
            self.stdscr.addstr(0, 0, top_bar[:max_x].ljust(max_x))
            self.stdscr.attroff(curses.color_pair(1))
            self.last_top_bar = top_bar

        if command_input != self.last_command_input or force_redraw:
            self.stdscr.addstr(max_y - 3, 0, command_input[:max_x - 1].ljust(max_x - 1))
            self.last_command_input = command_input

        if display_names is None:
            display_names = self.display_names

        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + max_songs:
            self.scroll_offset = self.selected_index - max_songs + 1

        need_song_redraw = (
            force_redraw or 
            display_names != self.last_display_names or 
            self.selected_index != self.last_selected or
            self.scroll_offset != self.last_scroll_offset
        )

        if need_song_redraw:
            for i in range(max_songs):
                self.stdscr.move(1 + i, 0)
                self.stdscr.clrtoeol()
            
            visible_names = display_names[self.scroll_offset:self.scroll_offset + max_songs]
            for i, song_name in enumerate(visible_names):
                idx = self.scroll_offset + i
                if idx == self.selected_index:
                    self.stdscr.attron(curses.color_pair(2))
                    self.stdscr.addstr(1 + i, 0, song_name[:max_x - 1].ljust(max_x - 1))
                    self.stdscr.attroff(curses.color_pair(2))
                else:
                    self.stdscr.addstr(1 + i, 0, song_name[:max_x - 1].ljust(max_x - 1))
            
            self.last_display_names = display_names[:]
            self.last_selected = self.selected_index
            self.last_scroll_offset = self.scroll_offset

        status = keybinding_helper_row(self.keybindings)
        if status != self.last_status or force_redraw:
            self.stdscr.addstr(max_y - 1, 0, status[:max_x - 1].ljust(max_x - 1))
            self.last_status = status

        self.stdscr.refresh()

    def load_playlist(self, path):
        songs = glob.glob(os.path.join(path, '*.mp3'))
        self.playlist = songs
        self.display_names = []
        self.durations = []
        if not os.path.exists(path):
            self.display_names = ["[Invalid folder: not found]"]
            self.durations = [""]
            self.playlist = []
            return
        if not songs:
            self.display_names = ["[No songs found in folder]"]
            self.durations = [""]
            self.playlist = []
            return
        for song in songs:
            name, timestamp = self.get_display_name_and_duration(song)
            self.display_names.append(name)
            self.durations.append(timestamp)

    def process_input(self):
        self.stdscr.nodelay(True)
        search_mode = False
        search_query = ""
        filtered_indices = None
        last_draw = 0
        redraw_interval = 0.1
        kb = self.keybindings
        command_mode = False
        command_buffer = ""
        quit_prompt = False
        
        self.display_menu(force_redraw=True)
        
        while True:
            now = time.time()
            need_redraw = now - last_draw > redraw_interval
            
            if need_redraw:
                if command_mode:
                    command_input = command_buffer
                elif quit_prompt:
                    command_input = "Quit? (y/n): "
                else:
                    command_input = f"/{search_query}" if search_mode else ""
                
                if search_mode:
                    if search_query:
                        query_lower = search_query.lower()
                        word_matches = [
                            name for name in self.display_names
                            if any(word == query_lower for word in name.lower().split())
                        ]
                        exact_matches = [
                            name for name in self.display_names
                            if name.lower() == query_lower and name not in word_matches
                        ]
                        fuzzy_matches = difflib.get_close_matches(
                            search_query, self.display_names, n=len(self.display_names), cutoff=0.3
                        )
                        substring_matches = [
                            name for name in self.display_names
                            if query_lower in name.lower()
                            and name not in word_matches
                            and name not in exact_matches
                            and name not in fuzzy_matches
                        ]
                        all_matches = word_matches + exact_matches + fuzzy_matches + substring_matches
                        seen = set()
                        ordered_matches = []
                        for name in all_matches:
                            if name not in seen:
                                ordered_matches.append(name)
                                seen.add(name)
                        filtered_indices = [self.display_names.index(m) for m in ordered_matches]
                    else:
                        filtered_indices = None
                    display_names = [self.display_names[i] for i in filtered_indices] if filtered_indices else self.display_names
                    self.display_menu(display_names, command_input)
                else:
                    self.display_menu(command_input=command_input)
                last_draw = now
            
            key = self.stdscr.getch()
            if key == -1:
                time.sleep(0.01)
                continue
                
            force_redraw = True
            
            if quit_prompt:
                if key in (ord('y'), ord('Y')):
                    break
                elif key in (ord('n'), ord('N')):
                    quit_prompt = False
                continue
            if command_mode:
                if key in (27,):
                    command_mode = False
                    command_buffer = ""
                elif key in (10, 13):
                    if command_buffer.startswith(":a "):
                        folder = command_buffer[3:].strip()
                        if folder and os.path.exists(folder):
                            self.music_folder = folder
                            self.config["music_folder"] = folder
                            save_config(self.config)
                            self.load_playlist(self.music_folder)
                        else:
                            self.display_names = ["[Invalid folder: not found]"]
                            self.durations = [""]
                            self.playlist = []
                    elif command_buffer.strip() == ":q":
                        break
                    command_mode = False
                    command_buffer = ""
                elif key in (curses.KEY_BACKSPACE, 127, 8):
                    command_buffer = command_buffer[:-1]
                elif 32 <= key <= 126:
                    command_buffer += chr(key)
                continue
            if search_mode:
                if key_match(key, kb["quit"]):
                    search_mode = False
                    search_query = ""
                    filtered_indices = None
                    self.selected_index = 0
                elif key_match(key, kb["enter"]):
                    if filtered_indices is not None and filtered_indices:
                        idx = filtered_indices[self.selected_index]
                        self.current_index = idx
                        self.player.load_song(self.playlist[idx])
                        self.player.play()
                    elif self.playlist:
                        self.current_index = self.selected_index
                        self.player.load_song(self.playlist[self.current_index])
                        self.player.play()
                    search_mode = False
                    search_query = ""
                    filtered_indices = None
                    self.selected_index = 0
                elif key in (curses.KEY_BACKSPACE, 127, 8):
                    search_query = search_query[:-1]
                elif 32 <= key <= 126:
                    search_query += chr(key)
                self.selected_index = 0
                continue
            if key == ord('q'):
                quit_prompt = True
                continue
            elif key_match(key, kb["quit"], buffer=command_buffer if command_buffer == ":q" else None):
                break
            elif key_match(key, kb.get("shuffle", [])):
                self.shuffle = not self.shuffle
                continue
            elif key_match(key, kb.get("repeat", [])):
                self.repeat = not self.repeat
                continue
            elif key_match(key, kb["search"]):
                search_mode = True
                search_query = ""
                filtered_indices = None
                continue
            elif key_match(key, kb["next"]):
                self.next_song()
            elif key_match(key, kb["prev"]):
                self.prev_song()
            elif key_match(key, kb["play_pause"]):
                self.toggle_play_pause()
            elif key_match(key, kb["down"]):
                if filtered_indices is not None:
                    if self.selected_index < len(filtered_indices) - 1:
                        self.selected_index += 1
                else:
                    if self.selected_index < len(self.playlist) - 1:
                        self.selected_index += 1
            elif key_match(key, kb["up"]):
                if self.selected_index > 0:
                    self.selected_index -= 1
            elif key_match(key, kb["enter"]):
                if filtered_indices is not None and filtered_indices:
                    idx = filtered_indices[self.selected_index]
                    self.current_index = idx
                    self.player.load_song(self.playlist[idx])
                    self.player.play()
                elif self.playlist:
                    self.current_index = self.selected_index
                    self.player.load_song(self.playlist[self.current_index])
                    self.player.play()
            elif key == ord(':'):
                command_mode = True
                command_buffer = ":"

    def next_song(self):
        if self.playlist:
            if self.shuffle:
                self.current_index = random.randint(0, len(self.playlist) - 1)
            else:
                if self.current_index is None:
                    self.current_index = 0
                else:
                    self.current_index = (self.current_index + 1) % len(self.playlist)
            self.selected_index = self.current_index
            song = self.playlist[self.current_index]
            self.player.load_song(song)
            self.player.play()

    def prev_song(self):
        if self.playlist:
            if self.shuffle:
                self.current_index = random.randint(0, len(self.playlist) - 1)
            else:
                if self.current_index is None:
                    self.current_index = 0
                else:
                    self.current_index = (self.current_index - 1) % len(self.playlist)
            self.selected_index = self.current_index
            song = self.playlist[self.current_index]
            self.player.load_song(song)
            self.player.play()

    def toggle_play_pause(self):
        if self.player.playing:
            self.player.pause()
        else:
            self.player.unpause()

def main(stdscr):
    config = load_config()
    curses.curs_set(0)
    stdscr.keypad(True)
    cli = CLI(stdscr, config)
    cli.load_playlist(cli.music_folder)
    cli.process_input()

curses.wrapper(main)