import os
import re
import sys
from dataclasses import dataclass

from discord.client import Client
from discord import Message, Intents

from time import perf_counter

from spotify_helper import (
    get_tracks_to_add,
    get_shared_asset_name,
    add_tracks_to_playlist,
)

message_regex = re.compile(r"[\s\S.]*https://\w+\.spotify.com/(\w+)/(\w+)\?[\s\S.]*")
default_blame = "an unknown suspect from long long ago"

@dataclass
class HistoryScanResult:
    blame: str | None
    next_cursor: Message | None


async def get_history(curr_asset_id, orig_message_id, history):
    latest_message = None

    async for message in history:
        res = re.match(message_regex, message.content)
        if res:
            share_type, asset_id = res.groups()
            print(share_type, asset_id)
            if asset_id == curr_asset_id:
                if message.id == orig_message_id:
                    print("Originating message match")
                    blame = default_blame
                else:
                    created_at_date = message.created_at.date().isoformat()
                    blame = f"{message.author} @ {created_at_date}"
                return HistoryScanResult(
                    blame=blame,
                    next_cursor=None,
                )
        latest_message = message
    return HistoryScanResult(blame=None, next_cursor=latest_message)


async def get_blame(curr_asset_id, orig_message_id, channel):
    history_factory = channel.history if hasattr(channel, "history") else channel
    cursor = None

    while True:
        history = history_factory(limit=300, oldest_first=True, after=cursor)
        result = await get_history(curr_asset_id, orig_message_id, history)
        if result.blame is not None:
            return result.blame
        if result.next_cursor is None or result.next_cursor == cursor:
            return False
        cursor = result.next_cursor


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
                    blame = await get_blame(asset_id, message.id, message.channel)
                    await message.reply(
                        f"{share_type_str} \"{asset_name}\" already exists in playlist \"{self.playlist_name}\"\n"
                        f"Blame: {blame}"
                    )
                
                timer_end = perf_counter()
                duration = timer_end-timer_start
                print(f"Duration: {duration}")


if __name__=="__main__":
    intents = Intents.default()
    intents.message_content = True
    intents.guild_messages = True
    intents.messages = True

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
