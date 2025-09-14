import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
from mutagen import File
import time

class MusicPlayer:
    def __init__(self):
        try:
            pygame.mixer.init()
        except Exception:
            pass
        self.current_song = None
        self.playing = False
        self.start_time = 0
        self.pause_time = 0

    def load_song(self, song_path):
        if os.path.exists(song_path):
            pygame.mixer.music.load(song_path)
            self.current_song = song_path
            self.start_time = 0
            self.pause_time = 0
        else:
            self.current_song = None

    def play(self):
        if self.current_song:
            pygame.mixer.music.play()
            self.playing = True
            self.start_time = time.time() - self.pause_time

    def stop(self):
        pygame.mixer.music.stop()
        self.playing = False
        self.start_time = 0
        self.pause_time = 0

    def pause(self):
        if self.playing:
            pygame.mixer.music.pause()
            self.playing = False
            self.pause_time = time.time() - self.start_time

    def unpause(self):
        if not self.playing:
            pygame.mixer.music.unpause()
            self.playing = True
            self.start_time = time.time() - self.pause_time

    def fadeout(self, ms=2000):
        pygame.mixer.music.fadeout(ms)
        self.playing = False

    def set_volume(self, volume):
        pygame.mixer.music.set_volume(volume)

    def get_volume(self):
        return pygame.mixer.music.get_volume()

    def queue_song(self, song_path):
        if os.path.exists(song_path):
            pygame.mixer.music.queue(song_path)

    def get_song_info(self):
        if self.current_song:
            audio = File(self.current_song)
            title = ""
            artist = ""
            duration = 0
            if audio:
                duration = int(audio.info.length)
                if audio.tags:
                    title = audio.tags.get('TIT2', [""])[0] if 'TIT2' in audio.tags else audio.tags.get('title', [""])[0]
                    artist = audio.tags.get('TPE1', [""])[0] if 'TPE1' in audio.tags else audio.tags.get('artist', [""])[0]
            return {
                "title": str(title) if title else "",
                "artist": str(artist) if artist else "",
                "duration": duration
            }
        return {}

    def get_pos(self):
        if self.playing and self.start_time > 0:
            return int(time.time() - self.start_time)
        elif self.pause_time > 0:
            return int(self.pause_time)
        else:
            return 0

    def seek(self, seconds):
        if self.current_song:
            audio = File(self.current_song)
            song_length = int(audio.info.length) if audio and audio.info else 0
            current_pos = self.get_pos()
            new_pos = max(0, min(current_pos + seconds, song_length))
            
            if self.playing:
                self.start_time = time.time() - new_pos
            else:
                self.pause_time = new_pos

    def is_song_finished(self):
        return self.current_song and not pygame.mixer.music.get_busy()