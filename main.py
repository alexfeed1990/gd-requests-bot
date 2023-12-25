import tkinter as tk
from tkinter import ttk
from dotenv import load_dotenv
import requests, os, datetime, time, json
import sv_ttk, pytchat  # i use pytchat because quota :sob:
import lib.yt as yt  # lib/yt.py
import lib.embedbuilder as embedbuilder  # lib/embedbuilder.py

load_dotenv()

# config #

CONFIG_FILE = "bot/options.json"

try:
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            config_obj = json.load(file)
    else:
        print(f"[Error]: Loading Options: {CONFIG_FILE} does not exist.")
except Exception as e:
    print(f"[Error] Loading Options: {e}")

######################################################################################################################
# Bot variables                                                                                                      #
######################################################################################################################

root = tk.Tk()  # this is for ui

persistent_rerequests = tk.BooleanVar()
persistent_rerequests.set(config_obj["persistent_rerequests"])

separate_rerequest_webhook = tk.BooleanVar()
separate_rerequest_webhook.set(config_obj["separate_rerequest_webhook"])

prefix = tk.StringVar();
prefix.set(config_obj["bot_prefix"]);

SEEN_FILE = config_obj["seen_file"]
commands = ["submit", "help"]
seen_levels = []
WEBHOOK_URL = config_obj["webhook_url"]
REREQUEST_WEBHOOK_URL = config_obj["rerequest_webhook_url"]

######################################################################################################################
# Bot functions                                                                                                  #
######################################################################################################################

def bot_loop():
    try:
        chat = pytchat.create(video_id=broadcast_id)
        
        while chat.is_alive():
            for obj in chat.get().sync_items():
                if obj.message[0] != prefix.get():
                    continue

                message = obj.message[1:]
                message = message.split(" ")

                command = message[0]
                message.pop(0) # stupid python logic
                args = message

                if command == "submit":
                    submit(args[0], obj.author.name)
    except Exception as e:
        print(f"[Error] bot_loop(): {e} \nThis is likely because the stream is private (or inevitably pytchat is obsolete).")

# Dont use this unless pytchat is obsolete!!!!
# I have 0 idea if this works and i am not willing to test it
def bot_loop_google():
    try:
        # I use pytchat here because yt api reaches quota in like 2 hours with 5 second delay inbetween every request
        last_messages = []
        while time.sleep(5):  # 5 is also arbitrary number but again stupid quota limit
            messages = yt.get_live_chat_messages(bot_api_service, live_chat_id, 10)
            # 10 is arbitrary number but i do not recommed any more

            if len(messages) == 0:
                continue
            elif messages == last_messages:
                continue

            last_messages = messages
            for obj in messages:
                if obj["message"][0] != prefix.get():
                    continue

                message = obj["message"][1:]
                message = message.split(" ")

                command = message[0]
                message.pop(0)
                # stupid python logic
                args = message

                if command == "submit":
                    submit(args[0], obj["author"]["name"])
    except Exception as e:
        print(f"[Error] bot_loop_google(): {e} \nThis is likely because you reached the request quota limit on the YouTube Data API.")

# Helper functions

def pairwise(t):
    it = iter(t)
    return zip(it, it)


def load_seen_levels():
    try:
        if os.path.isfile(SEEN_FILE):
            with open(SEEN_FILE, "r") as file:
                lines = file.readlines()
                for line in lines:
                    seen_levels.append(line.strip())
        else:
            print(f"[Error]: load_seen_levels(): {SEEN_FILE} does not exist.")
            return
    except Exception as e:
        print(f"[Error] load_seen_levels(): {e}")


