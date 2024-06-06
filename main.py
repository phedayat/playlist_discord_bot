import os
import re

from discord.client import Client
from discord import DiscordException, Intents, Message

from spotify_helper import (
    build_track_uri,
    track_in_playlist,
    add_track_to_playlist,
)

message_regex_raw = r"[\s\S.]*https://\w+\.spotify.com/track/(\w+)\?[\s\S.]*"
message_regex = re.compile(message_regex_raw)

class PlaylistBot(Client):
    playlist_name = os.getenv("SPOTIFY_PLAYLIST_NAME")

    async def on_ready(self):
        print(f"Logged in as: {self.user}")

    async def on_message(self, message: Message):
        if message.channel.name == "music":
            res = re.match(message_regex, message.content)
            if res:
                track_id = res.groups()[0]

                if track_in_playlist(track_id):
                    print(f"Track {track_id} exists")
                    await message.reply(f"Song already exists in playlist \"{self.playlist_name}\"")
                else:
                    track_uri = build_track_uri(track_id)
                    try:
                        add_track_to_playlist(track_uri)
                        await message.reply(f"Song added to playlist \"{self.playlist_name}\"")
                    except DiscordException as e:
                        print(f"Error: {e}")


if __name__=="__main__":
    intents = Intents.default()
    intents.message_content = True
    client = PlaylistBot(intents=intents)

    if token := os.getenv("DISCORD_TOKEN"):
        client.run(token)
    else:
        print("Cannot access token")
