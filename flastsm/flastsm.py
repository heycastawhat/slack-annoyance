import json
import os
import threading
import time
from pathlib import Path
from random import choice

import requests
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

# --- CONFIGURATION ---
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_APP_TOKEN = os.getenv("APP_TOKEN")
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

POLL_INTERVAL = 25  # seconds between checks
SESSION_TIMEOUT = 10 * 60  # 10 minutes inactivity resets session

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
CHANNELS_FILE = DATA_DIR / "channels.json"

# --- SETUP ---
app = App(token=SLACK_TOKEN)

# --- Music Responses ---
custom_messages = [
    "Oh look, {ping} is listening to *{song}* by *{artist}*",
    "Really? You're listening to *{song}* by *{artist}* in 2026? Questionable.",
    ":loll: Imagine thinking *{song}* by *{artist}* is good in 2026.",
    "Oh look, {ping} is listening to *{song}* by *{artist}*.",
    "Really? You're seriously listening to *{song}* by *{artist}* in 2026?",
    "*{song}* by *{artist}*? That's the hill you're dying on?",
    "Not {ping} playing *{song}* by *{artist}* like it's still relevant.",
    "*{song}* by *{artist}* just came on… instant judgment.",
    "*{song}* by *{artist}*? PEAK :ultrafastcatppuccinparrot:",
    "Hey, {ping} is listening to my favourite song, *{song}* by *{artist}*",
    "Wow, *{song}* by *{artist}* is such a classic. Just like {ping}'s taste in music.",
    "Alert the media! {ping} is jamming out to *{song}* by *{artist}*.",
    "Why is {ping} listening to *{song}* by *{artist}*? I thought we agreed on better music.",
    "Look alive everyone, {ping} is playing *{song}* by *{artist}*.",
    "Brace yourselves, *{song}* by *{artist}* is on.",
    "Oh no, {ping} is listening to *{song}* by *{artist}* again.",
]


# --- Channel config persistence ---
def load_channels():
    if CHANNELS_FILE.exists():
        with open(CHANNELS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_channels(channels):
    with open(CHANNELS_FILE, "w") as f:
        json.dump(channels, f, indent=2)


# Per-channel session state: { channel_id: { last_track, thread_ts, last_activity, last_reply } }
sessions = {}


# --- Slash Command ---
@app.command("/flastsm-setup")
def handle_flastsm_setup(ack, respond, command, client):
    ack()

    channel_id = command["channel_id"]
    user_id = command["user_id"]
    text = command.get("text", "").strip()

    # Check if the user is a channel manager (creator) or workspace admin/owner
    try:
        channel_info = client.conversations_info(channel=channel_id)["channel"]
        user_info = client.users_info(user=user_id)["user"]
        is_channel_creator = channel_info.get("creator") == user_id
        is_admin = user_info.get("is_admin", False) or user_info.get("is_owner", False)
        if not is_channel_creator and not is_admin:
            respond("You must be a channel manager or workspace admin to set up flastsm in this channel.")
            return
    except Exception as e:
        respond(f"Failed to verify permissions: {e}")
        return

    if not text:
        respond("Usage: `/flastsm-setup <lastfm_username>` — sets up Last.fm tracking for you in this channel.")
        return

    lastfm_user = text.split()[0]

    channels = load_channels()
    channels[channel_id] = {
        "lastfm_user": lastfm_user,
        "slack_uid": user_id,
    }
    save_channels(channels)

    respond(
        response_type="in_channel",
        text=f":ultrafastcatppuccinparrot: Last.fm tracking set up! Now watching *{lastfm_user}*'s scrobbles in this channel for <@{user_id}>.",
    )


# --- Polling Loop ---
def poll_lastfm():
    from slack_sdk import WebClient

    slack = WebClient(token=SLACK_TOKEN)

    while True:
        channels = load_channels()
        for channel_id, config in channels.items():
            try:
                lastfm_user = config["lastfm_user"]
                slack_uid = config["slack_uid"]

                response = requests.get(
                    "http://ws.audioscrobbler.com/2.0/",
                    params={
                        "method": "user.getrecenttracks",
                        "user": lastfm_user,
                        "api_key": LASTFM_API_KEY,
                        "format": "json",
                        "limit": 1,
                    },
                ).json()

                track = response["recenttracks"]["track"][0]
                now_playing = track.get("@attr", {}).get("nowplaying") == "true"
                current_time = time.time()

                # Initialize session state for this channel if needed
                if channel_id not in sessions:
                    sessions[channel_id] = {
                        "last_track": None,
                        "thread_ts": None,
                        "last_activity": 0,
                        "last_reply": "",
                    }

                session = sessions[channel_id]

                # Reset session if timeout reached
                if session["thread_ts"] and (current_time - session["last_activity"]) > SESSION_TIMEOUT:
                    session["thread_ts"] = None
                    session["last_track"] = None
                    session["last_activity"] = 0

                if now_playing and track["name"] != session["last_track"]:
                    session["last_track"] = track["name"]
                    session["last_activity"] = current_time

                    # If no thread exists, start a new session
                    if session["thread_ts"] is None:
                        resp = slack.chat_postMessage(
                            channel=channel_id,
                            text=f"<@{slack_uid}> started a listening session",
                        )
                        session["thread_ts"] = resp["ts"]

                    # Get album art url
                    images = track.get("image", [])
                    album_art_url = next(
                        (img["#text"] for img in reversed(images) if img.get("#text")),
                        None,
                    )

                    if track["name"].strip().lower() == "buddy holly":
                        slack.chat_postMessage(
                            channel=channel_id,
                            reply_broadcast=True,
                            thread_ts=session["thread_ts"],
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
                    elif track["name"].strip().lower() == "overcompensate":
                        slack.chat_postMessage(
                            channel=channel_id,
                            reply_broadcast=True,
                            thread_ts=session["thread_ts"],
                            text=f"{track['name']} by {track['artist']['#text']}",
                            blocks=[
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"<@{slack_uid}> is overcompensating hard with *Overcompensate* by *Twenty One Pilots*... I am so mature. :sunglasses:",
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
                            unformatted_reply = choice(custom_messages)
                            if unformatted_reply != session["last_reply"]:
                                session["last_reply"] = unformatted_reply
                                break
                        reply = unformatted_reply.format(
                            ping=f"<@{slack_uid}>",
                            song=track["name"],
                            artist=track["artist"]["#text"],
                        )
                        slack.chat_postMessage(
                            channel=channel_id,
                            thread_ts=session["thread_ts"],
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
                print(f"Error polling {channel_id}: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    # Start polling in a background thread
    poller = threading.Thread(target=poll_lastfm, daemon=True)
    poller.start()

    # Start Socket Mode handler (no public URL needed)
    print("flastsm running via Socket Mode...")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
