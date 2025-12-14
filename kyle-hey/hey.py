from os import getenv

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# setup env variables
load_dotenv()
SLACK_TOKEN = getenv("SLACK_TOKEN")
APP_TOKEN = getenv("APP_TOKEN")

# main setup
MY_CHANNEL = "C09KB5MT6N6"
app = App(token=SLACK_TOKEN)


@app.event("member_joined_channel")
def joined_channel(event, say):
    if event["channel"] == MY_CHANNEL:
        say(
            f"Hey there, <@{event["user"]}>! Welcome to <@U091HG1TP6K>'s channel! (This bot automatically added you to my ping group! :yay:) Kyle come say hi soon :yay: (unless he's asleep :loll:)"
        )

        # add the joining user to the ping usergroup if not already a member
        try:
            UG_ID = "S09P5N455FS"
            user_id = event.get("user")
            if user_id:
                # fetch current members of the usergroup
                resp = app.client.usergroups_users_list(usergroup=UG_ID)
                if resp.get("ok"):
                    members = resp.get("users", []) or []
                else:
                    members = []

                if user_id not in members:
                    members.append(user_id)
                    # update the usergroup membership (comma-separated user IDs)
                    upd = app.client.usergroups_users_update(
                        usergroup=UG_ID, users=",".join(members)
                    )
                    if not upd.get("ok"):
                        print("Failed to update usergroup:", upd)
        except Exception as e:
            print("Error adding user to usergroup:", e)


if __name__ == "__main__":
    SocketModeHandler(app=app, app_token=APP_TOKEN).start()
