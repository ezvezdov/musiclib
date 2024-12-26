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
import re 
import time

EXT = ".mp3"
# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=api_key.spotify_client_id, client_secret=api_key.spotify_client_secret))

ydl_opts = {
    'format': 'bestaudio/best',  # Select the best audio format available
    'outtmpl': '%(id)s.%(ext)s',  # Custom output template
    'download_archive': 'downloaded_videos.txt',
    'retries': 5,  # Retry 5 times for errors
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
    }


# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG,  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log message format
    filename='.musiclib.log',   # Log to file, omit for console logging
    filemode='w'          # Overwrite ('w') or append ('a') to log file
)

def trackname_remove_unnecessary(title):
    name = re.sub(r'\(feat.*?\)|\(ft.*?\)|feat.*|ft.*|\(Feat.*?\)|\(Ft.*?\)|\(prod.*?\)|\[prod.*?\]|\(Prod.*?\)', '', title)
    return name.rstrip()


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
        logging.info(f"Lyrics: there is no lyrics for {artists_names} - {track_name}")
        return ""
    
    logging.info(f"Lyrics: {lyrics_type} lyrics saved for {artists_names} - {track_name}")
    return lrc.rstrip()

def get_track_info_spotify(track_name, artist_name):
    """
    Retrieves detailed information about a specific track.

    Searches for the track using the provided track name and artist name, fetches 
    metadata such as album details, release date, track number, and thumbnail URL.
    Also attempts to fetch lyrics for the track.

    Args:
        track_name (str): The name of the track.
        artist_name (str): The name of the artist.

    Returns:
        dict: A dictionary containing track information with the following keys:
            - `track_name` (str): Name of the track.
            - `track_artists` (list[str]): List of artists who performed the track.
            - `album_name` (str): Name of the album containing the track.
            - `release_date` (str): Release date of the album.
            - `track_number` (int): Track's position in the album.
            - `total_tracks` (int): Total number of tracks in the album.
            - `album_artists` (list[str]): List of artists credited for the album.
            - `lyrics` (str): Lyrics of the track.
            - `thumbnail_url` (str): URL of the album's thumbnail image.

    Logging:
        - Logs the track details if the track is found.
        - Logs a message if the track is not found.
    """
    logging.info(f"Get information about track: {artist_name} - {track_name}")

    # Construct the query
    query = f"track:{track_name} artist:{artist_name}"
    results = sp.search(q=query, type="track", limit=1)

    track_info = dict()

    if results.get('tracks', {}).get('items', []):
        track = results['tracks']['items'][0]
        album = track.get('album', {})

        track_info['track_name'] = trackname_remove_unnecessary(track.get('name', ''))
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

    else:
        logging.warning(f"Track {artist_name} - {track_name} was not found.")
    
    return track_info

