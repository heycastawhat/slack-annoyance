import argparse
import os
import random
from slack_sdk import WebClient

# optionally load environment variables from a .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

# --- CONFIG ---
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")

SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

# only respond in these channels
ALLOWED_CHANNELS = [
    "C09H93AKCLA",
    "C09H6322H7D",
    "C09KB5MT6N6",
    "C0A1TJJTT8U",
    "C09AHN6V1U7",
    "C0A21M6CWLU",
    "C0A1XK69529",
    "C09KUCDAXFE",
]

print("Hit continue on line 15, slack token and channels loaded")

QUOTES = [
    "\"Meanwhile, I'll Investigate These Orange-Like Items Growing In The Trees. I Suspect They're Real Oranges!\" - Tom Nook",
    '"Have You Ever Used A Smart Phone Before?" - Tom Nook',
    '"But We Don\'t Do Things Because They Are Easy Hm? We Do Them Because They Are Profitable." - Tom Nook',
    '"Whoa, whoa...WHOA!" - Tom Nook',
    "\"I’m so sad I feel like my superhero name should be 'Sad-Man'.\" - Papi",
    '"I don’t know if I told you this, but I’m allergic to bad vibes!" - Pietro',
    '"Sorry. I Just Got Nervous Thinking About You Out There… Digging… And What You Might Find…" - Rosie',
    '"I Thought Real Hard On It, But I Could Only Think Of Stuff I Want! I Hope He Likes Apple Cobbler." - Sherb',
    '"I’m Going To Try Using My Muscles To Scare Away The Germs, Mango." - Rowan',
    '"I Had To Work Once. It Was The Worst!" - Papi',
    '"Hmmm… There Really Isn’t Any News To Speak Of Today." - Isabelle',
    '"I caught an anchovy! Stay away from my pizza!" - Player',
    '"I caught an ant! TELL ME WHERE THE QUEEN IS!" - Player',
    "\"I caught an arowana! I'd make a joke, but I don't 'wana.\" - Player",
    '"I caught a betta! I betta not drop it!" - Player',
    '"I caught a boot! It, uh, wasn\'t made for swimming." - Player',
    '"I caught a carp! If I catch another they can carpool!" - Player',
    '"I caught a centipede! 99 more and I\'ll have a dollarpede!" - Player',
    '"I caught a clown fish! How many can fit in a carfish?" - Player',
    '"I caught a drone beetle! Shouldn\'t you have more propellers?" - Player',
    '"I caught a dung beetle! This species likes feces!" - Player',
    '"I caught a flea! The curse is lifted." - Player',
    '"I caught a fly! I was just wingin\' it..." - Player',
]
print("Hit continue on line 43, quote chosen")


def get_random_quote() -> str:
    return random.choice(QUOTES) if QUOTES else ""


def post_random_quote(channel_id: str = "C0A1XK69529") -> str:
    if not SLACK_TOKEN:
        raise RuntimeError("SLACK_TOKEN not set in environment")
    client = WebClient(token=SLACK_TOKEN)
    text = get_random_quote()
    client.chat_postMessage(channel=channel_id, text=text)
    return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tom Nook quote helper")
    parser.add_argument(
        "--post", action="store_true", help="Post one random quote to Slack channel"
    )
    parser.add_argument(
        "--channel", default="C0A1XK69529", help="Slack channel ID to post to"
    )
    args = parser.parse_args()

    if args.post:
        try:
            posted = post_random_quote(channel_id=args.channel)
            print(f"Posted: {posted}")
        except RuntimeError as e:
            print(f"Error: {e}")
            raise SystemExit(1)
    else:
        print(get_random_quote())
