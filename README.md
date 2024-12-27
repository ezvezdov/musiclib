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

You can simply download discograpy of artist using only YouTube API.
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
[!TIP]
> Use MusiclibS for improved performance


[!WARNING]
> In case of problem with Spotify API, you can set your API key at `api_key.py`
> 1. Generate client_id and client_secret at [developer.spotify.com](https://developer.spotify.com/dashboard/create).
> 2. Pass this data to the `api_key.py` file