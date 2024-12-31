# Musiclib

Musiclib is a Python script that allows you to create your own music library.
Music is downloaded from YouTube, and music tags are constructed using data from YouTube and Spotify.

# Instalation
```bash
git clone https://github.com/ezvezdov/musiclib
cd musiclib/
python -m venv .venv
source .venv/bin/activate
pip install yt_dlp ytmusicapi spotipy mutagen syncedlyrics
```

# Usage

You can simply download discography of artist (Spotify API by default).
```
python musiclib.py
>>> Please enter the path for music library: ...
>>> Please enter artist name: ...
```

This script creates a simple database (`.info/db.json`) to track downloaded tracks, allowing you to update an artist's discography without re-downloading existing tracks.

## Available clases

There are two classes that can be used:
+ `Musiclib(library_path: str)`: library class that uses YouTube Music metadata.
+ `MusiclibS(library_path: str)`: library class that uses Spotify metadata.

> [!TIP]
> Use MusiclibS for improved performance


> [!WARNING]
> If you encounter issues with the Spotify API, you can provide your API key in the `api_key.py` file.
> 1. Generate client_id and client_secret at [developer.spotify.com](https://developer.spotify.com/dashboard/create).
> 2. Pass this data to the `api_key.py` file.
> 
> Alternatively you can use `Musiclib` instead of `MusiclibS`.