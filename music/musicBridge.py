import os
import traceback
import asyncio
import json
from typing import Any, Literal, Optional, Union
import discord
import discord.ui
from discord import app_commands
from random import shuffle as queueshuffle

import musicUtils
import musicPlayer
import musicObjects
from config import Colors as col, language
from constants import urlsync_folder

if language == "IT":
    from lang import it as lang
elif language == "EN":
    from lang import en as lang

from mPrint import mPrint as mp
def mPrint(tag, text):
    mp(tag, 'musicBridge', text)

def parseUserInput(userQuery:str, playlists : dict[str, list[str]], urlsync: list[dict]) -> Union[list[str], None, Literal[404]]:
    """
    Parses user input and retuns a list of URLs
    :param userQuery: can be an URL, a saved playlist or a youtube search (multiple items delimited by `,`)
    """
    # remove leading and trailing spaces (eg "   url, url, playlist   ")
    userQuery = userQuery.strip()
    parsedQueries = []


    # - if entire query string is exact match with playlist, use that
    if userQuery in [playlist_name for playlist_name in playlists]:
        mPrint('DEBUG', "found saved playlist")
        for track in playlists[userQuery]:
            parsedQueries.append(track)
        return parsedQueries
    
    # - if entire query is present in urlsync, use that
    for data in urlsync:
        if not('youtube_url' in data): 
            continue
        if ('spotify_url' in data) and (userQuery == data['spotify_url']):
            parsedQueries.append(data['youtube_url'])
            mPrint('DEBUG', "spotify_url match urlsync")
            return parsedQueries
        if ('query' in data) and (userQuery == data['query']):
            parsedQueries.append(data['youtube_url'])
            mPrint('DEBUG', "query match urlsync")
            return parsedQueries

    # - else, search track info
    if ',' in userQuery:
        mPrint('DEBUG', "splitting request into multiple queries")
        individualQueries = [q.strip() for q in userQuery.split(',')] # " A, A A,AA" -> ["A", "A A", "AA"]
    else: #one query
        mPrint('DEBUG', "parsing single query")
        individualQueries = [userQuery]

    for query in individualQueries:
        #check for matches against urlsync
        continue_flag = False
        for data in urlsync:
            if not('youtube_url' in data): 
                continue
            if ('spotify_url' in data) and (query == data['spotify_url']):
                parsedQueries.append(data['youtube_url'])
                continue_flag = True
                break
            if ('query' in data) and (query == data['query']):
                parsedQueries.append(data['youtube_url'])
                continue_flag = True
                break
        if continue_flag: continue

        #query is URL
        if "spotify." in query or "youtube.com" in query or "youtu.be" in query:
            mPrint('DEBUG', f'query is URL')
            query = musicUtils.cleanURL(query)
            parsedQueries.append(query)
        
        #query is playlist
        elif query in [playlist_name for playlist_name in playlists]:
            mPrint('DEBUG', f'query is playlist')
            for track in playlists[query]:
                parsedQueries.append(track)
        
        #query is youtube search
        else:
            mPrint('DEBUG', f'query is yt search: ({query})')
            trackURL = musicUtils.youtubeParser.searchYTurl(query)
            if trackURL == None:
                continue
            if trackURL == 404:
                # error print already in searchYTurl()
                return 404
            mPrint('DEBUG', f'found url: {trackURL}')
            parsedQueries.append(trackURL)

    return parsedQueries

