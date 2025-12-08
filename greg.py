from os import getenv
import random

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from tomnook import QUOTES

# SET UP TOKENS AND CONSTANTS
load_dotenv()

SLACK_TOKEN = getenv("SLACK_TOKEN")
APP_TOKEN = getenv("APP_TOKEN")

ALLOWED_CHANNELS = ["C0A1XK69529"]

app = App(token=SLACK_TOKEN)


def process_message(body, say):
    channel = body["event"]["channel"]
    if channel in ALLOWED_CHANNELS:
        event_ts = body["event"]["ts"]
        text = body["event"]["text"]
        print(text)

        # get_sarcastic_reply(text)
        say(text="Replying to ping in an authed channel", thread_ts=event_ts)
    else:
        print("Someone pinged bot in", channel)


@app.command("/acnhquote")
def acnh_quote(ack, body, client, logger):
    ack()

    channel_id = body["channel_id"]  # The channel the command was typed in
    user_id = body["user_id"]

    client.chat_postMessage(
        channel=channel_id, text=f"Hey <@{user_id}>! Here's your Animal Crossing quote! \n*{random.choice(QUOTES)}*"
    )


@app.message("assistdev")
@app.message("grdev")
@app.event("app_mention")
def on_pinged(ack, body, say):
    ack()
    process_message(body, say)


@app.event("message")
def this_stops_a_bunch_of_debug_logs():
    pass


if __name__ == "__main__":
    SocketModeHandler(app, APP_TOKEN).start()
