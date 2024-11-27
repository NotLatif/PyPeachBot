#version in line 1 of ./changelog.md
import asyncio
import os
import shutil
import json
import random
import copy
import sys
import traceback
import discord
from discord.utils import get
from datetime import datetime
from discord import app_commands
from typing import Union

#custom modules
sys.path.insert(0, 'utils/')
sys.path.insert(0, 'music/')
sys.path.insert(0, 'chessGame/')
#utils
import config
import getevn
from constants import SETTINGS_TEMPLATE, settings_folder
from config import Colors as col
from mPrint import mPrint as mp
#music and chessGame
import chessBridge
import musicBridge

if config.language == "IT":
    from lang import it as lang
elif config.language == "EN":
    from lang import en as lang
def mPrint(tag, value):mp(tag, 'bot', value)

print()
mPrint('WARN', "# =------------------------------------------------= #")
mPrint('WARN', "#  THIS BOT IS CURRENTLY IN BETA. BUGS ARE EXPECTED  #")
mPrint('WARN', "# =------------------------------------------------= #")
mPrint('WARN', "please submit issues https://github.com/NotLatif/CuloBot/issues")
print()

TOKEN = getevn.getenv('DISCORD_TOKEN', True)
try:
    OWNER_ID = int(getevn.getenv('OWNER_ID')) #(optional) needed for the bot to send you feedback when users use /feedback command
                                        # you will still see user-submitted feedback in the feedback.log file (will be createt automatically if not present)
except ValueError:
    pass

intents = discord.Intents.all()
intents.members = True
intents.messages = True


# ===| INDIVIDUAL GUILD SETTINGS HANDLER (move to it's own module?) |=== #

global settings
settings = {}

def dumpSettings(guild_id:int = 0): # settings disctionary -> json files
    """Saves the settings to file"""
    # mPrint('FUNC', f"dumping settings for {settings_folder}{guild_id}.json")
    dump = settings[guild_id]
    with open(settings_folder + f"{guild_id}.json", 'w') as f:
        json.dump(dump, f, indent=2)

def loadSettings(guild_id:int): # json files -> settings dictionary
    global settings
    mPrint('FUNC', "Loading guild settings")
    try:
        with open(settings_folder + f"{guild_id}.json", 'r') as f:
            settings[guild_id] = json.load(f)
    except json.JSONDecodeError:
        mPrint('ERROR', traceback.format_exc())
    except Exception:
        mPrint('ERROR', f"Could not load settings for [{guild_id}]{traceback.format_exc()}")

def createSettings(guild_id:int): # new json files
    guild_id = int(guild_id)
    mPrint('FUNC', "Generating new settings for guild")

    if (not os.path.isdir(settings_folder)): 
        os.mkdir(settings_folder)

    temp = SETTINGS_TEMPLATE["id"]
    with open(settings_folder + f"{guild_id}.json", 'w') as f:
        json.dump(temp, f, indent=2)

def checkSettingsIntegrity(guild_id:int):
    guild_id = int(guild_id)
    mPrint('FUNC', f'Checking settings integrity for guild')

    try:
        settingsToCheck = copy.deepcopy(settings[guild_id])
    except KeyError:
        mPrint('FATAL', f'Settings for guild were not initialized correctly\n{traceback.format_exc()}')
        sys.exit(-1)

    #check if there is more data than there should
    for key in settingsToCheck:
        if(key not in SETTINGS_TEMPLATE["id"]): #check if there is a key that should not be there
            del settings[guild_id][key]
            mPrint('DEBUG', f'Deleting: {key}')

        if(type(settingsToCheck[key]) == dict):
            #if(key in ["saved_playlists", "urlsync"]): continue #whitelist
            for subkey in settingsToCheck[key]:
                if(subkey not in SETTINGS_TEMPLATE["id"][key]): #check if there is a subkey that should not be there
                    del settings[guild_id][key][subkey]
                    mPrint('DEBUG', f'Deleting: {subkey}')

    #check if data is missing
    for key in SETTINGS_TEMPLATE["id"]:
        if(key not in settings[guild_id]): #check if a key is missing
            settings[guild_id][key] = SETTINGS_TEMPLATE["id"][key]
            mPrint('DEBUG', f'Creating key: {key}')

        #it it's a dict also check it's keys
        if(type(SETTINGS_TEMPLATE["id"][key]) == dict):
            for subkey in SETTINGS_TEMPLATE["id"][key]:
                if(subkey not in settings[guild_id][key]): #check if a subkey is missing
                    settings[guild_id][key][subkey] = SETTINGS_TEMPLATE["id"][key][subkey]
                    mPrint('DEBUG', f'Creating subkey: {subkey}')

    dumpSettings(guild_id)

# ===| helper functions |=== #
def getWord(all=False) -> Union[str, list]:
    """
    :return: A random line from the words.txt file.
    e.g. culo, i culi
    """
    with open('botFiles/words.txt', 'r') as words:
        lines = words.read().splitlines()
        if(all):
            return lines
        return random.choice(lines)

def parseWord(message:str, i:int, words:str, articoli:list[str]) -> tuple[str, str]:
    #message = 'No voglio il rosso'
    #words = 'il culo, i culi'
    
    article_word = words.split(', ') #['il culo', 'i culi']
    #sorry for spaghetti code maybe will reparse later

    if len(article_word) == 1: #word has only one form (eg: ['il culo'])
        if len(article_word[0].split()) == 1:
            return (message[i-1], article_word[0]) #eg. words = ['culo']
        if message[i-1] not in articoli: #don't change the word before if not an article
            return (message[i-1], article_word[0].split()[1]) #eg. words = ['il culo']
        return (article_word[0].split()[0], article_word[0].split()[1]) #eg. words = ['il culo']

    if message[i-1] not in articoli: #the word before is not an article
        if message[i-1].isnumeric(): #e.g. '3 cavolfiori'
            if message[i-1] == '1':
                return (message[i-1], article_word[0].split()[1]) #'1 culo'
            else:
                return (message[i-1], article_word[1].split()[1]) #'3 culi'
        return (message[i-1], article_word[0].split()[1]) #eg. returns ('ciao', 'culo')

    if message[i-1] in ['il', 'lo', 'la']: #eg. returns ('il', 'culo')
        return (article_word[0].split()[0], article_word[0].split()[1])

    if message[i-1] in ['i', 'gli', 'le']: #eg. returns ('i', 'culi')
        return (article_word[1].split()[0], article_word[1].split()[1])
    
    return ('parsing error', 'parseWord(str, int, str, list[str]) -> tuple[str, str]')


