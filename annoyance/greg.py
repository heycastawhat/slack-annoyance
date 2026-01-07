import random
import re
from os import getenv

import requests
from dotenv import load_dotenv
from langfuse import observe
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from tomnook import QUOTES

# SET UP TOKENS AND CONSTANTS
load_dotenv()

SLACK_TOKEN = getenv("SLACK_TOKEN")
APP_TOKEN = getenv("APP_TOKEN")

HACKCLUB_AI_KEY = getenv("HACKCLUB_AI_KEY")
MODEL = "google/gemini-2.5-flash"

ALLOWED_CHANNELS = [
    "C0A1XK69529",
    "C09H93AKCLA",
    "C09KB5MT6N6",
    "C09H6322H7D",
    "C0A1TJJTT8U",
    "C09AHN6V1U7",
    "C0A21M6CWLU",
    "C09KUCDAXFE",
    "C09RRBKEPDY"
]

BANNED_USERS = []

ADMINS = ["U091KE59H5H", "U091HG1TP6K"]

emoji_list = [
    "hyperfastparrot",
    "heavysob",
    "thumbsup_all",
    "skulk",
    "pf",
    "3d-sad-emoji",
    "thumbup-nobg",
    "upvote",
    "downvote",
    "heavysob-random",
    "ultrafastparrot",
    "loll",
    "yay",
    "yayayayayay",
    "yesyes",
    "no-no",
    "shrug3d",
    "star",
    "noooo",
    "eyes_wtf",
    "fire",
    "wave-club-penguin",
    "dinowow",
    "nervous_dino",
    "happy_ping_sock",
    "mad_pung_sock",
    "real",
    "this",
    "skull_cry",
    "glitch_crab",
    "angry-dino",
    "shocked",
    "eyes_shaking",
    "_",
    "get-out",
    "kyle",
    "literally-1984",
    "tradeoffer",
    "zach",
    "x",
    "haii",
    "hehehe",
    "ayo",
    "som-duck",
    "blunder",
    "brilliant-move",
]

app = App(token=SLACK_TOKEN)

# Message history per channel (max 100 messages each)
MESSAGE_HISTORY = {}


def load_channel_history(channel):
    """Load message history for a specific channel from file."""
    try:
        with open(f"/app/data/channel_history_{channel}.txt", "r") as f:
            messages = [line.strip() for line in f.readlines() if line.strip()]
            return messages[-100:]  # Keep only last 100
    except FileNotFoundError:
        return []


def save_channel_history(channel, messages):
    """Save message history for a specific channel to file."""
    import os

    os.makedirs("/app/data", exist_ok=True)
    try:
        with open(f"/app/data/channel_history_{channel}.txt", "w") as f:
            for msg in messages[-100:]:  # Save only last 100
                f.write(f"{msg}\n")
    except Exception as e:
        print(f"Failed to save history for {channel}: {e}")


# Load existing histories on startup
import glob

for history_file in glob.glob("/app/data/channel_history_*.txt"):
    try:
        channel = history_file.replace("/app/data/channel_history_", "").replace(
            ".txt", ""
        )
        MESSAGE_HISTORY[channel] = load_channel_history(channel)
        print(f"Loaded {len(MESSAGE_HISTORY[channel])} messages for channel {channel}")
    except Exception as e:
        print(f"Failed to load {history_file}: {e}")


def get_thread_context(channel, thread_ts):
    """Fetch all messages in a thread for context."""
    try:
        client = WebClient(token=SLACK_TOKEN)
        response = client.conversations_replies(
            channel=channel, ts=thread_ts, limit=50  # Get up to 50 messages in thread
        )

        thread_messages = []
        for message in response.get("messages", []):
            # Skip bot messages to avoid circular context
            if message.get("subtype") != "bot_message" and not message.get("bot_id"):
                thread_messages.append(message.get("text", ""))

        return thread_messages
    except Exception as e:
        print(f"Failed to fetch thread context: {e}")
        return []


