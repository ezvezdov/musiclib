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


You can use Musiclib class in source code this way
```python
import musiclib
muslib = musiclib.Musiclib(library_path)
muslib.download_artist_disocgrapy("Artist name", library_path)
```

You can use `MusiclibS` instead of `Musiclib`.
`MusiclibS` retrieves information about tracks from the Spotify.
> [!TIP]
> Use MusiclibS for improved performance


> [!WARNING]
> If you encounter issues with the Spotify API, you can provide your API key in the `api_key.py` file.
> 1. Generate client_id and client_secret at [developer.spotify.com](https://developer.spotify.com/dashboard/create).
> 2. Pass this data to the `api_key.py` file