import base64
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TDRC, TRCK, USLT, APIC, TXXX



def add_tag(audio_path, track_info):
    """
    Adds or updates ID3 tags for an MP3 file.

    This function writes metadata such as track name, artists, album details,
    release date, lyrics, and album artwork to the specified MP3 file.

    Args:
        audio_path (str): Path to the MP3 file to be updated.
        track_info (dict): Dictionary containing track information with the following keys:
            - `track_name` (str): Name of the track.
            - `track_artists` (list[str]): List of artists who performed the track.
            - `release_date` (str): Release date of the track.
            - `album_name` (str, optional): Name of the album containing the track.
            - `album_artists` (list[str], optional): List of artists credited for the album.
            - `track_number` (int): Track's position in the album.
            - `total_tracks` (int): Total number of tracks in the album.
            - `lyrics` (str): Lyrics of the track.
            - `thumbnail_url` (str, optional): URL of the album's thumbnail image.
    """
    if audio_path.endswith('.mp3'):
        import tag_utils.mp3 as mp3
        mp3.add_tag(audio_path, track_info)
    elif audio_path.endswith('.opus'):
        import tag_utils.opus as opus
        opus.add_tag(audio_path, track_info)

def get_tag(audio_path):

    if audio_path.endswith('.mp3'):
        import tag_utils.mp3 as mp3
        return mp3.get_tag(audio_path)
    if audio_path.endswith('.opus'):
        import tag_utils.opus as opus
        return opus.get_tag(audio_path)