import os
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
import syncedlyrics
from mutagen.id3 import SYLT, USLT, Encoding
import yt_dlp
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, TXXX, USLT, APIC
import requests
import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import api_key

# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=api_key.spotify_client_id, client_secret=api_key.spotify_client_secret))



# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG,  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log message format
    filename='.musiclib.log',   # Log to file, omit for console logging
    filemode='w'          # Overwrite ('w') or append ('a') to log file
)


def get_lyrics(track_name, artists_names):

    lyrics_type = "synchronized"

    # Search for synced lyrics
    lrc = syncedlyrics.search(f"{artists_names} {track_name}", providers=[ 'Lrclib', 'NetEase'],enhanced=True)

    # Search for plain lyrics
    if lrc is None:
        lyrics_type = "plain"
        lrc = syncedlyrics.search(f"{artists_names} {track_name}", providers=['Genius', 'Lrclib', 'NetEase'])

    # There is no lyrics for this track
    if lrc is None:
        logging.info(f"Lyrics: there is no lyrics for {artists_names} - {track_name}")
        return ""
    
    logging.info(f"Lyrics: {lyrics_type} lyrics saved for {artists_names} - {track_name}")
    return lrc.rstrip()

def get_track_info(track_name, artist_name):

    logging.info(f"Get information about track: {artist_name} - {track_name}")

    # Construct the query
    query = f"track:{track_name} artist:{artist_name}"
    results = sp.search(q=query, type="track", limit=1)

    track_info = dict()

    if results.get('tracks', {}).get('items', []):
        track = results['tracks']['items'][0]
        album = track.get('album', {})

        track_info['track_name'] = track.get('name', '')
        track_info['track_artists'] = [artist.get('name', '') for artist in track.get('artists', [])]
        track_info['album_name'] = album.get('name', '')
        track_info['release_date'] = album.get('release_date', '')
        track_info['track_number'] = track.get('track_number', -1)
        track_info['total_tracks'] = album.get('total_tracks', -1)
        track_info['album_artists'] = [artist.get('name', '') for artist in album.get('artists', [])]
        track_info['lyrics'] = get_lyrics(track_info['track_name'], ", ".join(track_info['track_artists']))

        # Safely get the thumbnail URL
        images = album.get('images', [])
        track_info['thumbnail_url'] = images[0].get('url', '') if images else ''

        # Logging
        logging.info("Track Name:", track_info['track_name'])
        logging.info("Artist(s):", track_info['track_artists'])
        logging.info("Album:", track_info['album_name'])
        logging.info("Release date:", track_info['release_date'])
        logging.info("Track number:", track_info['track_number'])
        logging.info("Total tacks:", track_info['total_tracks'])
        logging.info("Album artists:", track_info['album_artists'])
        logging.info("Thumbnail:", track_info['thumbnail_url'])
    else:
        
        logging.info(f"Track {artist_name} - {track_name} was not found.")
    

    return track_info

def add_tag(audio_path, track_info):
    # Load the MP3 file
    audio = MP3(audio_path, ID3=ID3)


    # Add or update tags
    audio['TIT2'] = TIT2(encoding=3, text=track_info['track_name'])  # Track Name
    audio['TPE1'] = TPE1(encoding=3, text="|".join(track_info['track_artists']))  # Track Artists
    audio['TDRC'] = TDRC(encoding=3, text=track_info['release_date'])  # Release Date


    if track_info['track_number'] > 0 and track_info['total_tracks'] > 0:
        audio['TALB'] = TALB(encoding=3, text=track_info['album_name'])  # Album Name
        audio['TXXX:Album Artist'] = TXXX(encoding=3, desc='Album Artist', text=", ".join(track_info['album_artists']))  # Album Artists
        audio['TRCK'] = TRCK(encoding=3, text=f'{track_info['track_number']}/{track_info['total_tracks']}')  # Track Number / Total Tracks
    elif track_info['track_number'] > 0:
        audio['TRCK'] = TRCK(encoding=3, text=f'{track_info['track_number']}')  # Track Number
    
    audio['USLT'] = USLT(encoding=3, lang='eng', desc='', text=track_info['lyrics'])  # Lyrics

    if track_info['thumbnail_url']:
        response = requests.get(track_info['thumbnail_url'])
        if response.status_code == 200:
            audio.tags.add(
                APIC(
                    encoding=3,  # UTF-8 encoding
                    mime='image/jpeg',  # MIME type
                    type=3,  # Cover (front)
                    desc='Thumbnail',
                    data=response.content,  # Image data
                )
            )
    else:
        raise Exception(f"Failed to download image. Status code: {response.status_code}")

    
    # Save changes
    audio.save()


