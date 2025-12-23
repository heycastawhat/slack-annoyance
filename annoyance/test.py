import requests
from greg import HACKCLUB_AI_KEY, MODEL

prompt = "hi this is a test"

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

print(r.json)
