import os
import traceback
from typing import Callable
import discord
import asyncio
import time
from yt_dlp import YoutubeDL, utils

from musicObjects import Track, Queue

import config
from config import Colors as col
from mPrint import mPrint as mp
def mPrint(tag, text):
    mp(tag, 'musicPlayer', text)

max_precision = config.timeline_max

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    # 'postprocessors': [{
    #     'key': 'FFmpegExtractAudio',
    #     'preferredcodec': 'mp3',
    #     'preferredquality': '192',
    # }],
    'outtmpl': '%(title)s.%(etx)s',
    'quiet': True,
    # 'verbose': True
}

if os.path.isfile("music/.yt_cookies.txt"):
    YDL_OPTIONS['cookiefile'] = 'music/.yt_cookies.txt'

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

def conversion(sec):
    sec = int(sec)
    sec_value = sec % (24 * 3600)
    hour_value = sec_value // 3600
    sec_value %= 3600
    min = sec_value // 60
    sec_value %= 60
    h = f'{int(hour_value):02}:' if int(hour_value) != 0 else ''
    return f'{h}{int(min):02}:{int(sec_value):02}'

def textToSeconds(text):
    text = text.split(':')
    seconds = 0
    if len(text) >= 3: seconds += (3600 * int(text[-3]))
    if len(text) >= 2: seconds += (60 * int(text[-2]))
    seconds += int(text[-1])
    
    return seconds

