import os
import syncedlyrics

import logging_utils
import tag_utils

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

    # Extract track name (title) and artist
    track_info = tag_utils.get_tag_mp3(audio_path)
    track_name = track_info['track_name']
    artists_names = track_info['track_artists_str']
    
    # Skip if there is no information about track
    if not track_name or not artists_names:
        logging_utils.logging.error("ERROR: Unknown title or Artist!")
        return
    
    #  Lyrics already exists
    if 'lyrics' in track_info and track_info['lyrics']: return

    # Get lyrics
    lrc = get_lyrics(track_name, artists_names)
    
    # There is no lyrics for this track
    if lrc is None: return


    track_info['lyrics'] = lrc

    tag_utils.add_tag_mp3(audio_path,track_info)


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