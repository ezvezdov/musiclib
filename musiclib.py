import os
import re
import json
import time
import base64
import requests
from pathlib import Path

import yt_dlp
from ytmusicapi import YTMusic
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy

import api_key

import lyrics_utils
import tag_utils
import logging_utils


EXT = ".mp3"

def _trackname_remove_unnecessary(track_name):
    name = re.sub(r'\(feat.*?\)|\(ft.*?\)|feat.*|ft.*|\(Feat.*?\)|\(Ft.*?\)|\(prod.*?\)|\[prod.*?\]|\(Prod.*?\)', '', track_name)
    return name.rstrip()


def _get_feat_artists(track_name):
    match = re.search(r'\((?:feat|ft)\.*.*?\)|(?:feat|ft)\.*.*', track_name, re.IGNORECASE)

    if match:
        result = re.sub(r'.*?(feat|ft)\.*', '', match.group(0), flags=re.IGNORECASE).strip("() ")

        artists = re.split(r',|\s&\s', result)

        # Clean up whitespace
        artists = [artist.strip() for artist in artists]

        return artists

    return []

def _replace_slash(str):
    return str.replace("/","⁄")

def _sanitize_filename(filename, replacement="_"):
    """
    Remove or replace unsupported characters in a filename.
    :param filename: Original filename.
    :param replacement: Character to replace unsupported characters.
    :return: Sanitized filename.
    """
    # Define invalid characters for different platforms
    if os.name == 'nt':  # Windows
        invalid_chars = r'[<>:"/|?*\0]'  # Windows-specific invalid characters
    else:  # macOS/Linux
        invalid_chars = r'[\0]'
    
    # Replace invalid characters
    sanitized = re.sub(invalid_chars, replacement, filename)
    
    # Handle reserved names in Windows (optional)
    reserved_names = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                      'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3',
                      'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
    if os.name == 'nt' and sanitized.upper().split('.')[0] in reserved_names:
        sanitized = f"{replacement}{sanitized}"
    
    return sanitized

def _get_image(url, retries=3, delay=2):
    for attempt in range(retries):
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode('utf-8')
        else:
            time.sleep(delay)

    logging_utils.logging.warning(f"Failed to download image. Status code: {response.status_code}")
    return {}

def _find_mp3_files(directory):
    return list(Path(directory).rglob("*.mp3"))

def _init_track_info():
    track_info = {}
    track_info['ytm_id'] = ""
    track_info['ytm_title'] = ""
    track_info['track_name'] = ""
    track_info['track_artists'] = []
    track_info['track_artists_str'] = ""
    track_info['release_date'] = ""
    track_info['album_name'] = ""
    track_info['album_artists'] = []
    track_info['track_number'] = ""
    track_info['total_tracks'] = ""
    track_info['lyrics'] = ""
    track_info['thumbnail'] = ""
    return track_info

