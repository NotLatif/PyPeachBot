import traceback
import yt_dlp
from urllib.parse import urlparse
from musicObjects import Track, ydl_opts, youtubeDomain, download, ytPlistDTO

from mPrint import mPrint as mp
def mPrint(tag, text):
    mp(tag, 'youtubeParser', text)

SOURCE = "youtube"

def searchYTurl(query) -> str:
    """
    gets the url of the first song in queue (the one to play)
    """
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        results = ydl.extract_info(f"ytsearch:{query}", download=False)['entries']
        if(len(results) == 0):
            mPrint('ERROR', "ytsearch result was empty (no track found from query)")
            return 404 
        result = results[0]
        try:
            int(result['duration'])
        except TypeError: #If duration is null video is probably was live, just skip it
            mPrint('DEBUG', f'Skipping live video {youtubeDomain}{result["url"]}')
            return None
        return f'{youtubeDomain}{result["url"]}'

def stampToSec(str : str) -> int:
    seconds = 0
    str = str.split(':')[::-1] # [sec, min, hr, ...]
    if len(str) >= 1: #we have seconds
        seconds += int(str[0])
    if len(str) >= 2: #we have minutes
        seconds += int(str[1]) * 60
    if len(str) >= 3: #we have hrs
        seconds += int(str[2]) * 60
    return seconds

# youtube FETCHER
def fetchTracks(target: str) -> list[Track]|None:
    # mPrint('FUNC', f"youtubeParser.fetchTracks({url=})")
    if "music.youtube.com" in target: #target is youtube music URL
        #replacing the strings gets the same link in youtube video form
        target = target.replace("music.youtube.com", "www.youtube.com", 1)

    elif "www.youtube.com" not in target and "youtu.be" not in target: #
        for x in ['http://', 'https://', 'www.']:
            if x in target: 
                mPrint('DEBUG', 'Link is not a valid URL')
                return None
            
        mPrint("DEBUG", "target is not a youtube link, searching query")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                r_result = ydl.extract_info(f"ytsearch:{target}", download=False)
                response = r_result['entries'][0]
                target = f'{youtubeDomain}{response["url"]}'
                mPrint('DEBUG', f'Found url:{target}')
            except TypeError:
                mPrint('WARN', f'Query result is null (?)')
                mPrint('DEBUG', traceback.format_exc())
                return None            

    # Parse url to get IDs for video and playlist, as well as the current index
    yt_url = urlparse(target)
    url_queries = {x.split('=')[0]:x.split('=')[1] for x in yt_url.query.split('&')}
    
    # parse and check yt url queries
    v, plist, index = None, None, 1
    if ('v' in url_queries): v = url_queries['v']                   # video ID
    if ('list' in url_queries): plist = url_queries['list']         # plist ID
    if ('index' in url_queries): index = int(url_queries['index'])  # plist start index
    if (v == None and plist == None):                               # no video ID and no plist ID (not enough info)
        mPrint('DEBUG', 'url did not contain a video ID nor a playlist ID: skipping target.')
        return None

    response : ytPlistDTO = {} 

    #Extract data from the url NB: videos and playlists have a different structure
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            response = ydl.extract_info(target, False)

        except yt_dlp.utils.DownloadError:
            mPrint('ERROR', f'yt_dlp.utils.DownloadError: (Probably) Age restricted video\n{traceback.format_exc()}')
    
    if len(response) == 0: return None

    # Organize Track info and return
    tracks : list[Track] = []
    
    # target is a playlist
    if plist != None:
        def addTracks(i) -> None:
            videoData = response['entries'][i]

            try:
                duration = int(videoData['duration'])
            except TypeError: # triggers for live and hidden videos
                mPrint('DEBUG', f'Skipping unavailable video {youtubeDomain}{videoData["url"]}')
                return -1

            tracks.append(Track(
                SOURCE,
                f"{youtubeDomain}{videoData['url']}",
                videoData["title"],
                [{"name": videoData["uploader"], "url": videoData["uploader_url"]}],
                duration,
                f"{youtubeDomain}{videoData['url']}",
                None
            ))

        # add songs starting from the selected one
        start_index = 0 # find index of first song (index query not reliable)
        if (v != None):
            for j, video_data in enumerate(response['entries']):
                if v == video_data['id']:
                    start_index = j
                    break
                # if not found add from the first one
                    
        # add tracks from (start_index to end) then (from 0 to start_index)
        for i in range(start_index, len(response['entries'])):
            addTracks(i)
        for i in range(start_index):
            addTracks(i)

    # target is one video
    else: 
        tracks.append(Track(
            SOURCE,
            response['webpage_url'],
            response['title'],
            [{"name": response["uploader"], "url": response["uploader_url"]}],
            int(response['duration']),
            response['webpage_url'],
            response['thumbnail'],
            #response['age_limit']
        ))

    
    return tracks
