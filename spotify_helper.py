import os
import json

import spotipy
from spotipy.oauth2 import SpotifyOAuth

scopes = "playlist-read-collaborative,playlist-modify-public,playlist-modify-private"
playlist_id = os.getenv("SPOTIFY_PLAYLIST_ID")

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=scopes,
    )
)

def _get_track_id(track_url):
    return track_url.split("/")[-1].split("?")[0]

def build_track_uri(track_id):
    return f"spotify:track:{track_id}"

def _get_playlist_length():
    res = sp.playlist(playlist_id=playlist_id, fields="tracks.total")
    if res:
        return res["tracks"]["total"]
    return 0

def track_in_playlist(track_id):
    item_limit = 100
    n_total_tracks = _get_playlist_length()

    n_pages = int(n_total_tracks/item_limit)

    for i in range(n_pages+1):
        res = sp.playlist_items(playlist_id=playlist_id, fields="items.track.id", limit=item_limit, offset=i*item_limit)
        if res:
            items = res["items"]
            ids = set([item["track"]["id"] for item in items])
            if track_id in ids:
                return True
    return False

def add_track_to_playlist(track_uri):
    return sp.playlist_add_items(
        playlist_id=playlist_id,
        items=[track_uri],
    )

if __name__=="__main__":
    pass
