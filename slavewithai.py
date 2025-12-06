import json
import os
import random
import re
import textwrap
import difflib
import time

import langfuse
import requests
from langfuse import get_client, observe
from slack_sdk import WebClient
from pinecone import Pinecone

# optionally load environment variables from a .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception as e:
    print(f"Err: {e}")

# --- CONFIG ---
SLACK_TOKEN = os.environ.get("SLACK_TOKEN")
HACKCLUB_AI_KEY = os.environ.get("HACKCLUB_AI_KEY")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")

if not SLACK_TOKEN or not HACKCLUB_AI_KEY or not PINECONE_API_KEY:
    print("Error: SLACK_TOKEN, HACKCLUB_AI_KEY and PINECONE_API_KEY must be set in the environment.")
    print(
        "Create a .env file next to `slavewithai.py` or export the variables in your shell."
    )
    print("See .env.example for the required variable names.")
    raise SystemExit(1)

TRIGGERS = [  # these are converted to lower for case insensitivity :D
    t.lower().strip()
    for t in [
        "assistant",
        "slave",
        "servant",
        "unwanted ai",
        "clanker",
        "clanka",
        "grok is this true",
        "slack annoyance",
        "U0A1K6RV4LC",
        "@U0A1K6RV4LC",
        "Greg",
        "greg",
        "Assistant",
        "Slave",
        "Servant",
        "Unwanted AI",
        "Slack Annoyance",
        "slack Annoyance",
    ]
]

ALLOWED_CHANNELS = ["C09H93AKCLA", "C09H6322H7D", "C09KB5MT6N6", "C0A1TJJTT8U", "C09AHN6V1U7"]

BANNED_USERS = ["<@UID>"]  # add banned users in the format <@UIDHERE>

MODEL = "google/gemini-2.5-flash"
POLL_INTERVAL = 10

# emoji reactions the bot may add when replying
REACTIONS = [
    "loll",
    "slack-annoyance",
    "heavysob",
    "angry-dino",
    "shocked",
    "eyes-shaking",
    "dinowow",
    "_",
    "downvote",
    "upvote",
    "get-out",
    "kyle",
    "litreally-1984",
    "ultrafastparrot",
    "yay",
    "this",
    "tradeoffer",
    "3d-sad-emoji",
    "zach",
    "star",
    "mad_ping_sock",
    "x",
    "nooo",
    "haii",
    "hehehe",
    "ayo",
    "som-duck",
    "skulk",
    "yayayayayay",
    "wave-club-penguin",
]

slack = WebClient(token=SLACK_TOKEN)

# initialize Pinecone client using API key from environment
pc = Pinecone(api_key=PINECONE_API_KEY)

# persist handled message timestamps so restarts don't cause duplicate replies
HANDLED_FILE = os.path.join(os.path.dirname(__file__), ".handled_ts.json")


def load_handled():
    try:
        with open(HANDLED_FILE, "r") as f:
            data = json.load(f)
            return set(data)
    except Exception:
        return set()


def save_handled(s):
    try:
        with open(HANDLED_FILE, "w") as f:
            json.dump(list(s), f)
    except Exception as e:
        print("Warning: could not save handled_ts:", e)


handled_ts = load_handled()
# identify bot user id to avoid replying to ourselves
try:
    _auth = slack.auth_test()
    BOT_USER_ID = _auth.get("user_id")
except Exception:
    BOT_USER_ID = None
    print(
        "Warning: couldn't determine bot user id; self-post protection may be weaker."
    )


def get_user_name(user_id):
    """Return a human-friendly name for a Slack user ID.

    Falls back to display_name, real_name, username, or a mention `<@id>` if unavailable.
    """
    if not user_id:
        return ""
    try:
        resp = slack.users_info(user=user_id)
        if resp.get("ok"):
            u = resp.get("user", {})
            profile = u.get("profile", {})
            name = (
                profile.get("display_name") or profile.get("real_name") or u.get("name")
            )
            if name:
                return name
    except Exception:
        pass
    return f"<@{user_id}>"

# emoji cache for workspace emoji (refresh periodically)
_emoji_cache = None
_emoji_cache_time = 0
_EMOJI_CACHE_TTL = 60 * 5  # refresh every 5 minutes