#           -----           CULOBOT            -----       #
class CuloBot(discord.Client):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.isReady = False

    async def on_error(self, *args, **kwargs):
        mPrint('ERROR', f"DISCORDPY on_error:\n{traceback.format_exc()}")
        mPrint('WARN', "ARGS:")
        for x in args:
            mPrint('ERROR', {x})

    async def on_guild_join(self, guild:discord.Guild):
        guild_id = int(guild.id)
        mPrint("INFO", f"Joined guild {guild.name} (id: {guild_id})")

        members = '\n - '.join([member.name for member in guild.members])
        mPrint('DEBUG', f'Guild Members:\n - {members}')
        if (guild_id not in settings):
            createSettings(guild_id)
        else:
            mPrint('DEBUG', f'settings for {guild_id} are present in {settings}')

        loadSettings(guild_id)
        checkSettingsIntegrity(guild_id)

        # voice_client : discord.VoiceClient = get(bot.voice_clients, guild=guild)
        # if voice_client != None and voice_client.is_connected():
        #     await voice_client.disconnect()

    async def on_guild_remove(self, guild:discord.Guild):
        pass
    
    async def on_ready(self):
        if self.isReady: return # ensure that on_ready only runs one time
        self.isReady = True
        mPrint("DEBUG", "Called on_ready")

        try:
            self.dev = await bot.fetch_user(OWNER_ID)
        except discord.errors.NotFound:
            self.dev = None
        except NameError:
            pass
        await bot.change_presence(status=config.bot_status, activity=discord.Activity(type=discord.ActivityType.listening, name=config.bot_description))

        mPrint("INFO", f'Connected to {len(bot.guilds)} guild(s)')
        for guild in bot.guilds:
            guild_id = int(guild.id)

            mPrint('DEBUG', f'Initializing guild {guild_id} -')
            if (not os.path.isfile(settings_folder+f"{guild_id}.json")):
                createSettings(guild_id)

            loadSettings(guild_id)
            # mPrint('DEBUG', json.dumps({guild_id: settings[guild_id]}, indent=2))
            checkSettingsIntegrity(guild_id)

        mPrint('DEBUG', "command tree sync...")
        await tree.sync()

        mPrint('INFO', "bot is ready.")

    async def on_member_join(self, member : discord.Member):
        if not config.discord_events: return
        if settings[int(member.guild.id)]['responseSettings']['send_join_msg']:
            joinString:str = settings[int(member.guild.id)]['responseSettings']['join_message']
            joinString = joinString.replace('%name%', member.name)
            await member.guild.system_channel.send(joinString)

    async def on_member_remove(self, member : discord.Member):
        if not config.discord_events: return
        if settings[int(member.guild.id)]['responseSettings']['send_leave_msg']:
            leaveString:str = settings[int(member.guild.id)]['responseSettings']['leave_message']
            leaveString= leaveString.replace('%name%', member.name)
            await member.guild.system_channel.send(leaveString)
    
    async def on_guild_available(self, guild : discord.Guild):
        pass

    async def on_message(self, message : discord.Message):
        if not config.reply: return

        if len(message.content.split())==0: return
        global settings

        try:
            respSettings = settings[int(message.guild.id)]["responseSettings"]
        except AttributeError:
            return #this gets triggered with ephemeral messages

        if message.channel.id in settings[message.guild.id]['responseSettings']['disabled_channels']:
            return #module is in blacklist for this channel

        #don't respond to self, commands, messages with less than 2 words
        if message.author.id == bot.user.id or message.content[0] in ["!", "/", "?", "|", '$', "&", ">", "<"] or len(message.content.split()) < 2:
            return

        #if guild does not want bot responses and sender is a bot, ignore the message
        if message.author.bot and not respSettings["will_respond_to_bots"]: return 0

        #culificazione
        articoli = ['il', 'lo', 'la', 'i', 'gli', 'le'] #Italian specific

        if random.randrange(1, 100) > respSettings["response_perc"]: #implement % of answering
            return

        msg = message.content.split() #trasforma messaggio in lista
        
        for i in range(len(msg) // 3): #culifico al massimo un terzo delle parole
            scelta = random.randrange(1, len(msg)) #scegli una parola

            # se la parola scelta è un articolo (e non è l'ultima parola), cambio la prossima parola
            # e.g "ciao sono il meccanico" (se prendo la parola DOPO "il") -> "ciao sono il culo"   
            if msg[scelta] in articoli and scelta < len(msg)-1:
                scelta += 1
            parola = getWord() #scegli con cosa cambiarla
            articolo, parola = parseWord(msg, scelta, parola, articoli)

            msg[scelta-1] = articolo
            if(msg[scelta].isupper()): #controlla se la parola è maiuscola, o se la prima lettera è maiuscola
                parola = parola.upper()
            elif(msg[scelta][0].isupper()):
                parola = parola[0].upper() + parola[1:]
            msg[scelta] = parola #sostituisci parola

            if(random.randrange(1, 100) > respSettings['other_response']):
                i+=1
            i+=1

        msg = " ".join(msg) #trasforma messaggio in stringa

        await message.reply(msg, mention_author=False)
        mPrint('DEBUG', f'Ho risposto ad un messaggio.')


bot = CuloBot(intents = intents)
tree = app_commands.CommandTree(bot)



#           -----           CULOBOT SLASH COMMANDS           -----       #
# ======== REPLY ========= #
@tree.command(name="join-msg", description=lang.slash.join_msg)
async def joinmsg(interaction : discord.Interaction, message : str = None, enabled : bool = None):
    if not config.reply:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /join-msg {message}')
    guildID = int(interaction.guild.id)

    if enabled != None:
        settings[guildID]['responseSettings']['send_join_msg'] = enabled
        dumpSettings(guildID)

    if message != None: #edit join-message or show help
        settings[guildID]['responseSettings']['join_message'] = message
        dumpSettings(guildID)

    embed = discord.Embed(
        title=lang.commands.join_msg_embed_title,
        description=lang.commands.join_msg_embed_desc(settings[guildID]['responseSettings']['send_join_msg'], settings[guildID]['responseSettings']['join_message']),
        color=col.orange
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="leave-msg", description=lang.slash.leave_msg)
async def leavemsg(interaction : discord.Interaction, message : str = None, enabled : bool = None):
    if not config.reply:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /leave-msg {message}')
    guildID = int(interaction.guild.id)

    if enabled != None:
        settings[guildID]['responseSettings']['send_leave_msg'] = enabled
        dumpSettings(guildID)

    if message != None: #edit join-message or show help
        settings[guildID]['responseSettings']['leave_message'] = message
        dumpSettings(guildID)
    
    embed = discord.Embed(
        title=lang.commands.leave_msg_embed_title,
        description=lang.commands.leave_msg_embed_desc(settings[guildID]['responseSettings']['send_leave_msg'], settings[guildID]['responseSettings']['leave_message']),
        color=col.orange
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="respond-perc", description=lang.slash.respond_perc)
async def responsePerc(interaction : discord.Interaction, value : int = -1):
    if not config.reply:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return

    mPrint('CMDS', f'called /respond-perc {value}')
    guildID = int(interaction.guild.id)

    respSettings = settings[guildID]["responseSettings"] #readonly 

    if(value == -1):
        await interaction.response.send_message(lang.commands.resp_info(str(respSettings["response_perc"])))
        return
    
    elif (respSettings['response_perc'] == value):
        await interaction.response.send_message(lang.nothing_changed)
        return
    #else
    #keep value between 0 and 100
    value = 100 if value > 100 else 0 if value < 0 else value

    await interaction.response.send_message(lang.commands.resp_newperc(value))

    mPrint('INFO', f'{interaction.user.name} set response to {value}%')
    settings[guildID]['responseSettings']['response_perc'] = value
    dumpSettings(guildID)

@tree.command(name="respond-to-bots", description=lang.slash.respond_to_bots)
async def botRespToggle(interaction : discord.Interaction, value : bool):
    if not config.reply:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /respond-to-bots {value}')
    guildID = int(interaction.guild.id)
        
    if value == True:
        response = lang.commands.resp_resp_to_bots_affirmative
    else:
        response = lang.commands.resp_resp_to_bots_negative
    await interaction.response.send_message(response)

    settings[guildID]['responseSettings']['will_respond_to_bots'] = value
    dumpSettings(guildID)
    return

@tree.command(name="respond-to-bots-perc", description=lang.slash.respond_to_bots_perc)
async def botRespPerc(interaction : discord.Interaction, value : int = -1):
    if not config.reply:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /respond-to-bots-perc {value}')
    guildID = int(interaction.guild.id)

    if value == -1:
        await interaction.response.send_message(
            lang.commands.resp_to_bots_info(
                settings[guildID]["responseSettings"]["will_respond_to_bots"],
                settings[guildID]["responseSettings"]["response_to_bots_perc"]
            )
        )
        
        return

    #else
    #keep value between 0 and 100
    value = 100 if value > 100 else 0 if value < 0 else value

    await interaction.response.send_message(lang.commands.resp_to_bots_edit(value))
    settings[guildID]['responseSettings']['response_to_bots_perc'] = value
    dumpSettings(guildID)
    return

@tree.command(name="dictionary", description=lang.slash.dictionary)
async def dictionary(interaction : discord.Interaction):
    if not config.reply:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /dictionary')
    guildID = int(interaction.guild.id)

    #1. Send a description
    custom_words = settings[guildID]['responseSettings']['custom_words']
    description = lang.commands.words_info(interaction.guild.name)

    if not settings[guildID]['responseSettings']['use_global_words']:
        description += lang.commands.words_use_global_words(interaction.guild.name)
        
    embed = discord.Embed(
        title = lang.commands.words_known_words,
        description = description,
        colour = col.orange
    )

    value = ''
    #2a. get the global words
    botWords = getWord(True)

    #2b. if the guild uses the global words, append them to value
    if settings[guildID]['responseSettings']['use_global_words']:
        #is server uses default words
        value = '\n'.join(botWords)
        embed.add_field(name = lang.commands.words_bot_words, value=value)
        value = '' 

    #2c. append the guild(local) words to value
    for i, cw in enumerate(custom_words):
        value += f'[`{i}`]: {cw}\n'
    if value == '': value=lang.commands.words_guild_words
    embed.add_field(name = lang.commands.words_guild_words(interaction.guild.name), value=value)
    
    #3. send the words
    await interaction.response.send_message(embed=embed)

@tree.command(name="dictionary-add", description=lang.slash.dictionary_add)
async def dictionary_add(interaction : discord.Interaction, new_word : str):
    """
    Aggiunge una parola al dizionario.
    
    :param new_word: La parola che si vuole aggiungere
    """
    if not config.reply:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /dictionary add {new_word}')
    guildID = int(interaction.guild.id)

    settings[guildID]['responseSettings']['custom_words'].append(new_word)
    await interaction.response.send_message(lang.commands.words_learned, ephemeral=True)
    dumpSettings(guildID)
    return

@tree.command(name="dictionary-edit", description=lang.slash.dictionary_edit)
async def dictionary_edit(interaction : discord.Interaction, id : int, new_word : str):
    """
    Modifica una parola del dizionario.
    
    :param id: L'id della parola che vuoi modificare
    :param new_word: La parola che vuoi rimpiazzare
    """
    if not config.reply:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /dictionary edit {id}, {new_word}')
    guildID = int(interaction.guild.id)

    editWord = id
    if len(settings[guildID]['responseSettings']['custom_words']) > editWord:
        settings[guildID]['responseSettings']['custom_words'][editWord] = new_word
        dumpSettings(guildID)
        await interaction.response.send_message(lang.done, ephemeral=True)
    else:
        await interaction.response.send_message(lang.commands.words_id_not_found, ephemeral=True)
    return

@tree.command(name="dictionary-del", description=lang.slash.dictionary_del)
async def dictionary_del(interaction : discord.Interaction, id : int):
    """
    It deletes a word from the dictionary.

    :param id: L'id della parola che vuoi eliminare
    """
    if not config.reply:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /dictionary del {id}')
    guildID = int(interaction.guild.id)

    delWord = id
    if len(settings[guildID]['responseSettings']['custom_words']) > delWord:
        del settings[guildID]['responseSettings']['custom_words'][delWord]
        dumpSettings(guildID)
        await interaction.response.send_message(lang.done, ephemeral=True)
    else:
        await interaction.response.send_message(lang.commands.words_id_not_found, ephemeral=True)
    return

@tree.command(name="dictionary-useglobal", description=lang.slash.dictionary_use_global)
async def dictionary_default(interaction : discord.Interaction, value : bool ):
    if not config.reply:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /dictionary useglobal {value}')
    guildID = int(interaction.guild.id)

    settings[guildID]["responseSettings"]["use_global_words"] = value
    await interaction.response.send_message(f'useDefault: {value}', ephemeral=True)
    dumpSettings(guildID)
    return

# ======== CHESS ========= #
@tree.command(name="chess", description=lang.slash.chess)
async def chess(interaction : discord.Interaction, challenge : Union[discord.Role, discord.User] = None):
    """
    :param challenge: Il ruolo o l'utente da sfidare
    :param fen: Il layout delle pedine nella scacchiera (Se numerico indica uno dei FEN salvati)
    :param design: Il nome del design della scacchiera
    """
    if not config.chess:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /chess: ch: {challenge}')
    guildID = int(interaction.guild.id)

    if interaction.channel.id in settings[guildID]['chessGame']['disabled_channels']:
        await interaction.response.send_message(lang.module_not_enabled, ephemeral=True)
        return

    await interaction.channel.typing()
#1. Prepare the variables
    #info about the player challenging another player or a role to a match
    class Challenge:
        type = 0             #can be: 0-> Everyone / 1-> Role / 2-> Player
        whitelist = []       #list of user ids (int) (or 1 role id) 
        authorJoined = False #Needed when type = 1

    challengeData = Challenge()

    #2A. parse challenges
    if challenge == None:
        mPrint('DEBUG', 'Challenged everyone')
        challengeData.type = 0

    elif '<@&' in challenge.mention: #user challenged role
        mPrint('DEBUG', f'challenged role: {challenge.id} ({challenge.name})')
        challengeData.type = 1
        challengeData.whitelist.append(challenge.id)
        
    else: #user challenged user
        mPrint('DEBUG', f'challenged user: {challenge.id} ({challenge.name})')
        challengeData.type = 2
        challengeData.whitelist.append(interaction.user.id)
        challengeData.whitelist.append(challenge.id)

    #useful for FENs: eg   (!chess) game fen="bla bla bla" < str.strip will return ["game", "fen=bla", "bla", "bla"]
    # args = splitString(args)                    #wheras splitString will return ["game", "fen=", "bla", "bla", "bla"]

    #Ask user if he wants FEN and/or design
    class GameData():
        selectedLayout = None
        selectedDesign = None
    gameData = GameData()

    #FEN options
    globalBoards = chessBridge.getBoards()
    guildBoards = settings[guildID]['chessGame']['boards']
    layoutChoices = discord.ui.Select(options=[], placeholder=lang.chess.layout_render_select)

    for layout in globalBoards: #global layouts
        isDefault = False
        if layout == settings[guildID]["chessGame"]["default_board"]:
            isDefault = True
            gameData.selectedLayout = globalBoards[layout]
        layoutChoices.add_option(label=f"FEN: {layout}", description=globalBoards[layout], value=globalBoards[layout], default=isDefault)

    for layout in guildBoards: #guild layouts
        isDefault = False
        if layout == settings[guildID]["chessGame"]["default_board"]:
            isDefault = True
            gameData.selectedLayout = guildBoards[layout]
        layoutChoices.add_option(label=f"FEN: {layout}", description=guildBoards[layout], value=guildBoards[layout], default=isDefault)

    #Design options
    globalDesigns = chessBridge.chessMain.getDesignNames()
    guildDesigns = settings[guildID]['chessGame']['designs']
    designChoices = discord.ui.Select(options=[], placeholder=lang.chess.design_render_select)

    for design in globalDesigns: #guild layouts
        isDefault = False
        if design == settings[guildID]["chessGame"]["default_design"]:
            isDefault = True
            gameData.selectedDesign = design
        designChoices.add_option(label=f"Design: {design}", value=design, default=isDefault)
    for design in guildDesigns: #guild layouts
        isDefault = False
        if design == settings[guildID]["chessGame"]["default_design"]:
            isDefault = True
            gameData.selectedDesign = design
        designChoices.add_option(label=f"Design: {design}", description=str(guildDesigns[design]), value=design, default=isDefault)

    #handlers for select choices
    async def layoutChoice(interaction : discord.Interaction):
        gameData.selectedLayout = str(layoutChoices.values[0])
        mPrint('DEBUG', f'Selected layout {gameData.selectedLayout}')
        await interaction.response.defer()

    async def designChoice(interaction : discord.Interaction):
        gameData.selectedDesign = str(designChoices.values[0])
        mPrint('DEBUG', f'Selected design {gameData.selectedDesign}')
        
        await interaction.response.defer()

    layoutChoices.callback = layoutChoice
    designChoices.callback = designChoice

    async def btn_cancel(interaction : discord.Interaction): #User cancels matchmaking
        confirm.disabled = True
        cancel.disabled = True
        layoutChoices.disabled = True
        designChoices.disabled = True
        await interaction.response.edit_message(view=view)
        return

    async def btn_confirm(interaction : discord.Interaction): # When user confirms the data this function starts the game
        if (gameData.selectedDesign != None) and (gameData.selectedLayout != None):
            confirm.disabled = True
            cancel.disabled = True
            layoutChoices.disabled = True
            designChoices.disabled = True
            await interaction.response.edit_message(view=view)
            await interaction.channel.typing()
            await startGame(interaction, gameData.selectedLayout, gameData.selectedDesign)
        else:
            await interaction.response.send_message(lang.chess.design_btn_confirm_response, ephemeral=True)
        return

    confirm = discord.ui.Button(label=lang.confirm, style = discord.ButtonStyle.primary)
    confirm.callback = btn_confirm

    cancel = discord.ui.Button(label=lang.cancel, style=discord.ButtonStyle.danger)
    cancel.callback = btn_cancel

    view = discord.ui.View()
    view.add_item(layoutChoices)
    view.add_item(designChoices)
    view.add_item(confirm)
    view.add_item(cancel)

    await interaction.response.send_message(view=view, ephemeral=True)
    
    async def startGame(interaction:discord.Interaction, gameFEN, gameDesign):
        designName = gameDesign
    #2C. double-check the data retreived
        board = ()
        if gameFEN != '': #if fen is provided, check if valid
            if('k' not in gameFEN or 'K' not in gameFEN):
                print(gameFEN)
                embed = discord.Embed(
                    title = lang.chess.embedTitle_fen_king_missing,
                    description= lang.chess.embedDesc_fen_king_missing("black" if "k" not in gameFEN else "", "white" if "K" not in gameFEN else ""),
                    color = col.red
                )
                await interaction.response.send_message(embed=embed)
                return -1
            #else, fen is valid
            board = ('FEN', gameFEN)

        mPrint('TEST', f'Design {gameDesign} ')
        # check if design exists
        if gameDesign in settings[guildID]['chessGame']['designs']:
            mPrint('TEST', f'Found Local design {gameDesign} ')
            colors = settings[guildID]['chessGame']['designs'][gameDesign]
            gameDesign = chessBridge.chessMain.gameRenderer.renderBoard(colors, interaction.id)
        elif chessBridge.chessMain.gameRenderer.doesDesignExist(gameDesign):
            mPrint('TEST', f'Found Global design {gameDesign}')
            gameDesign = chessBridge.chessMain.gameRenderer.getGlobalDesign(gameDesign) 
        else:
            mPrint('TEST', f'Design not found')
            gameDesign = 'default'
        
    # 3. All seems good, now let's send the embed to find some players
        #3A. Challenge one user
        class Challenge:
            type = 0             #can be: 0-> Everyone / 1-> Role / 2-> Player
            whitelist = []       #list of user ids (int) (or 1 role id) 
            authorJoined = False #Needed when type = 1

        if challengeData.type == 2: 
            embed = discord.Embed(title = lang.chess.challenge_e1t(challenge.name, interaction.user.name),
                description= lang.chess.challenge_ed(gameFEN, designName),
                color = col.blu
            )
            
        #3B. Challenge one guild
        elif challengeData.type == 1:
            embed = discord.Embed(title = lang.chess.challenge_e2t(challenge.name, interaction.user.name),
                description= lang.chess.challenge_ed(gameFEN, designName),
                color = col.blu
            )

        #3C. Challenge everyone
        else:
            embed = discord.Embed(title = lang.chess.challenge_e3t,
                description= lang.chess.challenge_ed(gameFEN, designName),
                color = col.blu).set_footer(text=lang.chess.challenge_f(interaction.user.name))
                        
        #3D. SEND THE EMBED FINALLY
        if challengeData.type != 0:
            await interaction.channel.send(lang.chess.challenge_s(interaction.user, challenge.mention))
        playerFetchMsg = await interaction.channel.send(embed=embed)

    #4. Await player joins
        #4A. setting up
        reactions = ('⚪', '🌑') #('🤍', '🖤')
        r1, r2 = reactions

        availableTeams = [reactions[0], reactions[1]] # Needed to avoid players from joining the same team
        players = [0, 0] #this will store discord.Members

        mPrint('DEBUG','chessGame: challenge whitelist')
        mPrint('DEBUG', challengeData.whitelist)

        #add reactions to the embed that people can use as buttons to join the teams
        await playerFetchMsg.add_reaction(r1)
        await playerFetchMsg.add_reaction(r2)
        await playerFetchMsg.add_reaction("❌") #if the author changes their mind


        def fetchChecker(reaction : discord.Reaction, user : Union[discord.Member, discord.User]) -> bool: #this is one fat checker damn
            """Checks if user team join request is valid"""

            # async def remove(reaction, user): #remove invalid reactions
            #     await reaction.remove(user)   #will figure out some way

            mPrint('DEBUG', f'chessGame: Check: {reaction}, {user}\nchallenge whitelist: {challengeData.whitelist}\navailable: {availableTeams}\n--------')
            
            #1- prevent bot from joining teams
            if (user == bot.user): 
                return False
            
            if (reaction.message.id != playerFetchMsg.id): #the reaction was given to another message
                return False

            if(str(reaction.emoji) == "❌" and user == interaction.user):
                return True #only the author can cancel the search

            #2- check if color is still available (prevent two players from joining the same team)
            if(str(reaction.emoji) not in availableTeams):
                return False #remember to remove the reaction before every return True

            userID = int(user.id)
            
            #3a- If player challenged a user:
            if(challengeData.type == 2): #0 everyone, 1 role, 2 user
                #check if joining player is in whitelist
                if userID not in challengeData.whitelist: return False
                
                challengeData.whitelist.remove(userID) #prevent user from rejoining another team
                availableTeams.remove(str(reaction.emoji)) #prevent player/s from joining the same team
                return True

            #3b- If player challenged a role:
            elif(challengeData.type == 1):
                challengedRole = challenge.id #challenge has only one entry containing the role id
                
                #if the user joining is the author:
                if user == interaction.user and challengeData.authorJoined == False: #the message author can join even if he does not have the role
                    mPrint('DEBUG', 'chessGame: User is author') #check the user BEFORE the role, so if the user has the role it does not get deleted
                    challengeData.authorJoined = True #prevent author from joining 2 teams
                    availableTeams.remove(str(reaction.emoji)) #prevent player/s from joining the same team
                    return True 
                
                #if the user joining isn't the author but has the role requested
                elif user.get_role(challengedRole) != None: #user has the role  
                    mPrint('DEBUG', 'chessGame: User has required role')
                    challengeData.whitelist = [] #delete the role to prevent two players with the role from joining (keeping out the author)
                    availableTeams.remove(str(reaction.emoji)) #prevent player/s from joining the same team
                    return True

                mPrint('WARN',f'chessGame: User {user.name} is not allowerd to join (Role challenge)')
                return False

            #3c- If player challenged everyone:
            else: #no need to check who joins (can also play with yourself)
                availableTeams.remove(str(reaction.emoji)) #prevent player/s from joining the same team
                return True

            # fetchChecker end #

        #4B. await user joins (with reactions)
        async def stopsearch():
            embed.title = lang.chess.stop_title
            embed.description = ""
            embed.color = col.red

            designFolder = f'{chessBridge.chessMain.gameRenderer.spritesFolder}{design}'
            if design.find('\\') != -1 or design.find('/') != -1:
                shutil.rmtree(designFolder)
            await playerFetchMsg.clear_reactions()
            await playerFetchMsg.edit(embed=embed)

        try:
            #i. await first player
            r1, players[0] = await bot.wait_for('reaction_add', timeout=60.0, check=fetchChecker)
            if str(r1.emoji) == "❌": 
                await stopsearch()
                return -2
            embed.description += lang.chess.p_join(players[0], r1)
            await playerFetchMsg.edit(embed=embed)
            

            #ii. await second player
            r2, players[1] = await bot.wait_for('reaction_add', timeout=60.0, check=fetchChecker)
            if str(r2.emoji) == "❌": 
                await stopsearch()
                return -2
            embed.description += lang.chess.p2_join(players[0], r1)
            embed.set_footer(text = 'fake loading screen lets goooo')
            
            embed.color = col.green
            await playerFetchMsg.edit(embed=embed)
            #iii. fake sleep for professionality
            await asyncio.sleep(random.randrange(0,2))

        except asyncio.TimeoutError: #players did not join in time
            embed = discord.Embed(
                title = lang.chess.not_enough_players,
                colour = col.red
            )
            await interaction.channel.send(embed=embed)
            await playerFetchMsg.delete()
            return -1

        else: #players did join in time

            if str(r1.emoji) == reactions[0]: #first player choose white
                player1 = players[1] #white
                player2 = players[0] #black
            else: #first player choose black
                player1 = players[0] #white
                player2 = players[1] #black
            mPrint('INFO', f'p1: {player1}\np2: {player2}')

            #iv. Send an embed with the details of the game
            embed = discord.Embed(
                title = lang.chess.found_players_t(r1, player1, player2, r2),
                description = lang.chess.found_players_d(gameFEN, gameDesign),
                colour = col.green
            )
            
            #v. start a thread where the game will be disputed, join the players in there
            thread = await interaction.channel.send(embed=embed)
            gameThread = await thread.create_thread(name=(f'{str(player1)[:-5]} -VS- {str(player2)[:-5]}'), auto_archive_duration=60, reason='Chess')
            await gameThread.add_user(player1)
            await gameThread.add_user(player2)
            await playerFetchMsg.delete()
            mainThreadEmbed = (thread, embed)

    #5. FINALLY, start the game
            mPrint('TEST', f'design: {gameDesign}')
            await chessBridge.loadGame(gameThread, bot, [player1, player2], mainThreadEmbed, board, gameDesign)
            #                                        #send them backwards (info on chessBrige.py) [black, white]
            await gameThread.edit(archived=True, locked=True)
            designFolder = f'{chessBridge.chessMain.gameRenderer.spritesFolder}{gameDesign}'
            if gameDesign.find('\\') != -1 or design.find('/') != -1:
                shutil.rmtree(designFolder)

@tree.command(name="chess-layout", description=lang.slash.chess_layout)
@app_commands.choices(sub_command=[
        app_commands.Choice(name=lang.choices.info, value="0"),
        app_commands.Choice(name=lang.choices.render, value="1"),
        app_commands.Choice(name=lang.choices.add, value="2"),
        app_commands.Choice(name=lang.choices.edit, value="3"),
        app_commands.Choice(name=lang.choices.remove, value="4"),
])
@app_commands.describe(sub_command=lang.choices.description)
async def chess_layout(interaction : discord.Interaction, sub_command: app_commands.Choice[str]): #, name:str=None, fen:str = None
    if not config.chess:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /chess-layout: {sub_command.name}')
    guildID = int(interaction.guild.id)
    response = int(sub_command.value)
    botBoards = chessBridge.getBoards()
    guildBoards = settings[guildID]['chessGame']['boards']
    

    #send saved layouts
    if response == 0: 
        embed = discord.Embed(
            title = lang.chess.layout_description,
            colour = col.orange
        )
        #ii. append the global data boards to the embed
        
        value = ''
        for b in botBoards:
            value += f"**{b}**: {botBoards[b]}\n"
        embed.add_field(name = lang.chess.layout_global_layouts, value=value, inline=False)

        #iii. if guild data has boards, append them to the embed
        if settings[guildID]['chessGame']['boards'] != {}:
            guildBoards = ''
            for b in settings[guildID]['chessGame']['boards']:
                guildBoards += f"**{b}**: {settings[guildID]['chessGame']['boards'][b]}\n"
            embed.add_field(name = lang.chess.layout_guild_layouts(interaction.guild.name), value=guildBoards, inline=False)
        
        #iv. send the embed
        await interaction.response.send_message(embed=embed)
        return 0

    elif response == 1: # renders a FEN and send it in chat
        choices = discord.ui.Select(options= #global layouts
            [discord.SelectOption(label=name, description=botBoards[name], value=botBoards[name]) for name in botBoards],
            placeholder=lang.chess.layout_render_select
        )
        for layout in guildBoards: #guild layouts
            choices.add_option(label=layout, description=guildBoards[layout], value=guildBoards[layout])

        view = discord.ui.View()
        view.add_item(choices)

        async def render_and_send_image(interaction : discord.Interaction):
            mPrint("TEST", choices.values)
            layoutFEN = choices.values[0]
            
            #ii. let the Engine make the image
            try:
                image = chessBridge.getBoardImgPath(layoutFEN, interaction.id)
                mPrint('DEBUG', f'got image path: {image}')
            except Exception:
                await interaction.response.send_message(lang.chess.layout_render_error)
                return -2

            if image == 'Invalid':
                await interaction.response.send_message(f"{lang.chess.layout_render_invalid} {layoutFEN}")
                return -1
            mPrint('DEBUG', f'rendered image: {image}')

            #iii. Send the image to discord
            imgpath = (f'{image[0]}')
            with open(imgpath, "rb") as fh:
                f = discord.File(fh, filename=imgpath)
            #iv. data hoarding is bad
            await interaction.response.send_message(lang.chess.layout_user_rendered(interaction.user.name, layoutFEN), file=f)
            try:
                os.remove(imgpath)
            except PermissionError:
                mPrint('ERROR', f'Could not delete file {imgpath}\n{traceback.format_exc()}')

            try:
                os.remove(imgpath.replace('png', 'log'))
            except PermissionError:
                mPrint('ERROR', f'Could not delete file {imgpath.replace("png", "log")}\n{traceback.format_exc()}')
            
        choices.callback = render_and_send_image
        await interaction.response.send_message(view=view, ephemeral=True)
        return 0

    elif response == 2: # adds a board in the Data
        class NewLayoutData(discord.ui.Modal, title='Inserisci un nuovo layout'):
            name = discord.ui.TextInput(label='Nome', placeholder="Name", style=discord.TextStyle.short, required=True)
            fen = discord.ui.TextInput(label='FEN', placeholder="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 0", default="https://lichess.org/editor", style=discord.TextStyle.long, required=True)

            async def on_submit(self, interaction: discord.Interaction):
                mPrint('TEST', f"{self.name}: {self.fen}")
                if str(self.name) not in settings[guildID]['chessGame']['boards']:
                    #iii. append the board and dump the json data
                    settings[guildID]['chessGame']['boards'][str(self.name)] = str(self.fen)
                    dumpSettings(guildID)
                    await interaction.response.send_message(lang.chess.layout_add_done(str(self.name), str(self.fen)))
                else:
                    await interaction.response.send_message(lang.chess.layout_add_exists)

        await interaction.response.send_modal(NewLayoutData())

        return

    elif response == 3: #rename a board
        # setup guild layout in choices
        choices = discord.ui.Select(options=
            [discord.SelectOption(label=name, description=guildBoards[name]) for name in guildBoards],
            placeholder=lang.chess.layout_edit_select
        )
        view = discord.ui.View()
        view.add_item(choices)

        async def edit_board(interaction : discord.Interaction): # This triggers when user selects the board to edit
            layoutname = str(choices.values[0])
            class EditLayoutData(discord.ui.Modal, title=lang.chess.layout_edit_title(layoutname)):
                newfen = discord.ui.TextInput(label=f'Edit the FEN for "{layoutname}"', default=guildBoards[layoutname], style=discord.TextStyle.long, required=True)

                async def on_submit(self, interaction: discord.Interaction): #this triggers when user submits the modal with the new data
                    settings[guildID]['chessGame']['boards'][layoutname] = str(self.newfen)
                    dumpSettings(guildID)
                    await interaction.response.send_message(lang.chess.layout_edit_ok(layoutname, str(self.newfen)))
            await interaction.response.send_modal(EditLayoutData())

        choices.callback = edit_board

        if guildBoards != {}:
            await interaction.response.send_message(view=view, ephemeral=True)
        else:
            await interaction.response.send_message(lang.chess.layout_no_layouts, ephemeral=True)
        return 0
    
    elif response == 4: #delete a board
        # setup guild layout in choices
        choices = discord.ui.Select(options=
            [discord.SelectOption(label=name, description=guildBoards[name]) for name in guildBoards],
            placeholder=lang.chess.layout_delete_select
        )
        view = discord.ui.View()
        view.add_item(choices)

        async def delete_board(interaction : discord.Interaction): # This triggers when user selects the board to edit
            layoutname = choices.values[0]
            if layoutname in settings[guildID]['chessGame']['boards']:
                fen = settings[guildID]['chessGame']['boards'].pop(layoutname)
                dumpSettings(guildID)
                await interaction.response.send_message(lang.chess.layout_delete_ok(layoutname, fen))

        choices.callback = delete_board
        if guildBoards != {}:
            await interaction.response.send_message(view=view, ephemeral=True)
        else:
            await interaction.response.send_message(lang.chess.layout_no_layouts, ephemeral=True)
        return 0
    
@tree.command(name="chess-designs", description=lang.slash.chess_designs)
@app_commands.choices(sub_command=[
        app_commands.Choice(name=lang.choices.info, value="0"),
        app_commands.Choice(name=lang.choices.render, value="1"),
        app_commands.Choice(name=lang.choices.add, value="2"),
        app_commands.Choice(name=lang.choices.edit, value="3"),
        app_commands.Choice(name=lang.choices.remove, value="4"),
])
@app_commands.describe(sub_command=lang.choices.description)
async def chess_design(interaction : discord.Interaction, sub_command: app_commands.Choice[str]): #, name:str=None, fen:str = None
    if not config.chess:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /chess-designs: {sub_command.name}')
    guildID = int(interaction.guild.id)
    response = int(sub_command.value)

    globalDesigns = chessBridge.chessMain.getDesignNames()
    guildDesigns = settings[guildID]['chessGame']['designs']

    mPrint('TEST', globalDesigns)
    mPrint('TEST', guildDesigns)

    def parseHEX(hex1, hex2) -> list: #helper function
        colors = [hex1, hex2]
        possible = ['#', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']
        for i, hex in enumerate(colors): #foreach color
            mPrint('DEBUG', f'parsing hex {hex}')
            # if it has not an # add it
            if hex[0] != '#': 
                hex = '#' + hex
            for char in hex: #check if color digits are valid
                if char.lower() not in possible:
                    return '0'
            if len(hex) == 4: #if the hex type is #fff expand it to #ffffff
                hex = f'#{hex[1]}{hex[1]}{hex[2]}{hex[2]}{hex[3]}{hex[3]}'
            if len(hex) != 7:
                return '0'
            colors[i] = hex
        return colors

    if response == 0: #show board designs
        embed = discord.Embed(
            title = lang.chess.design_available,
            colour = col.orange
        )

        #ii. append the global data designs to the embed
        value = ''
        for b in range(len(globalDesigns)):
            value += f"{globalDesigns[b]}\n"

        embed.add_field(name =lang.chess.design_available, value=value, inline=False)

        #iii. if guild data has designs, append them to the embed
        if settings[guildID]['chessGame']['designs'] != {}:
            guildDesigns = ''
            for b in settings[guildID]['chessGame']['designs']:
                guildDesigns += f"**{b}**: {settings[guildID]['chessGame']['designs'][b]}\n"
            embed.add_field(name = f'Design ({interaction.guild.name}):', value=guildDesigns, inline=False)
        
        #iv. send the embed
        await interaction.response.send_message(embed=embed)
        return 0
        
    if response == 1: # Render and send designs
        choices = discord.ui.Select(options= #global layouts
            [discord.SelectOption(label=x, value=x) for x in globalDesigns],
            placeholder=lang.chess.design_render_select
        )
        for design in guildDesigns: #guild layouts
            choices.add_option(label=design, description=str(guildDesigns[design]), value=design)

        view = discord.ui.View()
        view.add_item(choices)

        async def render_and_send_image(interaction : discord.Interaction):
            mPrint("TEST", choices.values)
            designChoice = str(choices.values[0])
            if designChoice in settings[guildID]['chessGame']['designs']: #design exists in guildData
                colors = settings[guildID]['chessGame']['designs'][designChoice]
                designPath = chessBridge.chessMain.gameRenderer.renderBoard(colors, interaction.message.id)
                with open(designPath+'chessboard.png', "rb") as fh:
                    f = discord.File(fh, filename=(designPath + 'chessboard.png'))
                    await interaction.response.send_message(lang.chess.design_generated(interaction.user.name, designChoice), file=f)
                shutil.rmtree(designPath, ignore_errors=False, onerror=None)
                return 0

            #design does not exist in guildData, search if exists in sprites folder
            elif chessBridge.chessMain.gameRenderer.doesDesignExist(designChoice):
                design = f'{chessBridge.chessMain.gameRenderer.spritesFolder}{designChoice}/chessboard.png'
                with open(design, "rb") as fh:
                    f = discord.File(fh, filename=design)
                    await interaction.response.send_message(lang.chess.design_generated(interaction.user.name, designChoice), file=f)
            else:
                await interaction.response.send_message(lang.chess.design_404)
    
        choices.callback = render_and_send_image
        await interaction.response.send_message(view=view, ephemeral=True)
        return 0

    elif response == 2: # adds a design in guildsData
        class NewDesignData(discord.ui.Modal, title=lang.chess.insert_design):
            name = discord.ui.TextInput(label='Name', placeholder="", style=discord.TextStyle.short, required=True)
            hex1 = discord.ui.TextInput(label='Primary', placeholder="#aabbcc | #abc", style=discord.TextStyle.short, required=True, max_length=7)
            hex2 = discord.ui.TextInput(label='Secondary', placeholder="#11dd33 | #1d3", style=discord.TextStyle.short, required=True, max_length=7)

            async def on_submit(self, interaction: discord.Interaction):
                name = str(self.name)
                col1 = str(self.hex1)
                col2 = str(self.hex2)

                mPrint('TEST', f"{self.name}: {col1} {col2}")
                if name not in settings[guildID]['chessGame']['designs']:#check if already exists
                    #if not, make new design
                    #parse colors
                    colors = parseHEX(col1, col2)
                    if colors == '0':
                        await interaction.response.send_message(lang.chess.design_HEX_invalid(col1, col2), ephemeral=True)
                        return -2
                    settings[guildID]['chessGame']['designs'][name] = colors
                    await interaction.response.send_message(lang.chess.design_add_done(name, colors))
                    dumpSettings(guildID)
                    
                else:
                    await interaction.response.send_message(lang.chess.design_add_exists)

        await interaction.response.send_modal(NewDesignData())

        return

    elif response == 3: # edits a design in guildsData
        # setup guild designs in choices
        choices = discord.ui.Select(options=
            [discord.SelectOption(label=design, description=str(guildDesigns[design]), value=design) for design in guildDesigns],
            placeholder=lang.chess.design_edit_select
        )

        view = discord.ui.View()
        view.add_item(choices)

        async def edit_design(interaction : discord.Interaction): # This triggers when user selects the board to edit
            designName = choices.values[0]
            class EditDesignData(discord.ui.Modal, title=lang.chess.design_edit_title(designName)):
                c1 = discord.ui.TextInput(label=f'Primary  ', default=guildDesigns[designName][0], placeholder="#aabbcc | #abc", style=discord.TextStyle.short, required=True, max_length=7)
                c2 = discord.ui.TextInput(label=f'Secondary', default=guildDesigns[designName][1], placeholder="#11dd33 | #1d3", style=discord.TextStyle.short, required=True, max_length=7)

                async def on_submit(self, interaction: discord.Interaction): #this triggers when user submits the modal with the new data
                    col1,col2 = str(self.c1), str(self.c2)
                    colors = parseHEX(col1, col2)
                    if colors == '0':
                        await interaction.response.send_message(lang.chess.design_HEX_invalid(col1, col2), ephemeral=True)
                        return -2
                    #else
                    settings[guildID]['chessGame']['designs'][designName] = [col1, col2]
                    await interaction.response.send_message(lang.chess.design_edit_ok(designName, str([col1, col2])))
            await interaction.response.send_modal(EditDesignData())

        choices.callback = edit_design

        if guildDesigns != {}:
            await interaction.response.send_message(view=view, ephemeral=True)
        else:
            await interaction.response.send_message(lang.chess.design_no_designs, ephemeral=True)
        return 0

    elif response == 4: # deletes a design in guildsData
        # setup guild designs in choices
        choices = discord.ui.Select(options=
            [discord.SelectOption(label=design, description=str(guildDesigns[design]), value=design) for design in guildDesigns],
            placeholder=lang.chess.design_delete_select
        )
        view = discord.ui.View()
        view.add_item(choices)

        async def delete_board(interaction : discord.Interaction): # This triggers when user selects the board to edit
            designname = choices.values[0]
            if designname in settings[guildID]['chessGame']['designs']:
                colors = settings[guildID]['chessGame']['designs'].pop(designname)
                dumpSettings(guildID)
                await interaction.response.send_message(lang.chess.design_delete_ok(designname, colors))

        choices.callback = delete_board
        if guildDesigns != {}:
            await interaction.response.send_message(view=view, ephemeral=True)
        else:
            await interaction.response.send_message(lang.chess.design_no_designs, ephemeral=True)
        return 0

# ======== MUSIC ========= #
@tree.command(name="playlist", description=lang.slash.playlist)
@app_commands.choices(sub_command=[
        app_commands.Choice(name=lang.choices.info, value="0"),
        app_commands.Choice(name=lang.choices.add, value="1"),
        app_commands.Choice(name=lang.choices.edit, value="2"),
        app_commands.Choice(name=lang.choices.remove, value="3"),
])
async def playlists(interaction : discord.Interaction, sub_command: app_commands.Choice[str]):
    if not config.music:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /playlist: ')
    guildID = int(interaction.guild.id)
    response = int(sub_command.value)

    savedPlaylists = settings[guildID]["musicbot"]["saved_playlists"]

    if response == 0: #send the playlist list list to user
        
        embed = discord.Embed(
            title = lang.music.embedTitle_playlist_saved(interaction.guild.name),
            description = lang.music.embedDesc_playlist_saved,
            color=col.green
        )
        for plist in settings[guildID]["musicbot"]["saved_playlists"]:
            urls=''
            for i, t in enumerate(settings[guildID]["musicbot"]["saved_playlists"][plist]):
                urls += f'**{i}**: {t}\n' 
            embed.add_field(name=plist, value=urls, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return    

    elif response == 1:  #add a new playlist
        class NewPlaylist(discord.ui.Modal, title = lang.music.playlist_create_title):
            name = discord.ui.TextInput(label='Nome', placeholder="", style=discord.TextStyle.short, required=True)
            user_queries = discord.ui.TextInput(label='Tracks ', placeholder=lang.music.newplaylist_tp, style=discord.TextStyle.paragraph, required=True)

            async def on_submit(self, modal_interaction: discord.Interaction):
                await modal_interaction.response.defer(ephemeral=True)
                name = str(self.name)
                user_queries = str(self.user_queries).replace(",", "").split('\n')

                mPrint('TEST', f"{name}: {user_queries}")

                if (name in settings[guildID]['musicbot']['saved_playlists']):
                    await modal_interaction.followup.send(lang.music.playlist_already_exists(self.user_queries))
                    return

                
                guild_playlists = settings[guildID]['musicbot']['saved_playlists']
                guild_urlsync = musicBridge.musicUtils.getUrlSync(guildID)

                tracks = musicBridge.parseUserInput(",".join(user_queries), guild_playlists, guild_urlsync)
                if tracks == None:
                    await modal_interaction.followup.send(lang.music.input_error)
                    return -1
                elif tracks == 404:
                    await modal_interaction.followup.send(lang.music.play_error_404)
                    return -1
                
                trackList = ''
                for i, t in enumerate(tracks):
                    trackList += f"\n**{i}**. {t}"

                #Save the song/playlist URL in a list of one element and inform the user
                settings[guildID]["musicbot"]["saved_playlists"][name] = tracks
                dumpSettings(guildID)

                embed = discord.Embed(
                    title = f"Playlist {name}: ",
                    description=f"```{trackList}```",
                    color = col.orange
                )
                await modal_interaction.followup.send(embed=embed, ephemeral=True)
                
                return

        await interaction.response.send_modal(NewPlaylist())
        return

    elif response == 2: #edit a playlist
        # get playlists and put them in choices
        choices = discord.ui.Select(options=
            [discord.SelectOption(label=playlist, value=playlist) for playlist in savedPlaylists],
            placeholder=lang.music.playlist_edit_select
        )

        view = discord.ui.View()
        view.add_item(choices)

        async def edit_playlist(interaction : discord.Interaction): # This triggers when user selects which playlist to edit
            playlistName = str(choices.values[0])
            mPrint('TEST', f'playlist name: {playlistName}')
            class EditPlaylistData(discord.ui.Modal, title=lang.music.playlist_edit_title(playlistName)):
                plists = '\n'.join(savedPlaylists[playlistName])
                links = discord.ui.TextInput(label='Tracks', placeholder=lang.music.newplaylist_tp, default=plists, style=discord.TextStyle.paragraph, required=True)

                async def on_submit(self, modal_interaction: discord.Interaction): #this triggers when user submits the modal with the new data
                    await modal_interaction.response.defer(ephemeral=True)
                    user_queries = str(self.links).replace(",", "").split('\n')
                    # this is the same as creating a new playlist

                    mPrint('TEST', f"{playlistName}: {user_queries}")

                    guild_playlists = settings[guildID]['musicbot']['saved_playlists']
                    guild_urlsync = musicBridge.musicUtils.getUrlSync(guildID)

                    tracks = musicBridge.parseUserInput(",".join(user_queries), guild_playlists, guild_urlsync)
                    if tracks == None:
                        await modal_interaction.followup.send(lang.music.input_error)
                        return -1
                    elif tracks == 404:
                        await modal_interaction.followup.send(lang.music.play_error_404)
                        return -1

                    trackList = ''
                    for i, t in enumerate(tracks):
                        trackList += f"\n**{i}**. {t}"

                    #Save the song/playlist URL in a list of one element and inform the user
                    settings[guildID]["musicbot"]["saved_playlists"][playlistName] = tracks
                    dumpSettings(guildID)

                    embed = discord.Embed(
                        title = f"Playlist {playlistName}: ",
                        description=f"```{trackList}```",
                        color = col.orange
                    )
                    await modal_interaction.response.send_message(embed=embed, ephemeral=True)
                    
                    return

            await interaction.response.send_modal(EditPlaylistData())

        choices.callback = edit_playlist

        if savedPlaylists != {}:
            await interaction.response.send_message(view=view, ephemeral=True)
        else:
            await interaction.response.send_message(lang.music.playlist_404, ephemeral=True)
        return 0

    elif response == 3: #remove a playlist
        # setup guild designs in choices
        choices = discord.ui.Select(options=
            [discord.SelectOption(label=playlist, value=playlist) for playlist in savedPlaylists],
            placeholder=lang.music.playlist_delete_select
        )
        view = discord.ui.View()
        view.add_item(choices)

        async def delete_playlist(option_interaction : discord.Interaction): # This triggers when user selects the playlist to delete
            await option_interaction.response.defer(ephemeral=True)
            playlistName = str(choices.values[0])
            if playlistName in settings[guildID]["musicbot"]['saved_playlists']:
                links = settings[guildID]["musicbot"]['saved_playlists'].pop(playlistName)
                dumpSettings(guildID)
                links = "\n".join(links)
                await option_interaction.followup.send(lang.music.playlist_delete_ok(playlistName, f'```{links}```'), ephemeral=True)

        choices.callback = delete_playlist
        if savedPlaylists != {}:
            await interaction.response.send_message(view=view, ephemeral=True)
        else:
            await interaction.response.send_message(lang.music.playlist_404, ephemeral=True)
        return 0

    return

@tree.command(name="player-settings", description=lang.slash.player_settings)
@app_commands.choices(setting=[
        app_commands.Choice(name=lang.choices.info, value="0"),
        app_commands.Choice(name=lang.choices.shuffle, value="1"),
        app_commands.Choice(name=lang.choices.precision, value="2"),
])
async def playerSettings(interaction : discord.Interaction, setting : app_commands.Choice[str], value : int = None):
    """
    :param setting: DO NOT INSERT value FOR SHUFFLE 
    """
    if not config.music:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    
    mPrint('CMDS', f'called /player-settings: ')
    guildID = int(interaction.guild.id)
    response = int(setting.value)

    if response == 0: #print settings
        embed = discord.Embed(
            title=lang.music.settings_embed_title,
            description="/player-settings",
            color=col.green
        )
        embed.add_field(name="Shuffle: ", value=f"{settings[guildID]['musicbot']['player_shuffle']}", inline=False)
        embed.add_field(name="Precision: ", value=f"{settings[guildID]['musicbot']['timeline_precision']} / {config.timeline_max}", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    elif response == 1: # shuffle setting
        is_shuffle = bool(settings[guildID]['musicbot']["player_shuffle"])
        choices = discord.ui.Select(options=[
            discord.SelectOption(label="True", value=True, default=is_shuffle),
            discord.SelectOption(label="False", value=False, default=(not is_shuffle))
            ]
        )
        view = discord.ui.View()
        view.add_item(choices)

        async def shuffle_response(response_interaction : discord.Interaction):
            await response_interaction.response.defer(ephemeral=True)
            mPrint('TEST', f"{choices.values[0]}")
            settings[guildID]['musicbot']["player_shuffle"] = choices.values[0]
            dumpSettings(guildID)

        choices.callback = shuffle_response
        await interaction.response.send_message(view=view, ephemeral=True)

    elif response == 2: #precision
        if value == None:
            await interaction.response.send_message(lang.music.settings_arg_needed, ephemeral=True)
            return
        warnmsg = ''
        newPrec = value
        if newPrec > config.timeline_max:
            newPrec = config.timeline_max
            warnmsg = lang.music.settings_timeline_max(config.timeline_max)

        if newPrec < 0:
            newPrec = 0
            warnmsg = lang.music.settings_timeline_min
        
        settings[guildID]['musicbot']["timeline_precision"] = newPrec
        dumpSettings(guildID)
        await interaction.response.send_message(lang.music.settings_new_precision(f"{newPrec}{warnmsg}"), ephemeral=True)

    return

@tree.command(name="play", description=lang.slash.play)
@app_commands.describe(tracks="URL / Title / saved playlist (/playlist); use , for mutiple items")
async def playSong(interaction:discord.Interaction, tracks:str, shuffle:bool = None):
    guildID = int(interaction.guild.id)
    
    if not config.music:
        await interaction.response.send_message(lang.disabled_module, ephemeral=True)
        return
    if interaction.channel.id in settings[guildID]['musicbot']['disabled_channels']:
        await interaction.response.send_message(lang.module_not_enabled, ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    if not os.path.exists("music/urlsync/"): os.mkdir('music/urlsync/')
    
    # Load useful variables
    if shuffle == None: shuffle = settings[guildID]['musicbot']["player_shuffle"]
    # else -> shuffle = shuffle
    precision = settings[guildID]['musicbot']["timeline_precision"]
    playlists = settings[guildID]['musicbot']['saved_playlists']
    urlsync = musicBridge.musicUtils.getUrlSync(guildID)

    # Parse user query
    queueTrackLinks = musicBridge.parseUserInput(tracks, playlists, urlsync)
    if queueTrackLinks == None:
        await interaction.followup.send(lang.music.input_error)
        return -1
    elif queueTrackLinks == 404:
        await interaction.followup.send(lang.music.play_error_404)
        return -1

    # Fetch voice channel and load voice client 
    try:
        userVC = bot.get_channel(interaction.user.voice.channel.id)
    except AttributeError:
        await interaction.followup.send(lang.music.play_user_not_in_vc, ephemeral=True)
        return

    voice_client : discord.VoiceClient = get(bot.voice_clients, guild=interaction.guild)
    if voice_client != None and voice_client.is_connected():
        if userVC!=None and voice_client.channel.id == userVC.id:
            await interaction.followup.send(lang.music.play_wrong_command, ephemeral=True)
        else:
            await interaction.followup.send(lang.music.play_already_connected, ephemeral=True)
        return
    
    # Remove guild musicbot slash commands if they exist (will regenerate them later)
    cmds = tree.get_commands(guild=interaction.guild)
    if len(cmds) != 0:
        tree.clear_commands(guild=interaction.guild)
        mPrint('DEBUG', f'Syncing musicbot tree for guild')
        await tree.sync(guild=interaction.guild)

    #Start music module
    try:
        mPrint('TEST', f'playing input: {queueTrackLinks}')
        await musicBridge.play(queueTrackLinks, interaction, bot, tree, shuffle, precision, urlsync, playlists)
        mPrint('TEST', 'musicBridge.play() returned')
    except Exception:
        await interaction.followup.send(lang.music.player.generic_error, ephemeral=True)
        mPrint('ERROR', traceback.format_exc())

# ======== MISC ========= #
@tree.command(name="module-info", description=lang.slash.module_info)
@app_commands.default_permissions()
async def module_info(interaction : discord.Interaction):
    if (not config.reply) and (not config.chess) and (not config.music):
        await interaction.response.send_message("There are no available modules.", ephemeral=True)
        return
    
    guildID = int(interaction.guild.id)
    await interaction.response.defer(ephemeral=True)

    embed=discord.Embed(
        title=lang.commands.module_info_embedTitle(guildName=interaction.guild.name),
        description=lang.commands.module_info_embedDesc,
        color=col.orange
    )

    #get all guild channels
    allChannels = await interaction.guild.fetch_channels()
    #extract only the TextChannels
    allChannels:list[discord.TextChannel] = [x for x in allChannels if x.type == discord.ChannelType.text]
    allChannelsID:list[int] = [x.id for x in allChannels if x.type == discord.ChannelType.text]

    responseChannels = ""
    #foreach disabled channel (id)
    for channelID in settings[guildID]['responseSettings']['disabled_channels']:
        #if channel id is present in the guild
        for guildCh in allChannels:
            if channelID == guildCh.id:
                responseChannels = responseChannels + f"{guildCh.mention}\n"
                break
        #clean guildsData from no-longer existing channels:
        if channelID not in allChannelsID:
            mPrint('DEBUG', f'found removed channel {ch}')
            settings[guildID]['responseSettings']['disabled_channels'].remove(ch)
    #Add N/A if string
    responseChannels = lang.commands.module_info_no_blacklisted if responseChannels == "" else responseChannels

    chessChannels = ""
    #foreach disabled channel (id)
    for ch in settings[guildID]['chessGame']['disabled_channels']:
        #if channel id is present in the guild
        for guildCh in allChannels:
            if ch == guildCh.id:
                chessChannels = chessChannels + f"{guildCh.mention}\n"
                break
        #clean guildsData from no-longer existing channels:
        if ch not in allChannelsID:
            mPrint('DEBUG', f'found removed channel {ch}')
            settings[guildID]['chessGame']['disabled_channels'].remove(ch)
    #Add N/A if string
    chessChannels = lang.commands.module_info_no_blacklisted if chessChannels == "" else chessChannels

    musicChannels = ""
    #foreach disabled channel (id)
    for ch in settings[guildID]['musicbot']['disabled_channels']:
        #if channel id is present in the guild
        for guildCh in allChannels:
            if ch == guildCh.id:
                musicChannels = musicChannels + f"{guildCh.mention}\n"
                break
        #clean guildsData from no-longer existing channels:
        if ch not in allChannelsID:
            mPrint('DEBUG', f'found removed channel {ch}')
            settings[guildID]['musicbot']['disabled_channels'].remove(ch)
    #Add N/A if string
    musicChannels = lang.commands.module_info_no_blacklisted if musicChannels == "" else musicChannels

    if config.reply: embed.add_field(name="**Chat replies blacklist:**", value=responseChannels, inline=False)
    if config.chess: embed.add_field(name="**Chess blacklist:**", value=chessChannels, inline=False)
    if config.music: embed.add_field(name="**Music Bot blacklist:**", value=musicChannels, inline=False)
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="module", description=lang.slash.module)
@app_commands.choices(modules=[
    app_commands.Choice(name=lang.choices.all, value="0"),
    app_commands.Choice(name=lang.choices.reply, value="1"),
    app_commands.Choice(name=lang.choices.chess, value="2"),
    app_commands.Choice(name=lang.choices.music, value="3"),
])
@app_commands.default_permissions()
async def module_settings(interaction : discord.Interaction, modules:app_commands.Choice[str], channel:discord.TextChannel=None, enable:bool=None):
    """
    :param channel: on which text channel (default=every channel)
    :param enable: whether to enable or disable the module
    """
    if (not config.reply) and (not config.chess) and (not config.music):
        await interaction.response.send_message("There are no available modules.", ephemeral=True)
        return
    
    mPrint('CMDS', f'called /module: {modules.name})')
    guildID = int(interaction.guild.id)
    response = int(modules.value)
    await interaction.response.defer(ephemeral=True)

    wantedModules = []
    if response == 0:
        if config.reply: wantedModules.append('responseSettings')
        if config.chess: wantedModules.append('chessGame')
        if config.music: wantedModules.append('musicbot')
    elif response == 1:
        if config.reply: wantedModules = ['responseSettings']
    elif response == 2:
        if config.chess: wantedModules = ['chessGame']
    elif response == 3:
       if config.music:  wantedModules = ['musicbot']
    else:
        mPrint('ERROR', f'Invalid response "{response}" for module_settings()')
        await interaction.followup.send("There was an error with your request")
        return
    
    if wantedModules == []:
        await interaction.followup.send("Module(s) not available.", ephemeral=True)
        return


    if len(wantedModules) == 1:
        module = wantedModules[0]
        if enable == None: #send info about the module
            resp = lang.commands.module_disabled_in_channel(modules.name) 
            for ch in settings[guildID][module]['disabled_channels']:
                channel = await bot.fetch_channel(ch)
                resp = resp + f"{channel.mention}\n"
            await interaction.followup.send(resp, ephemeral=True)
            return
        elif channel == None: #change setting for every channel
            if enable == False: #user wants to disable setting in every channel
                allChannels = await interaction.guild.fetch_channels()
                settings[guildID][module]['disabled_channels'] = []
                for c in allChannels:
                    if c.type == discord.ChannelType.text:
                        settings[guildID][module]['disabled_channels'].append(c.id)
                dumpSettings(guildID)
                await interaction.followup.send(lang.commands.module_disabled_all_channels(modules.name), ephemeral=True)
            else: #user wants to enable setting in every channel
                settings[guildID][module]['disabled_channels'] = []
                dumpSettings(guildID)
                await interaction.followup.send(lang.commands.module_enabled_all_channels(modules.name), ephemeral=True)
        else: #change setting for specific channel
            if channel.id in settings[guildID][module]['disabled_channels']: #channel was already disabled
                if enable == False:
                    await interaction.followup.send(lang.commands.module_already_disabled(modules.name, channel.mention), ephemeral=True)
                    pass #channel was already enabled
                else:
                    settings[guildID][module]['disabled_channels'].remove(channel.id)
                    dumpSettings(guildID)
                    await interaction.followup.send(lang.commands.module_now_enabled(modules.name, channel.mention), ephemeral=True)
            else: #channel was enabled
                if enable == False:
                    settings[guildID][module]['disabled_channels'].append(channel.id)
                    dumpSettings(guildID)
                    await interaction.followup.send(lang.commands.module_now_disabled(modules.name, channel.mention), ephemeral=True)
                else:
                    await interaction.followup.send(lang.commands.module_already_enabled(modules.name, channel.mention), ephemeral=True)
                    pass #channel was already disabled
    else:
        if enable == None:
            await interaction.followup.send(lang.commands.module_arg_missing, ephemeral=True)
            return
        try:
            allChannels = await interaction.guild.fetch_channels()
            for module in wantedModules:
                if channel == None: #change every module for every channel
                    if enable == False: #user wants to disable setting in every channel
                        settings[guildID][module]['disabled_channels'] = []
                        for ch in allChannels:
                            if ch.type == discord.ChannelType.text:
                                settings[guildID][module]['disabled_channels'].append(ch.id)
                        
                    else: #user wants to enable setting in every channel
                        settings[guildID][module]['disabled_channels'] = []
                        
                else: #change setting for specific channel
                    if channel.id in settings[guildID][module]['disabled_channels']: #channel was disabled
                        if enable == False:
                            pass #channel was already disabled
                        else:
                            settings[guildID][module]['disabled_channels'].remove(channel.id)
                            
                    else: #channel was enabled
                        if enable == False:
                            settings[guildID][module]['disabled_channels'].append(channel.id)
                        else:
                            pass #channel was already disabled
            dumpSettings(guildID)
            await interaction.followup.send(lang.commands.module_done)
        except Exception:
            mPrint('ERROR', f'0x1000\n{traceback.format_exc()}')
            await interaction.followup.send(lang.commands.module_error, ephemeral=True)

@tree.command(name="feedback", description=lang.slash.feedback)
@app_commands.choices(category=[
        app_commands.Choice(name="Bug report", value="0"),
        app_commands.Choice(name="Feature request", value="1"),
        app_commands.Choice(name="Other", value="2"),
])
async def feedback(interaction : discord.Interaction, category:app_commands.Choice[str]):
    """
    :param category: PRESS ENTER AFTER SELECTING CATEGORY
    """
    class Feedback(discord.ui.Modal, title='Invia il feedback'):
        input = discord.ui.TextInput(label="This form is anonymous", style=discord.TextStyle.long, required=True, placeholder="If you want a reply, add your name#0000 in this form")
 
        async def on_submit(self, interaction: discord.Interaction):
            now = datetime.now().strftime("[%d/%m/%y %H:%M:%S]")
            message = f"{now}-({interaction.id})\nUser submitted feedback **{category.name}**\n`{str(self.input.value)}`\n"
            try:
                if bot.dev != None:
                    await bot.dev.send(message)
            except Exception:
                await bot.dev.send(f"Someone sent a feedback: ID -> {interaction.id}")

            mPrint('INFO', message)
            with open('feedback.log', 'a') as f:
                f.writelines(message)

            await interaction.response.send_message(f'Thank you for your feedback ❤', ephemeral=True)
 
    await interaction.response.send_modal(Feedback())

    return

# @tree.command(name="test", description="a testing command for user Spotify Activities")
# async def feedback(interaction : discord.Interaction):
#     for a in interaction.user.activities:
#         print(a)
#     await interaction.response.send_message('ok', ephemeral=True)


#           -----           BOT RUN SCRIPT           -----       #

try:
    bot.run(TOKEN)
except:
    mPrint('FATAL', f'Discord key absent or wrong. Unauthorized\n{traceback.format_exc()}')


# Birthday: 07/May/2022 🥳
