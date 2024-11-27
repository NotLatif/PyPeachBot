import json
import os
import traceback
import yt_dlp
from typing import Literal, Union
from random import shuffle, randrange

from mPrint import mPrint as mp
def mPrint(tag, text):
    mp(tag, 'musicObjects', text)

youtubeDomain = '' #LEAVE BLANK (switch from youtube_dl to yt_dlp)
download = False
if not os.path.isfile("music/.yt_cookies.txt"):
    mPrint('WARN', 'file `music/.yt_cookies.txt` is missing, explicit songs may get skipped.')
    mPrint('WARN', 'For info look into README.md')
    ydl_opts = {
        'quiet': True,
        'ignoreerrors': True,
        'writedescription': False,
        'extract_flat': 'in_playlist',
    }
else:
    ydl_opts = {
        'quiet': True,
        'ignoreerrors': True,
        'writedescription': False,
        'extract_flat': 'in_playlist',
        'cookiefile': 'music/.yt_cookies.txt',
    }

class Track:
    def __init__(self, source, url, title, artists: list[dict[str, str]], durationSeconds, youtubeURL= None, thumbnailURL = None, explicit = None, spotifyThumbnail = None, spotifyURL = None) -> None:
        self.source = source
        self.url = url
        self.title = title
        self.artists = artists
        self.durationSeconds = durationSeconds
 
        self.youtubeURL = youtubeURL
        self.thumbnailURL = thumbnailURL
        self.explicit = explicit
        self.spotifyThumbnail = spotifyThumbnail
        self.spotifyURL = spotifyURL

    def getSource(self) -> Union[Literal['spotify', 'youtube', 'soundcloud'], None]: #soundcloud should be coming soon
        if self.url == None:
            return 'query'
        if 'spotify' in self.url:
            return 'spotify'
        elif 'youtube' in self.url:
            return 'youtube'
        elif 'soundcloud' in self.url:
            return 'soundcloud'
        else:
            return None
        
    def getArtists(self) -> str:
        if self.artists[0]['name'] == '': # [{name?: "name", url?: "url"}, ...]
            return "N/A"

        artists = ""
        for a in self.artists:
            try:
                artists += f"{a['name']}, "
            except KeyError: #tracks with not artist name?
                mPrint("DEBUG", f"found track without artist name; artist object: {a}")
                continue
    
        return artists[:-2] #remove last ", " before returning

    def getVideoUrl(self, search = True) -> Union[str, None]:
        if self.youtubeURL != None: return self.youtubeURL

        if search == False: return None

        # we don't know the url but we can search it
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            mPrint('DEBUG', f'Searching URL -> {self.getQuery()}')
            try:
                r_result = ydl.extract_info(f"ytsearch:{self.getQuery()}", download=False)
                result = r_result['entries'][0]
            except TypeError:
                mPrint('ERROR', 'Query result is null (?)')
                mPrint('DEBUG', f"result: {r_result}")
                return None
            except IndexError:
                mPrint('ERROR', 'Query result is empty (?)')
                mPrint('DEBUG', f"result: {r_result}")
                return None
            except Exception:
                mPrint('ERROR', 'Exception in getVideoUrl')
                mPrint('DEBUG', f"result: {r_result}")
                return None


            try:
                int(result['duration'])
            except TypeError: #If duration is null video is probably was live, just skip it
                mPrint('DEBUG', f'Skipping live video {youtubeDomain}{result["url"]}')
                return None

            #while at it, we can also update the duration to match the youtube video duration
            self.durationSeconds = int(result['duration'])
            self.youtubeURL = f'{youtubeDomain}{result["url"]}'
            if self.artists == None: self.artists = result['uploader']
            # mPrint('TEST', f'getURL() -> found |{youtubeDomain}{result["url"]}|')
            return f'{youtubeDomain}{result["url"]}'

    def getVideoThumbnailUrl(self) -> Union[str, None]:
        # mPrint('FUNC', "Track.getVideoThumbnailUrl()")
        if self.thumbnailURL != None: 
            return self.thumbnailURL

        # we don't know the url but we can search it
        videoUrl = self.getVideoUrl()
        if videoUrl == None:
            mPrint('WARN', 'getVideoUrl() returned None')
            return None

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            mPrint('DEBUG', f'Searching thumbnail for {videoUrl}')
            try:
                result = ydl.extract_info(videoUrl, download)
                self.thumbnailURL = result['thumbnail']
                # mPrint('TEST', f'getThumbnail() -> found |{result["thumbnail"]}|')
                return result['thumbnail']
            except yt_dlp.utils.DownloadError:
                mPrint('ERROR', 'youtube_dl.utils.DownloadError: (Probably) Age restricted video')
                return None
    
    def getQuery(self) -> str:
        """Returns a youtube search query for the Track"""
        if self.artists[0]['name'] == '':
            return self.title
        return f"{self.title} {self.artists[0]['name']}{' (Explicit)' if self.explicit else ''}"
    
    def toDict(self, search = False) -> dict:
        # mPrint('FUNC', "Track.toDict()")
        if self.artists == ['']: artists = None
        else: artists = self.artists

        return {
            "title": self.title,
            "artists": artists,
            "url": self.url,
            "youtube_url": self.getVideoUrl(search),
            "spotify_url": self.spotifyURL,
            "search_query": self.getQuery(),
            "duration_seconds": self.durationSeconds,
            "spotify_image": self.spotifyThumbnail,
            "explicit": self.explicit
        }

    def __str__(self) -> str:
        artistString = ""
        if self.artists[0]['name'] != '':
            for a in self.artists:
                artistString += f"{a['name']}, "
            return f'{self.title} [{artistString[:-2]}]' #:-2 to remove the last ', '
        else:
            return self.title

    def __len__(self) -> int:
        return self.durationSeconds

