import os

import spotipy

from functools import reduce
from typing import Set, Optional
from concurrent.futures import ThreadPoolExecutor

from spotipy.oauth2 import SpotifyOAuth

scopes = "playlist-read-collaborative,playlist-modify-public,playlist-modify-private"

client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scopes,
))


def _get_track_name(track_id: str) -> Optional[str]:
    track = sp.track(track_id)
    if track:
        return track["name"]


def _get_album_name(album_id: str) -> Optional[str]:
    album = sp.album(album_id)
    if album:
        return album["name"]


def _get_playlist_name(playlist_id: str) -> Optional[str]:
    playlist = sp.playlist(playlist_id)
    if playlist:
        return playlist["name"]


SHARE_TYPES = {
    "track": _get_track_name,
    "album": _get_album_name,
    "playlist": _get_playlist_name,
}

def get_shared_asset_name(share_type: str, asset_id: str) -> Optional[str]:
    if share_type in SHARE_TYPES:
        return SHARE_TYPES[share_type](asset_id)


def _build_track_uri(track_id: str) -> str:
    return f"spotify:track:{track_id}"


def _get_playlist_length(playlist_id: str) -> int:
    res = sp.playlist(playlist_id=playlist_id, fields="tracks.total")
    if res:
        return res["tracks"]["total"]
    return 0

def _get_page_track_ids(playlist_id: str, item_limit: int, i: int) -> Set[str]:
    res = sp.playlist_items(
        playlist_id=playlist_id,
        fields="items.track.id",
        limit=item_limit,
        offset=i*item_limit,
    )
    if res:
        valid_items = filter(lambda x: x and x["track"], res["items"])
        item_ids = set(map(lambda x: x["track"]["id"], valid_items))
        return item_ids
    return set()


def _get_tracks_in_page(playlist_id: str, track_ids: Set[str], item_limit: int, i: int) -> Set[str]:
    item_ids = _get_page_track_ids(playlist_id, item_limit, i)
    if item_ids:
        return track_ids & item_ids
    return set()


def _get_album_tracks(album_id) -> Set[str]:
    res = sp.album_tracks(album_id=album_id)
    if res:
        return set(map(lambda track: track["id"], res["items"]))
    return set()


def _get_external_playlist_tracks(playlist_id: str) -> Set[str]:
    n_tracks = _get_playlist_length(playlist_id)
    n_pages = n_tracks // 100 + 1
    
    args_list = [
        (playlist_id, 100, i)
        for i in range(n_pages)
    ]
    pages = map(lambda x: _get_page_track_ids(*x), args_list)
    track_ids = reduce(lambda x, y: x | y, pages, set())
    return track_ids


def get_tracks_to_add(playlist_id: str, share_type: str, asset_id: str) -> Set[str]:
    max_workers = 5
    item_limit = 100

    n_tracks = _get_playlist_length(playlist_id)
    
    print("Total tracks: ", n_tracks)
    print("Share type: ", share_type)
    print("Asset ID: ", asset_id)

    n_pages = n_tracks // item_limit + 1

    if share_type == "album":
        track_ids = _get_album_tracks(asset_id)
    elif share_type == "playlist":
        track_ids = _get_external_playlist_tracks(asset_id)
    else:
        track_ids = set([asset_id])

    with ThreadPoolExecutor(max_workers=max_workers) as e:
        args_list = [
            (playlist_id, track_ids, item_limit, i)
            for i in range(n_pages)
        ]
        res = e.map(lambda x: _get_tracks_in_page(*x), args_list)
        tracks_in_playlist = reduce(lambda x, y: x | y, res, set())
        return track_ids - tracks_in_playlist


def add_tracks_to_playlist(playlist_id: str, track_ids: Set[str]):
    track_uris = map(_build_track_uri, track_ids)
    return sp.playlist_add_items(
        playlist_id=playlist_id,
        items=track_uris,
    )
