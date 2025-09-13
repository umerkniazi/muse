# Muse

Muse is a terminal-based music player for Windows and Linux, inspired by [cmus](https://cmus.github.io/).

## Features

- Play MP3 files from your music folder
- Keyboard controls for navigation and playback
- Search and fuzzy match for songs
- Shuffle and repeat modes
- Configurable keybindings
- Persistent music folder setting

## Installation

### Windows

1. Download and run `MuseSetup-v1.0.0.exe`.
2. The installer adds Muse to your PATH.
3. Launch Muse from any terminal by typing `muse`.

### Linux

1. Download and extract `muse-v1.0.0-linux.tar.gz`:
   ```
   tar -xzvf muse-v1.0.0-linux.tar.gz
   ```
2. Run the player:
   ```
   ./muse
   ```

## Usage

- Use arrow keys or configured keys to navigate.
- Press `SPACE` to play/pause.
- Press `n`/`p` for next/previous.
- Press `/` to search.
- Press `:q` to quit.

## Configuration

Edit `config.json` to change keybindings or set your music folder.

## Requirements

- Windows: Python 3, `mutagen`, `pygame`, `windows-curses` (if running from source)
- Linux: Python 3, `mutagen`, `pygame` (if running from source)

## License

MIT
