import os
import time
from random import choice

import requests
from dotenv import load_dotenv
from slack_sdk import WebClient

load_dotenv()

# --- CONFIGURATION ---
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_USER = os.getenv("LASTFM_USER")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")
SLACK_USER_ID = os.getenv("SLACK_UID")

MUSIC_MESSAGE_FILE = os.getenv("MESSAGE_FILE")

POLL_INTERVAL = 25  # seconds between checks
SESSION_TIMEOUT = 10 * 60  # 10 minutes inactivity resets session

# --- SETUP ---
slack = WebClient(token=SLACK_TOKEN)
last_track_name = None
thread_ts = None
last_activity_time = 0

with open(MUSIC_MESSAGE_FILE, "r") as f:  # pyright: ignore[reportArgumentType, reportCallIssue]
    MUSIC_MESSAGE = f.readline()

# --- Music Responses ---
custom_messages = [
    "Oh look, {ping} is listening to *{song}* by *{artist}*",
    "Really? You're listening to *{song}* by *{artist}* in 2026? Questionable.",
    ":loll: Imagine thinking *{song}* by *{artist}* is good in 2026.",
    "Oh look, {ping} is listening to *{song}* by *{artist}*.",
    "Really? You’re seriously listening to *{song}* by *{artist}* in 2026?",
    "*{song}* by *{artist}*? That’s the hill you’re dying on?",
    "Not {ping} playing *{song}* by *{artist}* like it’s still relevant.",
    "*{song}* by *{artist}* just came on… instant judgment.",
    "*{song}* by *{artist}*? PEAK :ultrafastcatppuccinparrot:",
    "Hey, {ping} is listening to my favourite song, *{song}* by *{artist}*",
]
last_reply = ""

# --- MAIN LOOP ---
while True:
    try:
        response = requests.get(
            "http://ws.audioscrobbler.com/2.0/",
            params={
                "method": "user.getrecenttracks",
                "user": LASTFM_USER,
                "api_key": LASTFM_API_KEY,
                "format": "json",
                "limit": 1,
            },
        ).json()

        track = response["recenttracks"]["track"][0]
        now_playing = track.get("@attr", {}).get("nowplaying") == "true"
        current_time = time.time()

        # Reset session if timeout reached
        if thread_ts and (current_time - last_activity_time) > SESSION_TIMEOUT:
            thread_ts = None
            last_track_name = None

        if now_playing and track["name"] != last_track_name:
            last_track_name = track["name"]
            last_activity_time = current_time

            # If no thread exists, start a new session
            if thread_ts is None:
                resp = slack.chat_postMessage(
                    channel=SLACK_CHANNEL,
                    text=f"<@{SLACK_USER_ID}> started a listening session, {MUSIC_MESSAGE}",
                )
                thread_ts = resp["ts"]

            # Get album art url
            images = track.get("image", [])

            album_art_url = next(
                (img["#text"] for img in reversed(images) if img.get("#text")), None
            )
            if track["name"].strip().lower() == "buddy holly":
                slack.chat_postMessage(
                    channel=SLACK_CHANNEL,
                    reply_broadcast=True,
                    thread_ts=thread_ts,
                    text=f"{track['name']} by {track['artist']['#text']}",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "GET WEEZERED :loll: It's Buddy Holly by Weezer.",
                            },
                        },
                        {
                            "type": "image",
                            "image_url": album_art_url,
                            "alt_text": "Album art",
                        },
                    ],
                )
            else:
                while True:
                    reply = choice(custom_messages)
                    if reply != last_reply:
                        last_reply = reply
                        break
                    reply.format(
                        ping=f"<@{SLACK_USER_ID}>",
                        song=track["name"],
                        artist=track["artist"]["#text"],
                    )
                # Post song under the session thread
                slack.chat_postMessage(
                    channel=SLACK_CHANNEL,
                    thread_ts=thread_ts,
                    text=reply,
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": reply,
                            },
                        },
                        {
                            "type": "image",
                            "image_url": album_art_url,
                            "alt_text": "Album art",
                        },
                    ],
                )

    except Exception as e:
        print(f"Error: {e}")

    time.sleep(POLL_INTERVAL)
