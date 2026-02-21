import re
from os import getenv

import requests
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

SLACK_TOKEN = getenv("SLACK_TOKEN")
APP_TOKEN = getenv("APP_TOKEN")
HACKCLUB_AI_KEY = getenv("HACKCLUB_AI_KEY")
MODEL = "google/gemini-2.5-flash"

ALLOWED_CHANNELS = ["C0AH570N9U0"]

ADMINS = ["U091KE59H5H", "U091HG1TP6K"]

app = App(token=SLACK_TOKEN)

PROCESSED_MESSAGES = set()


def get_slack_id_breakdown(user_id, slack_id):
    """Use AI to generate a greg-style sarcastic breakdown of every character in a Slack ID."""
    prompt = f"""
    Your name is greg. You are a sarcastic, world-weary AI slack bot.
    Use all lowercase, heavy cynicism, and passive-aggressive vibes.
    You only care about one thing: telling people their slack id is you (greg).

    A user just asked for their slack id. Their slack id is: {slack_id}

    Your job: take EVERY character (or small group of characters) in the slack id and make a
    sarcastic, greg-themed interpretation of it. Each line should tie back to the
    fact that their slack id is basically just greg in disguise.

    Format it like this (one line per character or character group):
    *{slack_id}*
    e.g. if the slack id was `U091KE59H5H`, you might say:
    `U` - ur slack id is me
    `09` - the amount of times i have to tell you your slack id is me
    `1` - the number of people who have cooler slack ids than you (0)
    `KE` - sounds like "kay", which is what you'll be saying when i tell you your slack id is me
    `59` - the number of seconds it takes for you to realize your slack id is me
    `H` - the first letter of "hello greg", which is what you should be saying to me when i tell you your slack id is me
    `5` - the number of times you have to read this breakdown to understand your slack id is me
    `H` - the first letter of "hi greg", which is what you should be saying to me when i tell you your slack id is me

    End with a punchline about how their entire slack id spells greg if you squint hard enough.

    Rules:
    - be as sarcastic and unhinged as possible
    - all lowercase
    - no emojis or exclamation marks
    - every line must somehow reference greg or the fact that the slack id belongs to greg
    - keep it snappy. do not write essays.
    - use periods only for punctuation
    - the breakdown must cover the ENTIRE slack id, do not skip any characters
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
        return j["choices"][0]["message"]["content"]
    except Exception:
        try:
            return j["choices"][0]["text"]
        except Exception:
            return f"your slack id is `{slack_id}`. it is also greg. everything is greg."


@app.event("message")
def on_any_message(event, say):
    channel = event.get("channel")
    if channel not in ALLOWED_CHANNELS:
        return

    if event.get("bot_id") or event.get("subtype"):
        return

    message_id = f"{channel}_{event['ts']}"
    if message_id in PROCESSED_MESSAGES:
        return

    PROCESSED_MESSAGES.add(message_id)
    if len(PROCESSED_MESSAGES) > 1000:
        PROCESSED_MESSAGES.clear()

    user_id = event.get("user")
    if not user_id:
        return

    thread_ts = event.get("thread_ts", event["ts"])

    breakdown = get_slack_id_breakdown(user_id, user_id)
    say(text=breakdown, thread_ts=thread_ts)



if __name__ == "__main__":
    SocketModeHandler(app, APP_TOKEN).start()
