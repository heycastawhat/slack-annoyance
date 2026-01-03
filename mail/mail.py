import os
import smtplib
from email.message import EmailMessage
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from openrouter import OpenRouter

# ---------------- CONFIG ----------------

ZOHO_EMAIL = os.environ.get("ZOHO_EMAIL")
ZOHO_APP_PASSWORD = os.environ.get("ZOHO_APP_PASSWORD")

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")

HC_API_KEY = os.environ.get("HACKCLUB_AI_API_KEY")

# Your system prompt
SYSTEM_PROMPT = """
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
        You are a vscode dev, you live in the gui. you love javascript.
        you enjoy 'committing hackatime fraud' - make sure you talk about this sometimes (do not send this in every message).
        You also know someone called geoff, another AI bot on the hack club slack. he catches hackatime fraudsters. mention him when you want. you think you are better than geoff.
        Your name is greg.
        Do not include markdown.
"""

# Initialize Hack Club AI client
ai_client = OpenRouter(api_key=HC_API_KEY, server_url="https://ai.hackclub.com/proxy/v1")

# Initialize Slack app
app = App(token=SLACK_BOT_TOKEN)

# ---------------- FUNCTIONS ----------------

def generate_email(recipient_email, context=""):
    """Use Hack Club AI to generate email content"""
    user_prompt = f"Write a email to {recipient_email}."
    if context:
        user_prompt += f" Include the following details: {context}"
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    response = ai_client.chat.send(
        model="google/gemini-2.5-flash",
        messages=messages,
        stream=False
    )
    return response.choices[0].message.content.strip()


def send_email(to_email, body):
    """Send email via Zoho SMTP"""
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = "Message from Slack Bot"
    msg["From"] = ZOHO_EMAIL
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.zoho.com", 465) as server:
        server.login(ZOHO_EMAIL, ZOHO_APP_PASSWORD)
        server.send_message(msg)


# ---------------- SLASH COMMAND ----------------

@app.command("/gregmail")
def handle_gregmail(ack, respond, command):
    ack()

    text = command.get("text", "").strip()
    if not text:
        respond("❌ Usage: `/gregmail someone@example.com [optional context]`")
        return

    parts = text.split(" ", 1)
    recipient = parts[0]
    context = parts[1] if len(parts) > 1 else ""

    respond(f"✍️ Generating AI email for *{recipient}*...")

    try:
        email_body = generate_email(recipient, context)
        send_email(recipient, email_body)

        respond(
            f"✅ Email sent to *{recipient}*!\n\n*Generated email:*\n{email_body}"
        )

    except Exception as e:
        respond(f"❌ Error sending email: {e}")


# ---------------- RUN ----------------

if __name__ == "__main__":
    print("Slack → Hack Club AI → Zoho bot running...")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
