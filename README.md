# 🤖 Autonomous LinkedIn Agent

An AI agent that turns a photo or video into a LinkedIn post — automatically. Drop a file in a folder, let Google Gemini write a caption in your voice, approve it (or ask for a rewrite) right in your terminal, and it publishes straight to LinkedIn.

Built by [Rudra Pratap Singh](https://www.linkedin.com/in/rudra-pratap-singh-997878289) as part of a public "learning in progress" build.

---

## ✨ What it does

1. Watches an `inbox/` folder for the next image or video to post.
2. Sends it to **Gemini** (`gemini-3.5-flash`) along with a profile/voice prompt so the caption sounds like *you*, not a generic AI post.
3. Shows you the generated caption in the terminal and lets you:
   - `y` — post it as-is
   - `r` — regenerate with the same hint
   - `h` — give Gemini a quick hint (e.g. "leg day PR") and regenerate
   - `q` — quit and leave the file untouched for next time
4. On approval, uploads the media and publishes the post to LinkedIn via the official LinkedIn API.
5. Moves the posted file into `posted/<date>/` so it's never posted twice.
6. Logs every run to `poster.log`.

---

## 🧰 Requirements

- **Python 3.10+**
- A **Google Gemini API key** — free at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- A **LinkedIn Developer app** with the `w_member_social` scope (see setup below)
- *(Optional)* **ffmpeg** on your PATH — only needed if you post videos, so a frame can be grabbed for Gemini to "see"

### Python packages

Installed via `requirements.txt`:

| Package | Why |
|---|---|
| `requests` | Talks to the LinkedIn REST API |
| `google-genai` | Official Google SDK for calling Gemini |
| `python-dotenv` | Loads secrets from `.env` |

---

## 🚀 Setup

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
pip install -r requirements.txt
```

### 2. Get a Gemini API key

Go to [Google AI Studio](https://aistudio.google.com/app/apikey), create a key, and keep it handy.

### 3. Create a LinkedIn app

1. Go to [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps) → **Create app**.
2. Under **Products**, request access to **"Share on LinkedIn"** (gives you `w_member_social`).
3. Under **Auth**, add this redirect URL:
   ```
   http://localhost:8765/callback
   ```
4. Copy the **Client ID** and **Client Secret** from the Auth tab.

### 4. Fill in your `.env`

Copy the template and fill it in:

```bash
cp .env.example .env
```

Add your `GEMINI_API_KEY`, `LINKEDIN_CLIENT_ID`, and `LINKEDIN_CLIENT_SECRET` to `.env`.

### 5. Authorize with LinkedIn

Run the helper script once — it opens a browser, you approve access, and it prints your access token + person URN:

```bash
python linkedin_auth_helper.py
```

Paste the two printed values (`LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN`) into `.env`.

> ⚠️ LinkedIn access tokens expire after **60 days**. Re-run `linkedin_auth_helper.py` to refresh it when it does.

### 6. Post something

Drop an image or video into `inbox/`, then run:

```bash
python daily_poster.py
```

Follow the terminal prompts to approve, tweak, or skip the caption.

---

## 📁 Project structure

```
.
├── daily_poster.py           # main script: caption + post
├── linkedin_auth_helper.py   # one-time OAuth helper to get your access token
├── inbox/                    # put today's photo/video here
├── posted/                   # auto-archive of what's already been posted, by date
├── poster.log                # run history
├── .env.example               # template for secrets — copy to .env
├── .env                       # your real secrets — NEVER commit this
└── requirements.txt
```

---

## 🔒 Security notes

- `.env` holds live API keys and your LinkedIn access token. It's already excluded via `.gitignore` — **never remove it from there or commit `.env`**.
- If a real key ever ends up in a commit (even by accident), rotate/regenerate it immediately (new Gemini key, new LinkedIn token) rather than just deleting the commit — Git history isn't a safe place to "undo" a leaked secret.

---

## ⏰ Running it on a schedule

The script is interactive by design (the `y/r/h/q` approval loop), which makes it a good fit for a local scheduler you can respond to — e.g. **Windows Task Scheduler**, **cron** with a terminal, or simply running it by hand each day.

If you want it to run **fully unattended** (e.g. on GitHub Actions, where there's no terminal to type into), you'd need to add a non-interactive mode — for example, auto-posting the first caption Gemini generates instead of waiting for `y/r/h/q` input. That's a natural next step if you want true "set and forget" automation.

---

## 🛠 Built with

- [Google Gemini API](https://ai.google.dev/) for caption generation
- [LinkedIn REST API](https://learn.microsoft.com/en-us/linkedin/) for publishing
- Python 3 standard library + `requests`, `python-dotenv`

---

## 📄 License

Add a license of your choice (MIT is a common pick for personal projects like this) — see [choosealicense.com](https://choosealicense.com/).
