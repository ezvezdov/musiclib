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


    if track_info['album_name']:
        audio['TALB'] = TALB(encoding=3, text=track_info['album_name'])  # Album Name
        audio['TPE2'] = TPE2(encoding=3, text=ARTIST_SEPARATOR.join(track_info['album_artists']))  # Album Artists
        if track_info['track_number']:
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


def get_tag_mp3(audio_path):
    # Load the MP3 file
    audio = MP3(audio_path, ID3=ID3)

    track_info = {}

    # Fetch info from tag
    track_info['ytm_id'] = audio["TXXX:ytm_id"].text[0] if 'TXXX:ytm_id' in audio else '' # YTM id
    track_info['track_name'] = audio['TIT2'].text[0] if 'TIT2' in audio else '' # Track Name
    track_info['track_artists'] = audio['TPE1'].text[0].split(ARTIST_SEPARATOR) if 'TPE1' in audio else '' # Track Artists
    track_info['track_artists_str'] = ", ".join(track_info['track_artists']) # Track Artists str
    track_info['release_date'] = str(audio['TDRC'].text[0].year) if 'TDRC' in audio else ''  # Release Date
    track_info['album_name'] = audio['TALB'].text[0]  if 'TALB' in audio else '' # Album Name
    track_info['album_artists'] = audio['TPE2'].text[0].split(ARTIST_SEPARATOR) if 'TPE2' in audio else '' # Album artist
    track_info['track_number'] = audio['TRCK'][0].split('/')[0] if 'TRCK' in audio else '' # Track Number
    track_info['total_tracks'] = audio['TRCK'][0].split('/')[-1] if 'TRCK' in audio else '' # Total Tracks
    track_info['lyrics'] = audio['USLT::XXX'].text if 'USLT::XXX' in audio else '' # Lyrics
    track_info['thumbnail'] = base64.b64encode(audio['APIC:Thumbnail'].data).decode('utf-8') if 'APIC:Thumbnail' in audio else ''
    
    return track_info