async def play(
        user_queries : list[str], 
        interaction : discord.Interaction, 
        bot : discord.Client, 
        tree : app_commands.CommandTree, 
        shuffle : bool, 
        precision : int, 
        urlsync : list[dict], 
        guildPlaylists : dict[str, list[str]]
    ):

    player_channel = interaction.channel

    # initialize queue
    Queue = musicObjects.Queue()

    for query in user_queries:
        #foreach urls find the songs it links to
        tracks = await musicUtils.asyncFetchTracks(query)
        if tracks == None:
            await interaction.followup.send("There was an error processing the url(s)")
            return -1
        for t in tracks:
            Queue.addTrack(t)

    if shuffle:
        Queue.shuffleQueue()
        
    #check that queue is not empty
    if len(Queue.queue) == 0:
        mPrint("ERROR", f"play function did not find any requested track {user_queries}")
        await interaction.followup.send(f"I could not find any track from your input.", ephemeral=True)
        return

    mPrint('DEBUG',f"There are {len(Queue)} songs in queue:")

    #make graphical interface for loading
    if precision != 0:
        desc = f'Now Playing: `                                      `\n▂▂▂▂▂▂▂▂▂▂ (00:00 - 00:00)\n'
    else:
        desc = f'Now Playing: `                                      `\n'
        
    embed = discord.Embed(
        title=f'Loading...',
        description=desc,
        color=col.red
    )

    queuePlaceholder = ''
    for i in range(6):
        queuePlaceholder += f"**{i}**- `                                      `\n"

    embed.add_field(name='Author:', value=f'`               `', inline=True)
    embed.add_field(name='Last 5 in queue', value=f'{queuePlaceholder}', inline=False)
    embed.set_footer(text='🍑 the best bot 🎶 https://notlatif.github.io/CuloBot/#MusicBot')
     
    try: #try connecting to vc
        vchannel = bot.get_channel(interaction.user.voice.channel.id)
        voiceClient : discord.VoiceClient = await vchannel.connect()
    except AttributeError:
        await interaction.followup.send(lang.music.player_user_not_vc, ephemeral=True)
        return
    except discord.ClientException:
        await interaction.followup.send(lang.music.player_bot_other_vc, ephemeral=True)
        return
    
    #Define commands enum
    class Commands: # ALL IDs MUST BE UNIQUE
        previous = 0,
        play_pause = 1,
        skip = 2,
        stop = 3,
        shuffle = 4,
        loop_one = 5,
        loop_queue = 6,
        report = 7,
        clear_queue = 8,
        resend_queue = 9,
        remove = 10,
        move = 11,
        add_song = 12,
        loop = 13
        pause = 14
        resume = 15

    #Define buttons
    buttonsCommands: dict[int, tuple[str, int, discord.ButtonStyle | None]] = {
        #cmd  : [emoji, row, optional(style)]
        Commands.previous:   ("⏮", 1),
        Commands.play_pause: ("⏯", 1),
        Commands.skip:       ("⏭", 1),
        Commands.stop:       ("⏹", 1, discord.ButtonStyle.red),
        Commands.shuffle:    ("🔀", 2),
        Commands.loop_one:   ("🔂", 2),
        Commands.loop_queue: ("🔁", 2),
        Commands.report:     ("⁉", 2),
    }

    # Make Button constructor
    class EmbedButtons(discord.ui.Button):
        def __init__(self, *, style: discord.ButtonStyle = discord.ButtonStyle.secondary, label: Optional[str] = None, disabled: bool = False, custom_id: Optional[str] = None, url: Optional[str] = None, emoji: Optional[Union[str, discord.Emoji, discord.PartialEmoji]] = None, row: Optional[int] = None, command:str):
            if len(label) > 80:
                label = label[:80]
            super().__init__(style=style, label=label, disabled=disabled, custom_id=custom_id, url=url, emoji=emoji, row=row)
            self.command = command
        
        async def callback(self, button_interaction: discord.Interaction) -> Any:
            await button_interaction.response.defer(ephemeral=True)
            #This will be called at button press
            try:
                #Check that user and bot are in the same vc
                if button_interaction.user.voice.channel.id == voiceClient.channel.id:
                    if self.command == Commands.report:
                        await actions(self.command, button_interaction)
                    else:
                        await actions(self.command)
            except AttributeError:
                #user was not in a voice channel
                pass
            
    # Create discord view
    view = discord.ui.View(timeout=None)

    # Add buttons to view
    # buttons : list[discord.ui.Button] = []
    for b in buttonsCommands:
        try:
            style = buttonsCommands[b][2]
        except IndexError:
            style = discord.ButtonStyle.secondary

        btn = EmbedButtons(label="", style=style, emoji=buttonsCommands[b][0], row=buttonsCommands[b][1], custom_id=f"{interaction.id}:playerbuttons:{b}", command=b)
        # buttons.append(btn)
        view.add_item(btn)

    #send embed with view
    await interaction.followup.send("Queue avviata", ephemeral=False)
    embedMSG = await player_channel.send(embed=embed, view=view)

    # Create Player and Embed handlers
    Player = musicPlayer.Player(voiceClient, Queue)
    MessageHandler = musicPlayer.MessageHandler(Player, embedMSG, Queue, precision, view)

    try:
        messageTask = asyncio.create_task(MessageHandler.start())
    except:
        await voiceClient.disconnect()
        voiceClient.cleanup()
        mPrint('FATAL', f'Error while creating tasks for player and message\n{traceback.format_exc()}')
        return

    # Define actions
    async def actions(action:Commands, arg1 = None, arg2 = None, arg3 = None):
        mPrint('DEBUG', f"Requested action: {action=} {arg1=} {arg2=}")

        if action == Commands.previous:
            mPrint('USER', 'Skipping to previous song')
            Player.previous()

        elif action == Commands.skip:
            times = arg1 if arg1 != None else 1
            mPrint('USER', f'Skipping {times} song(s)')
            if Player.queue.isLooped() == 1: # if looping one, remove loop
                Player.set_loop(0)
            Player.skip(times)

        elif action == Commands.shuffle:
            Player.shuffle()
            await MessageHandler.updateEmbed()

        elif action == Commands.play_pause:
            Player.play_pause()
            await MessageHandler.updateEmbed()

        elif action == Commands.pause:
            Player.pause()
            await MessageHandler.updateEmbed()

        elif action == Commands.resume:
            Player.resume()
            await MessageHandler.updateEmbed()

        elif action == Commands.stop:
            await MessageHandler.updateEmbed(True)
            Player.stop()
            messageTask.cancel()
            await voiceClient.disconnect()
            return 0

        elif action == Commands.remove:
            index = int(arg1)
            Player.remove(index)
            Player.skip()
            await MessageHandler.updateEmbed()

        elif action == Commands.clear_queue:
            Player.clear()
            await MessageHandler.updateEmbed()

        elif action == Commands.loop_one:
            if Player.queue.isLooped() == 1:
                Player.set_loop(0)
            else:
                Player.set_loop(1)
            await MessageHandler.updateEmbed()

        elif action == Commands.loop_queue:
            if Player.queue.isLooped() == 2:
                Player.set_loop(0)
            else:
                Player.set_loop(2)
            await MessageHandler.updateEmbed()

        elif action == Commands.loop:
            if arg1 == None:
                if Player.queue.isLooped() == 0: # NO
                    arg1 = 2
                elif Player.queue.isLooped() == 1: # ONE
                    arg1 = 0
                else: # YES
                    arg1 = 0

            Player.set_loop(int(arg1))
            await MessageHandler.updateEmbed()

        elif action == Commands.resend_queue:
            await MessageHandler.embedMSG.clear_reactions()
            await MessageHandler.embedMSG.edit(embed=MessageHandler.getEmbed(move=True))
            MessageHandler.ready = False
            MessageHandler.embedMSG = await player_channel.send(embed=MessageHandler.getEmbed())

            MessageHandler.ready = True
            await MessageHandler.updateEmbed()
        
        elif action == Commands.move:
            Player.move(int(arg1), int(arg2))
            await MessageHandler.updateEmbed()

        elif action == Commands.add_song:
            targets = arg1
            index = 0 if arg2 == None else arg2
            shuffle = arg3

            tracks : list[musicObjects.Track] = []
            
            targets = parseUserInput(targets, guildPlaylists, urlsync)
            # mPrint('TEST', f"add_song {targets=}, {index=}, {shuffle=}")
            if targets == None or targets == 404 or targets == [None]: return None

            for t in targets:
                mPrint('TEST', f"{t=}")
                for track in await musicUtils.asyncFetchTracks(t):
                    tracks.append(track)

            # Search did not find any track
            if tracks == []: return None

            #if shuffle is not passed and playershuffle is enabled: shuffle
            #elif player requested shuffle: shuffle; else: don't shuffle (implied)
            if shuffle == None and Queue.isShuffle: queueshuffle(tracks)
            elif shuffle: queueshuffle(tracks)

            mPrint('DEBUG', f'Adding {len(t)} track(s)')
            for t in tracks:
                # mPrint('TEST', f'Adding track: {t.title}@{index}')
                Player.add_track(t, index)
                index += 1
            
            await MessageHandler.updateEmbed(pnext=index)
            return tracks
        
        elif action == Commands.report:
            interaction : discord.Interaction = arg1
            reportedTrack = Player.currentTrack
            class Feedback(discord.ui.Modal, title='Grazie per la segnalazione!'):
                input = discord.ui.TextInput(label="Se vuoi puoi dare un link come suggerimento", style=discord.TextStyle.short, required=False, placeholder='https://www.youtube.com/')
                
                async def on_submit(self, submit_interaction: discord.Interaction):
                    await submit_interaction.response.defer(ephemeral=True)
                    try:
                        suggested_url = self.input.value

                        if suggested_url != None:
                            if 'youtube.com' not in suggested_url:
                                await submit_interaction.followup.send("Suggestions must be youtube links.", ephemeral=True)
                                return
                            
                            # Create urlsync compatible object
                            newSuggestion = [{ "youtube_url": suggested_url, "query": Player.currentTrack.getQuery() }]
                            if(Player.currentTrack.spotifyURL): 
                                newSuggestion[0]['spotify_url'] = Player.currentTrack.spotifyURL
                            
                            # Read content from urlsync
                            with open(f'{urlsync_folder}{str(interaction.guild.id)}.json', 'r+') as f:
                                f.seek(0)
                                alreadySuggested = []
                                try: alreadySuggested = json.load(f) #read contents for already reported tracks
                                except json.decoder.JSONDecodeError: 
                                    mPrint('DEBUG', f"json.decoder.JSONDecodeError")
                                    pass # file is probably empty, it will be overwritten either way 

                                mPrint('TEST', f"{alreadySuggested=}")

                                # merge newSuggestion with already suggested tracks
                                tmp_merge = {}
                                for d in alreadySuggested + newSuggestion:
                                    tmp_merge.setdefault(d['youtube_url'], {}).update(d)
                                alreadySuggested = [tmp_merge[d] for d in tmp_merge]

                                # merge newSuggestion with urlsync
                                tmp_merge = {}
                                for d in urlsync + newSuggestion:
                                    tmp_merge.setdefault(d['youtube_url'], {}).update(d)
                                Player.urlsync = [tmp_merge[d] for d in tmp_merge]

                                f.seek(0)
                                json.dump(alreadySuggested, f, indent=2)
                                f.truncate()
                                mPrint('TEST', f"{alreadySuggested=}")
                            
                            # play suggested track and skip the (presumably) wrong track
                            if type(parseUserInput(suggested_url, guildPlaylists, urlsync)) == list:
                                resp = await actions(Commands.add_song, suggested_url, 0)
                                if resp == None:
                                    await submit_interaction.followup.send("Could not find your suggested track.", ephemeral=True)
                                    return

                                #delete (and skip) track if it didn't already finish
                                if reportedTrack == Player.currentTrack: 
                                    await actions(Commands.remove, 0)
                            else:
                                # failed to find suggested track
                                mPrint('DEBUG', "Unable to find suggested track.")
                                await submit_interaction.followup.send("Could not find your suggested tracks.", ephemeral=True)
                                return

                        mPrint('INFO', f"User reported discrepancy for song {Player.currentTrack.getQuery()}")
                        await submit_interaction.followup.send("Thanks for your suggestion!", ephemeral=True)

                    except Exception:
                        mPrint('ERROR', traceback.format_exc())
                        await submit_interaction.followup.send("There was an error.", ephemeral=True)        

            await interaction.response.send_modal(Feedback())

    # SLASH COMMANDS
    def checkAuthor(interaction: discord.Interaction):
        #Check that the user sent the message in the right channel and is connected in the right vc
        try:
            return interaction.channel.id == player_channel.id and interaction.user.voice.channel.id == voiceClient.channel.id
        except AttributeError:
            return False
        
    @tree.command(name="prev", description="Vai alla traccia precedente", guild=interaction.guild)
    async def prev(interaction: discord.Interaction):
        if checkAuthor(interaction):
            await interaction.response.defer(ephemeral=True)
            await actions(Commands.previous)
            await interaction.followup.send("Done")

    @tree.command(name="skip", description="Vai alla traccia successiva", guild=interaction.guild)
    async def skip(interaction: discord.Interaction, times: int=1):
        """
        :param times: quante volte skippare
        """
        if checkAuthor(interaction):
            await interaction.response.defer(ephemeral=True)
            await actions(Commands.skip, times)
            await interaction.followup.send(f"Skipped {times} tracks", ephemeral=True)

    @tree.command(name="shuffle", description="Attiva/Disattiva lo shuffle", guild=interaction.guild)
    async def queue_shuffle(interaction: discord.Interaction):
        if checkAuthor(interaction):
            await interaction.response.defer(ephemeral=True)
            await actions(Commands.shuffle)
            await interaction.followup.send("Done")

    @tree.command(name="play_pause", guild=interaction.guild)
    async def play_pause(interaction: discord.Interaction):
        if checkAuthor(interaction):
            await interaction.response.defer(ephemeral=True)
            await actions(Commands.play_pause)
            await interaction.followup.send("Paused" if Player.isPaused else "Resumed", ephemeral=True)   

    @tree.command(name="pause", guild=interaction.guild)
    async def pause(interaction: discord.Interaction):
        if checkAuthor(interaction):
            await interaction.response.defer(ephemeral=True)
            await actions(Commands.pause)
            await interaction.followup.send("Paused", ephemeral=True)  

    @tree.command(name="resume", guild=interaction.guild)
    async def resume(interaction: discord.Interaction):
        if checkAuthor(interaction):
            await interaction.response.defer(ephemeral=True)
            await actions(Commands.resume)
            await interaction.followup.send("Resumed", ephemeral=True)  

    @tree.command(name="stop", description="Cancella la playlist e ferma la riproduzione", guild=interaction.guild)
    async def stop(interaction: discord.Interaction):
        if checkAuthor(interaction):
            await interaction.response.defer(ephemeral=True)
            await actions(Commands.stop)
            await interaction.followup.send("Stopped queue.", ephemeral=True)

    @tree.command(name="remove", description="Rimuovi una traccia", guild=interaction.guild)
    async def remove(interaction: discord.Interaction, index: int = 0):
        """
        :param index: quale traccia eliminare
        """
        if checkAuthor(interaction):
            await interaction.response.defer(ephemeral=True)
            await actions(Commands.remove, index)
            await interaction.followup.send(f"Rmoved track {index}.", ephemeral=True)

    @tree.command(name="clear_queue", description="Cancella la playlist", guild=interaction.guild)
    async def clear(interaction: discord.Interaction):
        if checkAuthor(interaction):
            await interaction.response.defer(ephemeral=True)
            await actions(Commands.clear_queue)
            await interaction.followup.send("Cleared Queue.", ephemeral=True)

    @tree.command(name="loop", guild=interaction.guild)
    @app_commands.choices(mode=[
        app_commands.Choice(name="No", value="0"),
        app_commands.Choice(name="One song", value="1"),
        app_commands.Choice(name="Playlist", value="2"),])
    async def loop(interaction: discord.Interaction, mode: str):
        if checkAuthor(interaction):
            await interaction.response.defer(ephemeral=True)
            await actions(Commands.loop, int(mode))
            await interaction.followup.send(f"Ok")

    @tree.command(name="move", description="Scambia due tracce", guild=interaction.guild)
    async def move(interaction: discord.Interaction, traccia1: int, traccia2: int):
        if checkAuthor(interaction):
            await interaction.response.defer(ephemeral=True)
            await actions(Commands.move, traccia1, traccia2)
            await interaction.followup.send(f"Ho scambiato {traccia1} con {traccia2}", ephemeral=True)

    @tree.command(name="add_song", description="Aggiungi canzone in queue", guild=interaction.guild)
    async def add_song(interaction: discord.Interaction, url: str, position: str = '0', shuffle: bool = None):
        """
        :param position: Usa 'END' per aggiungere una traccia alla fine (default: 0)
        """
        if 'end' in position.lower():
            position = len(Player.queue)
        
        if type(position) == str and not position.isnumeric():
            mPrint('WARN', f'User used unsupported value for addsong {position} defaulting to 0')
            position = 0

        if checkAuthor(interaction):
            await interaction.response.defer(ephemeral=True)
            resp = await actions(Commands.add_song, url, int(position), shuffle)

            if resp == None:
                await interaction.followup.send(f"C'è stato un errore durante la ricerca della traccia {url}", ephemeral=True)
                return
            else:
                if len(resp) == 1:
                    try: message = f"Ho aggiunto {resp[0]} in queue"
                    except AttributeError: message = 'Fatto'
                else:
                    message = f"Fatto"
                await interaction.followup.send(message, ephemeral=True)
            
    @tree.command(name="report", description="Avvisa che la canzone trovata su youtube è sbagliata.", guild=interaction.guild)
    async def report(interaction: discord.Interaction):
        if checkAuthor(interaction):
            await actions(Commands.report, interaction)

    mPrint('INFO', 'syncing commands')
    asyncio.create_task(tree.sync(guild=interaction.guild))

    # @bot.event
    # async def on_interaction(interaction : discord.Interaction):
    #     mPrint('TEST', f"{interaction.id=}")


    val = Player.playQueue()
    mPrint('TEST', f"player.playQueue() returned with code {val}")

    #while player.isplaying: continue
    # TODO