def getDifficultyString(level):
    if level["auto"] and len(level["auto"].strip()) > 0:
        return "<:Auto:1187920512937103390>Auto"
    if level["demon"] == "1":
        return {
            3: "<:EasyDemon:1187920085856309348>Easy Demon",
            4: "<:MediumDemon:1187920082622480494>Medium Demon",
            0: "<:HardDemon:1187920077983580260>Hard Demon",
            5: "<:InsaneDemon:1187920072275136592>Insane Demon",
            6: "<:ExtremeDemon:1187920070052155412>Extreme Demon",
        }[int(level["demon_difficulty"])]
    return {
        0: "<:Unrated:1187920515793420319>N/A",
        10: "<:Easy:1187920102625128498>Easy",
        20: "<:Normal:1187920106995585144>Normal",
        30: "<:Hard:1187920099668135946>Hard",
        40: "<:Harder:1187920095633231924>Harder",
        50: "<:Insane:1187920090386141204>Insane",
    }[int(level["difficulty_numerator"])]


# https://wyliemaster.github.io/gddocs/#/resources/server/level
level_keys = {
    1: "id",
    2: "name",
    3: "description",
    5: "version",
    6: "creator_id",
    9: "difficulty_numerator",
    10: "downloads",
    12: "official_song",
    14: "likes",
    17: "demon",  # 1 if yes otherwise empty str
    43: "demon_difficulty",
    18: "stars",  # erm it's moons actually 🤓
    19: "feature_score",
    42: "epic",  # if non 0 it's epic
    45: "object_count",
    37: "coins",
    35: "custom_song_id",
    25: "auto",
}  # auto is bullshit, check GDApi how it parses bools

######################################################################################################################
# Command functions                                                                                                  #
######################################################################################################################

# Level submit function
def submit(id, user):
    data = {
        "type": 0,  # normal search
        "str": id,  # level id
        "secret": "Wmfd2893gb7",
    }

    # Look up the level
    try:
        req = requests.post(url="http://www.boomlings.com/database/getGJLevels21.php", data=data, headers={"User-Agent": ""})
        if req.text == -1:
            yt.send_message(bot_api_service, live_chat_id, f"@{user} Level {id} does not exist. Please try again!")
            return;
        [levels, creators, songs, page_info, hash] = req.text.split("#")
        creators_parsed = {x[0]: {"username": x[1], "account_id": x[2]} for x in map(lambda c: c.split(":"), creators.split("|"))}
        levels_parsed = []
    except Exception as e:
        print(f"[Error] submit() (init): {e} \nThis is likely because you're banned from GD servers (very unlikely).")

    # Parses level
    try:
        for level in levels.split("|"):
            level_obj = {}
            pairs = pairwise(level.split(":"))
            for pair in pairs:
                k = int(pair[0])
                v = pair[1]
                key = level_keys.get(k)
                if key is not None:
                    if key == "creator_id":
                        level_obj["creator_name"] = creators_parsed[v]["username"]
                    level_obj[key] = v

            # Rerequest check
            level_obj["rerequest"] = level_obj["id"] in seen_levels
            levels_parsed.append(level_obj)

        # sanity check
        if len(levels_parsed) == 0:
            yt.send_message(bot_api_service, live_chat_id, f"@{user} Level {id} does not exist. Please try again!")
            return
    except Exception as e:
        print(f"[Error] submit() (parsing level): {e}")

    # write to seen levels
    try:
        level = levels_parsed[0]
        seen_levels.append(level["id"])
        with open(SEEN_FILE, "a+") as file:
            file.write(level["id"] + "\n")
    except Exception as e:
        print(f"[Error] submit(): {e}")

    # Variables
    level_name = level["name"]
    creator_name = level["creator_name"]
    coin_count = int(level["coins"])

    # Send level to discord
    try:
        embed = (embedbuilder.Embed("",
                 f"**{level_name}** by **{creator_name}** sent by **{user}**", # desc
                 0x8E30E6 if level["rerequest"] else 0x00FFFF,) # color
                 .Field("Level ID:", level["id"], True)
                 .Field("Difficulty:", getDifficultyString(level), True)
                 .Field("Downloads:", "<:downloads:364076905130885122>" + level["downloads"], True,)
                 .Field("Likes:", "<:likes:364076087648452610>" + level["likes"], True)
                 .Field("Coins:", "None :(" if coin_count < 1 else ("<:coin:376444770438086667>" * coin_count), True,)
                 .Field("Stars:", "<:stars:831285660841148487>" + level["stars"], True)
                 .Timestamp(datetime.datetime.utcnow().isoformat())
                 .Author('Level resubmitted!' if level["rerequest"] else 'Level submitted!', 
                         'https://i.imgur.com/RvWaD6v.png' if level["rerequest"] else 'https://i.imgur.com/asoMj1W.png'))                 

        discord_message = {             
            "content": "",
            "tts": False,
            "embeds": [
                json.loads(embed.Build())
        ]}
        
        # send the stuff
        json_data = json.dumps(discord_message)
        if separate_rerequest_webhook.get():      
            requests.post(REREQUEST_WEBHOOK_URL if level["rerequest"] else WEBHOOK_URL, data=json_data, headers={"Content-Type": "application/json"})
        else:
            requests.post(WEBHOOK_URL, data=json_data, headers={"Content-Type": "application/json"})
    except Exception as e:
        print(f"[Error] submit(): {e} \nThis is likely because of incorrect data sent from the message (unicode characters in author name?) or because of an incorrect Disocrd webhook url.")

    yt.send_message(bot_api_service, live_chat_id, f"@{user} Level {id} has been sent!")


