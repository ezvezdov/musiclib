import os
import musiclib


def add_lyrics_all(library_path):
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
            add_lyrics_all(f.path)
        elif f.name.lower().endswith(musiclib.EXT):
            musiclib.search_and_add_lyrics(f.path)