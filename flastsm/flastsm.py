import requests
from slack_sdk import WebClient
import time
from dotenv import load_dotenv
import os

load_dotenv()

# --- CONFIGURATION ---
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_USER = os.getenv("LASTFM_USER")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")
SLACK_USER_ID = os.getenv("SLACK_UID")

POLL_INTERVAL = 25           # seconds between checks
SESSION_TIMEOUT = 10 * 60    # 10 minutes inactivity resets session

# --- SETUP ---
slack = WebClient(token=SLACK_TOKEN)
last_track_name = None
thread_ts = None
last_activity_time = 0

with open("message.txt", 'r') as f:
   MUSIC_MESSAGE = f.readline() 

# --- MAIN LOOP ---
while True:
    try:
        response = requests.get("http://ws.audioscrobbler.com/2.0/", params={
            "method": "user.getrecenttracks",
            "user": LASTFM_USER,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "limit": 1
        }).json()

        track = response['recenttracks']['track'][0]
        now_playing = track.get('@attr', {}).get('nowplaying') == 'true'
        current_time = time.time()

        # Reset session if timeout reached
        if thread_ts and (current_time - last_activity_time) > SESSION_TIMEOUT:
            thread_ts = None
            last_track_name = None

        if now_playing and track['name'] != last_track_name:
            last_track_name = track['name']
            last_activity_time = current_time

            # If no thread exists, start a new session
            if thread_ts is None:
                resp = slack.chat_postMessage(
                    channel=SLACK_CHANNEL,
                    text=f"<@{SLACK_USER_ID}> started a listening session, {MUSIC_MESSAGE}",
                )
                thread_ts = resp['ts']

            # Post song under the session thread
            slack.chat_postMessage(
                channel=SLACK_CHANNEL,
                text=f"{track['name']} by {track['artist']['#text']}",
                thread_ts=thread_ts
            )

    except Exception as e:
        print(f"Error: {e}")

    time.sleep(POLL_INTERVAL)
