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


@app.event("app_mention")
def on_pinged(ack, body, say):
    ack()
    channel = body["event"]["channel"]
    if channel in ALLOWED_CHANNELS:
        say("The channel is set as allowed - i am scared")
    else:
        print("Someone pinged bot in", channel)


if __name__ == "__main__":
    SocketModeHandler(app, APP_TOKEN).start()
