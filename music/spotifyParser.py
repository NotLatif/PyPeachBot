import json
import traceback
import spotipy
from musicObjects import Track
from spotipy.oauth2 import SpotifyClientCredentials
from math import ceil

from mPrint import mPrint as mp
def mPrint(tag, value):mp(tag, 'spotifyParser', value)

#Since I had problems getting getenv to work on linux for some reason I'm writing my own function in case someone else has the same problems
import getevn

CLIENT_ID = getevn.getenv('SPOTIFY_ID')
CLIENT_SECRET = getevn.getenv('SPOTIFY_SECRET')

SOURCE = "spotify"

authenticated = False
#Authentication
try:
    client_credentials_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    sp = spotipy.Spotify(client_credentials_manager = client_credentials_manager, requests_timeout=10, retries=5)
    authenticated = True
except spotipy.oauth2.SpotifyOauthError:
    mPrint('WARN', 'Spotify keys are wrong or not present. The bot won\'t be able to play music from spotify')


def spotifyUrlParser(URL:str) -> tuple[str, str]:
    """gets a spotify link and returns a tuple with (URL, type); type can be playlist, album, track"""
    id = URL.split("/")[-1].split("?")[0]
    type = URL.split("/")[-2]
    return (id, type)

def fetchTracks(URL:str) -> list[Track]:
    if not authenticated:
        return -1
    id, type = spotifyUrlParser(URL)

    if type == "playlist": tracks = getTracksFromPlaylist(id)
    elif type == "album": tracks = getTracksFromAlbum(id)
    elif type == "track": tracks = getTracksFromTrack(id)
    else: return -2

    return tracks

#"spsync": [], # {spotify_uri: {query: str, spotify_url: str, youtube_url: str, soundcloud_url?: str}}
def getTracksFromPlaylist(URL) -> list[Track]:
    # mPrint('FUNC', f"spotifyParser.getTracksFromPlaylist({URL=}, urlsync)")
    #acquire playlist size and spotify GET limit
    trackNumber = sp.playlist_tracks(URL)["total"]
    trackLimit = sp.playlist_tracks(URL)["limit"]
    tracks : list[Track] = []

    # when size > limit (eg. 350 songs, 100max)
    # this will GET 100 songs at a time (eg. last GET req. will only have 50 songs)
    for i in range( ceil(trackNumber / trackLimit) ):
        playlistDataRes = sp.playlist_tracks(URL, offset=i*trackLimit)["items"]

        for trackData in playlistDataRes:
            trackData = trackData['track']

            trackSpotifyURL = ""
            if ("spotify" in trackData["external_urls"]):
                trackSpotifyURL = trackData["external_urls"]["spotify"]
            else:
                trackSpotifyURL = f"https://open.spotify.com/playlist/{URL}"
            
            artists : list[dict[str, str]] = [] # [{name: "John", url: "spotify.com/John"}, ...]
            for a in trackData['artists']:
                try:
                    if (a['name'] != ''):
                        artists.append({"name": a['name'], "url": a['external_urls']['spotify']})
                    else:
                        artists.append({"name": ''})
                except KeyError:
                    mPrint('ERROR', f'artists parsing error, artists object:')
                    print(a)
            if len(artists) == 0: artists = [{"name": "N/A", "url": "#"}]

            yt_url = None
            try:
                if trackData['is_local'] == False:
                    tracks.append(Track(
                        SOURCE,
                        trackSpotifyURL,
                        trackData['name'],
                        artists,
                        trackData['duration_ms']/1000,
                        yt_url,
                        explicit = trackData['explicit'],
                        spotifyThumbnail = trackData['album']['images'][-1]['url'],
                        spotifyURL = trackSpotifyURL
                    ))
                else:
                    #For non local tracks the bot will try to get the youtube query when needed
                    tracks.append(Track(
                        'youtube',
                        None,
                        trackData["name"],
                        artists,
                        trackData['duration_ms']/1000
                    ))
            except:
                mPrint('ERROR', f'Track \ntitle: {trackData["name"]}; {artists=}')
                mPrint('TEST', json.dumps(trackData, indent=2))

    return tracks

def getTracksFromAlbum(URL) -> list[Track]:
    # mPrint('FUNC', f"spotifyParser.getTracksFromAlbum({URL=}, urlsync)")
    #acquire playlist size and spotify GET limit
    trackNumber = sp.album_tracks(URL)["total"]
    trackLimit = sp.album_tracks(URL)["limit"]
    tracks : list[Track] = []

    # when size > limit (eg. 350 songs, 100max)
    # this will GET 100 songs at a time (last GET req. will only have 50 songs)

    for i in range( ceil(trackNumber / trackLimit) ):
        albumDataRes = sp.album_tracks(URL, offset=i*trackLimit)["items"]
        for trackData in albumDataRes:
            trackSpotifyURL = ""
            if ("spotify" in trackData["external_urls"]):
                trackSpotifyURL = trackData["external_urls"]["spotify"]
            else:
                trackSpotifyURL = f"https://open.spotify.com/album/{URL}"

            artists : list[dict[str, str]] = [] # [{name: "John", url: "spotify.com/John"}, ...]
            for a in trackData['artists']:
                try:
                    if (a['name'] != ''):
                        artists.append({"name": a['name'], "url": a['external_urls']['spotify']})
                    else:
                        artists.append({"name": ''})
                except KeyError:
                    mPrint('ERROR', f'artists parsing error, artists object:')
                    print(a)
            if len(artists) == 0: artists = [{"name": "N/A", "url": "#"}]
            
            yt_url = None
            tracks.append(Track(
                SOURCE,
                trackSpotifyURL,
                trackData['name'],
                artists,
                trackData['duration_ms']/1000,
                yt_url,
                explicit = trackData['explicit'],
                spotifyThumbnail = None, # Album search does not give image data :(
                spotifyURL = trackSpotifyURL
            ))

    return tracks

def getTracksFromTrack(URL) -> list[Track]:
    # mPrint('FUNC', f"spotifyParser.getTracksFromTrack({URL=}, urlsync)")
    trackData: dict = sp.track(URL)

    trackSpotifyURL = ""
    if ("spotify" in trackData["external_urls"]):
        trackSpotifyURL = trackData["external_urls"]["spotify"]
    else:
        trackSpotifyURL = f"https://open.spotify.com/track/{URL}"

    #make a list of artist names
    artists : list[dict[str, str]] = [] # [{name: "John", url: "spotify.com/John"}, ...]
    for a in trackData['artists']:
        try:
            if (a['name'] != ''):
                artists.append({"name": a['name'], "url": a['external_urls']['spotify']})
            else:
                artists.append({"name": ''})
        except KeyError:
            mPrint('ERROR', f'artists parsing error, artists object:')
            print(a)
    if len(artists) == 0: artists = [{"name": "N/A", "url": "#"}]

    yt_url = None
    #return a single item list with the data
    return [Track(
        SOURCE,
        trackSpotifyURL,
        trackData['name'],
        artists,
        trackData['duration_ms']/1000,
        yt_url,
        explicit = trackData['explicit'],
        spotifyThumbnail = trackData['album']['images'][-1]['url'],
        spotifyURL = trackSpotifyURL
    )]
