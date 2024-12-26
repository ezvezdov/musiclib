import os
import time
import requests
import logging
import re

import yt_dlp
from ytmusicapi import YTMusic
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy

import api_key

import lyrics_utils
import tag_utils


EXT = ".mp3"
# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=api_key.spotify_client_id, client_secret=api_key.spotify_client_secret))




# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG,  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log message format
    filename='.musiclib.log',   # Log to file, omit for console logging
    filemode='w'          # Overwrite ('w') or append ('a') to log file
)

def make_request(url, retries=3, delay=2):
    for attempt in range(retries):
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response
        else:
            time.sleep(delay)
    return {}

def trackname_remove_unnecessary(title):
    name = re.sub(r'\(feat.*?\)|\(ft.*?\)|feat.*|ft.*|\(Feat.*?\)|\(Ft.*?\)|\(prod.*?\)|\[prod.*?\]|\(Prod.*?\)', '', title)
    return name.rstrip()


class Musiclib():
    def __init__(self, library_path):

        self.ydl_opts = {
            'format': 'bestaudio/best',  # Select the best audio format available
            'outtmpl': '%(id)s.%(ext)s',  # Custom output template
            # 'download_archive': 'ydl.txt',
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

        self.library_path = library_path
        self.init_library()

        self.ytmusic = YTMusic()

        
    
    def init_library(self):

        # Ensure the path ends with a slash (optional)
        self.library_path = os.path.join(self.library_path, '')

        # Create the directory
        try:
            os.makedirs(self.library_path, exist_ok=True)
            logging.debug(f"Folders created successfully at: {self.library_path}")
        except Exception as e:
            logging.error(f"Error creating folders: {e}")

        self.ydl_opts['outtmpl'] = os.path.join(self.library_path, self.ydl_opts['outtmpl'])
        if "download_archive" in self.ydl_opts:
            self.ydl_opts['download_archive'] = os.path.join(self.library_path, ".info", self.ydl_opts['download_archive'])

    def get_discography_by_artist_youtube(self,artist_name):
        search_results = self.ytmusic.search(artist_name, filter="artists")
        if not search_results:
            return {}
        
        artist_browse_id = search_results[0]['browseId']
        artist_details = self.ytmusic.get_artist(artist_browse_id)

        tracks_metadata = {}

        if "albums" in artist_details:
            for album in artist_details['albums']['results']:
                album_details = self.ytmusic.get_album(album['browseId'])
                for track in album_details['tracks']:        
                    track_info = {}
                    track_info['track_name'] = trackname_remove_unnecessary(track['title'])
                    track_info['track_artists'] = [artist['name'] for artist in track['artists']]
                    track_info['album_name'] = album_details['title']
                    track_info['release_date'] = album_details['year']
                    track_info['track_number'] = track['trackNumber']
                    track_info['total_tracks'] = album_details['trackCount']
                    track_info['album_artists'] = [artist['name'] for artist in album_details['artists']]
                    track_info['lyrics'] = lyrics_utils.get_lyrics(track_info['track_name'], ", ".join(track_info['track_artists']))
                    track_info['thumbnail_url'] = album_details['thumbnails'][-1]['url']

                    tracks_metadata[track['videoId']] = track_info
        if "singles" in artist_details:
            for track in artist_details['singles']['results']:

                album_details = self.ytmusic.get_album(track['browseId'])

                track_info = {}
                track_info['track_name'] = trackname_remove_unnecessary(track['title'])
                track_info['track_artists'] = [artist['name'] for artist in album_details['artists']]
                track_info['release_date'] = track['year']
                track_info['total_tracks'] = -1
                track_info['album_artists'] = []
                track_info['lyrics'] = lyrics_utils.get_lyrics(track_info['track_name'], ", ".join(track_info['track_artists']))
                track_info['thumbnail_url'] = track['thumbnails'][-1]['url']

                tracks_metadata[album_details['tracks'][0]['videoId']] = track_info
        
        return tracks_metadata
    
    def get_metadata_another_metadata(self, title, artists):
        return {}
    
    def download_artist_disocgrapy(self, artist_name, library_path, prefer_spotify_metadata=True):
        track_metadata = self.get_discography_by_artist_youtube(artist_name)

        for id, track_info in track_metadata.items():
            self.download_track_youtube(id)

            track_info_another = self.get_metadata_another_metadata(track_info['track_name'], ", ".join(track_info['track_artists']))
            if track_info_another:
                track_info = track_info_another
            
            file_path = os.path.join(library_path, f"{id}{EXT}")
            new_filename = ", ".join(track_info['track_artists']) + " - " + track_info['track_name'] + EXT

            new_path = os.path.join(library_path, track_info['track_artists'][0], new_filename)
            if track_info['total_tracks'] > 1:
                new_filename = f"{track_info['track_number']}. {new_filename}"
                release_year = track_info['release_date'].split("-")[0]
                new_path = os.path.join(library_path, track_info['track_artists'][0], f"[{release_year}] {track_info['album_name']}", new_filename)

            tag_utils.add_tag_mp3(file_path,track_info)

            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            os.rename(file_path, new_path)

    def download_track_youtube(self,track_id):
        # Construct the URL for YouTube Music
        track_url = f"https://music.youtube.com/watch?v={track_id}"

        # Download using yt-dlp
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            ydl.download([track_url])



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
    """
    logging.debug(f"Get information about track: {artist_name} - {track_name}")

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
        track_info['lyrics'] = lyrics_utils.get_lyrics(track_info['track_name'], ", ".join(track_info['track_artists']))

        # Safely get the thumbnail URL
        images = album.get('images', [])
        track_info['thumbnail_url'] = images[0].get('url', '') if images else ''

    else:
        logging.warning(f"Track {artist_name} - {track_name} was not found.")
    
    return track_info

def get_track_info_genius(track_name, artists_names):
    search_term = f"{artists_names} - {track_name}"
    genius_search_url = f"http://api.genius.com/search?q={search_term}&access_token={api_key.genius_client_access_token}"

    response = make_request(genius_search_url)
    if not response: return {}
        
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
    track_info['lyrics'] = lyrics_utils.get_lyrics(track_info['track_name'], ", ".join(track_info['track_artists']))

    track_info['thumbnail_url'] = track['header_image_url']

    return track_info










if __name__ == "__main__":
    library_path = input("Please enter the path for music library: ").strip()

    muslib = Musiclib(library_path)
    muslib.download_artist_disocgrapy("Big Baby Tape", library_path) # Big Baby Tape