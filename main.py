import os
import re

from discord.client import Client
from discord import (
    Message,
    Intents,
    DiscordException,
)

from spotify_helper import (
    get_album_name,
    get_track_name,
    build_track_uri,
    get_tracks_to_add,
    get_playlist_length,
    add_track_to_playlist,
)

message_regex_raw = r"[\s\S.]*https://\w+\.spotify.com/(\w+)/(\w+)\?[\s\S.]*"
message_regex = re.compile(message_regex_raw)

class ShareType:
    ALBUM = "album"
    TRACK = "track"
    PLAYLIST = "playlist"

class PlaylistBot(Client):
    playlist_name = os.getenv("SPOTIFY_PLAYLIST_NAME")

    async def on_ready(self):
        print(f"Logged in as: {self.user}")

    async def on_message(self, message: Message):
        if message.channel.name == "music":
            res = re.match(message_regex, message.content)
            if res:
                share_type, asset_id = res.groups()
                n_tracks = get_playlist_length()
                
                if tracks_to_add := get_tracks_to_add(share_type, asset_id, n_tracks):
                    try:
                        for track_id in tracks_to_add:
                            track_uri = build_track_uri(track_id)
                            add_track_to_playlist(track_uri)
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
    client = PlaylistBot(intents=intents)

    if token := os.getenv("DISCORD_TOKEN"):
        client.run(token)
    else:
        print("Cannot access token")
