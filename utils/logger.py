import codecs
from datetime import datetime
import os
import traceback
from constants import ALL, FUNC, TEST, DEBUG, INFO, WARN, ERROR, FATAL
from colorama import Fore, Back, Style, init
from config import do_print_color, min_print_level, min_log_level, \
                    do_print_date, do_print_time, do_print_guild_id, \
                    debug_mode
init()

HOSTNAME = 'logs5.papertrailapp.com'
PORT = 28649

severity_str = {
    FATAL: 'FATAL',
    ERROR: 'ERROR',
    WARN: 'WARN',
    INFO: 'INFO',
    DEBUG: 'DEBUG',
    TEST: 'TEST',
    FUNC: 'FUNC',
    ALL: 'ALL'
}


# logging.basicConfig(handlers=[
#     SysLogHandler(address=(HOSTNAME, PORT)),
# ])

#terminal handler
# terminal_logger = logging.getLogger('bot')
# terminal_logger.setLevel(logging.DEBUG)

# sh = logging.StreamHandler()
# sh.setLevel(logging.DEBUG)
# sh.setFormatter(logging.Formatter(Style.BRIGHT + Fore.LIGHTBLACK_EX + "%(asctime)s %(message)s" + Style.RESET_ALL, "%d/%m/%y %H:%M:%S"))
# terminal_logger.addHandler(sh)

#papertrail handler
# papertrail_logger = logging.getLogger('testlog')
# papertrail_logger.setLevel(logging.DEBUG)

class LoggerHandler():
    def __init__(self, module_name, guild_id = None) -> None:
        self.module_name = module_name
        self.guild_id = guild_id

    def getModuleName(self) -> str:
        return f"({self.module_name})" * debug_mode

    def fatal(self, message) -> None:
        format_msg = f"{Fore.RED}{Style.BRIGHT} [FATAL]{self.getModuleName()} {Style.NORMAL}{message}{Fore.RESET}"
        self.log(message, format_msg, FATAL)
        # papertrail_logger.critical(f"FATAL {message}")

        # xd = f"{self.guild_id} {Fore.RED}FATAL {message}"
        # terminal_logger.critical(f"<{self.guild_id}>{Fore.RED}{Style.BRIGHT} FATAL {Style.NORMAL}{message}{Fore.RESET}")
        # papertrail_logger.critical(f"FATAL {message}")

    def error(self, message) -> None:
        format_msg = f"{Fore.RED}{Style.BRIGHT} [ERROR]{self.getModuleName()} {Style.NORMAL}{message}{Fore.RESET}"
        self.log(message, format_msg, ERROR)

    def warn(self, message) -> None:
        format_msg = f"{Fore.YELLOW}{Style.BRIGHT}  [WARN]{self.getModuleName()} {Style.NORMAL}{message}{Fore.RESET}"
        self.log(message, format_msg, WARN)

    def info(self, message) -> None:
        format_msg = f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}  [INFO]{self.getModuleName()} {Style.NORMAL}{message}{Fore.RESET}"
        self.log(message, format_msg, INFO)

    def debug(self, message) -> None:
        format_msg = f"{Fore.MAGENTA}{Style.BRIGHT} [DEBUG]{self.getModuleName()} {Style.NORMAL}{message}{Fore.RESET}"
        self.log(message, format_msg, DEBUG)

    def test(self, message) -> None:
        format_msg = f"{Fore.YELLOW}{Style.BRIGHT}  [TEST]{self.getModuleName()} {Style.NORMAL}{message}{Fore.RESET}"
        self.log(message, format_msg, TEST)

    def func(self, message) -> None:
        format_msg = f"{Fore.LIGHTBLACK_EX}  [FUNC]{self.getModuleName()} {Style.NORMAL}{message}{Fore.RESET}"
        self.log(message, format_msg, INFO)

    # ---- #
    def log(self, original_msg, message, level):
        now = ""
        now_print = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        if do_print_date and do_print_time:
            now = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        elif do_print_date:
            now = datetime.now().strftime("%d/%m/%y")
        elif do_print_time:
            now = datetime.now().strftime("%H:%M:%S")
        now = f"{Fore.LIGHTBLACK_EX}{Style.BRIGHT}{now}"
        
        guild = ""
        if do_print_guild_id:
            guild = f"{Fore.LIGHTBLACK_EX}{Style.BRIGHT} <{self.guild_id}>"

        if level >= min_print_level: 
            print(f"{now}{guild}{Fore.RESET}{message}")

        if level > min_log_level:
            path = f'logs/{self.guild_id}.log' if (self.guild_id != None) else 'logs/default'
            
            if not(os.path.exists('logs/')): os.mkdir('logs/')
            if not(os.path.exists(path)): 
                with open(path, 'w'):
                    print('DEBUG generated new logfile')

            with codecs.open(path, 'a', 'utf-8') as f:
                f.write(f'[{now_print}] {self.guild_id} [{severity_str[level]}] {original_msg}\n')
  

 

# l = LoggerHandler('logger', '1234567890')
# l.fatal('nest')
# l.error('test')
# l.warn('test')
# l.info('test')
# l.debug('test')
# l.test('test')
# l.func('test')