import os

import spotipy

from functools import reduce
from typing import List, Set, Optional
from concurrent.futures import ThreadPoolExecutor

from spotipy.oauth2 import SpotifyOAuth

class ShareType:
    ALBUM = "album"
    TRACK = "track"
    PLAYLIST = "playlist"

scopes = "playlist-read-collaborative,playlist-modify-public,playlist-modify-private"

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=scopes,
    )
)


def build_track_uri(track_id: str) -> str:
    return f"spotify:track:{track_id}"


def get_playlist_length(playlist_id: str) -> int:
    res = sp.playlist(playlist_id=playlist_id, fields="tracks.total")
    if res:
        return res["tracks"]["total"]
    return 0


def get_track_name(track_id: str) -> Optional[str]:
    track = sp.track(track_id)
    if track:
        return track["name"]


def get_album_name(album_id: str) -> Optional[str]:
    album = sp.album(album_id)
    if album:
        return album["name"]


def _get_tracks_in_page(playlist_id: str, track_ids: Set[str], i: int, item_limit: int) -> Optional[Set[str]]:
    res = sp.playlist_items(
        playlist_id=playlist_id,
        fields="items.track.id",
        limit=item_limit,
        offset=i*item_limit,
    )
    if res:
        items = filter(None, res["items"])
        item_ids = map(lambda track: track["id"], items)
        item_ids_set = frozenset(item_ids)
        return track_ids & item_ids_set


def _get_album_tracks(album_id) -> Optional[Set[str]]:
    res = sp.album_tracks(album_id=album_id)
    if res:
        return set(map(lambda track: track["id"], res["items"]))


def _get_external_playlist_tracks(playlist_id):
    item_limit = 100

    res = sp.playlist(
        playlist_id=playlist_id,
        fields="tracks(total, items.track.id)",
    )
    if res:
        tracks = res["tracks"]
        out = [item["track"]["id"] for item in tracks["items"] if item["track"]]

        n_pages = tracks["total"] // item_limit + 1
        for i in range(n_pages):
            res = sp.playlist(
                playlist_id=playlist_id,
                fields="tracks(total, items.track.id)",
            )
            if res:
                tracks = res["tracks"]
                out += [item["track"]["id"] for item in tracks["items"]]
        return set(out)


def get_tracks_to_add(playlist_id: str, share_type: str, asset_id: str) -> Optional[Set[str]]:
    max_workers = 3
    item_limit = 100

    n_tracks = get_playlist_length(playlist_id)
    n_pages = n_tracks // item_limit + 1

    if share_type == "album":
        album_tracks = _get_album_tracks(asset_id)
        track_ids = album_tracks or set()
    elif share_type == "playlist":
        playlist_tracks = _get_external_playlist_tracks(asset_id)
        track_ids = playlist_tracks or set()
    else:
        track_ids = set([asset_id])

    with ThreadPoolExecutor(max_workers=max_workers) as e:
        args_list = [
            (track_ids, i, item_limit)
            for i in range(n_pages)
        ]
        res = e.map(lambda x: _get_tracks_in_page(*x), args_list)
        if res:
            items = filter(None, res)
            tracks_in_playlist = reduce(lambda x, y: x | y, items)
            return track_ids - tracks_in_playlist


def add_tracks_to_playlist(playlist_id: str, track_uris):
    return sp.playlist_add_items(
        playlist_id=playlist_id,
        items=track_uris,
    )