class Musiclib():
    def __init__(self, library_path):

        self.ydl_opts = {
            'format': 'bestaudio/best',  # Select the best audio format available
            'outtmpl': '%(id)s.%(ext)s',  # Custom output template
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
            'quiet': True,  # Show progress and details
            'cookiefile': "assets/cookies.txt",
        }

        self.info_path = '.musiclib'

        self.library_path = library_path
        self.db_path = "db.json"
        self._backup_path_prefix = "musiclib_backup_"
        self._init_library()

        self.db = {}
        self.__load_db()

        self.ytmusic = YTMusic()
        self.ydl = yt_dlp.YoutubeDL(self.ydl_opts)

        
    
    def _init_library(self):

        # Ensure the path ends with a slash (optional)
        self.library_path = os.path.join(self.library_path, '')

        # Create the directory
        try:
            os.makedirs(self.library_path, exist_ok=True)
            logging_utils.logging.debug(f"Folders created successfully at: {self.library_path}")
        except Exception as e:
            logging_utils.logging.error(f"Error creating folders: {e}")

        self.ydl_opts['outtmpl'] = os.path.join(self.library_path, self.ydl_opts['outtmpl'])

        # Database path
        self.info_path = os.path.join(self.library_path, self.info_path)
        os.makedirs(self.info_path, exist_ok=True)
        self.db_path = os.path.join(self.info_path, self.db_path)
        

    def _get_discography_by_artist(self,artist_name):
        search_results = self.ytmusic.search(artist_name, filter="artists")
        if not search_results:
            return {}
        
        artist_browse_id = search_results[0]['browseId']
        artist_details = self.ytmusic.get_artist(artist_browse_id)

        tracks_metadata = {}

        if "albums" in artist_details:
            albums = artist_details['albums']['results']

            if artist_details['albums']['browseId']:
                albums = self.ytmusic.get_artist_albums(artist_details['albums']['browseId'], params=None, limit=None)
            
            for album in albums:
                album_details = self.ytmusic.get_album(album['browseId'])
                for track in album_details['tracks']:        
                    track_info = _init_track_info()
                    track_info['ytm_id'] = track['videoId']
                    track_info['track_name'] = _trackname_remove_unnecessary(track['title'])
                    track_info['track_artists'] = [artist['name'] for artist in track['artists']]
                    track_info['track_artists_str'] = ", ".join(track_info['track_artists'])
                    track_info['album_name'] = album_details['title']
                    track_info['release_date'] = album_details['year']
                    track_info['track_number'] = track['trackNumber']
                    track_info['total_tracks'] = album_details['trackCount']
                    track_info['album_artists'] = [artist['name'] for artist in album_details['artists']]                    
                    track_info['lyrics'] = lyrics_utils.get_lyrics(track_info['track_name'], track_info['track_artists_str'], ytmusic=self.ytmusic, id=track_info['ytm_id'])
                    track_info['thumbnail'] = _get_image(album_details['thumbnails'][-1]['url'])
                    track_info['ytm_title'] = f"{track_info['track_artists_str']} - {track['title']}"

                    tracks_metadata[track_info['ytm_id']] = track_info
        if "singles" in artist_details:
            
            singles = artist_details['singles']['results']
            
            if artist_details['singles']['browseId']:
                singles = self.ytmusic.get_artist_albums(artist_details['singles']['browseId'], params=None, limit=None)

            for track in singles:

                album_details = self.ytmusic.get_album(track['browseId'])

                track_info = _init_track_info()
                track_info['ytm_id'] = album_details['tracks'][0]['videoId']
                track_info['track_name'] = _trackname_remove_unnecessary(track['title'])
                track_info['track_artists'] = [artist['name'] for artist in album_details['artists']] + _get_feat_artists(track['title'])
                track_info['track_artists_str'] = ", ".join(track_info['track_artists'])
                track_info['release_date'] = track['year']
                track_info['track_number'] = ''
                track_info['total_tracks'] = ''
                track_info['album_artists'] = track_info['track_artists']
                track_info['lyrics'] = lyrics_utils.get_lyrics(track_info['track_name'], track_info['track_artists_str'], ytmusic=self.ytmusic, id=track_info['ytm_id'])
                track_info['thumbnail'] = _get_image(track['thumbnails'][-1]['url'])
                track_info['ytm_title'] = f"{track_info['track_artists_str']} - {track['title']}"

                tracks_metadata[track_info['ytm_id']] = track_info
        
        return tracks_metadata
    
    def download_artist_discography(self, artist_name):
        track_metadata = self._get_discography_by_artist(artist_name)

        for id, track_info in track_metadata.items():
            self._download_by_id(id, track_info)
    
    def download_track_by_name(self, search_term, download_top_result=False):
        tracks = self.ytmusic.search(search_term, filter="songs")
        
        for track in tracks:
            album_details = self.ytmusic.get_album(track['album']['id'])

            track_info = _init_track_info()


            track_info['track_name'] = _trackname_remove_unnecessary(track['title'])
            track_info['track_artists'] = [artist['name'] for artist in track['artists']] + _get_feat_artists(track['title'])
            track_info['track_artists_str'] = ", ".join(track_info['track_artists'])

            # Doesn't work normally, because track can have videoId of track and videoId of clip.
            # There are differet ids in search and album for track.
            track_info['ytm_id'] = track['videoId']
            track_info['ytm_title'] = f"{track_info['track_artists_str']} - {track['title']}"


            if not download_top_result:
                track_full_name = track_info['track_artists_str'] + " - " + track_info['track_name']
                answer = input(f"Did you search track {track_full_name}? [y/n]: ")

                # Skip current track
                if answer.lower()[0] != 'y': continue

            track_info['release_date'] = album_details['year']

            if album_details['trackCount'] > 1:
                track_info['total_tracks'] = album_details['trackCount']
                track_info['album_name'] = album_details['title']
                track_info['album_artists'] = [artist['name'] for artist in album_details['artists']]

                for t in album_details['tracks']:
                    if t['title'] == track_info['track_name']:
                        track_info['track_number'] = t['trackNumber']
            else:
                track_info['album_artists'] = track_info['track_artists']

            track_info['lyrics'] = lyrics_utils.get_lyrics(track_info['track_name'], track_info['track_artists_str'], ytmusic=self.ytmusic, id=track_info['ytm_id'])
            track_info['thumbnail'] = _get_image(album_details['thumbnails'][-1]['url'])

            
            self._download_by_id(track_info['ytm_id'],track_info)
            return
    
    def backup_library(self):
        track_metadata = dict()
        mp3_files = _find_mp3_files(self.library_path)
        for mp3_path in mp3_files:
            track_info = tag_utils.get_tag_mp3(mp3_path)

            mp3_rpath = os.path.relpath(str(mp3_path), start=self.library_path)
            track_info['path'] = mp3_rpath

            track_metadata[track_info['ytm_id']] = track_info
        

        formatted_timestamp = time.strftime('%Y%m%d%H%M%S', time.localtime())
        backup_path = os.path.join(self.info_path, f'{self._backup_path_prefix}{formatted_timestamp}.json')

        with open(backup_path, "w", encoding="utf-8") as file:
            json.dump(track_metadata, file, indent=4, ensure_ascii=False)
        
        return backup_path
            
    def restore_library(self, backup_filepath):
        if not os.path.exists(backup_filepath):
            print(f"File {backup_filepath} doesn't exist.")
            return
        if not os.path.isfile(backup_filepath):
            print(f"File {backup_filepath} is directory.")
            return
        
        track_metadata = {}
        with open(backup_filepath, "r", encoding="utf-8") as file:
            track_metadata = json.load(file)
        
        for id, track_info in track_metadata.items():
            self._download_by_id(id, track_info)   

    def _download_by_id(self, id, track_info):
        if id in self.db: return

        self.__download_track_youtube(id)
        
        file_path = os.path.join(self.library_path, f"{id}{EXT}")

        # Add tag to the track
        tag_utils.add_tag_mp3(file_path,track_info)

        # Rename and move track
        self.__move_downloaded_track(id, track_info)
        
        # Save database
        self.db[id] = track_info['track_artists_str'] + " - " + track_info['track_name']
        self.__write_db()

    def __move_downloaded_track(self, id, track_info):
        file_path = os.path.join(self.library_path, f"{id}{EXT}")
        new_filename = _replace_slash(track_info['track_artists_str']) + " - " + _replace_slash(track_info['track_name']) + EXT

        new_path = os.path.join(self.library_path, track_info['track_artists'][0], new_filename)
        if track_info['total_tracks']:
            if track_info['track_number']:
                new_filename = f"{track_info['track_number']}. {new_filename}"
            release_year = track_info['release_date'].split("-")[0]
            new_path = os.path.join(self.library_path, _replace_slash(track_info['track_artists'][0]), f"[{release_year}] {_replace_slash(track_info['album_name'])}", new_filename)

        if os.path.exists(new_path):
            rpath = os.path.relpath(new_path, start=self.library_path)
            new_path = os.path.join(self.library_path, "DUPLICATE", rpath)

        if 'path' in track_info:
            new_path = os.path.join(self.library_path,os.path.normpath(track_info['path']))

        new_path = _sanitize_filename(new_path)

        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        os.rename(file_path, new_path)
        print(f"Successfully downloaded {new_path}")


    def __download_track_youtube(self,track_id):
        # Construct the URL for YouTube Music
        track_url = f"https://music.youtube.com/watch?v={track_id}"

        # Download using yt-dlp
        self.ydl.download([track_url])
    
    def __write_db(self):
        # write database to the db.json file
        with open(self.db_path, "w", encoding="utf-8") as file:
            json.dump(self.db, file, indent=4, ensure_ascii=False)

    def __load_db(self):
        # fetch database from db.json file
        if not os.path.exists(self.db_path) or not os.path.isfile(self.db_path):
            self.__write_db()

        with open(self.db_path, "r", encoding="utf-8") as file:
            self.db = json.load(file)



