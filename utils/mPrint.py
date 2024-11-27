from typing import Literal
import config
import codecs
from datetime import datetime
from colorama import Fore, Style, init
init()

useColors = config.do_print_color
logLevel = config.min_log_level
printLevel = config.min_print_level
timeInTerminal = config.do_print_date

tagType = Literal['ERROR', 'FATAL', 'IMPORTANT', 'SONGERROR', 'WARN', 'GAMErr',
    'INFO', 'MUSIC', 'USER', 'GAME', 'DEBUG', 'VARS', 'TEST', 'FUNC', 
    'CMDS']

def mPrint(tag: tagType, source, text):
    """
    Custom print function to use colors
    """
    willPrint = False
    willLog = False 
    songError = True if tag == 'SONGERROR' else False

    if printLevel <= 3: #ERROR
        if tag in ['ERROR', 'FATAL', 'SONGERROR', 'IMPORTANT']: willPrint = True
    if printLevel <= 2: #WARN
        if tag in ['WARN', 'GAMEErr']: willPrint = True
    if printLevel <= 1: #INFO
        if tag in ['INFO', 'MUSIC', 'USER', 'GAME']: willPrint = True
    if printLevel <= 0: #DEBUG
        if tag in ['DEBUG', 'VARS', 'TEST', 'FUNC', 'CMDS', 'DB']: willPrint = True

    if logLevel <= 3: #ERROR
        if tag in ['ERROR', 'FATAL', 'SONGERROR', 'IMPORTANT']: willLog = True
    if logLevel <= 2: #WARN
        if tag in ['WARN', 'GAMEErr']: willLog = True
    if logLevel <= 1: #INFO
        if tag in ['INFO', 'MUSIC', 'USER', 'GAME']: willLog = True
    if logLevel <= 0: #DEBUG
        if tag in ['DEBUG', 'VARS', 'TEST', 'FUNC', 'CMDS', 'DB']: willLog = True

    if willPrint == False: return

    now = datetime.now().strftime("[%d/%m/%y %H:%M:%S]")

    logstr = f"{now} > [{tag}]({source}): {text}\n"

    style = Style.RESET_ALL

    #tags
    if tag in ['INFO', 'MUSIC']:
        tag = f"{Fore.LIGHTCYAN_EX}[{tag}]"

    elif tag == 'WARN':
        tag = f"{Fore.YELLOW}[{tag}]"

    elif tag in ['ERROR', 'FATAL', 'SONGERROR', 'IMPORTANT']:
        tag = f"{Fore.RED}[{tag}]"
        style = Style.BRIGHT

    elif tag == 'DEBUG':
        tag = f"{Fore.MAGENTA}[{tag}]"

    elif tag in ['FUNC', 'CMDS', 'DB']:
        tag = f"{Fore.LIGHTBLACK_EX}[{tag}]"

    elif tag == 'TEST':
        tag = f"{Fore.YELLOW}[{tag}]"
        style = Style.BRIGHT
 
    elif tag == 'USER':
        tag = f"{Fore.CYAN}[{tag}]"

    #chessEngine TODO
    elif tag == 'GAME':
        tag = f"{Fore.GREEN}[{tag}]"

    elif tag == 'GAMEErr':
        tag = f"{Fore.RED}[{tag}]"

    elif tag == 'VARS':
        tag = f"{Fore.YELLOW}[{tag}]"
        style = Style.DIM

    else:
        tag = f"[{tag}]"

#							  p2 is only used for ENGINE
    time = f"{Fore.LIGHTBLACK_EX}{now}" if timeInTerminal else ''
    print(f'{time}{style}{tag}({source}) - {text}{Fore.RESET}')

    # logger.debug(f"({source}) - {text}")

    #log string
    if willLog:
        with codecs.open('bot.log', 'a', 'utf-8') as f:
            f.write(logstr)