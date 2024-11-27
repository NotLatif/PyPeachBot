#from utils.constants import ALL, DEBUG, INFO, WARN, ERROR, FATAL
from discord import Status
# This file contains global configs (which affect every guild) and configs about the script.
# Modifications are effective only after a bot restart

bot_name = "CuloBot"
bot_description = "/play"
bot_status = Status.online
debug_mode = True

language = "EN" # [IT, EN]

# logging
min_log_level = 2       # | 0: all / 1: info / 2: warn / 3: error |
min_print_level = 0     # |                  -                    |
do_print_color = True
do_print_date = True
do_print_time = True
do_print_guild_id = True
remote_logging = False #WIP (does not work yet)

# BOT

#MUSIC PLAYER
timeline_chars = ('▂', '▅')
# Default: ('▂', '▅') -> The character shown in the timeline (tuple[str:str], the first str is the base, the second is the current progress)

timeline_max = 14 
#the max timeline precision guilds can set
# WARNING: a value too high could get you rate limited by the discord API

max_alone_time = 60 * 5
# Default: 300 -> (max=300) The maximum time (in seconds) the bot can play music while no one is connected to the voice channel
no_music_timeout = 60
# Default: 60 The time (in seconds) the bot will stay in VC after the queue ends (0 for not time) (-1 for infinite time)

class Colors:
    error = 0xff0000
    red = 0xd32c41
    orange = 0xf39641
    blu = 0x0a7ace
    blue = 0x0a7ace
    aqua = 0x7cdcfe
    green = 0x27E039
    black = 0x030303
    white = 0xf2f2f2

# Enable/Disable individual modules globally (for every guild)
reply = False 
chess = True
music = True
discord_events = False # message on member join and leave 