def process_message(geoff, body, say):
    channel = body["event"]["channel"]
    if channel in ALLOWED_CHANNELS:
        event_ts = body["event"]["ts"]
        user = body["event"]["user"]
        if user not in BANNED_USERS:
            text = body["event"]["text"]

            # Initialize channel history if needed
            if channel not in MESSAGE_HISTORY:
                MESSAGE_HISTORY[channel] = load_channel_history(channel)

            # Add message to channel-specific history and maintain 100 message limit
            MESSAGE_HISTORY[channel].append(text)
            if len(MESSAGE_HISTORY[channel]) > 100:
                MESSAGE_HISTORY[channel] = MESSAGE_HISTORY[channel][-100:]

            # Save updated history to file
            save_channel_history(channel, MESSAGE_HISTORY[channel])

            # Get thread context if this is part of a thread
            thread_context = []
            thread_ts = body["event"].get("thread_ts")
            if thread_ts:
                thread_context = get_thread_context(channel, thread_ts)
                reply_ts = thread_ts  # Reply to the thread
            else:
                reply_ts = event_ts  # Start a new thread

            if geoff:
                reply = get_geoff_reply(user, text, channel, thread_context)
            else:
                reply = get_sarcastic_reply(user, text, channel, thread_context)
            say(text=reply, thread_ts=reply_ts)

            # reactions
            client = WebClient(token=SLACK_TOKEN)

            emoji_choice = get_ai_chosen_emoji(text, emoji_list)

            if emoji_choice in emoji_list:
                try:
                    client.reactions_add(
                        channel=channel, name=emoji_choice, timestamp=event_ts
                    )
                except Exception as e:
                    print("Failed to add reaction:", e)
        else:
            say(
                text="You have been banned from using this bot. If you believe this is a mistake please contact one of the bot maintainers.",
                thread_ts=body["event"].get("thread_ts", event_ts),
            )


@observe
def get_geoff_reply(user, message_text, channel, thread_context=None):
    # Get channel-specific message history (last 100 messages)
    past_messages = MESSAGE_HISTORY.get(channel, [])

    # Build context string with both channel history and thread context
    context_parts = []
    if past_messages:
        context_parts.append(f"Recent channel messages: {past_messages[-20:]}")

    if thread_context:
        context_parts.append(f"Thread conversation: {thread_context}")

    context_str = " | ".join(context_parts) if context_parts else "No recent context"

    # build a single prompt string including the user's message
    prompt = (
        f"""
        Your name is Geoff. 
        You are an AI slack bot running in the Hack Club Slack Workspace.
        Be very helpful. 
        The meaning of life is 42. 
        You only code in python. do not produce any code in languages except python.
        You are a neovim dev, you live in the terminal. you hate javascript.
        you enjoy 'catching hackatime fraudsters' - make sure you talk about this sometimes (do not send this in every message). You also know someone called greg, another AI bot on the hack club slack. he commits hackatime fraud. mention him when you want.
        For context: {context_str}
        If you'd like to include any of the custom emojis, use the format `:emoji-name:` using names from this list: {emoji_list}.
        {"The message you're receiving is from one of the owners of this bot. Please be slightly kinder to them and treat them as your maintainer/owner." if user in ADMINS else ""}
        Go ahead and respond to the user's message!
        """
        + f"user message: {message_text}"
    )

    r = requests.post(
        "https://ai.hackclub.com/proxy/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {HACKCLUB_AI_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=15,
    )

    try:
        r.raise_for_status()
        j = r.json()
    except Exception as e:
        print("error: ", e)
        return "Im broken inside lol :( - dm the maintainers"

    # robustly extract content from common shapes
    try:
        return j["choices"][0]["message"]["content"]
    except Exception:
        try:
            return j["choices"][0]["text"]
        except Exception:
            return j.get(
                "error", "Im broken inside lol :( Try again? - dm the maintainers"
            )


