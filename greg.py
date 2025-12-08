from os import getenv

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# SET UP TOKENS AND CONSTANTS
load_dotenv()

SLACK_TOKEN = getenv("SLACK_TOKEN")
APP_TOKEN = getenv("APP_TOKEN")

ALLOWED_CHANNELS = ["C0A1XK69529"]

app = App(token=SLACK_TOKEN)

def process_message(body, say):
    channel = body["event"]["channel"]
    event_ts = body["event"]["ts"]
    if channel in ALLOWED_CHANNELS:
        say(text="Replying to ping in an authed channel", thread_ts=event_ts)
    else:
        print("Someone pinged bot in", channel)


@app.event("app_mention")
def on_pinged(ack, body, say):
    ack()
    process_message(body, say)

@app.message("assistdev")
def on_pingword(body, say):
    process_message(body, say)


if __name__ == "__main__":
    SocketModeHandler(app, APP_TOKEN).start()
