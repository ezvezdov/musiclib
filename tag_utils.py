import base64
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TDRC, TRCK, USLT, APIC, TXXX

ARTIST_SEPARATOR = "|"


def add_tag_mp3(audio_path, track_info):
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
    # Load the MP3 file
    audio = MP3(audio_path, ID3=ID3)

    # Clear all existing tags
    audio.delete()

    # Add or update tags
    audio["TXXX:ytm_id"] = TXXX(encoding=3, desc="ytm_id", text=track_info['ytm_id'])
    audio['TIT2'] = TIT2(encoding=3, text=track_info['track_name'])  # Track Name
    audio['TPE1'] = TPE1(encoding=3, text=ARTIST_SEPARATOR.join(track_info['track_artists']))  # Track Artists
    audio['TDRC'] = TDRC(encoding=3, text=track_info['release_date'])  # Release Date


    if track_info['total_tracks']:
        audio['TALB'] = TALB(encoding=3, text=track_info['album_name'])  # Album Name
        audio['TPE2'] = TPE2(encoding=3, text=ARTIST_SEPARATOR.join(track_info['album_artists']))  # Album Artists
        audio['TRCK'] = TRCK(encoding=3, text=f'{track_info['track_number']}/{track_info['total_tracks']}')  # Track Number / Total Tracks
    
    if track_info['lyrics']:
        audio['USLT'] = USLT(encoding=3, lang='XXX', desc='', text=track_info['lyrics'])  # Lyrics

    if track_info['thumbnail']:
        audio['APIC'] = APIC(
                encoding=3,  # UTF-8 encoding
                mime='image/jpeg',  # MIME type
                type=3,  # Cover (front)
                desc='Thumbnail',
                data=base64.b64decode(track_info['thumbnail']),  # Image data
            )
        
    # Save changes
    audio.save()