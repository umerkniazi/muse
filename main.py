import os
import sys
import glob
import time
import random
import json
from music_player import MusicPlayer
from mutagen import File
from config import load_config, save_config
from utils import key_match, search, get_folder_hash
from ui import keybinding_helper_row, help_text

APP_VERSION = "1.1.2"

if len(sys.argv) > 1 and sys.argv[1] in ("-v", "--version"):
    print(APP_VERSION)
    sys.exit(0)

if sys.platform == "win32":
    os.system(f"title Muse {APP_VERSION}")
else:
    print(f"\33]0;Muse {APP_VERSION}\a", end="", flush=True)

try:
    import curses
except ImportError:
    if sys.platform.startswith("win"):
        print("Missing 'windows-curses'. Please run: pip install windows-curses")
        sys.exit(1)
    else:
        raise

class CLI:
    def __init__(self, stdscr, config):
        self.player = MusicPlayer()
        self.stdscr = stdscr
        self.config = config
        self.keybindings = config.get("keybindings", {})
        self.music_folder = os.path.expanduser(config.get("music_folder", ""))
        self.seek_seconds = config.get("seek_seconds", 5)
        self.playlist = []
        self.display_names = []
        self.durations = []
        self.current_index = None
        self.current_song_path = None
        self.selected_index = 0
        self.scroll_offset = 0
        self.shuffle = config.get("shuffle", False)
        self.repeat = config.get("repeat", False)
        self.last_top_bar = ""
        self.last_command_input = ""
        self.last_status = ""
        self.last_selected = -1
        self.last_display_names = []
        self.last_scroll_offset = -1
        self.volume = config.get("volume", 1.0)
        self.player.set_volume(self.volume)
        self.view_mode = config.get("default_view", 1)
        self.queue_list = []
        self.version_message = ""
        self.albums = {}
        self.album_names = []
        self.album_view_selected = 0
        self.queue_index = 0
        self.album_songs_scroll = 0
        self.album_song_selected = 0
        self.search_selected = 0
        self.album_column = 0
        self.error_message = ""

    def get_display_name_and_duration(self, filepath):
        try:
            audio = File(filepath)
            title = ""
            artist = ""
            album = ""
            duration = 0
            if audio:
                duration = int(audio.info.length)
                if audio.tags:
                    title = (
                        audio.tags.get('TIT2', [""])[0]
                        if 'TIT2' in audio.tags else
                        audio.tags.get('title', [""])[0]
                    )
                    artist = (
                        audio.tags.get('TPE1', [""])[0]
                        if 'TPE1' in audio.tags else
                        audio.tags.get('artist', [""])[0]
                    )
                    album = (
                        audio.tags.get('TALB', [""])[0]
                        if 'TALB' in audio.tags else
                        audio.tags.get('album', [""])[0]
                    )
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
                name = os.path.splitext(os.path.basename(filepath))[0]
            return name, timestamp, album
        except Exception:
            return os.path.splitext(os.path.basename(filepath))[0], "--:--", None

    def get_current_names(self):
        if self.view_mode == 2:
            return [self.get_display_name_and_duration(song)[0] for song in self.queue_list]
        elif self.view_mode == 3:
            selected_album = self.album_names[self.album_view_selected] if self.album_names else None
            if selected_album:
                return [self.get_display_name_and_duration(song)[0] for song in self.albums[selected_album]]
            return []
        else:
            return self.display_names

    def get_current_songs(self):
        if self.view_mode == 2:
            return self.queue_list
        elif self.view_mode == 3:
            selected_album = self.album_names[self.album_view_selected] if self.album_names else None
            if selected_album:
                return self.albums[selected_album]
            return []
        else:
            return self.playlist

    def display_menu(self, display_names=None, command_input="", force_redraw=False, search_mode=False, filtered_indices=None, search_selected=0):
        max_y, max_x = self.stdscr.getmaxyx()
        max_songs = max(0, max_y - 4)
        if not hasattr(self, 'colors_initialized'):
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
            self.colors_initialized = True
        now_playing = ""
        playback_pos = ""
        if self.current_song_path and self.current_song_path in self.playlist:
            song_index = self.playlist.index(self.current_song_path)
            name = self.display_names[song_index]
            timestamp = self.durations[song_index]
            try:
                pos_seconds = int(self.player.get_pos())
            except Exception:
                pos_seconds = 0
            pos_min = pos_seconds // 60
            pos_sec = pos_seconds % 60
            playback_pos = f"{pos_min:02}:{pos_sec:02}"
            status_icon = "PAUSED" if not self.player.playing else "PLAYING"
            now_playing = f" | {status_icon} {name} [{playback_pos}/{timestamp}] | Vol:{int(self.player.get_volume()*100)}%"
        if self.view_mode == 3:
            view_label = "Albums"
        elif self.view_mode == 2:
            view_label = f"Queue ({len(self.queue_list)})"
        else:
            view_label = f"Library ({len(self.playlist)})"
        shuffle_icon = "ON" if self.shuffle else "OFF"
        repeat_icon = "ON" if self.repeat else "OFF"
        top_bar = f" {view_label}{now_playing} | Shuffle:{shuffle_icon} | Repeat:{repeat_icon}"
        if top_bar != self.last_top_bar or force_redraw:
            self.stdscr.attron(curses.color_pair(1))
            try:
                self.stdscr.addstr(0, 0, top_bar[:max_x].ljust(max_x))
            except curses.error:
                pass
            self.stdscr.attroff(curses.color_pair(1))
            self.last_top_bar = top_bar
        if self.version_message:
            self.stdscr.attron(curses.color_pair(3))
            try:
                self.stdscr.addstr(max_y - 3, 0, f"Muse v{self.version_message} - Press any key to continue".ljust(max_x))
            except curses.error:
                pass
            self.stdscr.attroff(curses.color_pair(3))
        elif command_input != self.last_command_input or force_redraw:
            try:
                self.stdscr.addstr(max_y - 3, 0, command_input[:max_x].ljust(max_x))
            except curses.error:
                pass
            self.last_command_input = command_input
        if self.error_message:
            self.stdscr.attron(curses.color_pair(3))
            try:
                self.stdscr.addstr(max_y - 2, 0, f"Error: {self.error_message}".ljust(max_x))
            except curses.error:
                pass
            self.stdscr.attroff(curses.color_pair(3))
        else:
            try:
                self.stdscr.addstr(max_y - 2, 0, "".ljust(max_x))
            except curses.error:
                pass
        current_names = display_names if display_names is not None else self.get_current_names()
        selected_index = self.selected_index
        if search_mode and filtered_indices is not None:
            filtered_names = [current_names[i] for i in filtered_indices if i < len(current_names)]
            selected_index = search_selected
            if selected_index < self.scroll_offset:
                self.scroll_offset = selected_index
            elif selected_index >= self.scroll_offset + max_songs:
                self.scroll_offset = selected_index - max_songs + 1
            for i in range(max_songs):
                try:
                    self.stdscr.move(1 + i, 0)
                    self.stdscr.clrtoeol()
                except curses.error:
                    pass
            visible_names = filtered_names[self.scroll_offset:self.scroll_offset + max_songs]
            for i, name in enumerate(visible_names):
                idx = self.scroll_offset + i
                try:
                    if idx == selected_index:
                        self.stdscr.attron(curses.color_pair(2))
                        self.stdscr.addstr(1 + i, 0, name[:max_x].ljust(max_x))
                        self.stdscr.attroff(curses.color_pair(2))
                    else:
                        self.stdscr.addstr(1 + i, 0, name[:max_x].ljust(max_x))
                except curses.error:
                    pass
            self.last_display_names = filtered_names[:]
            self.last_selected = selected_index
            self.last_scroll_offset = self.scroll_offset
        elif self.view_mode == 3:
            left_width = max_x // 2
            right_width = max_x - left_width
            album_names = self.album_names
            selected_index = self.album_view_selected
            selected_album = album_names[selected_index] if album_names else None
            album_songs = []
            album_song_names = []
            if selected_album:
                for song in self.albums[selected_album]:
                    name, timestamp, _ = self.get_display_name_and_duration(song)
                    album_songs.append(song)
                    album_song_names.append(f"{name} [{timestamp}]")
            if self.album_column == 0:
                if selected_index < self.scroll_offset:
                    self.scroll_offset = selected_index
                elif selected_index >= self.scroll_offset + max_songs:
                    self.scroll_offset = selected_index - max_songs + 1
            else:
                if self.album_song_selected < self.album_songs_scroll:
                    self.album_songs_scroll = self.album_song_selected
                elif self.album_song_selected >= self.album_songs_scroll + max_songs:
                    self.album_songs_scroll = self.album_song_selected - max_songs + 1
            for i in range(max_songs):
                try:
                    self.stdscr.move(1 + i, 0)
                    self.stdscr.clrtoeol()
                except curses.error:
                    pass
                idx = self.scroll_offset + i
                if idx < len(album_names):
                    album_track_count = len(self.albums[album_names[idx]])
                    track_label = "track" if album_track_count == 1 else "tracks"
                    album_text = f"Album: {album_names[idx]} ({album_track_count} {track_label})"
                    try:
                        if idx == selected_index and self.album_column == 0:
                            self.stdscr.attron(curses.color_pair(2))
                            self.stdscr.addstr(1 + i, 0, album_text[:left_width].ljust(left_width))
                            self.stdscr.attroff(curses.color_pair(2))
                        else:
                            self.stdscr.addstr(1 + i, 0, album_text[:left_width].ljust(left_width))
                    except curses.error:
                        pass
            for i in range(max_songs):
                song_idx = self.album_songs_scroll + i
                if song_idx < len(album_song_names):
                    song_text = f"{song_idx + 1:2}. {album_song_names[song_idx]}"
                    try:
                        if song_idx == self.album_song_selected and self.album_column == 1:
                            self.stdscr.attron(curses.color_pair(2))
                            self.stdscr.addstr(1 + i, left_width, song_text[:right_width].ljust(right_width))
                            self.stdscr.attroff(curses.color_pair(2))
                        else:
                            self.stdscr.addstr(1 + i, left_width, song_text[:right_width].ljust(right_width))
                    except curses.error:
                        pass
            self.last_display_names = album_names[:]
            self.last_selected = selected_index
            self.last_scroll_offset = self.scroll_offset
        else:
            if selected_index < self.scroll_offset:
                self.scroll_offset = selected_index
            elif selected_index >= self.scroll_offset + max_songs:
                self.scroll_offset = selected_index - max_songs + 1
            need_song_redraw = (
                force_redraw or
                current_names != self.last_display_names or
                selected_index != self.last_selected or
                self.scroll_offset != self.last_scroll_offset
            )
            if need_song_redraw:
                for i in range(max_songs):
                    try:
                        self.stdscr.move(1 + i, 0)
                        self.stdscr.clrtoeol()
                    except curses.error:
                        pass
                visible_names = current_names[self.scroll_offset:self.scroll_offset + max_songs]
                current_songs = self.get_current_songs()
                for i, name in enumerate(visible_names):
                    idx = self.scroll_offset + i
                    if self.view_mode == 1:
                        display_text = f"{idx + 1:3}. {name}"
                        if idx < len(self.durations):
                            display_text += f" [{self.durations[idx]}]"
                    else:
                        display_text = f"{idx + 1:2}. {name}"
                    try:
                        if idx == selected_index:
                            self.stdscr.attron(curses.color_pair(2))
                            self.stdscr.addstr(1 + i, 0, display_text[:max_x].ljust(max_x))
                            self.stdscr.attroff(curses.color_pair(2))
                        else:
                            if idx < len(current_songs) and current_songs[idx] == self.current_song_path:
                                self.stdscr.attron(curses.color_pair(3))
                                self.stdscr.addstr(1 + i, 0, display_text[:max_x].ljust(max_x))
                                self.stdscr.attroff(curses.color_pair(3))
                            else:
                                self.stdscr.addstr(1 + i, 0, display_text[:max_x].ljust(max_x))
                    except curses.error:
                        pass
                self.last_display_names = current_names[:]
                self.last_selected = selected_index
                self.last_scroll_offset = self.scroll_offset
        status = keybinding_helper_row(self.keybindings)
        status += " | 1:Library 2:Queue 3:Albums"
        if status != self.last_status or force_redraw:
            try:
                self.stdscr.addstr(max_y - 1, 0, status[:max_x].ljust(max_x))
            except curses.error:
                pass
            self.last_status = status
        try:
            self.stdscr.refresh()
        except curses.error:
            pass

    def load_playlist(self, path):
        path = os.path.expanduser(path)
        if not path.strip():
            self.display_names = ["[No music folder set. Use ':a <folder>' to add one.]"]
            self.durations = [""]
            self.playlist = []
            self.error_message = "No music folder set."
            return
        cache_file = f"playlist_cache_{get_folder_hash(path)}.json"
        try:
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                self.playlist = cache.get("playlist", [])
                self.display_names = cache.get("display_names", [])
                self.durations = cache.get("durations", [])
                self.albums = cache.get("albums", {})
                self.album_names = cache.get("album_names", [])
                self.error_message = ""
                return
            extensions = [
                '*.mp3', '*.wav', '*.flac', '*.ogg', '*.aac', '*.m4a', '*.wma',
                '*.aiff', '*.ape', '*.opus', '*.mpc', '*.spx', '*.wv', '*.tta',
                '*.mp2', '*.mp1', '*.caf', '*.dsf', '*.dff', '*.au', '*.snd',
                '*.oga', '*.mogg', '*.xm', '*.mod', '*.it', '*.s3m', '*.mtm', '*.umx'
            ]
            songs = []
            for ext in extensions:
                songs.extend(glob.glob(os.path.join(path, "**", ext), recursive=True))
            self.playlist = sorted(songs)
            self.display_names = []
            self.durations = []
            self.albums = {}
            self.album_names = []
            if not os.path.exists(path):
                self.display_names = ["[Invalid folder: not found]"]
                self.durations = [""]
                self.playlist = []
                self.error_message = "Music folder not found."
                return
            if not songs:
                self.display_names = ["[No music files found in folder and subfolders]"]
                self.durations = [""]
                self.playlist = []
                self.error_message = "No music files found."
                return
            for song in self.playlist:
                name, timestamp, album = self.get_display_name_and_duration(song)
                self.display_names.append(name)
                self.durations.append(timestamp)
                if album:
                    if album not in self.albums:
                        self.albums[album] = []
                    self.albums[album].append(song)
            self.album_names = sorted(list(self.albums.keys()))
            self.error_message = ""
            cache = {
                "playlist": self.playlist,
                "display_names": self.display_names,
                "durations": self.durations,
                "albums": self.albums,
                "album_names": self.album_names
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f)
        except Exception as e:
            self.display_names = ["[Error loading music folder]"]
            self.durations = [""]
            self.playlist = []
            self.error_message = str(e)

    def refresh_playlist(self):
        cache_file = f"playlist_cache_{get_folder_hash(self.music_folder)}.json"
        if os.path.exists(cache_file):
            os.remove(cache_file)
        self.load_playlist(self.music_folder)
        self.selected_index = 0
        self.scroll_offset = 0

    def play_song(self, song_path):
        try:
            self.player.stop()
            self.player.load_song(song_path)
            self.player.play()
            self.current_song_path = song_path
            if song_path in self.playlist:
                self.current_index = self.playlist.index(song_path)
                self.selected_index = self.current_index
            self.last_top_bar = ""
            self.error_message = ""
        except Exception:
            self.error_message = f"Failed to play: {os.path.basename(song_path)}"

    def process_input(self):
        self.stdscr.nodelay(True)
        search_mode = False
        search_query = ""
        filtered_indices = None
        last_draw = 0
        redraw_interval = 0.05
        kb = self.keybindings
        command_mode = False
        command_buffer = ""
        quit_prompt = False
        self.display_menu(force_redraw=True)
        while True:
            if self.current_song_path and self.player.is_song_finished():
                if self.queue_list and self.queue_index < len(self.queue_list):
                    next_song = self.queue_list[self.queue_index]
                    self.play_song(next_song)
                    self.queue_index += 1
                else:
                    if self.shuffle:
                        if self.playlist:
                            next_song = random.choice(self.playlist)
                            self.play_song(next_song)
                    else:
                        if self.playlist and self.current_song_path in self.playlist:
                            idx = self.playlist.index(self.current_song_path)
                            next_idx = (idx + 1) % len(self.playlist)
                            self.play_song(self.playlist[next_idx])
            now = time.time()
            need_redraw = now - last_draw > redraw_interval
            if need_redraw:
                if command_mode:
                    command_input = command_buffer
                elif quit_prompt:
                    command_input = "Quit Muse? (y/n): "
                else:
                    command_input = f"/{search_query}" if search_mode else ""
                self.display_menu(
                    display_names=self.get_current_names(),
                    command_input=command_input,
                    search_mode=search_mode,
                    filtered_indices=filtered_indices,
                    search_selected=self.search_selected
                )
                last_draw = now
            key = self.stdscr.getch()
            if key == -1:
                time.sleep(0.01)
                continue
            force_redraw = True
            if quit_prompt:
                if key in (ord('y'), ord('Y')):
                    self.config["volume"] = self.volume
                    self.config["shuffle"] = self.shuffle
                    self.config["repeat"] = self.repeat
                    save_config(self.config)
                    break
                elif key in (ord('n'), ord('N')):
                    quit_prompt = False
                continue
            if command_mode:
                if key in (27,):
                    command_mode = False
                    command_buffer = ""
                elif key in (10, 13):
                    cmd = command_buffer.strip()
                    if cmd == ":help":
                        help_msg = help_text(self.keybindings)
                        self.stdscr.clear()
                        lines = help_msg.splitlines()
                        max_y, max_x = self.stdscr.getmaxyx()
                        for i, line in enumerate(lines):
                            if i >= max_y - 2:
                                break
                            try:
                                self.stdscr.addstr(i, 0, line[:max_x])
                            except curses.error:
                                pass
                        try:
                            self.stdscr.addstr(max_y - 1, 0, "Press any key to return...".ljust(max_x))
                        except curses.error:
                            pass
                        self.stdscr.refresh()
                        while True:
                            if self.stdscr.getch() != -1:
                                break
                            time.sleep(0.01)
                        self.display_menu(force_redraw=True)
                        command_mode = False
                        command_buffer = ""
                        force_redraw = True
                        continue
                    elif cmd.startswith(":a "):
                        folder = command_buffer[3:].strip()
                        folder = os.path.expanduser(folder)
                        if folder and os.path.exists(folder):
                            self.music_folder = folder
                            self.config["music_folder"] = folder
                            save_config(self.config)
                            self.load_playlist(self.music_folder)
                            self.selected_index = 0
                            self.scroll_offset = 0
                            self.error_message = ""
                        else:
                            self.display_names = ["[Invalid folder: not found]"]
                            self.durations = [""]
                            self.playlist = []
                            self.error_message = "Folder not found."
                    elif cmd == ":refresh":
                        self.refresh_playlist()
                        self.error_message = ""
                    elif cmd == ":q":
                        self.config["volume"] = self.volume
                        self.config["shuffle"] = self.shuffle
                        self.config["repeat"] = self.repeat
                        save_config(self.config)
                        break
                    elif cmd in (":v", ":version"):
                        self.version_message = APP_VERSION
                        self.display_menu(force_redraw=True)
                        while True:
                            key2 = self.stdscr.getch()
                            if key2 != -1:
                                self.version_message = ""
                                break
                            time.sleep(0.01)
                        self.error_message = ""
                    elif cmd == ":clear":
                        self.queue_list = []
                        self.queue_index = 0
                        self.error_message = ""
                    elif cmd.startswith(":remove "):
                        try:
                            num_str = command_buffer[8:].strip()
                            remove_index = int(num_str) - 1
                            if 0 <= remove_index < len(self.queue_list):
                                del self.queue_list[remove_index]
                                if self.queue_index > remove_index:
                                    self.queue_index -= 1
                                if self.selected_index >= len(self.queue_list) and self.queue_list:
                                    self.selected_index = len(self.queue_list) - 1
                                elif not self.queue_list:
                                    self.selected_index = 0
                                self.error_message = ""
                            else:
                                self.error_message = "Invalid queue index."
                        except (ValueError, IndexError):
                            self.error_message = "Invalid queue index."
                    elif cmd == "":
                        self.error_message = ""
                    else:
                        self.error_message = f"Unknown command: {cmd}"
                    command_mode = False
                    command_buffer = ""
                elif key in (curses.KEY_BACKSPACE, 127, 8):
                    command_buffer = command_buffer[:-1]
                elif 32 <= key <= 126:
                    command_buffer += chr(key)
                continue
            if search_mode:
                if self.view_mode == 3:
                    search_mode = False
                    search_query = ""
                    filtered_indices = None
                    self.search_selected = 0
                    continue
                current_names = self.get_current_names()
                filtered_indices = search(search_query, current_names)
                if key_match(key, kb["down"]):
                    if filtered_indices and self.search_selected < len(filtered_indices) - 1:
                        self.search_selected += 1
                elif key_match(key, kb["up"]):
                    if self.search_selected > 0:
                        self.search_selected -= 1
                elif key_match(key, kb["quit"]) or key == 27:
                    search_mode = False
                    search_query = ""
                    filtered_indices = None
                    self.search_selected = 0
                elif key_match(key, kb["enter"]):
                    if filtered_indices and len(filtered_indices) > 0 and self.search_selected < len(filtered_indices):
                        original_idx = filtered_indices[self.search_selected]
                        self.selected_index = original_idx
                    search_mode = False
                    search_query = ""
                    filtered_indices = None
                    self.search_selected = 0
                elif key in (curses.KEY_BACKSPACE, 127, 8):
                    if search_query:
                        search_query = search_query[:-1]
                        self.search_selected = 0
                    else:
                        search_mode = False
                        search_query = ""
                        filtered_indices = None
                        self.search_selected = 0
                elif 32 <= key <= 126:
                    search_query += chr(key)
                    self.search_selected = 0
                if filtered_indices:
                    if self.search_selected >= len(filtered_indices):
                        self.search_selected = max(0, len(filtered_indices) - 1)
                else:
                    self.search_selected = 0
                continue
            if key == ord('q'):
                quit_prompt = True
                continue
            elif key_match(key, kb.get("search", [])):
                if self.view_mode == 3:
                    continue
                search_mode = True
                search_query = ""
                filtered_indices = None
                self.search_selected = 0
                continue
            elif key_match(key, kb.get("shuffle", [])):
                self.shuffle = not self.shuffle
                continue
            elif key_match(key, kb.get("repeat", [])):
                self.repeat = not self.repeat
                continue
            elif key_match(key, kb["next"]):
                self.next_song()
            elif key_match(key, kb["prev"]):
                self.prev_song()
            elif key_match(key, kb["play_pause"]):
                self.toggle_play_pause()
            elif key_match(key, kb.get("volume_up", [])):
                self.volume = min(1.0, self.volume + 0.05)
                self.player.set_volume(self.volume)
            elif key_match(key, kb.get("volume_down", [])):
                self.volume = max(0.0, self.volume - 0.05)
                self.player.set_volume(self.volume)
            elif key_match(key, kb.get("fadeout", [])):
                self.player.fadeout()
            elif key_match(key, kb.get("seek_forward", [])) and self.view_mode != 3:
                self.player.seek(self.seek_seconds)
            elif key_match(key, kb.get("seek_backward", [])) and self.view_mode != 3:
                self.player.seek(-self.seek_seconds)
            elif key == ord(':'):
                command_mode = True
                command_buffer = ":"
            elif key == ord('1'):
                self.view_mode = 1
                self.selected_index = 0
                self.scroll_offset = 0
                force_redraw = True
                continue
            elif key == ord('2'):
                self.view_mode = 2
                self.selected_index = 0
                self.scroll_offset = 0
                force_redraw = True
                continue
            elif key == ord('3'):
                self.view_mode = 3
                self.album_view_selected = 0
                self.scroll_offset = 0
                self.album_songs_scroll = 0
                self.album_song_selected = 0
                self.album_column = 0
                force_redraw = True
                continue
            elif self.view_mode == 3:
                album_names = self.album_names
                selected_album = album_names[self.album_view_selected] if album_names else None
                album_songs = self.albums[selected_album] if selected_album else []
                if key_match(key, kb["down"]):
                    if self.album_column == 0:
                        if self.album_view_selected < len(album_names) - 1:
                            self.album_view_selected += 1
                            self.album_songs_scroll = 0
                            self.album_song_selected = 0
                    else:
                        if album_songs and self.album_song_selected < len(album_songs) - 1:
                            self.album_song_selected += 1
                elif key_match(key, kb["up"]):
                    if self.album_column == 0:
                        if self.album_view_selected > 0:
                            self.album_view_selected -= 1
                            self.album_songs_scroll = 0
                            self.album_song_selected = 0
                    else:
                        if self.album_song_selected > 0:
                            self.album_song_selected -= 1
                elif key == curses.KEY_RIGHT or key == ord('l'):
                    if self.album_column == 0:
                        self.album_column = 1
                elif key == curses.KEY_LEFT or key == ord('h'):
                    if self.album_column == 1:
                        self.album_column = 0
                elif key_match(key, kb["enter"]):
                    if self.album_column == 1 and album_songs and self.album_song_selected < len(album_songs):
                        song = album_songs[self.album_song_selected]
                        self.play_song(song)
                elif key_match(key, kb.get("queue", [])):
                    if self.album_column == 1 and album_songs and self.album_song_selected < len(album_songs):
                        song = album_songs[self.album_song_selected]
                        if song not in self.queue_list:
                            self.queue_list.append(song)
            elif self.view_mode == 2:
                if key_match(key, kb["down"]):
                    if self.selected_index < len(self.queue_list) - 1:
                        self.selected_index += 1
                elif key_match(key, kb["up"]):
                    if self.selected_index > 0:
                        self.selected_index -= 1
                elif key_match(key, kb["enter"]):
                    if self.queue_list and self.selected_index < len(self.queue_list):
                        song = self.queue_list[self.selected_index]
                        self.play_song(song)
                elif key in (curses.KEY_DC, ord('d')):
                    if self.queue_list and self.selected_index < len(self.queue_list):
                        del self.queue_list[self.selected_index]
                        if self.selected_index >= len(self.queue_list) and self.queue_list:
                            self.selected_index = len(self.queue_list) - 1
                        if self.queue_index > self.selected_index:
                            self.queue_index -= 1
                elif key_match(key, kb.get("queue", [])):
                    if self.queue_list and self.selected_index < len(self.queue_list):
                        song = self.queue_list[self.selected_index]
                        if song not in self.queue_list:
                            self.queue_list.append(song)
                        if self.selected_index < len(self.queue_list) - 1:
                            self.selected_index += 1
            elif key_match(key, kb["down"]):
                if self.view_mode == 1:
                    if self.selected_index < len(self.display_names) - 1:
                        self.selected_index += 1
            elif key_match(key, kb["up"]):
                if self.selected_index > 0:
                    self.selected_index -= 1
            elif key_match(key, kb["enter"]):
                if self.view_mode == 1 and self.playlist and self.selected_index < len(self.playlist):
                    song = self.playlist[self.selected_index]
                    self.play_song(song)
            elif key_match(key, kb.get("queue", [])):
                if self.view_mode == 1 and self.playlist and self.selected_index < len(self.playlist):
                    song = self.playlist[self.selected_index]
                    if song not in self.queue_list:
                        self.queue_list.append(song)
                    if self.selected_index < len(self.playlist) - 1:
                        self.selected_index += 1

    def next_song(self):
        if self.playlist:
            if self.shuffle:
                song = self.playlist[random.randint(0, len(self.playlist) - 1)]
            else:
                if self.current_song_path and self.current_song_path in self.playlist:
                    current_idx = self.playlist.index(self.current_song_path)
                    next_idx = (current_idx + 1) % len(self.playlist)
                else:
                    next_idx = 0
                song = self.playlist[next_idx]
            self.selected_index = self.playlist.index(song)
            self.play_song(song)

    def prev_song(self):
        if self.playlist:
            if self.shuffle:
                song = self.playlist[random.randint(0, len(self.playlist) - 1)]
            else:
                if self.current_song_path and self.current_song_path in self.playlist:
                    current_idx = self.playlist.index(self.current_song_path)
                    prev_idx = (current_idx - 1) % len(self.playlist)
                else:
                    prev_idx = 0
                song = self.playlist[prev_idx]
            self.selected_index = self.playlist.index(song)
            self.play_song(song)

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

if __name__ == "__main__":
    curses.wrapper(main)