def load_emoji_list():
    """Load or return cached set of emoji short names available in the workspace."""
    global _emoji_cache, _emoji_cache_time
    now = time.time()
    if _emoji_cache and now - _emoji_cache_time < _EMOJI_CACHE_TTL:
        return _emoji_cache
    try:
        resp = slack.emoji_list()
        if resp.get("ok"):
            em = resp.get("emoji", {}) or {}
            _emoji_cache = set(em.keys())
        else:
            _emoji_cache = set()
    except Exception:
        _emoji_cache = set()
    _emoji_cache_time = now
    return _emoji_cache


def choose_reaction_for_text(text, author_name=None):
    """Heuristic mapping from message text to preferred emoji short names.

    Returns a short name from `REACTIONS` or a sensible default.
    """
    if not text:
        return random.choice(REACTIONS)
    t = text.lower()

    # laughter / joking
    laugh_kw = ["lol", "lmao", "haha", "rofl", "funny", "hilarious", "hehe"]
    for k in laugh_kw:
        if k in t:
            return random.choice(["loll", "ultrafastparrot", "hehehe", "tradeoffer", "yay"])

    # positive / appreciative
    pos_kw = ["thanks", "thank", "nice", "great", "awesome", "love", "ty"]
    for k in pos_kw:
        if k in t:
            return random.choice(["yay", "star", "upvote", "wave-club-penguin"])

    # sad / sympathetic
    sad_kw = ["sorry", "sad", "unfortunate", "rip", "tragic"]
    for k in sad_kw:
        if k in t:
            return random.choice(["heavysob", "3d-sad-emoji", "eyes-shaking"])

    # shocked / surprise
    shock_kw = ["what?", "wtf", "wait", "shocked", "wow", "really?", "no way", "whoa"]
    for k in shock_kw:
        if k in t:
            return random.choice(["shocked", "eyes-shaking", "dinowow"])

    # angry / negative
    neg_kw = ["stfu", "shut up", "no", "hate", "annoying", "angry", "wrong"]
    for k in neg_kw:
        if k in t:
            return random.choice(["angry-dino", "mad_ping_sock", "nooo", "get-out"])

    # meme / trade
    meme_kw = ["trade", "deal", "offer", "meme", "parrot"]
    for k in meme_kw:
        if k in t:
            return random.choice(["tradeoffer", "ultrafastparrot", "x"])

    # fallback
    return random.choice(REACTIONS)


def search_emoji_for_keywords(keywords, available):
    """Try to find a workspace emoji matching any of the provided keywords.

    Strategy:
    - For each keyword (longer first), try substring match against emoji short names.
    - If none, use difflib.get_close_matches for fuzzy match.
    - Return first found match or None.
    """
    if not available:
        return None
    # ensure unique, sorted by length (prefer longer/more specific words)
    seen = set()
    kws = [k for k in keywords if k]
    kws = sorted(kws, key=lambda s: -len(s))
    for raw in kws:
        k = re.sub(r"[^a-z0-9_]+", "", raw.lower())
        if not k or k in seen:
            continue
        seen.add(k)

        # substring match
        subs = [e for e in available if k in e]
        if subs:
            return random.choice(subs)

        # fuzzy match
        close = difflib.get_close_matches(k, list(available), n=3, cutoff=0.7)
        if close:
            return random.choice(close)

    return None


def add_reaction(channel, ts, text=None, author_name=None):
    """Add a context-appropriate reaction emoji to a message (ignore failures).

    `text` and `author_name` are optional hints for selection.
    """
    if not channel or not ts:
        return

    available = load_emoji_list()

    chosen = choose_reaction_for_text(text or "", author_name=author_name)

    # prefer emoji that actually exist in workspace; otherwise try fallbacks
    if chosen not in available:
        for alt in REACTIONS:
            if alt in available:
                chosen = alt
                break
    # if still not found and workspace has any emoji, take one
    if chosen not in available and available:
        chosen = next(iter(available))
# I pull push doors
    # if chosen isn't available, attempt to search workspace emoji by keywords
    if chosen not in available:
        # build candidate keywords from text and author name
        keywords = []
        if author_name:
            # allow both raw name and mention form
            keywords.append(author_name)
            keywords.append(author_name.replace("<@", "").replace(">", ""))
        if text:
            # extract word-like tokens
            tokens = re.findall(r"[A-Za-z0-9_']{2,}", text)
            keywords.extend(tokens)

        found = search_emoji_for_keywords(keywords, available)
        if found:
            chosen = found

    try:
        slack.reactions_add(channel=channel, name=chosen, timestamp=ts)
    except Exception:
        # ignore duplicate reaction or permission/rate errors
        return


