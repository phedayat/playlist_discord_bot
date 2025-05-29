import os
import re
import sys

from discord.client import Client
from discord import Message, Intents

from time import perf_counter

from spotify_helper import (
    get_tracks_to_add,
    get_shared_asset_name,
    add_tracks_to_playlist,
)

message_regex = re.compile(r"[\s\S.]*https://\w+\.spotify.com/(\w+)/(\w+)\?[\s\S.]*")

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
                share_type_str = share_type.capitalize()

                asset_name = get_shared_asset_name(share_type, asset_id)
                if asset_name is None:
                    await message.reply(f"Unsupported share type: {share_type}")
                    return

                timer_start = perf_counter()

                if tracks_to_add := get_tracks_to_add(self.playlist_id, share_type, asset_id):
                    add_tracks_to_playlist(self.playlist_id, tracks_to_add)
                    
                    await message.reply(f"{share_type_str} \"{asset_name}\" added to \"{self.playlist_name}\"")
                else:
                    await message.reply(f"{share_type_str} \"{asset_name}\" already exists in playlist \"{self.playlist_name}\"")
                
                timer_end = perf_counter()
                duration = timer_end-timer_start
                print(f"Duration: {duration}")


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