def apply_settings():    
    try:
        # change settings in obj
        config_obj["bot_prefix"] = prefix.get()
        print(prefix.get())
        config_obj["separate_rerequest_webhook"] = separate_rerequest_webhook.get()
        config_obj["persistent_rerequests"] = persistent_rerequests.get()

        # WARNING: this does not work properly
        # it deletes your current seen levels if you change the option
        if persistent_rerequests.get() == True:
            load_seen_levels()
        else:
            seen_levels = []
    except Exception as e:
        print(f"[Error] apply_settings() (changing config_obj): {e}")

    try:
        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "w") as file:
                file.write(json.dumps(config_obj, indent=4))
        else:
            print(f"[Error]: apply_settings(): {CONFIG_FILE} does not exist.")
    except Exception as e:
        print(f"[Error] apply_settings() (writing to options file): {e}")

# YT Data API authentication #

try:
    bot_api_service = yt.bot_authenticate()  # Bot api
    user_api_service = yt.user_authenticate()  # Live streaming user api

    broadcast_id = yt.get_latest_live_broadcast_id(bot_api_service, yt.get_channel_id(user_api_service))
    live_chat_id = yt.get_live_chat_id(user_api_service, broadcast_id)
except Exception as e:
    print(f"[Error] Auth code: {e} \nThis is likely because of a wrong login in either of the accounts.")

# GUI #

try:
    prefix_label = ttk.Label(root, text="Prefix")
    prefix_label.grid(row=0, column=0, pady=2, padx=5)
    prefix_entry = ttk.Entry(root, textvariable=prefix)
    prefix_entry.grid(row=0, column=1, pady=10, padx=5)

    persistent_rerequests_checkbox = ttk.Checkbutton(root, text="Persistent rerequests", variable=persistent_rerequests)
    persistent_rerequests_checkbox.grid(row=1, column=0, columnspan=2, pady=10, sticky="w")

    separate_rerequests_checkbox = ttk.Checkbutton(root, text="Separate rerequests", variable=separate_rerequest_webhook)
    separate_rerequests_checkbox.grid(row=2, column=0, columnspan=2, pady=10, sticky="w")

    apply = ttk.Button(root, text="Apply settings", command=apply_settings)
    apply.grid(row=3, column=0, columnspan=2, pady=10)

    button = ttk.Button(root, text="Start Chatbot", command=bot_loop)
    button.grid(row=4, column=0, columnspan=2, pady=10)
except Exception as e:
    print(f"[Error] UI code error: {e}")

# UI Init code #

try:
    if config_obj["persistent_rerequests"]:  # i should find a better place to put this
        load_seen_levels()
    else:
        seen_levels = []

    sv_ttk.set_theme("dark")
    root.mainloop()
except Exception as e:
    print(f"[Error] UI Init code: {e}\n This is likely because of wrong UI code.")