def get_track_info_genius(track_name, artists_names):
    search_term = f"{artists_names} - {track_name}"
    genius_search_url = f"http://api.genius.com/search?q={search_term}&access_token={api_key.genius_client_access_token}"

    response = requests.get(genius_search_url)
    json_data = response.json()

    track = json_data['response']['hits'][0]['result']

    track_info = dict()

    track_info['track_name'] = trackname_remove_unnecessary(track.get('title', ''))
    track_info['track_artists'] = [track['primary_artist']['name']]
    track_info['album_name'] = ""
    track_info['release_date'] = f"{track['release_date_components']['year']} - {track['release_date_components']['month']} - {track['release_date_components']['day']}"

    track_info['track_number'] = track.get('track_number', -1)
    track_info['total_tracks'] = -1
    track_info['album_artists'] = track_info['track_artists']
    track_info['lyrics'] = get_lyrics(track_info['track_name'], ", ".join(track_info['track_artists']))

    track_info['thumbnail_url'] = track['header_image_url']

    return track_info


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

    Notes:
        - Adds synchronized lyrics if available in the `lyrics` key.
        - Adds album artwork if a valid URL is provided in `thumbnail_url`.
        - Ensures the MP3 file's metadata is saved after modification.

    Logging:
        - Logs a warning if the thumbnail image cannot be downloaded.
    """
    # Load the MP3 file
    audio = MP3(audio_path, ID3=ID3)

    # Clear all existing tags
    audio.delete()

    # Add or update tags
    audio['TIT2'] = TIT2(encoding=3, text=track_info['track_name'])  # Track Name
    audio['TPE1'] = TPE1(encoding=3, text="/".join(track_info['track_artists']))  # Track Artists
    audio['TDRC'] = TDRC(encoding=3, text=track_info['release_date'])  # Release Date


    if track_info['total_tracks'] > 1:
        audio['TALB'] = TALB(encoding=3, text=track_info['album_name'])  # Album Name
        audio['TXXX:Album Artist'] = TXXX(encoding=3, desc='Album Artist', text="/".join(track_info['album_artists']))  # Album Artists
        audio['TRCK'] = TRCK(encoding=3, text=f'{track_info['track_number']}/{track_info['total_tracks']}')  # Track Number / Total Tracks
    
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
        logging.warning(f"Failed to download image. Status code: {response.status_code}")

    
    # Save changes
    audio.save()


def tmp(path):
    for f in os.scandir(path):
        if f.is_file():
            name = f.name[:-4]
            info = name.split("<|>")
            inf = get_track_info_spotify(info[-1], info[0])
            add_tag(f.path,inf)

def search_and_add_lyrics(audio_path):

    audioID3 = ID3(audio_path)

    # Extract track name (title) and artist
    track_name = audioID3.get("TIT2", None)
    artists = audioID3.get("TPE1", None)
    

    if track_name is None or artists is None:
        logging.error("ERROR: Unknown title or Artist!")
        return

    track_name = track_name.text[0]
    artists_names = ", ".join(artists.text)

    # Search for synced lyrics
    # lrc = syncedlyrics.search(f"{artists_names} {track_name}", providers=[ 'Lrclib', 'NetEase'],enhanced=True)
    lrc = syncedlyrics.search(f"{artists_names} {track_name}")

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
        elif f.name.lower().endswith(EXT):
            search_and_add_lyrics(f.path)

# def youtube_get_artist_id(artist_name):
#     search_query = f"ytsearch:{artist_name} site:music.youtube.com"
#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         search_results = ydl.extract_info(search_query, download=False)
#     print(search_results)

#     artist_id = search_results['entries'][0]['channel_id']

#     return artist_id


def download_by_title_youtube(title, artist_name):
    query = f"ytsearch1:{artist_name} {title}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        metadata = ydl.extract_info(query, download=True)
        # import json
        # with open("data.json", "w") as json_file:
        #     json.dump(metadata["entries"], json_file, indent=4)  # Use indent=4 for pretty-printing
        return metadata["entries"]


def download_track_youtube(track_id):
    # Construct the URL for YouTube Music
    track_url = f"https://music.youtube.com/watch?v={track_id}"

    # Download using yt-dlp
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([track_url])

def download_by_artist(artist_name, library_path, prefer_spotify_metadata=True):
    downloaded = {}

    # artist_id = youtube_get_artist_id(artist_name)

    # url = f"https://music.youtube.com/channel/{artist_id}"
    # with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    #     channel_metadata = ydl.extract_info(url, download=True)  # Get metadata without downloading

    # if not 'entries' in channel_metadata: return
    
    # Deezer, get discography
    # titles = get_discography_by_artist_deezer(artist_name)
    # for title in titles:
    #     entry = download_by_title_youtube(title, artist_name)
    #     if entry['id'] in downloaded:
    #         downloaded[entry['id']].append([title, artist_name]) 
    #     else:
    #         downloaded[entry['id']] = [[title, artist_name]]

    # YouTube music, get discography
    track_metadata = get_discography_by_artist_youtube(artist_name)
    # for track_id, track_info in track_metadata.items():
    #     track_url = f"https://music.youtube.com/watch?v={track_id}"

    #     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    #         ydl.download([track_url])
        

    # for entry in channel_metadata['entries']:
    #     title = trackname_remove_unnecessary(entry['title'])
    #     if entry['id'] in downloaded:
    #         downloaded[entry['id']].append([title, artist_name]) 
    #     else:
    #         downloaded[entry['id']] = [[title, artist_name]]


    for id, track_info in track_metadata.items():
        download_track_youtube(id)
        # track_info = {}
        # for title in info:
        if prefer_spotify_metadata:
            track_info_spotify = get_track_info_spotify(trackname_remove_unnecessary(track_info['track_name']), ", ".join(track_info['track_artists']))
            if track_info_spotify:
                track_info = track_info_spotify


            # if not track_info: continue
        
        file_path = os.path.join(library_path, f"{id}{EXT}")
        new_filename = ", ".join(track_info['track_artists']) + " - " + track_info['track_name'] + EXT

        new_path = os.path.join(library_path, track_info['track_artists'][0], new_filename)
        if track_info['total_tracks'] > 1:
            new_filename = f"{track_info['track_number']}. {new_filename}"
            release_year = track_info['release_date'].split("-")[0]
            new_path = os.path.join(library_path, track_info['track_artists'][0], f"[{release_year}] {track_info['album_name']}", new_filename)

        add_tag(file_path,track_info)

        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        os.rename(file_path, new_path)




def api_request(url, retries=3, delay=2):
    for attempt in range(retries):
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            time.sleep(delay)
    return {}

def deezer_all_fragments(url):
    all_data = []
    while True:
        data = api_request(url)
        all_data.extend(data["data"])
        if "next" in data:
            url = data["next"]
        else:
            return all_data

def get_discography_by_artist_deezer(artist_name):
    artist_search_url = f"https://api.deezer.com/search/artist?q={artist_name}"
    artist_search = api_request(artist_search_url)

    if not "data" in artist_search or len(artist_search["data"]) == 0:
        return []


    artist_id = artist_search["data"][0]["id"]
    albums_url = f"https://api.deezer.com/artist/{artist_id}/albums"
    
    titles = []

    albums = deezer_all_fragments(albums_url)
    
    for album in albums:
        tracks_url = album["tracklist"]
        tracks = deezer_all_fragments(tracks_url)
        for track in tracks:
            title = trackname_remove_unnecessary(track["title"])
            titles.append(title)
    
    return titles

def get_discography_by_artist_youtube(artist_name):
    ytmusic = YTMusic()
    search_results = ytmusic.search(artist_name, filter="artists")
    if not search_results:
        return {}
    
    artist_browse_id = search_results[0]['browseId']
    artist_details = ytmusic.get_artist(artist_browse_id)

    tracks_metadata = {}

    if "albums" in artist_details:
        for album in artist_details['albums']['results']:
            album_details = ytmusic.get_album(album['browseId'])
            for track in album_details['tracks']:        
                track_info = {}
                track_info['track_name'] = trackname_remove_unnecessary(track['title'])
                track_info['track_artists'] = [artist['name'] for artist in track['artists']]
                track_info['album_name'] = album_details['title']
                track_info['release_date'] = album_details['year']
                track_info['track_number'] = track['trackNumber']
                track_info['total_tracks'] = album_details['trackCount']
                track_info['album_artists'] = [artist['name'] for artist in album_details['artists']]
                track_info['lyrics'] = get_lyrics(track_info['track_name'], ", ".join(track_info['track_artists']))
                track_info['thumbnail_url'] = album_details['thumbnails'][-1]['url']

                tracks_metadata[track['videoId']] = track_info
    if "singles" in artist_details:
        for track in artist_details['singles']['results']:

            album_details = ytmusic.get_album(track['browseId'])
            import json
            with open("data.json", "w") as json_file:
                json.dump(album_details, json_file, indent=4)  # Use indent=4 for pretty-printing

            track_info = {}
            track_info['track_name'] = trackname_remove_unnecessary(track['title'])
            track_info['track_artists'] = [artist['name'] for artist in album_details['artists']]
            track_info['release_date'] = track['year']
            track_info['total_tracks'] = -1
            track_info['album_artists'] = []
            track_info['lyrics'] = get_lyrics(track_info['track_name'], ", ".join(track_info['track_artists']))
            track_info['thumbnail_url'] = track['thumbnails'][-1]['url']

            tracks_metadata[album_details['tracks'][0]['videoId']] = track_info
    
    return tracks_metadata



if __name__ == "__main__":
    library_path = input("Please enter the path for music library: ").strip()
    
    # Ensure the path ends with a slash (optional)
    library_path = os.path.join(library_path, '')

    # Create the directory
    try:
        os.makedirs(library_path, exist_ok=True)
        logging.info(f"Folders created successfully at: {library_path}")
    except Exception as e:
        logging.warning(f"Error creating folders: {e}")

    ydl_opts['outtmpl'] = os.path.join(library_path,ydl_opts['outtmpl'])
    
    # download_by_artist("UCnh49MovlpQD702w35IqU-Q", library_path) # BABANGIDA
    # download_by_artist("UCzx6KkjhuWLZa_0gt_Y3MAQ", library_path) # LAPA
    # download_by_artist("UCPfUH32WlUYohFvTqo65GBA", library_path) # Aneezy
    # download_by_artist("UCxtUPmgn4pinQhVHLdKau9A", library_path) # Dima Ermuzevic
    download_by_artist("UCqhjJO7w2rv5Tkk7ZFYl7QA", library_path) # Big Baby Tape
    # download_by_artist("UCet06fFav7tnvdauZw7EwTA", library_path) # Oxxxymiron

    
    # tmp(library_path)

    # for artist_dir in os.scandir(library_path):

    #     # Skip non-artist
    #     if not artist_dir.is_dir(): continue

    #     # Set variables
    #     artist_name = artist_dir.name
    #     album_artist = artist_name

    #     for album_dir in os.scandir(artist_dir):
    #         # Skip singles
    #         if not album_dir.is_dir(): continue

    #         print(album_dir.path)
    #         for album_track in os.scandir(album_dir):
    #             if album_track.name.lower().endswith(".mp3"):
    #                 file_path = album_track.path
    #                 try:
    #                     audio = EasyID3(file_path)
    #                 except ID3NoHeaderError:
    #                     audio = EasyID3()  # Create if missing
    #                     audio.save(file_path)
                        

    #                 audio['albumartist'] = album_artist
    #                 audio.save()
    #                 print(f"Updated: {album_track.name}")


        # print(info)
        # # Write JSON to file
        # import json
        # with open("data.json", "w") as json_file:
        #     json.dump(info, json_file, indent=4)  # Use indent=4 for pretty-printing