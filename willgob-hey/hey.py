from os import getenv

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# setup env variables
load_dotenv()
SLACK_TOKEN = getenv("SLACK_TOKEN")
APP_TOKEN = getenv("APP_TOKEN")

# main setup
MY_CHANNEL = "C09RRBKEPDY"
app = App(token=SLACK_TOKEN)


@app.event("member_joined_channel")
def joined_channel(event, say):
    if event["channel"] == MY_CHANNEL:
        say(
            f"Hi<@{event['user']}>. Welcome to <@U09C832RGJW>'s pothole. <@U09C832RGJW>, get over here and say hello."
        )


if __name__ == "__main__":
    SocketModeHandler(app=app, app_token=APP_TOKEN).start()
