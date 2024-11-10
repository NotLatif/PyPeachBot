<img  align="right"  src="botFiles/src/logo.png"  width="200px">

# [CuloBot](https://culobot.notlatif.com)

**Note:** This project is currently abandoned, but I might come back in the future and pick it back up.

A discord bot that can play music, let's you play chess and do other things.
**please submit issues, thank you**

If you like the project and want to help, consider [buying me a coffee!](https://www.buymeacoffee.com/CuloBot)


### [Join the Discord](https://discord.com/invite/YTvn5Zwc5R)



  

## About

Sorry for the poor documentation, I'll improve it later (maybe)


## How to self-host the bot
#### Prerequisites:
- Python 3.9.2

- modules in `requirements.txt` file
- A copy of [ffmpeg](https://ffmpeg.org) added to [path](https://www.thewindowsclub.com/how-to-install-ffmpeg-on-windows-10) (Only needed to use the musicbot module)

- The discord token of your bot [create a bot here](https://discord.com/developers/applications)

- [optional] The spotify key and user id [You can get them here](https://developer.spotify.com/dashboard/applications)

  

#### steps:

1. clone repository in a folder `git clone https://github.com/NotLatif/CuloBot .`

1. open the folder in a terminal and `cd` to the folder

1. `python -m venv .venv` to create a python virtual environment (recommended)

    - `.\.venv\Scripts\activate` to activate the virtual environment
    - When needed use `deactivate` to deactivate the virtual environment

1. `python -m pip install -r .\requirements.txt` to install the required modules

1. run the `bot.py` file with python

1. edit the `.env` file adding your keys without quotes

1. on the Developer portal, enable intents under `Privileged gateway intents`

1. click on `OAuth2` -> `Url generator`

1. check `Bot` in the left and choose the permissions you want the bot to have

1. add the bot to your server

1. set your wanted configs in `config.py`

1. run `bot.py`

1. everything should be good

#### Youtube age restricted videos

To enable the download of age restricted videos

1. Sign in to Youtube on your browser
2. Save all the cookies using a cookie grabber extension
3. While browsing youtube (or preferably watching an age restricted video), click on the extension and export the cookies captured by the extension to `music/.yt_cookies.txt`
