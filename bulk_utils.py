import os
import musiclib
from mutagen.id3 import ID3, USLT

def add_lyrics(audio_path):
    
    # Get ID3 of audio
    audioID3 = ID3(audio_path)

    # Extract track name (title) and artist
    track_name = audioID3.get("TIT2", None)
    artists = audioID3.get("TPE1", None)
    
    # Skip if there is no information about track
    if track_name is None or artists is None:
        logging.error("ERROR: Unknown title or Artist!")
        return

    track_name = track_name.text[0]
    artists_names = ", ".join(artists.text)
    
    lrc = get_lyrics(track_name, artists_names)
    
    # There is no lyrics for this track
    if lrc is None:
        logging.warning(f"Skip {artists_names} - {track_name}")
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