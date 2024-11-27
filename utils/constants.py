SETTINGS_TEMPLATE = {
    "id": {
        "responseSettings": {
            "disabled_channels":[],
            "join_message": "",
            "leave_message": "",
            "send_join_msg": False,
            "send_leave_msg": False,
            "response_perc": 35,
            "other_response": 9,
            "response_to_bots_perc": 35,
            "will_respond_to_bots": False,
            "use_global_words": False,
            "custom_words": ["butt"]
        },
        "chessGame": {
            "disabled_channels": [],
            "default_board": "default",
            "boards": {},
            "default_design": "default",
            "designs": {}
        },
        "musicbot": {
            "player_shuffle": True,
            "disabled_channels": [],
            "saved_playlists": {},
            "timeline_precision": 14
        }
    }
}

# folders
spotify_netloc = 'open.spotify.com'

settings_folder = "botFiles/guilds_data/"
urlsync_folder = 'music/urlsync/'


FATAL = 100
ERROR = 70
WARN = 60
INFO = 30
DEBUG = 10
TEST = 9
FUNC = 5
ALL = 0