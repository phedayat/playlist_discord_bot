import os
import re
import sys

from discord.client import Client
from discord import (
    Message,
    Intents,
    DiscordException,
)

from spotify_helper import (
    ShareType,
    get_album_name,
    get_track_name,
    build_track_uri,
    get_tracks_to_add,
    get_playlist_length,
    add_tracks_to_playlist,
)

message_regex_raw = r"[\s\S.]*https://\w+\.spotify.com/(\w+)/(\w+)\?[\s\S.]*"
message_regex = re.compile(message_regex_raw)

class PlaylistBot(Client):
    def __init__(self, playlist_id: str, playlist_name: str, **kwargs):
        super().__init__(**kwargs)
        self.playlist_name = playlist_name
        self.playlist_id = playlist_id

    async def on_ready(self):
        print(f"Logged in as: {self.user}")

    async def on_message(self, message: Message):
        if message.channel.name == "music":
            res = re.match(message_regex, message.content)
            if res:
                share_type, asset_id = res.groups()
                n_tracks = get_playlist_length(self.playlist_id)
                
                if tracks_to_add := get_tracks_to_add(self.playlist_id, share_type, asset_id):
                    try:
                        track_uris = map(build_track_uri, tracks_to_add)
                        add_tracks_to_playlist(self.playlist_id, track_uris)
                        
                        if share_type == ShareType.TRACK:
                            track_name = get_track_name(asset_id)
                            await message.reply(f"Track \"{track_name}\" added to \"{self.playlist_name}\"")
                        else:
                            album_name = get_album_name(asset_id)
                            await message.reply(f"Album \"{album_name}\" added to \"{self.playlist_name}\"")
                        return
                    except DiscordException as e:
                        print(f"Error: {e}")
                else:
                    if share_type == ShareType.TRACK:
                        track_name = get_track_name(asset_id)
                        await message.reply(f"Track \"{track_name}\" already exists in playlist \"{self.playlist_name}\"")
                    else:
                        album_name = get_album_name(asset_id)
                        await message.reply(f"Album \"{album_name}\" already exists in playlist \"{self.playlist_name}\"")
                    return


if __name__=="__main__":
    intents = Intents.default()
    intents.message_content = True

    playlist_name = os.getenv("SPOTIFY_PLAYLIST_NAME")
    playlist_id = os.getenv("SPOTIFY_PLAYLIST_ID")

    if playlist_id is None:
        print("Must set SPOTIFY_PLAYLIST_ID")
        sys.exit(1)
    elif playlist_name is None:
        print("Must set SPOTIFY_PLAYLIST_NAME")
        sys.exit(1)

    client = PlaylistBot(
        playlist_id,
        playlist_name,
        intents=intents,
    )

    if token := os.getenv("DISCORD_TOKEN"):
        client.run(token)
    else:
        print("Cannot access token")
