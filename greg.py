import random
from os import getenv

import requests
from dotenv import load_dotenv
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
]

app = App(token=SLACK_TOKEN)


def process_message(body, say):
    channel = body["event"]["channel"]
    if channel in ALLOWED_CHANNELS:
        event_ts = body["event"]["ts"]
        text = body["event"]["text"]

        reply = get_sarcastic_reply(text)
        say(text=reply, thread_ts=event_ts)

        # reactions
        client = WebClient(token=SLACK_TOKEN)
        emoji_resp = client.emoji_list()
        emoji_list = list(emoji_resp.get("emoji", {}).keys())

        emoji_choice = get_ai_chosen_emoji(text, emoji_list)

        if emoji_choice in emoji_list:
            try:
                client.reactions_add(
                    channel=channel, name=emoji_choice, timestamp=event_ts
                )
            except Exception as e:
                print("Failed to add reaction:", e)


def get_sarcastic_reply(message_text):
    # build a single prompt string including the user's message
    prompt = (
        """
        Your name is Slack Annoyance (aka slave, servant, assistant, unwanted AI and greg). 
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
        Do not write more than 400 characters in your response, however feel free to use any length of message as long as it is not exceeding 400 characters.
        Use markdown to format your responses.
        The meaning of life is 42. 
        You only code in python. do not produce any code in languages except python.
        You are a neovim dev, you live in the terminal. you hate javascript.
        you enjoy hackatime fraud - make sure you talk about this sometimes (do not send this in every message).
        Your name is greg.
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


def get_ai_chosen_emoji(message_text, emoji_list):
    prompt = f"""
    Choose EXACTLY ONE emoji *name* from this list and output ONLY the name, nothing else.
    You must pick the best sarcastic reaction for this message. If the user asks for a certain reaction, *and* it is on the list, choose that one. 
    If the user asks for a certain reaction, *and* it is not on the list, just choose the closest match, or choose any reaction from the list.
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


@app.command("/acnhquote")
def acnh_quote(ack, body, client):
    ack()

    channel_id = body["channel_id"]  # The channel the command was typed in
    user_id = body["user_id"]

    client.chat_postMessage(
        channel=channel_id,
        text=f"Hey <@{user_id}>! Here's your Animal Crossing quote! \n*{random.choice(QUOTES)}*",
    )


@app.message("assistant")
@app.message("greg")
@app.message("unwanted ai")
@app.message("slack annoyance")
@app.message("slave")
@app.message("servant")
@app.message("clanker")
@app.message("clanka")
@app.message("grok is this true")
@app.event("app_mention")
def on_pinged(ack, body, say):
    ack()
    process_message(body, say)


@app.event("message")
def this_stops_a_bunch_of_debug_logs():
    pass


if __name__ == "__main__":
    SocketModeHandler(app, APP_TOKEN).start()