class Player():
    def __init__(self, vc : discord.VoiceClient, queue : Queue) -> None:
        mPrint('DEBUG', 'called Player __init__')
        self.queue : Queue = queue
        self.currentTrack : Track = None

        self.voiceClient = vc
        self.isConnected = True
        self.timeout = config.no_music_timeout  # time for bot to stay in vc after queue ends
        self.isWaiting = False                  # whether the bot is waiting after queue ends

        #flags needed to communicate with EmbedHandler
        self.wasReported = False
        self.skipped = False
        self.isPaused = False
        self.songStartTime = 0
        self.songStarted = False
        self.pauseStart = 0
        self.pauseEnd = 0

        # user spotify activity sync feature [WIP]
        # self.isSpotifySync = False

        # currently unused
        self.modifiersChanged = False

        # for future observer pattern implementation
        # self.asyncObservers: list[Callable[[str], None]] = []
        self.observers: list[Callable[[str], None]] = []

    # Observer pattern
    def notify(self, message):
        if (message in ["play_pause", "resume", "pause", "loop", "shuffle"]):
            self.modifiersChanged = True
        
        # for o in self.asyncObservers:
        #     try: asyncio.create_task(o(message))
        #     except: mPrint('ERROR', f"Error notifying async observer\n{o}({message=})\n{traceback.format_exc()}")

        for o in self.observers:
            try: o(message)
            except: mPrint('ERROR', f"Error notifying observer\n{o}({message=})\n{traceback.format_exc()}")

    def subscribe(self, callable: Callable[[dict], None], isasync = False):
        if isasync:
            self.asyncObservers.append(callable)
        else:
            self.observers.append(callable)

    async def waitAfterQueueEnd(self) -> bool:
        self.isWaiting = True
        if self.timeout == -1: # wait indefinitely for user input
            mPrint('INFO', "Waiting until new track gets added or bot gets disconnected")
            while True:
                await asyncio.sleep(1)
                if self.queue.hasNext():
                    mPrint('DEBUG', "Found new song, playing...")
                    self.isWaiting = False
                    return True
                if not self.isConnected: #Stop waiting if the user stops or disconnects the bot
                    mPrint('DEBUG', "Bot was disconnected by user, stopping wait function")
                    self.isWaiting = False
                    return False
        #else
        mPrint('INFO', f"Waiting ({self.timeout}seconds) until new track gets added or bot gets disconnected")
        start = time.time()
        while time.time() - start < self.timeout:
            await asyncio.sleep(1)
            if self.queue.hasNext():
                self.isWaiting = False
                mPrint('DEBUG', "Found new song, playing...")
                return True
            if not self.isConnected: #Stop waiting if the user stops or disconnects the bot
                mPrint('DEBUG', "Bot was disconnected by user, stopping wait function")
                self.isWaiting = False
                return False
        self.isWaiting = False
        return False

    # Player functions

    def playQueue(self, error = None):
        self.notify("queueNext")
        if error != None: mPrint('ERROR', f"{error}")

        # get current track and check that it exists
        self.currentTrack = self.queue.getNext()
        if self.currentTrack == None: #if there is no next
            if self.timeout == 0: # if timeout is 0s, quit
                mPrint('INFO', f'QUEUE Ended, quitting.')
                self.stop()
                return 0

            # else wait for user the estabilished time            
            if not asyncio.run(self.waitAfterQueueEnd()):
                # No song added after timeout
                mPrint('INFO', f'QUEUE Ended, quitting after {self.timeout}')
                self.stop()
                return 0
            else:
                self.currentTrack = self.queue.getNext()

        if self.isConnected == False:
            mPrint('INFO', "Disconnected from voice.")

        mPrint('INFO', "Playing next track")
        if self.isPaused: self.resume()

        try:
            song_url = self.currentTrack.getVideoUrl()
            mPrint('DEBUG', f'URL: {song_url}')
            if song_url == None:
                # careful with recursion
                
                self.playQueue(f"Expected video url, got None, trying next\n[{self.currentTrack.title}]({self.currentTrack.url})")
                return

            if self.voiceClient.is_playing(): 
                # if this triggers something very weird happened
                mPrint('ERROR', 'musicbot was already playing, stopping song.')
                self.voiceClient.stop()
            
            mPrint('MUSIC', f'Now Playing: ({self.currentTrack.title}) URL = {song_url}')

            info = 0
            with YoutubeDL(YDL_OPTIONS) as ydl:
                try:
                    info = ydl.extract_info(song_url, download=False)
                except utils.DownloadError:
                    # careful with recursion
                    self.playQueue("Error trying to download song")
                    return

            # get and play audio data
            format_url = info['url']
            source = discord.FFmpegPCMAudio(format_url, **FFMPEG_OPTIONS)
            self.songStarted = True
            self.songStartTime = time.time()
            try:
                self.voiceClient.play(source, after=self.playQueue)
            except discord.errors.ClientException:
                mPrint('WARN', "bot was disconnected from vc with ClientException")
                mPrint('WARN', traceback.format_exc())
               
        except discord.ClientException:
            #bot got disconnected
            mPrint('FATAL', f'Bot is not connected to vc {traceback.format_exc()}')
            self.stop()
            return -1

        except Exception:
            mPrint('FATAL', traceback.format_exc())
    
    def skip(self, times = 1):
        if self.queue.isLooped() == 1:
            self.queue.setLoop(0) # if looping one, remove loop
            self.notify("loop")

        if times == 1:
            mPrint('MUSIC', f'Track skipped.')
        else:
            mPrint('MUSIC', f'Skipping {times} tracks')
            self.queue.skipMultiple(times-1)

        self.voiceClient.stop()
        self.skipped = True
        #self.notify("skip")

    def previous(self):
        self.queue.previous()
        self.voiceClient.stop() #automatically starts next (previous) track
        self.notify("previous")
    
    def shuffle(self):
        if self.queue.isShuffle:
            self.queue.unshuffleQueue()
        else:
            self.queue.shuffleQueue()
        self.notify("shuffle")

    def play_pause(self):
        if self.isPaused: self.resume()
        else: self.pause()
        self.notify("play_pause")

    def pause(self):
        mPrint('MUSIC', 'Pausing song')
        self.voiceClient.pause()
        self.isPaused = True
        self.notify("pause")
        self.pauseStart = time.time()

    def resume(self):
        mPrint('MUSIC', 'Resuming song')
        self.voiceClient.resume()
        self.isPaused = False
        self.notify("resume")
        self.pauseStart = time.time()

    def remove(self, index = 0):
        self.queue.removeAtIndex(index)
        self.notify("queueEdit")

    def clear(self): #kind of does not make sense this just seems like stop() but spicy
        self.queue.clear()
        self.notify("queueEdit")

    def stop(self):
        self.isWaiting = False
        self.isConnected = False
        self.voiceClient.cleanup()
        self.clear()
        return 0

    def set_loop(self, loopMode):
        self.queue.setLoop(loopMode)
        self.notify("loop")

    def move(self, fromIndex: int, toIndex: int):
        self.queue.move(fromIndex, toIndex)
        self.notify("queueEdit")

    def add_track(self, track: Track, index: int):
        self.queue.addTrack(track, index)
        self.notify("queueNext")

