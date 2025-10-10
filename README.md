# Muse

Muse is a terminal-based music player for Windows and Linux, inspired by [cmus](https://cmus.github.io/).

## Features

- Tracks, Albums, and Queue views
- Add/remove songs to/from the queue
- Play/pause, skip forward/back, and volume control
- Fuzzy search for songs
- Shuffle and repeat modes
- Configurable keybindings
- Persistent music folder setting
- Supports almost all audio formats

## Installation

### Windows

1. Download and run `MuseSetup-v1.1.2.exe`.
2. The installer adds Muse to your PATH.
3. Launch Muse from any terminal by typing `muse`.

### Linux

1. Download and extract `muse-v1.1.2-linux.tar.gz`:
   ```
   tar -xzvf muse-v1.1.2-linux.tar.gz
   ```
2. Run the player:
   ```
   ./main
   ```

## Usage

- Use arrow keys or configured keys to navigate.
- Press `SPACE` to play/pause.
- Press `n`/`p` for next/previous.
- Press `/` to search.
- Press `:q` to quit.
- Press `1`, `2`, or `3` to switch between Tracks, Queue, and Albums views.
- Use `+`/`-` to adjust volume.
- Use left/right arrows for forward/back playback.
- Use `:help` for a full list of commands.

## Configuration

Edit `config.json` to change keybindings or set your music folder.

## Requirements

- Windows: Python 3, `mutagen`, `pygame`, `windows-curses` (if running from source)
- Linux: Python 3, `mutagen`, `pygame` (if running from source)

## License

MIT