class MusiclibS(Musiclib):
    def __init__(self, library_path):
        super().__init__(library_path)

        # Authenticate with Spotify
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=api_key.spotify_client_id, client_secret=api_key.spotify_client_secret))

    def _get_track_info_spotify(self, track_name, artist_name):
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
        logging_utils.logging.debug(f"Get information about track: {artist_name} - {track_name}")

        # Construct the query
        query = f"track:{track_name} artist:{artist_name}"
        results = self.sp.search(q=query, type="track", limit=1)

        track_info = _init_track_info()

        if results.get('tracks', {}).get('items', []):
            track = results['tracks']['items'][0]
            album = track.get('album', {})

            track_info['track_name'] = _trackname_remove_unnecessary(track.get('name', ''))
            track_info['track_artists'] = [artist['name'] for artist in track['artists']]
            track_info['track_artists_str'] = ", ".join(track_info['track_artists'])
            track_info['release_date'] = album.get('release_date', '')

            if int(album['total_tracks']) > 1:
                track_info['album_name'] = album.get('name', '')
                track_info['track_number'] = track.get('track_number', '')
                track_info['total_tracks'] = album.get('total_tracks', '')
                track_info['album_artists'] = [artist['name'] for artist in album['artists']]
            else:
                track_info['album_artists'] = track_info['track_artists']

            track_info['lyrics'] = lyrics_utils.get_lyrics(track_info['track_name'], track_info['track_artists_str'])
            track_info['thumbnail'] = _get_image(album['images'][0]['url'])

        else:
            logging_utils.logging.warning(f"Track {artist_name} - {track_name} was not found.")
        
        return track_info

    def _get_all_artist_albums(self, artist_id):
        albums = []
        for album_type in ['album', 'single', 'compilation']:
            results = self.sp.artist_albums(artist_id, album_type=album_type)
            albums.extend(results['items'])

            while results['next']:
                results = self.sp.next(results)
                albums.extend(results['items'])

        return albums

    def _get_discography_by_artist(self,artist_name):
        results = self.sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
        if results['artists']['items']:
            artist = results['artists']['items'][0]
            artist_id = artist['id']
        else:
            return {}


        tracks_metadata = []


        albums = self._get_all_artist_albums(artist_id)

        for album in albums:
            # Fetch tracks for each album
            tracks = self.sp.album_tracks(album['id'])
            for track in tracks['items']:
                track_info = _init_track_info()
                track_info['track_name'] = _trackname_remove_unnecessary(track['name'])
                track_info['track_artists'] = [artist['name'] for artist in track['artists']]
                track_info['track_artists_str'] = ", ".join(track_info['track_artists'])
                track_info['release_date'] = album['release_date'].split("-")[0]

                if int(album['total_tracks']) > 1:
                    track_info['album_name'] = album['name']
                    track_info['track_number'] = track['track_number']
                    track_info['total_tracks'] = album['total_tracks']
                    track_info['album_artists'] = [artist['name'] for artist in album['artists']]
                else:
                    track_info['album_artists'] = track_info['track_artists']

                track_info['lyrics'] = lyrics_utils.get_lyrics(track_info['track_name'], track_info['track_artists_str'])
                track_info['thumbnail'] = _get_image(album['images'][0]['url'])

                tracks_metadata.append(track_info)
        return tracks_metadata
    
    def download_artist_discography(self, artist_name):
        tracks_metadata = self._get_discography_by_artist(artist_name)

        for track_info in tracks_metadata:
            self._download_track_by_metdata(track_info)
    
    def _download_track_by_metdata(self, track_info):
        search_term = f"{track_info['track_artists_str']} - {track_info['track_name']}"
        tracks = self.ytmusic.search(search_term, filter="songs")
        
        if tracks:
            track_info['ytm_id'] = tracks[0]['videoId']

            # Add additional info about title from youtube music
            artists = [artist['name'] for artist in tracks[0]['artists']]
            artists_str = ", ".join(artists)
            track_info['ytm_title'] = f"{artists_str} - {tracks[0]['title']}"

            self._download_by_id(track_info['ytm_id'],track_info)



if __name__ == "__main__":
    library_path = input("Please enter the path for music library: ").strip()
    artist_name = input("Please enter artist name: ").strip()

    # ml = Musiclib(library_path)
    # ml.download_artist_discography(artist_name)

    mls = MusiclibS(library_path)
    mls.download_artist_discography(artist_name)