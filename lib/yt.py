import os, json

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# config #

CONFIG_FILE = "bot/options.json"
YT_SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

try:
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            config_obj = json.load(file);
    else:
        print(f"[Error]: Loading Options: {CONFIG_FILE} does not exist.");
except Exception as e:
    print(f"[Error] Loading Options: {e}")

# files #

BOT_CLIENT_SECRETS_FILE = config_obj["bot_client_secrets_file"]
BOT_TOKEN_FILE = config_obj["bot_token_file"]

USER_CLIENT_SECRETS_FILE = config_obj["user_client_secrets_file"]
USER_TOKEN_FILE = config_obj["user_token_file"]

# Authenticate bot
def bot_authenticate():
    credentials = None

    if os.path.exists(BOT_TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(BOT_TOKEN_FILE)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            print("Please log in as the bot account.")
            flow = InstalledAppFlow.from_client_secrets_file(BOT_CLIENT_SECRETS_FILE, YT_SCOPES)
            credentials = flow.run_local_server(port=0)

        with open(BOT_TOKEN_FILE, 'w') as token:
            token.write(credentials.to_json())

    return build('youtube', 'v3', credentials=credentials)

# Authenticate user
def user_authenticate():
    credentials = None

    if os.path.exists(USER_TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(USER_TOKEN_FILE)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            print("Please log in as the account who will be livestreaming.")
            flow = InstalledAppFlow.from_client_secrets_file(USER_CLIENT_SECRETS_FILE, YT_SCOPES)
            credentials = flow.run_local_server(port=0)

        with open(USER_TOKEN_FILE, 'w') as token:
            token.write(credentials.to_json())

    return build('youtube', 'v3', credentials=credentials)

# Function to retrieve live chat ID
def get_live_chat_id(api_service, broadcast_id):
    try:
        response = api_service.liveBroadcasts().list(
            part="snippet",
            id=broadcast_id,
            #broadcastStatus="active" # this line is super weird because sometimes you need this and sometimes you cant use it
        ).execute()

        if "items" in response and response["items"]:
            live_chat_id = response["items"][0]["snippet"]["liveChatId"]
            return live_chat_id
        else:
            return None
    except Exception as e:
        print(f"[Error] get_live_chat_id(): {e} \nThis is likely because the user account is not the correct account.")

# Get pfp (this is used for getting messages with google api)
def get_channel_info(api_service, channel_id):
    try:
        response = api_service.channels().list(
            part="snippet",
            id=channel_id
        ).execute()

        items = response.get("items", [])
        return items[0] if items else None
    except Exception as e:
        print(f"[Error] get_channel_info(): {e} \n");

# Get live messages (this is used for getting messages with google api)
def get_live_chat_messages(api_service, live_chat_id, max_results):
    try:
        messages = []
        response = api_service.liveChatMessages().list(
            part="snippet",
            liveChatId=live_chat_id,
            maxResults=max_results
        ).execute()

        for item in response.get("items", []):
            author_channel_id = item["snippet"]["authorChannelId"]
            author_info = get_channel_info(api_service, author_channel_id)
            
            # Extract relevant information from the author_info
            author_display_name = author_info.get("snippet", {}).get("title", "Unknown")
            pfp_url = author_info.get("snippet", {}).get("thumbnails", {}).get("default", {}).get("url", "")
            message_text = item["snippet"]["textMessageDetails"]["messageText"]
            
            messages.append({
                "author": {
                    "name": author_display_name,
                    "pfp": pfp_url
                },
                "message": message_text,
                "snippet": item["snippet"]
            })
        return messages
    except Exception as e:
        print(f"[Error] get_live_chat_messages(): {e} \nThis is likely because you reached the quota limit for requests to the YouTube Data API.");

# Function to send a message to the live chat
def send_message(api_service, live_chat_id, message_text):
    try:
        api_service.liveChatMessages().insert(
            part="snippet",
            body={
                "snippet": {
                    "liveChatId": live_chat_id,
                    "type": "textMessageEvent",
                    "textMessageDetails": {
                        "messageText": message_text
                    }
                }
            }
        ).execute()
    except Exception as e:
        print(f"[Error] send_message(): {e} \nThis is likely because live_chat_id is None, which means that the user account is not the account live streaming.")

# Function to get the latest live broadcast ID for a channel
def get_latest_live_broadcast_id(api_service, channel_id):
    try:
        response = api_service.search().list(
            part="id",
            channelId=channel_id,
            eventType="live",
            type="video",
            order="date"
        ).execute()

        if "items" in response and response["items"]:
            latest_broadcast_id = response["items"][0]["id"]["videoId"]
            return latest_broadcast_id
        else:
            return None
    except Exception as e:
        print(f"[Error] get_latest_live_broadcast_id(): {e} \nThis is likely because the stream is private or unlisted.")

# Get channel id of authenticated **user**
def get_channel_id(api_service):
    try:
        response = api_service.channels().list(part='snippet,contentDetails', mine=True).execute()
        channel_id = response['items'][0]['id']
        return channel_id
    except Exception as e:
        print(f"[Error] get_channel_id(): {e}")
        return None
