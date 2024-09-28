import os
from dotenv import load_dotenv
import requests
from base64 import b64encode

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

def get_spotify_token():
    auth_string = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = requests.post(url, headers=headers, data=data)
    json_result = result.json()
    return json_result["access_token"]


def search_album_info(artist, album):
    token = get_spotify_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.spotify.com/v1/search?q=album:{album}%20artist:{artist}&type=album&limit=1"

    response = requests.get(url, headers=headers)
    json_result = response.json()

    if 'albums' in json_result and json_result['albums']['items']:
        album_info = json_result['albums']['items'][0]
        album_art_url = album_info['images'][0]['url']  # Largest available image
        release_year = album_info['release_date'][:4]  # Extract year from release date
        return album_art_url, release_year
    else:
        return None, None


# Example usage
artist = "The Beatles"
album = "Abbey Road"
album_art_url, release_year = search_album_info(artist, album)
print(f"Album Art URL: {album_art_url}")
print(f"Release Year: {release_year}")