def tmp(path):
    for f in os.scandir(path):
        name = f.path.split("/")[-1][:-4]
        info = name.split("<|>")
        inf = get_track_info(info[-1], info[0])
        add_tag(f.path,inf)

def search_and_add_lyrics(audio_path):

    audioID3 = ID3(audio_path)

    # Extract track name (title) and artist
    track_name = audioID3.get("TIT2", None)
    artists = audioID3.get("TPE1", None)
    

    if track_name is None or artists is None:
        print("ERROR: Unknown title or Artist!")
        return

    track_name = track_name.text[0]
    artists_names = ", ".join(artists.text)

    # Search for synced lyrics
    lrc = syncedlyrics.search(f"{artists_names} {track_name}", providers=[ 'Lrclib', 'NetEase'],enhanced=True)

    # There is only plain lyrics
    if lrc is None:
        # Search for synced lyrics
        lrc = syncedlyrics.search(f"{artists_names} {track_name}", providers=['Genius', 'Lrclib', 'NetEase'])

    # There is no lyrics for this track
    if lrc is None:
        print(f"Skip {artists_names} - {track_name}")
        return
    
    clean_lyrics = lrc.rstrip()

    audioID3.add(USLT(encoding=3, lang='eng', desc='Lyrics', text=clean_lyrics))
    # audioID3.add(USLT(encoding=3, desc='Lyrics', text=lrc))
    audioID3.save()
    
    print(f"Lyrics saved for {artists_names} - {track_name}")
    # print(lrc)

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
        elif f.name.lower().endswith(".mp3"):
            search_and_add_lyrics(f.path)

def download_by_artist():
    # Define download options
    # download_options = {
    #     'format': 'bestaudio/best',
    #     'outtmpl': '%(artist)s<|>%(track)s.%(ext)s',
    #     'postprocessors': [{
    #         'key': 'FFmpegExtractAudio',
    #         'preferredcodec': 'm4a',
    #         'preferredquality': '192',
    #     }],
    #     'postprocessor_args': [
    #         '-c:a', 'aac',  # Use native FFmpeg AAC encoder
    #         '-b:a', '192k'  # Set bitrate
    #     ],
    #     'cookiesfrombrowser': ('chrome',),
    # }
    download_options = {
    'format': 'bestaudio/best',  # Select the best audio format available
    'outtmpl': '%(artist)s<|>%(track)s.%(ext)s',  # Custom output template
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',  # Set preferred codec to MP3
        'preferredquality': '192',  # Set preferred quality (in kbps)
    }],
    'postprocessor_args': [
        '-id3v2_version', '3',  # Use ID3v2.3 tags for maximum compatibility
        '-b:a', '192k'  # Set audio bitrate to 192 kbps
    ],
    'quiet': False,  # Show progress and details
    'cookiesfrombrowser': ('chrome',),
    }
    url = "https://music.youtube.com/channel/UCqhjJO7w2rv5Tkk7ZFYl7QA"
    with yt_dlp.YoutubeDL(download_options) as ydl:
        ydl.download([url])



if __name__ == "__main__":
    # Define library folder
    library_path = "/home/ezvezdov/Music"

    for artist_dir in os.scandir(library_path):

        # Skip non-artist
        if not artist_dir.is_dir(): continue

        # Set variables
        artist_name = artist_dir.name
        album_artist = artist_name

        for album_dir in os.scandir(artist_dir):
            # Skip singles
            if not album_dir.is_dir(): continue

            print(album_dir.path)
            for album_track in os.scandir(album_dir):
                if album_track.name.lower().endswith(".mp3"):
                    file_path = album_track.path
                    try:
                        audio = EasyID3(file_path)
                    except ID3NoHeaderError:
                        audio = EasyID3()  # Create if missing
                        audio.save(file_path)
                        

                    audio['albumartist'] = album_artist
                    audio.save()
                    print(f"Updated: {album_track.name}")