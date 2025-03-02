import os

import spotipy

from typing import List, Set
from concurrent.futures import ThreadPoolExecutor

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


def build_track_uri(track_id):
    return f"spotify:track:{track_id}"


def get_playlist_length():
    res = sp.playlist(playlist_id=playlist_id, fields="tracks.total")
    if res:
        return res["tracks"]["total"]
    return 0


# def get_tracks_names(track_ids: List[int]) -> List[str]:
#     if track_ids == []:
#         return []
#     tracks = sp.tracks(track_ids)
#     track_names = list(map(lambda x: x["name"], tracks))
#     return track_names

def get_track_name(track_id: str) -> str:
    track = sp.track(track_id)
    return track["name"]


def get_album_name(album_id: str) -> str:
    album = sp.album(album_id)
    return album["name"]


def _get_tracks_in_page(track_ids: Set[str], i: int, item_limit: int):
    res = sp.playlist_items(
        playlist_id=playlist_id,
        fields="items.track.id",
        limit=item_limit,
        offset=i*item_limit,
    )
    if res:
        l = [
            item["track"]["id"]
            for item in res["items"]
            if item["track"]
        ]
        items = frozenset(l)
        return track_ids & items


def _get_album_tracks(album_id):
    res = sp.album_tracks(album_id=album_id)
    if res:
        return [track["id"] for track in res["items"]]


def _get_external_playlist_tracks(playlist_id):
    item_limit = 100

    res = sp.playlist(
        playlist_id=playlist_id,
        fields="tracks(total, items.track.id)",
    )
    if res:
        tracks = res["tracks"]
        out = [item["track"]["id"] for item in tracks["items"] if item["track"]]

        n_pages = int(tracks["total"]/item_limit) + 1
        for i in range(n_pages):
            res = sp.playlist(
                playlist_id=playlist_id,
                fields="tracks(total, items.track.id)",
            )
            if res:
                tracks = res["tracks"]
                out += [item["track"]["id"] for item in tracks["items"]]
        return out


def get_tracks_to_add(share_type, asset_id, n_tracks):
    item_limit = 100
    max_workers = 3
    n_pages = int(n_tracks/item_limit)+1

    if share_type == "album":
        if album_tracks := _get_album_tracks(asset_id):
            track_ids = set(album_tracks)
        else:
            track_ids = set()
    elif share_type == "playlist":
        if playlist_tracks := _get_external_playlist_tracks(asset_id):
            track_ids = set(playlist_tracks)
        else:
            track_ids = set()
    else:
        track_ids = set([asset_id])

    with ThreadPoolExecutor(max_workers=max_workers) as e:
        res = e.map(lambda x: _get_tracks_in_page(*x), [
            (track_ids, i, item_limit)
            for i in range(n_pages)
        ])
        if res:
            tracks_in_playlist = set()
            for tracks in res:
                if tracks:
                    tracks_in_playlist |= tracks
            return track_ids - tracks_in_playlist


def add_track_to_playlist(track_uri):
    return sp.playlist_add_items(
        playlist_id=playlist_id,
        items=[track_uri],
    )