NO = 0
ONE = 1
YES = 2

class Queue:
    def __init__(self) -> None:
        self.queue:list[Track] = []
        self.queueOrder:list[int] = [] # contains pointers for the playing order
        self.alreadyPlayed:list[int] = [] # needed to return to previous song(s)
        self.isShuffle = False
        self.__loop = NO

        self.queue_changed = False # var used by updater.py to sync data
        self.modifier_changes = False # wether modifiers like 'shuffle' get enabled/disabled

    def addTrack(self, track:Track, index:int = None) -> None:
        self.queue.append(track)
        self.queue_changed = True
        if index == None:
            self.queueOrder.append(len(self.queue)-1)
        else:
            self.queueOrder.insert(index, len(self.queue)-1)
        # mPrint('TEST', f"ADDED {track.title} @ {index}")
        return

    def shuffleQueue(self) -> None:
        mPrint('MUSIC', 'Shuffling queue')
        self.queue_changed = True
        self.isShuffle = True
        shuffle(self.queueOrder)

    def unshuffleQueue(self) -> None:
        mPrint('MUSIC', 'Unshuffling queue')
        self.queue_changed = True
        self.isShuffle = False
        self.queueOrder.sort()

    def setLoop(self, value:Literal[0,1,2]) -> None:
        """
        no loop = 0\n
        loop one = 1\n
        loop playlist = 2
        """

        if value == NO:
            mPrint('MUSIC', 'No looping')
            self.__loop = NO

        elif value == ONE:
            mPrint('MUSIC', 'Looping one')
            self.__loop = ONE
            return

        elif value == YES:
            mPrint('MUSIC', 'Looping playlist')
            self.__loop = YES
        
        else:
            mPrint('ERROR', f'Value for setRepeat() [{value}] is invalid')

    def isLooped(self) -> int:
        return self.__loop

    def previous(self) -> None:
        """Goes back 1 song in queue without playing it"""
        if len(self.alreadyPlayed) == 0:
            mPrint('DEBUG', 'Called Queue.previous() but there are no previous songs.')
            return
            
        self.queue_changed = True
        if self.__loop == ONE: return

        self.queueOrder.insert(0, self.alreadyPlayed.pop())
        try:
            self.queueOrder.insert(0, self.alreadyPlayed.pop())
        except IndexError:
            pass
        

    def getNext(self) -> Union[Track, None]:
        """Returns the current track object and increments the index"""
        #If loop ONE return the same track
        if self.__loop == ONE:
            mPrint('TEST', f'Returning looped song {self.alreadyPlayed}')
            return self.queue[self.alreadyPlayed[-1]]
        
        # Behaviour after last song (or after all shuffled songs have played)
        if len(self.queueOrder) == 0 or len(self.alreadyPlayed) == len(self.queue):
            #norepeat returns no song
            if self.__loop == NO:
                return None

            #repeating queue returns the first song
            else: 
                self.alreadyPlayed = []
                self.queueOrder = [x for x in range(len(self.queue))]
                if self.isShuffle:
                    self.shuffleQueue()
        
        t = self.queue[self.queueOrder[0]]
        self.alreadyPlayed.append(self.queueOrder.pop(0))
        return t
    
    def hasNext(self) -> bool:
        if self.__loop == ONE: return True
        #  ( no more songs to play ) or (      all songs were already played     )
        if len(self.queueOrder) == 0 or len(self.alreadyPlayed) == len(self.queue):
            if self.__loop == NO:
                return False

            else: # repeating playlist
                return True
        
        if len(self.queueOrder) != 0:
            return True
    
    def skipMultiple(self, times) -> None:
        """Skip multiple tracks at once (call getNext to return the next one)"""
        for x in range(times):
            self.alreadyPlayed.append(self.queueOrder.pop(0))

    def removeAtIndex(self, index) -> None:
        try:
            if index == 0:
                self.alreadyPlayed.pop() # current track's index is the last one in this list
            else:
                self.queueOrder.pop(index-1) # Next track's index is the first one in this list
        except IndexError:
            pass

    def clear(self) -> None:
        self.queue_changed = True
        self.queue:list[Track] = []
        self.queueOrder:list[int] = []
        self.alreadyPlayed:list[int] = []
        self.isShuffle = False
        self.__loop = NO

    def getCurrentTrack(self) -> Track:
        """Returns currently playing track object without skipping"""
        try:
            return self.queue[self.alreadyPlayed[-1]]
        except IndexError:
            mPrint('ERROR', f'While trying to getCurrentTrack() at index [-1]\n{self.alreadyPlayed=}\n{traceback.format_exc()}')
    
    def getTrackAtIndex(self, index) -> Union[Track, None]:
        try:
            return self.queue[self.queueOrder[index]]
        except IndexError:
            return None

    def getQueueDict(self, limit = 100) -> list[dict]:
        """Returns the queue in playing order as a list of dictionaries"""
        return [ t.toDict() for t in self.getQueue(limit)]

    def getQueue(self, limit = 5) -> list[Track]:
        """Returns the Tracks in playing order starting from next one playing"""
        tracks = []
        if limit > len(self):
            limit = len(self)

        # mPrint('TEST', f"limit: {limit}; queueOrder: {self.queueOrder}; len(queue): {len(self)}")
        
        for x in range(limit):
            # mPrint('TEST', f'Getting {x} ({self.queueOrder[x]})')
            tracks.append(self.queue[self.queueOrder[x]])
        return tracks

    def move(self, arg1, arg2) -> None:
        self.queue_changed = True
        self.queueOrder.insert(arg2-1, self.queueOrder.pop(arg1-1))
    
    def isLoopOne(self) -> bool:
        return True if self.__loop == 1 else False

    def isLoopQueue(self) -> bool:
        return True if self.__loop == 2 else False

    def __len__(self):
        return len(self.queueOrder)
    
    def __str__(self) -> str:
        string = ''
        for i, track in enumerate(self.getQueue()):
            string += f'{i}: {str(track)}\n'
        return string


class ytThumbDTO:
    url: str
    height: int
    width: int
    id: str | None
    resolution: str | None

class ytTrackDTO:
    _type: str
    ie_key: str
    id: str
    url: str
    title: str
    # description: str
    duration: int
    channel_id: str
    channel: str
    channel_url: str
    uploader: str
    uploader_id: str | None
    uploader_url: str | None
    thumbnails: list[ytThumbDTO]
    # ...
    view_count: int

class ytPlistDTO:
    id: str
    title: str
    availability: str
    # description: str
    thumbnails: list[ytThumbDTO]
    playlist_count: int
    channel: str
    channel_id: str
    channel_url: str
    uploader: str
    uploader_id: str
    uploader_url: str
    entries: list[ytTrackDTO]
    webpage_url: str
    original_url: str
    #keys: ['id', 'title', 'availability', 'channel_follower_count', 'description', 'tags', 'thumbnails', 'modified_date', 'view_count', 
        # 'playlist_count', 'channel', 'channel_id', 'uploader_id', 'uploader', 'channel_url', 'uploader_url', '_type', 'entries', 
        # 'extractor_key', 'extractor', 'webpage_url', 'original_url', 'webpage_url_basename', 'webpage_url_domain', 'epoch']