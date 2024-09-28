import os

import requests
from dotenv import load_dotenv
from notion_client import Client
from base64 import b64encode
from bs4 import BeautifulSoup
import tempfile

# Load environment variables
load_dotenv()

# Initialize Notion client
notion = Client(auth=os.getenv("NOTION_TOKEN"))

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

def get_database_items(database_id):
    """Retrieve all items from the Notion database"""
    results = []
    has_more = True
    start_cursor = None

    while has_more:
        response = notion.databases.query(
            database_id=database_id,
            start_cursor=start_cursor
        )
        results.extend(response["results"])
        has_more = response["has_more"]
        start_cursor = response["next_cursor"]

    return results


def search_album_info_from_google(artist, album, min_width=500, min_height=500):
    """Search for album art and release year"""
    search_query = f"{artist} {album}"
    url = f"https://www.google.com/search?q={search_query}+album&tbm=isch"

    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")

    # extract album art url (this is a simplified example and may need adjustment)
    img_tags = soup.find_all("img")
    album_art_url = img_tags[1]["src"] if len(img_tags) > 1 else None

    # extract release year (this is a simplified example and may need adjustment)
    year_element = soup.find("span", string=lambda text: text and "released" in text)
    release_year = year_element.find_next("span").text if year_element else None

    return album_art_url, release_year


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


def search_album_info_from_spotify(artist, album):
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


def download_image(image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        return response.content
    return None


def upload_to_imgbb(image_data):
    api_key = os.getenv("IMGBB_API_KEY")
    url = "https://api.imgbb.com/1/upload"

    files = {
        'image': image_data
    }
    params = {
        'key': api_key
    }

    response = requests.post(url, files=files, params=params)
    if response.status_code == 200:
        return response.json()['data']['url']
    return None


def update_notion_item(page_id, album_art_url, release_year, artist, album):
    """Update Notion database item with album art and release year"""
    properties = {}

    if album_art_url:
        # Download the image
        image_data = download_image(album_art_url)
        if image_data:
            # Upload the image to imgbb
            hosted_url = upload_to_imgbb(image_data)

            if hosted_url:
                properties["Album Art"] = {
                    "files": [
                        {
                            "name": f"{artist} - {album} Cover",
                            "type": "external",
                            "external": {
                                "url": hosted_url
                            }
                        }
                    ]
                }

    if release_year:
        try:
            release_year_int = int(release_year)
            properties["Release Year"] = {"number": release_year_int}
        except ValueError:
            print(f"Invalid release year for page {page_id}: {release_year}")

    if properties:
        try:
            notion.pages.update(
                page_id=page_id,
                properties=properties
            )
            print(f"Successfully updated page {page_id}")
        except Exception as e:
            print(f"Error updating page {page_id}: {str(e)}")
    else:
        print(f"No updates for page {page_id}")


def main():
    database_id = os.getenv("NOTION_DATABASE_ID")
    items = get_database_items(database_id)

    for item in items:
        try:
            artist = item["properties"]["Artist"]["rich_text"][0]["plain_text"] if item["properties"]["Artist"][
                "rich_text"] else None
            album = item["properties"]["Album"]["title"][0]["plain_text"] if item["properties"]["Album"][
                "title"] else None

            # Grab number of album art files
            album_art_file_list = item["properties"]["Album Art"]["files"] if item["properties"]["Album Art"] else None
            album_art_file_number = len(album_art_file_list) if album_art_file_list else 0

            # If album art, skip
            if album_art_file_number:
                print(f"Skipping {artist} - {album} - already have album art")
                continue

            if artist is None or album is None:
                print(f"Missing artist or album information for item: {item['id']}")
                continue

            album_art_url, release_year = search_album_info_from_spotify(artist, album)

            # If Spotify search fails, try Google search
            if album_art_url is None or release_year is None:
                album_art_url, release_year = search_album_info_from_google(artist, album)

            if album_art_url or release_year:
                update_notion_item(item["id"], album_art_url, release_year, artist, album)
                print(f"Updated {artist} - {album}")
            else:
                print(f"Couldn't find information for {artist} - {album}")
        except Exception as e:
            print(f"An error occurred while processing item {item['id']}: {str(e)}")



if __name__ == "__main__":
    main()