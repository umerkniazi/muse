import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

class MusicPlayer:
    def __init__(self):
        try:
            pygame.mixer.init()
        except Exception as e:
            pass
        self.current_song = None
        self.playing = False

    def load_song(self, song_path):
        if os.path.exists(song_path):
            pygame.mixer.music.load(song_path)
            self.current_song = song_path
        else:
            self.current_song = None

    def play(self):
        if self.current_song:
            pygame.mixer.music.play()
            self.playing = True
        else:
            self.playing = False

    def stop(self):
        pygame.mixer.music.stop()
        self.playing = False

    def pause(self):
        pygame.mixer.music.pause()
        self.playing = False

    def unpause(self):
        pygame.mixer.music.unpause()
        self.playing = True

    def get_song_info(self):
        if self.current_song:
            audio = MP3(self.current_song)
            title = audio.get('TIT2', None)
            artist = audio.get('TPE1', None)
            duration = int(audio.info.length)
            return {
                "title": str(title) if title else "",
                "artist": str(artist) if artist else "",
                "duration": duration
            }
        return {}

    def get_pos(self):
        return pygame.mixer.music.get_pos() // 1000