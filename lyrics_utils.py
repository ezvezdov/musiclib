import os
from mutagen.id3 import ID3, USLT
import syncedlyrics

import logging_utils

def _convert_to_timestamp(ms):
    seconds = ms // 1000
    milliseconds = ms % 1000
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02}:{seconds:02}.{milliseconds:03}"

def get_lyrics_ytm(ytmusic, videoId):
    lyrics_object = {}

    watch_playlist = ytmusic.get_watch_playlist(videoId)

    lyrics_browseId = watch_playlist.get('lyrics',None)
    if lyrics_browseId is None: return None

    lyrics = ytmusic.get_lyrics(lyrics_browseId)


    if lyrics is None: return None

    if lyrics['hasTimestamps']:
        lyrics_object['lyrics'] = "\n".join(f"[{_convert_to_timestamp(line.start_time)}]{line.text}" for line in lyrics['lyrics'])
        lyrics_object['hasTimestamps'] = True
    else:
        lyrics_object['lyrics'] = lyrics['lyrics']
        lyrics_object['hasTimestamps'] = False
    
    return lyrics_object
    

def get_lyrics(track_name, artists_names, ytmusic=None, id=None):
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
    """
    lyrics_object = {}

    # Search for synced lyrics from YTM
    if not ytmusic is None and not id is None:
        lyrics_object = get_lyrics_ytm(ytmusic, id)
        if lyrics_object and lyrics_object['hasTimestamps']:
            logging_utils.logging.debug(f"Lyrics: synchronized lyrics saved for {artists_names} - {track_name}. Source: YTM.")
            return lyrics_object['lyrics'].rstrip()

    # Search for synced lyrics from Lrclib, NetEase
    lrc = syncedlyrics.search(f"{artists_names} {track_name}", providers=['Lrclib', 'NetEase'],enhanced=True)
    if not lrc is None:
        logging_utils.logging.debug(f"Lyrics: synchronized lyrics saved for {artists_names} - {track_name}. Source: Musixmatch, Lrclib, NetEase.")
        return lrc.rstrip()

    # Return plain lyrics from YTM
    if lyrics_object:
        logging_utils.logging.debug(f"Lyrics: plain lyrics saved for {artists_names} - {track_name}. Source: YTM.")
        return lyrics_object['lyrics'].rstrip()

    # Search for plain lyrics from Genius, Lrclib, NetEase
    lrc = syncedlyrics.search(f"{artists_names} {track_name}", providers=['Genius', 'Lrclib', 'NetEase'])
    if not lrc is None:
        logging_utils.logging.debug(f"Lyrics: plain lyrics saved for {artists_names} - {track_name}. Source: Genius, Lrclib, NetEase.")
        return lrc.rstrip()

    # There is no lyrics for this track
    logging_utils.logging.debug(f"Lyrics: there is no lyrics for {artists_names} - {track_name}")
    return None

def add_lyrics(audio_path):
    """
    Adds lyrics to an audio file using its metadata to retrieve lyrics.

    Args:
        audio_path (str): Path to the audio file.
    """
    # Get ID3 of audio
    audioID3 = ID3(audio_path)

    # Extract track name (title) and artist
    track_name = audioID3.get("TIT2", None)
    artists = audioID3.get("TPE1", None)
    
    # Skip if there is no information about track
    if track_name is None or artists is None:
        logging_utils.logging.error("ERROR: Unknown title or Artist!")
        return
    
    track_name = track_name.text[0]
    artists_names = ", ".join(artists.text)
    
    # Get lyrics
    lrc = logging_utils.get_lyrics(track_name, artists_names)
    
    # There is no lyrics for this track
    if lrc is None: return

    # Add lyrics to track
    audioID3.add(USLT(encoding=3, lang='eng', desc='Lyrics', text=lrc))
    audioID3.save()

def add_lyrics_library(library_path):
    """
    Recursively scans the provided library path and adds lyrics to all audio files.

    Args:
        library_path (str): The path to the music library directory.
    """
    for f in os.scandir(library_path):
        if f.is_dir():
            add_lyrics_library(f.path)
        elif f.name.lower().endswith(".mp3"): # Hardcoded, only mp3
            add_lyrics(f.path)