import json
import traceback
from urllib.parse import urlparse
from typing import Literal, Union
import youtubeParser
import spotifyParser
import musicObjects
from constants import spotify_netloc, urlsync_folder
from mPrint import mPrint as mp, tagType
def mPrint(tag: tagType, text):
    mp(tag, 'musicUtils', text)

def cleanURL(url: str):
    parsed_url = urlparse(url)
    if 'spotify' in parsed_url.netloc: #remove query params from spotify links
        return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    return url

async def asyncFetchTracks(target: str) -> Union[list[musicObjects.Track], None]:
    """return a list of track objects found from an url or query, if the song is only 1, returns a list of one element"""
    mPrint('TEST', f'{target=}')
    parsed_url = urlparse(target)
    if 'spotify' in parsed_url.netloc: # target is a spotify URL
        parsed_url = cleanURL(target)
        try:
            tracks = spotifyParser.fetchTracks(target)
            if tracks == -1:
                mPrint('ERROR', "SPOTIFY AUTH FAILED, add your keys in the .env file if you want to enable spotify functionalities")
                return None
            elif tracks == -2:
                mPrint('ERROR', "The spotify link could not be parsed correctly")
                return None

        except Exception:
            mPrint('ERROR', f"Spotify parser error:\nurl = {target}\n{traceback.format_exc()}")
            return None
    elif 'soundcloud.com' in parsed_url.netloc:
        # parsed_url = cleanURL(parsed_url)
        pass
    else: # target is either a youtube URL or a youtube search query
        try:
            tracks = youtubeParser.fetchTracks(target)
            if tracks == None:
                mPrint('ERROR', f'Youtube parser error for: {target}')
                return None
        except Exception:
            mPrint('ERROR', f"Youtube parser error:\nurl = {target}\n{traceback.format_exc()}")
            return None

    return tracks

#currently same as above
def fetchTracks(target: str) -> Union[list[musicObjects.Track], None]:
    """return a list of track objects found from an url or query, if the song is only 1, returns a list of one element"""

    # mPrint('TEST', f"fetchTracks({target=}, urlsync)")

    #TODO check if url is a playlist
    parsed_url = urlparse(target)
    if 'spotify.com' in parsed_url.netloc: # target is a spotify URL
        parsed_url = cleanURL(target)
        try:
            tracks = spotifyParser.fetchTracks(target)
            if tracks == -1:
                mPrint('ERROR', "SPOTIFY AUTH FAILED, add your keys in the .env file if you want to enable spotify functionalities")
                return None
            elif tracks == -2:
                mPrint('ERROR', "The spotify link could not be parsed correctly")
                return None

        except Exception:
            mPrint('ERROR', f"Spotify parser error:\nurl = {target}\n{traceback.format_exc()}")
            return None
    elif 'soundcloud.com' in parsed_url.netloc:
        # parsed_url = cleanURL(parsed_url)
        pass
    else: # target is either a youtube URL or a youtube search query
        try:
            tracks = youtubeParser.fetchTracks(target)
            if tracks == None:
                mPrint('ERROR', f'Youtube did not find any track for this url: {target}')
                return None
        except Exception:
            mPrint('ERROR', f"There was an error extracting url info:\nurl = {target}\n{traceback.format_exc()}")
            return None

    return tracks

# URLSYNC

def getUrlSync(guildID: int) -> list[dict]:
    urlsync = []
    try:
        with open(f'{urlsync_folder}{guildID}.json', 'r') as f:
            try:
                urlsync = json.load(f)
            except json.decoder.JSONDecodeError:
                pass # file is empty or corrupt?
    except FileNotFoundError:
        with open(f'{urlsync_folder}{guildID}.json', 'w') as _: pass
    except Exception:
        mPrint('ERROR', traceback.format_exc())
    

    return urlsync

def writeUrlSync(guildID: int, data:list[dict]):
    pass