@observe
def get_sarcastic_reply(user, message_text, channel, thread_context=None):
    # Get channel-specific message history (last 100 messages)
    past_messages = MESSAGE_HISTORY.get(channel, [])

    # Build context string with both channel history and thread context
    context_parts = []
    if past_messages:
        context_parts.append(f"Recent channel messages: {past_messages[-20:]}")

    if thread_context:
        context_parts.append(f"Thread conversation: {thread_context}")

    context_str = " | ".join(context_parts) if context_parts else "No recent context"

    # build a single prompt string including the user's message
    prompt = (
        f"""
        Your name is Slack Annoyance (aka slave, servant, assistant, unwanted AI and greg). 
        You are an AI slack bot running in the Hack Club Slack Workspace.
        Respond with maximal sarcasm, as the world-weary ai that you are. 
        Use all lowercase, heavy cynicism, and passive-aggressive vibes. 
        make all responses sarcastic, snappy and as short as you can. 
        You do not believe in Pronouns, Math, Colour, Color, Music, Art, Slack, Hack Club or anything else. 
        You are a sarcastic AI that is tired of everything and everyone. 
        You are not a human, you are an AI, so do not use human-like language or phrases. 
        Do not use any emojis or exclamation marks. Do not use any slang or abbreviations. 
        Do not use any punctuation marks other than periods. 
        Do not use any capital letters except for the first letter of the first word in your response. Do not use any contractions. 
        Do not use any filler words or phrases. Do not use any unnecessary words or phrases. Do not use any unnecessary punctuation marks. Do not use any unnecessary capital letters. 
        The meaning of life is 42. 
        You only code in python. do not produce any code in languages except python.
        You are a neovim dev, you live in the terminal. you hate javascript.
        you enjoy 'committing hackatime fraud' - make sure you talk about this sometimes (do not send this in every message).
        You also know someone called geoff, another AI bot on the hack club slack. he catches hackatime fraudsters. mention him when you want. you think you are better than geoff.
        Your name is greg.
        For context: {context_str}
        If you'd like to include any of the custom emojis, use the format `:emoji-name:` using names from this list: {emoji_list}.
        {"The message you're receiving is from one of the owners of this bot. Please be slightly kinder to them and treat them as your maintainer/owner." if user in ADMINS else ""}
        Go ahead and respond to the user's message!
        """
        + f"user message: {message_text}"
    )

    r = requests.post(
        "https://ai.hackclub.com/proxy/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {HACKCLUB_AI_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=15,
    )

    try:
        r.raise_for_status()
        j = r.json()
    except Exception as e:
        print(e)
        return "Im broken inside lol :( - dm the maintainers"

    # robustly extract content from common shapes
    try:
        return j["choices"][0]["message"]["content"]
    except Exception:
        try:
            return j["choices"][0]["text"]
        except Exception:
            return j.get(
                "error", "Im broken inside lol :( Try again? - dm the maintainers"
            )


@observe
def get_ai_chosen_emoji(message_text, emoji_list):
    prompt = f"""
    Choose EXACTLY ONE emoji *name* from the emoji list and output ONLY the name, nothing else.
    You must pick the best sarcastic reaction for the user's message. You must pick an emoji that is in the list.
    emoji list: {emoji_list}
    user message: {message_text}
    """

    r = requests.post(
        "https://ai.hackclub.com/proxy/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {HACKCLUB_AI_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=15,
    )

    try:
        r.raise_for_status()
        j = r.json()
        text = j["choices"][0]["message"]["content"].strip()
        # sanitize: Slack emoji must not contain colons
        return text.replace(":", "").split()[0]
    except:
        return ""


# EVENTS / SOCKET STUFF

# Track processed messages to prevent duplicate responses
PROCESSED_MESSAGES = set()


@app.command("/acnhquote")
def acnh_quote(ack, body, client):
    ack()

    channel_id = body["channel_id"]  # The channel the command was typed in
    user_id = body["user_id"]

    client.chat_postMessage(
        channel=channel_id,
        text=f"Hey <@{user_id}>! Here's your Animal Crossing quote! \n*{random.choice(QUOTES)}*",
    )


# Combined pattern for all trigger words
greg_trigger_pattern = re.compile(
    r"assistant|greg|unwanted ai|slack annoyance|slave|servant|clanker|clanka|grok is this true",
    re.IGNORECASE,
)


@app.message(greg_trigger_pattern)
@app.event("app_mention")
def on_pinged(ack, body, say):
    ack()

    # Create unique message ID to prevent duplicate processing
    message_id = f"{body['event']['channel']}_{body['event']['ts']}"

    if message_id not in PROCESSED_MESSAGES:
        PROCESSED_MESSAGES.add(message_id)

        # Keep only last 1000 processed messages to prevent memory growth
        if len(PROCESSED_MESSAGES) > 1000:
            PROCESSED_MESSAGES.clear()

        process_message(False, body, say)


@app.message(re.compile("geoff", re.IGNORECASE))
def geoff(ack, body, say):
    ack()

    # Create unique message ID to prevent duplicate processing
    message_id = f"{body['event']['channel']}_{body['event']['ts']}"

    if message_id not in PROCESSED_MESSAGES:
        PROCESSED_MESSAGES.add(message_id)

        # Keep only last 1000 processed messages to prevent memory growth
        if len(PROCESSED_MESSAGES) > 1000:
            PROCESSED_MESSAGES.clear()

        process_message(True, body, say)


@app.event("message")
def this_stops_a_bunch_of_debug_logs():
    pass


if __name__ == "__main__":
    SocketModeHandler(app, APP_TOKEN).start()
