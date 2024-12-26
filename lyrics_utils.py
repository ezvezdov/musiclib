import os
from mutagen.id3 import ID3, USLT
import syncedlyrics
import musiclib


def get_lyrics(track_name, artists_names):
    """
    Fetch the lyrics for a given track and artist(s).

    This function attempts to retrieve synchronized lyrics (LRC format) first.
    If synchronized lyrics are unavailable, it will search for plain text lyrics.
    If no lyrics are found, an empty string is returned.

    Args:
        track_name (str): The name of the track for which lyrics are being retrieved.
        artists_names (str): The name(s) of the artist(s) performing the track.

    Returns:
        str: The lyrics for the track, either synchronized or plain. Returns an empty
             string if no lyrics are available.

    Logging:
        - Logs a message indicating whether synchronized or plain lyrics were found.
        - Logs a message if no lyrics are available for the given track and artist(s).

    Notes:
        - Synchronized lyrics are prioritized, and providers for both types of lyrics
          are specified in the function.
        - Uses the `syncedlyrics` library to fetch lyrics from available providers
          (e.g., Lrclib, NetEase, Genius).
    """
    lyrics_type = "synchronized"

    # Search for synced lyrics
    lrc = syncedlyrics.search(f"{artists_names} {track_name}", providers=[ 'Lrclib', 'NetEase'],enhanced=True)

    # Search for plain lyrics
    if lrc is None:
        lyrics_type = "plain"
        lrc = syncedlyrics.search(f"{artists_names} {track_name}", providers=['Genius', 'Lrclib', 'NetEase'])

    # There is no lyrics for this track
    if lrc is None:
        musiclib.logging.info(f"Lyrics: there is no lyrics for {artists_names} - {track_name}")
        return ""
    
    musiclib.info(f"Lyrics: {lyrics_type} lyrics saved for {artists_names} - {track_name}")
    return lrc.rstrip()

def add_lyrics(audio_path):
    
    # Get ID3 of audio
    audioID3 = ID3(audio_path)

    # Extract track name (title) and artist
    track_name = audioID3.get("TIT2", None)
    artists = audioID3.get("TPE1", None)
    
    # Skip if there is no information about track
    if track_name is None or artists is None:
        musiclib.logging.error("ERROR: Unknown title or Artist!")
        return

    track_name = track_name.text[0]
    artists_names = ", ".join(artists.text)
    
    lrc = musiclib.get_lyrics(track_name, artists_names)
    
    # There is no lyrics for this track
    if lrc is None:
        musiclib.logging.warning(f"Skip {artists_names} - {track_name}")
        return
        
    
    clean_lyrics = lrc.rstrip()

    audioID3.add(USLT(encoding=3, lang='eng', desc='Lyrics', text=clean_lyrics))
    audioID3.save()

def add_lyrics_library(library_path):
    """
    Recursively scans the provided library path and adds lyrics to all audio files.

    This function goes through each file and subdirectory within the specified
    `library_path`. If a subdirectory is found, it calls itself recursively. 
    If a file is found, it processes the file by calling the `search_and_add_lyrics` function.

    Args:
        library_path (str): The path to the music library directory.

    Returns:
        None
    """
    for f in os.scandir(library_path):
        if f.is_dir():
            add_lyrics_library(f.path)
        elif f.name.lower().endswith(musiclib.EXT):
            musiclib.search_and_add_lyrics(f.path)