class MessageHandler():
    class MessageType:
        stop = 0
        playNext = 1,
        leftAlone = 2
        
    #Handles the embed of the player in parallel with the player
    def __init__(self, player : Player, embedMSG : discord.Message, queue : Queue, precision, view : discord.ui.View) -> None:
        mPrint('DEBUG', 'called MessageHandler __init__')
        self.player = player
        self.embedMSG = embedMSG
        self.queue = queue
        self.view = view
        self.ready = False

        self.currentTrack = None

        self.printPrecision = True if precision != 0 else False
        self.timelinePrecision = 1 if precision == 0 else precision
        self.timelineChars = config.timeline_chars
        self.timeBar = []

        self.timeStart = 0
        self.timeDone = 0
        self.stepProgress = 0
        self.duration = 0
        self.pauseDiff = 0

        self.didInformWaiting = False

        self.disconnectedCheck = 6 # When this value gets to 0 the embed loop stops (6 = 3 seconds)

        self.spotifyBtn = discord.ui.Button(label="Listen on Spotify", url="https://culobot.notlatif.com", row=3, disabled=True)
        self.lastThumbnail = None

        self.vchannel : discord.VoiceChannel = player.voiceClient.channel
        self.isAloneInVC = False
        self.aloneTimeStart = 0
        self.maxAloneTime = config.max_alone_time if config.max_alone_time <= 300 else 300

    async def start(self):
        await self.embedLoop()
        # when done stop the player
        await self.player.voiceClient.disconnect()
        self.player.isConnected = False
        mPrint('DEBUG', '[MessageHandler] Queue done, returning.')
        return

    async def embedLoop(self):
        while True:
            if self.player.isWaiting: # wait until Player stops waiting
                if not self.didInformWaiting:
                    mPrint('DEBUG', "Informing user that the bot is waiting")
                    self.didInformWaiting = True
                    await self.updateEmbed()

                await asyncio.sleep(1)
                continue
            self.didInformWaiting = False

            #this will execute after a song ends
            self.timeDone = time.time()
            if not self.player.isConnected:
                mPrint("DEBUG", f"[MessageHandler] detected bot disconnected from VC, stopping embedloop (1) {self.player.isConnected=}")
                await self.updateEmbed(stop = True)
                return

            if not self.player.songStarted:
                # mPrint("TEST", f"[MessageHandler] Song has not started yet, waiting... (duration: {self.player.currentSong['duration_sec']}, done after {self.timeDone - self.timeStart})")
                await asyncio.sleep(0.3)
                if not self.player.isConnected:
                    mPrint("DEBUG", "[MessageHandler][1] Bot was disconnected from vc, stopping embedloop")
                    return
                continue #don't do anything if player did not change song yet

            self.player.songStarted = False #flag song as not started for next iteration
            self.currentTrack = self.queue.getCurrentTrack()
            self.timeBar = [self.timelineChars[0] for x in range(self.timelinePrecision)]

            self.duration = self.currentTrack.durationSeconds
            stepSeconds = float(self.duration) / self.timelinePrecision
            self.stepProgress = 0

            mPrint('MUSIC', f'[MessageHandler] Song duration: {self.duration} sec.')

            initialTime = self.player.songStartTime
            #update timestamp every "step" seconds
            currentStep = 1
            mPrint('DEBUG', f"[MessageHandler] Step duration: {stepSeconds} sec.")
            timeDeltaError = 0
            await self.updateEmbed()
            self.timeStart = time.time()
            while True:
                await asyncio.sleep(0.5) #checked every .5 seconds
                
                # detect if bot looses connection for more than the disconnectedCheck threshold
                if not self.player.voiceClient.is_connected(): self.disconnectedCheck -= 1
                else: self.disconnectedCheck = 6

                if self.disconnectedCheck <= 0: 
                    self.player.isConnected = False
                    mPrint('DEBUG', f"Bot was disconnected for too long {self.disconnectedCheck=} {self.player.isConnected=} {self.player.voiceClient.is_connected()=}")

                # Detect if alone in voice channel
                if len(self.vchannel.members) == 1:
                    self.isAloneInVC == True
                    if self.aloneTimeStart == 0:
                        mPrint('WARN', 'I\'m alone in the vc...')
                        self.aloneTimeStart = time.time()
                    else:
                        if time.time() - self.aloneTimeStart > self.maxAloneTime:
                            mPrint('DEBUG', f'Waited for {time.time() - self.aloneTimeStart}s for people to join, now quitting')
                            self.player.stop()
                            await self.updateEmbed(leftAlone = True)
                            return
                else:
                    if self.isAloneInVC:
                        mPrint('INFO', 'Not alone anymore!')
                        self.isAloneInVC == False
                        self.aloneTimeStart = 0

                if self.player.isPaused: #pause started
                    if self.player.pauseEnd == 0: continue

                    #this won't get executed unless player resumes
                    self.pauseDiff = self.player.pauseStart - self.player.pauseEnd
                    self.player.pauseStart = 0
                    self.player.pauseEnd = 0
                    mPrint('DEBUG', f'[MessageHandler] timePassed = {time.time() - initialTime}')
                    mPrint('DEBUG', f'[MessageHandler] pauseTime = {self.pauseDiff}')
                    mPrint('DEBUG', f'[MessageHandler] paused = {self.player.isPaused}')

                timePassed = time.time() - initialTime + self.pauseDiff
                if self.player.isPaused == False and timePassed >= stepSeconds: # Triggered every time a new step is completed
                    timeDeltaError = timePassed - stepSeconds
                    initialTime = time.time() - timeDeltaError #idk, I think it's good now?

                    self.pauseDiff = 0
                    
                    self.stepProgress = stepSeconds * (currentStep)
                    #update timebar
                    for i in range(currentStep):
                        self.timeBar[i] = self.timelineChars[1]
                                    
                    #update message
                    currentStep += 1
                    await self.updateEmbed()
        
                    #reset time to current step
                    # mPrint('TEST', f"updating after: {timePassed}s; error: {timeDeltaError}")
                    # mPrint('TEST', f'step: {currentStep-1} of {self.timelinePrecision}')
                    
                if currentStep-1 == self.timelinePrecision: # BUG this gets triggered too soon
                    mPrint('DEBUG', "[MessageHandler] Steps finished")
                    break
                
                if self.player.skipped:
                    mPrint('DEBUG', "[MessageHandler] Skip detected")
                    self.player.skipped = False
                    await asyncio.sleep(0.5) #wait for player to get ready
                    break #repeat loop for next song

                # if not self.player.isConnected:
                #     mPrint("DEBUG", "[MessageHandler] detected EOPlaylist, stopping embedloop (2)")
                #     await self.updateEmbed(stop = True)
                #     return

                if not self.player.isConnected:
                    await asyncio.sleep(0.5)
                    if not self.player.isConnected:
                        mPrint("WARN", "[MessageHandler][2] Bot was disconnected from vc, stopping embedloop")
                        return
                    else:
                        mPrint("DEBUG", "[MessageHandler] Bot reconnected")

    def getEmbed(self, stop = False, move = False, pnext = False, leftAlone = False) -> discord.Embed:
        # mPrint('FUNC', "getEmbed()")
        self.currentTrack = self.player.currentTrack
        if self.currentTrack == None and not stop and not leftAlone:
            return None

        # Create queue title, get the next 6 Tracks in queue, add them in the last5 variable (one per line)
        last5 = f'__**0-** {self.currentTrack}__\n'
        queue : list[str] = [str(track) for track in self.queue.getQueue(limit=6)]
        for i in range(len(queue)):
            if pnext != False and pnext == i+1: # add arrow emoji if song was added
                last5 += '➡ '
            last5 += f'**{i+1}-** {queue[i]}\n'
        last5 = last5[:-1] # remove last \n

        # Create variable to store the title
        precision = self.printPrecision * f'{"".join(self.timeBar)} {conversion(self.stepProgress)} / {conversion(self.duration)}\n'

        try:
            desc = f'Now Playing: **{self.currentTrack.title}**\n{precision}'
        except AttributeError:
            desc = f'Now Playing: `                                      `\n▂▂▂▂▂▂▂▂▂▂ (00:00 - 00:00)\n'

        # Create Embed Object with title
        embed = discord.Embed(
            title = f'Queue: {len(self.queue)} songs. {"⏸" * int(self.player.isPaused)} {"🔂" * int(self.queue.isLoopOne())} {"🔁" * int(self.queue.isLoopQueue())} {"🔀" * int(self.queue.isShuffle)}',
            description = desc,
            color = col.orange if self.ready else col.red
            # url = "culobot.notlatif.com/api/{guildId}/{queueID}"
        )

        # Define artists and add them to the embed
        try:
            artists = self.currentTrack.getArtists()
            artistLabel = "Author:" if len(self.currentTrack.artists) >= 1 else "Authors:"
        except AttributeError:
            artists = 'N/A'
            artistLabel = "Author:"
        embed.add_field(name=artistLabel, value=artists)

        # Add latency to the embed
        if self.printPrecision:
            latency = "N/A" if self.player.voiceClient.latency == float('inf') else ("%.3fms" % self.player.voiceClient.latency)
            embed.add_field(name='Latency:', value=f'{latency}')

        if not move:
            # Add songs in queue
            while len(last5) > 1024: # Having more than 1024 chars can return a 400 Bad Request response
                last5 = "\n".join(last5.split('\n')[:-1]) # remove one line at a time starting from last until the lenght is acceptable
            embed.add_field(name='Next in queue:', value=last5, inline=False)
        else:
            # If /queue was used, inform the user with a message in the embed
            last5 = ''
            for i in range(6):
                last5 += f"**{i}**- `                                      `\n"
            embed.add_field(name="This message was moved, you may find the new one below", value=last5, inline=False)
            embed.color = col.black

        embed.set_footer(text='🍑 Powered by CuloBot')
        
        if self.player.isWaiting:
            availableTime = f"{config.no_music_timeout}s" if config.no_music_timeout != -1 else "♾️ time"
            embed.add_field(name="Waiting", value=f"The queue ended, you have {availableTime} to add another track with `/add_song` or stop the bot")
            embed.color = col.white

        if stop:
            embed.add_field(name=f'{"Queue finita" if not self.player.isConnected else "Queue annullata"}', value=f'Grazie per aver ascoltato con CuloBot!', inline=False)
            embed.color = col.black
        elif leftAlone:
            embed.add_field(name="Queue annullata", value="Mi avete lasciato da solo nel canale vocale 😭", inline=False)

        try:
            youtubeURL = self.currentTrack.youtubeURL
        except AttributeError:
            youtubeURL = None

        if self.player.wasReported and not stop:
            embed.add_field(name="Source", value=f"> {youtubeURL}\nQuesto link è stato segnalato, Grazie! 🧡")
        elif not stop and not leftAlone:
            embed.add_field(name="Source", value=f"> {youtubeURL}")#\nÈ la canzone sbagliata? fammelo sapere con il tasto ⁉")
        else:
            embed.add_field(name="Source", value=f"> {youtubeURL}")

        try:
            thumbnailURL = self.currentTrack.getVideoThumbnailUrl()
            if thumbnailURL == None:
                thumbnailURL = self.lastThumbnail
            self.lastThumbnail = thumbnailURL
        except AttributeError:
            thumbnailURL = self.lastThumbnail
        embed.set_image(url=thumbnailURL)
        
        return embed
    
    def updateButtons(self) -> None:
        def clearSourceLinkButtons(): # buttons in row 3
            row3btns = [btn for btn in self.view.children if btn.row == 3]
            for btn in row3btns:
                self.view.remove_item(btn)

        if self.currentTrack == None: return

        if self.currentTrack.source == 'spotify':
            #do not update the buttons if there is nothing to change
            if self.currentTrack.title in self.spotifyBtn.label: return

            clearSourceLinkButtons()
            btnlabel = f"Ascolta {self.currentTrack.title} su Spotify"
            if len(btnlabel) > 80:
                btnlabel = "Ascoltala su spotify"
            self.spotifyBtn.label = btnlabel
            self.spotifyBtn.url = self.currentTrack.spotifyURL
            self.spotifyBtn.disabled = False
            self.view.add_item(self.spotifyBtn)
        else:
            clearSourceLinkButtons()
            self.spotifyBtn.disabled = True

    async def updateEmbed(self, stop = False, pnext = False, leftAlone = False):
        await asyncio.sleep(0.5)
        try:
            if stop or leftAlone:
                mPrint('INFO', '[MessageHandler] Detected stop.')
                self.view.clear_items()
                await self.embedMSG.edit(embed=self.getEmbed(stop=stop, leftAlone=leftAlone), view=self.view)
            else:
                try:
                    self.updateButtons()
                except AttributeError:
                    mPrint('WARN', f"There was a problem updating Buttons, you can probably ignore this\n{traceback.format_exc()}")
                
                embed = self.getEmbed(pnext=pnext)
                if embed != None:
                    await self.embedMSG.edit(embed=embed, view=self.view)
                else:
                    mPrint('WARN', 'Trying to get a new Embed but got None instead.')

        except discord.errors.HTTPException:
            mPrint('ERROR', f"DISCORD ERROR (probably embed had blank value)\n{traceback.format_exc()}")
        except AttributeError:
            mPrint('WARN', f"There was an error while creating the Embed, skipping. {stop=} {pnext=} {leftAlone=}")
            mPrint('WARN', traceback.format_exc())
        except Exception:
            mPrint('ERROR', f"Exception: {traceback.format_exc()}")