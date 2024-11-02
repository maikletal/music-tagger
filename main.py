import os
import requests
import base64
from urllib.parse import quote
from dotenv import load_dotenv
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4, MP4Cover

# Cargar variables de entorno desde el archivo .env
load_dotenv()

CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
API_URL = os.getenv('SPOTIFY_API_URL')
AUTH_URL = os.getenv('SPOTIFY_ACCOUNT_URL')

# Función para obtener el token de acceso
def get_access_token():
    auth_response = requests.post(AUTH_URL, {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    })

    if auth_response.status_code == 200:
        auth_response_data = auth_response.json()
        return auth_response_data['access_token']
    else:
        print(f"Error al obtener el token: {auth_response.status_code}, {auth_response.text}")
        return None

# Obtener el token de acceso
access_token = get_access_token()
artist_genre_cache = {}

def get_genre_from_spotify(title, artist, token):
    search_url = f'{API_URL}/v1/search'
    headers = {
        'Authorization': f'Bearer {token}'
    }
    artist = artist.replace(':', ' ')
    params = {
        'q': f'track:{title} artist:{artist}',
        'type': 'track',
        'limit': 1
    }
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        results = response.json().get('tracks', {}).get('items', [])
        if results:
            artists = results[0]['artists']
            genres = []
            for artist in artists:
                artist_id = artist['id']
                if artist_id in artist_genre_cache:
                    genres.extend(artist_genre_cache[artist_id])
                else:
                    artist_url = f'{API_URL}/v1/artists/{artist_id}'
                    artist_response = requests.get(artist_url, headers=headers)
                    if artist_response.status_code == 200:
                        artist_data = artist_response.json()
                        artist_genres = artist_data.get('genres', [])
                        artist_genre_cache[artist_id] = artist_genres
                        genres.extend(artist_genres)
            return '/'.join(set(genres))  # Devolver géneros únicos como una cadena
        return None

def update_genre(file_path, genre):
    if file_path.endswith('.mp3'):
        audio = MP3(file_path, ID3=EasyID3)
        if audio.tags is None:
            audio.add_tags()
        audio.tags['genre'] = genre
        audio.save()
    elif file_path.endswith('.m4a'):
        audio = MP4(file_path)
        audio.tags['\xa9gen'] = genre
        audio.save()

def process_files(folder_path):
    token = get_access_token()
    if not token:
        print("Error al obtener el token de acceso")
        return

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            try:
                if file.endswith('.mp3') or file.endswith('.m4a'):
                    file_path = os.path.join(root, file)
                    print(f"\n###############\nFile: {file_path}")
                    if file.endswith('.mp3'):
                        audio = MP3(file_path, ID3=EasyID3)
                        title = audio.tags.get('title', [None])[0]
                        artist = audio.tags.get('artist', [None])[0]
                    elif file.endswith('.m4a'):
                        audio = MP4(file_path)
                        title = audio.tags.get('\xa9nam', [None])[0]
                        artist = audio.tags.get('\xa9ART', [None])[0]

                    if title and artist:
                        print(f"Buscando: {title} - {artist} ...")
                        genre = get_genre_from_spotify(title, artist, token)
                        if genre:
                            print(f'Generos: {genre}')
                            update_genre(file_path, genre)
            except Exception as e:
                print(f"Error al procesar {file}: {e}")

# Utiliza la carpeta actual donde se ejecuta el script
current_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")
process_files(current_folder)