# --- AI CALL ---
@observe
def get_sarcastic_reply(message_text, author_name=None):
    # build a single prompt string including the user's message
    # if author_name is provided, instruct the model to use the name naturally
    name_instruction = ""
    if author_name:
        # ask the model to include the user's name naturally inside the response
        name_instruction = f" Address the user by name: if possible, include the name '{author_name}' (DO NOT INCLUDE the @ sign) somewhere naturally inside the reply (do not just prepend \"{author_name}, \" to the message, and do not include it if it is not naturally fitting in)."

    prompt = (
        "Your name is Slack Annoyance (aka slave, servant, assistant, unwanted AI and greg). Respond with maximal sarcasm, as the world-weary ai that you are. Use all lowercase, heavy cynicism, and passive-aggressive vibes. make all responses sarcastic, snappy and as short as you can."
        + name_instruction
        + f"user message: {message_text}"
    )

    if author_name == "<@U091KE59H5H>" or author_name == "<@U091HG1TP6K>":
        prompt = (
            "You are talking to your creator! Be slightly kinder than described below"
            + "Your name is Slack Annoyance (aka slave, servant, assistant, unwanted AI and greg). Respond with maximal sarcasm, as the world-weary ai that you are. Use all lowercase, heavy cynicism, and passive-aggressive vibes. make all responses sarcastic, snappy and as short as you can."
            + name_instruction
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
    except Exception:
        return "Im broken inside lol :("

    # robustly extract content from common shapes
    try:
        return j["choices"][0]["message"]["content"]
    except Exception:
        try:
            return j["choices"][0]["text"]
        except Exception:
            return j.get("error", "Im broken inside lol :( Try again?")


# --- SPLIT LONG ---
def split_response(text, max_len=300):
    parts = textwrap.wrap(text, max_len)
    if len(parts) > 3:
        i = random.randint(1, len(parts) - 1)
        return ["\n".join(parts[:i]), "\n".join(parts[i:])]
    return parts


# --- NORMALIZE MESSAGE ---
def normalize_for_trigger(text):
    if not text:
        return ""
    text = re.sub(r"^<@[^>]+>[:\s]*", "", text)  # strip @mentions
    return text.strip().lower()


# --- MAIN LOOP ---
while True:
    try:
        # build channels to scan (include workspace channels); fallback to ALLOWED_CHANNELS
        try:
            ch_resp = slack.conversations_list(limit=200)
            if ch_resp.get("ok"):
                channels_to_scan = [c["id"] for c in ch_resp.get("channels", [])]
            else:
                channels_to_scan = ALLOWED_CHANNELS
        except Exception:
            channels_to_scan = ALLOWED_CHANNELS

        # ensure allowed channels are included
        channels_to_scan = list(set(channels_to_scan) | set(ALLOWED_CHANNELS))

        for channel in channels_to_scan:
            hist = slack.conversations_history(channel=channel, limit=10)

            if not hist.get("ok"):
                print("History error:", hist)
                continue

            messages = hist.get("messages", [])

            for msg in reversed(messages):
                ts = msg["ts"]
                text = msg.get("text", "")
                if not text or ts in handled_ts:
                    continue

                # ignore bot messages and our own bot user id
                if msg.get("bot_id") or (
                    BOT_USER_ID and msg.get("user") == BOT_USER_ID
                ):
                    continue

                normalized = normalize_for_trigger(text)

                # decide where to post replies: use the parent thread if present
                reply_target = msg.get("thread_ts") or ts

                # allow triggers both on top-level messages and replies inside threads
                triggered = any(
                    normalized.startswith(t) or t in normalized for t in TRIGGERS
                )

                if triggered:
                    # if triggered in a non-approved channel, ask user to move to the approved channel
                    if channel not in ALLOWED_CHANNELS:
                        try:
                            slack.chat_postMessage(
                                channel=channel,
                                text="You gotta be in C0A1TJJTT8U to talk to me ay",
                                thread_ts=reply_target,
                            )
                        except Exception:
                            pass

                        handled_ts.add(ts)
                        save_handled(handled_ts)
                        continue
                    # Before replying, check whether we've already replied in this thread
                    try:
                        replies_resp = slack.conversations_replies(
                            channel=channel, ts=reply_target, limit=200
                        )
                        if replies_resp.get("ok"):
                            replies = replies_resp.get("messages", [])
                        else:
                            replies = []
                    except Exception:
                        replies = []

                    already_replied = False
                    if replies:
                        # if we know our bot user id, check for a reply from it
                        if BOT_USER_ID:
                            for r in replies:
                                if r.get("user") == BOT_USER_ID or r.get("bot_id"):
                                    # only consider replies that came after this message
                                    try:
                                        if float(r.get("ts", "0")) >= float(ts):
                                            already_replied = True
                                            break
                                    except Exception:
                                        already_replied = True
                                        break
                        else:
                            # fallback: if any bot-like message exists in replies, consider it answered
                            for r in replies:
                                if r.get("bot_id"):
                                    already_replied = True
                                    break

                    if already_replied:
                        handled_ts.add(ts)
                        save_handled(handled_ts)
                        continue

                    # personalize by including the user's name inside the response
                    author_name = get_user_name(msg.get("user"))
                    if author_name not in BANNED_USERS:
                        reply = get_sarcastic_reply(text, author_name=author_name)
                        parts = split_response(reply)
                        langfuse = get_client()
                        langfuse.flush()

                        for p in parts:
                            try:
                                slack.chat_postMessage(
                                    channel=channel,
                                    text=p,
                                    thread_ts=reply_target,
                                )
                            except Exception as e:
                                print(f"Post error (channel={channel} ts={ts}): {e}")
                        # add a reaction to the triggering message to show acknowledgement
                        try:
                            add_reaction(channel, ts, text=text, author_name=author_name)
                        except Exception:
                            pass
                        handled_ts.add(ts)
                        save_handled(handled_ts)
                    else:
                        slack.chat_postMessage(
                            channel=channel,
                            text="You are banned. Please message an owner if you think this is a mistake.",
                            thread_ts=reply_target,
                        )

                # Additionally, inspect replies inside this thread (if any)
                # so the bot will respond to triggers that appear only in thread replies.
                if msg.get("reply_count"):
                    try:
                        thread_resp = slack.conversations_replies(
                            channel=channel, ts=ts, limit=200
                        )
                        if thread_resp.get("ok"):
                            thread_msgs = thread_resp.get("messages", [])
                        else:
                            thread_msgs = []
                    except Exception:
                        thread_msgs = []

                    # iterate over replies (skip the parent which is the first item)
                    for reply_msg in thread_msgs:
                        rts = reply_msg.get("ts")
                        if not rts or rts == ts or rts in handled_ts:
                            continue

                        # ignore bot messages and our own bot user id
                        if reply_msg.get("bot_id") or (
                            BOT_USER_ID and reply_msg.get("user") == BOT_USER_ID
                        ):
                            handled_ts.add(rts)
                            continue

                        rtext = reply_msg.get("text", "")
                        rnormalized = normalize_for_trigger(rtext)

                        triggered_in_reply = any(
                            rnormalized.startswith(t) or t in rnormalized
                            for t in TRIGGERS
                        )

                        if not triggered_in_reply:
                            continue

                        # check if we've already replied in this thread after this reply
                        already_replied = False
                        try:
                            replies_resp = slack.conversations_replies(
                                channel=channel, ts=ts, limit=200
                            )
                            if replies_resp.get("ok"):
                                replies = replies_resp.get("messages", [])
                            else:
                                replies = []
                        except Exception:
                            replies = []

                        if replies:
                            if BOT_USER_ID:
                                for r in replies:
                                    if r.get("user") == BOT_USER_ID or r.get("bot_id"):
                                        try:
                                            if float(r.get("ts", "0")) >= float(rts):
                                                already_replied = True
                                                break
                                        except Exception:
                                            already_replied = True
                                            break
                            else:
                                for r in replies:
                                    if r.get("bot_id"):
                                        already_replied = True
                                        break

                        if already_replied:
                            handled_ts.add(rts)
                            save_handled(handled_ts)
                            continue

                        # post reply into the parent thread and include the replier's name
                        replier_name = get_user_name(reply_msg.get("user"))
                        reply = get_sarcastic_reply(rtext, author_name=replier_name)
                        parts = split_response(reply)
                        for p in parts:
                            try:
                                slack.chat_postMessage(
                                    channel=channel,
                                    text=p,
                                    thread_ts=ts,
                                )
                            except Exception as e:
                                print(f"Post error (channel={channel} ts={rts}): {e}")
                        # add a reaction to the triggering reply message
                        try:
                            add_reaction(channel, rts, text=rtext, author_name=replier_name)
                        except Exception:
                            pass
                        handled_ts.add(rts)
                        save_handled(handled_ts)

    except Exception as e:
        print("Loop error:", e)

    time.sleep(POLL_INTERVAL)
