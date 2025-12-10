Slack Annoyance - One of the Slack bots of all time
---
<img width="256" height="256" alt="Untitled design" src="https://github.com/user-attachments/assets/41c2436d-7320-457d-9cd6-37f23bb8c5be" />
<img width="787" height="143" alt="Screenshot 2025-12-05 at 7 12 05 PM" src="https://github.com/user-attachments/assets/5eac5ca3-a016-4a00-8314-08e2a4263504" />
   <img width="351" height="126" alt="Screenshot 2025-12-05 at 7 18 40 PM" src="https://github.com/user-attachments/assets/19a7c9a5-5511-44d9-a7f4-abcc22381dba" />
   <img width="304" height="178" alt="Screenshot 2025-12-06 at 1 59 59 PM" src="https://github.com/user-attachments/assets/5baf5f42-db79-4066-9210-a0eaedfc54dc" />

---
## Features
- Annoying Ai That Responds to "Slave", "Servant", "@Slack Annoyance", "Slack Annoyance", "Assistant", "Grok is this true"
- Live Last.Fm Scrobble Updates (Full Release Coming Soon)
---
## Services Used
- Slack (slack.com)
- Hack Club AI (ai.hackclub.com)
- Langfuse (langfuse.com)
---
## Get started (development)
Use uv!

```bash
uv sync
```

Copy .env.local to .env and insert your api keys (This has been designed to work with Hack Club AI.) You'll also need to copy compose.example.yaml to compose.yaml edit the env vars in compose.yaml

Place your flastsm (last fm scrobble) custom message in the file path you specify in .env

Build docker images:

```bash
docker build -t flastsm flastsm
docker build -t greg annoyance
```

Run containers

```bash
docker compose up -d
