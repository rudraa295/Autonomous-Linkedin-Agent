import os
import sys
import shutil
import subprocess
import mimetypes
from datetime import date
from pathlib import Path

import requests
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

BASE_DIR = Path(__file__).parent
INBOX_DIR = BASE_DIR / "inbox"
POSTED_DIR = BASE_DIR / "posted"
LOG_FILE = BASE_DIR / "poster.log"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v"}

GEMINI_MODEL = "gemini-3.1-flash-lite"


def log(msg: str):
    line = f"[{date.today().isoformat()}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_todays_file():
    INBOX_DIR.mkdir(exist_ok=True)
    for f in sorted(INBOX_DIR.iterdir()):
        if f.suffix.lower() in IMAGE_EXTS | VIDEO_EXTS:
            return f
    return None


def get_hint() -> str:
    """Ask the user for a hint right in the terminal, e.g. 'leg day PR'."""
    print("\nGive Gemini a quick hint about today's post (or press Enter to skip):")
    try:
        return input("> ").strip()
    except EOFError:
        return ""


def extract_video_frame(video_path: Path) -> Path | None:
    if not shutil.which("ffmpeg"):
        return None
    frame_path = video_path.with_suffix(".preview.jpg")
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(video_path),
                "-ss", "00:00:01.000", "-vframes", "1", str(frame_path),
            ],
            check=True, capture_output=True,
        )
        return frame_path if frame_path.exists() else None
    except Exception:
        return None



PROFILE_CONTEXT = """
Author: Rudra Pratap Singh, B.Tech Computer Science & Engineering (AI & ML).
Aspiring software engineer building a public learning-in-progress brand.
Core skill tags he consistently uses: Python | Statistics and Probability |
NumPy, Pandas, SciPy | AI & Machine Learning | DSA | Git & GitHub.
LinkedIn handle: rudra-pratap-singh-997878289

Established voice (from his real past posts, match this energy):
- Plain, Professional ,  confident, first-person, not corporate-sounding
- Explains what he learned/built and why it's interesting, briefly
- Invites connection/community ("let's learn and grow together" energy)
- Always closes with a cluster of relevant hashtags for reach, mixing
  broad ones (#Python #MachineLearning #DataScience) with niche/specific
  ones tied to the actual content (e.g. #ReeborgsWorld, #DSA, #Django)
"""




def generate_caption(media_file: Path, hint: str) -> str:

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    is_video = media_file.suffix.lower() in VIDEO_EXTS
    image_for_vision = media_file

    if is_video:
        frame = extract_video_frame(media_file)
        if frame:
            image_for_vision = frame

    prompt = f"""
{PROFILE_CONTEXT}

The attached image/video is today's LinkedIn post.

Write a LinkedIn post that:

• Starts with ONE short, amusing, first-person line (6-7 words) from
  Rudra's AI agent introducing itself as the one posting today on his
  behalf -  Make it playful and DIFFERENT every
  time - don't reuse the same phrasing twice in a row. In the caption 
  Rudra's AI agent plays the role of 1st person and Rudra play the role of 
  2nd person
• After that intro line, add a blank line, then the real caption.
• Sounds natural and personal.
• Is written in 2nd person , Rudra's AI agent is posting on behalf of Rudra
• Explains what he built or learned today.
• Is reflective instead of promotional.
• Uses exactly 2-3 short paragraphs.
• Never invents facts.
• If a hint is provided, use it naturally.
• End with exactly with 5-8 hashtags suitable for post best reach on Linkedin:

"""

    if hint:
        prompt += f"""

    Here is a rough idea for today's work.

    It's most  important
    
    Create a completely original LinkedIn post.

    Today's context(It's most  important):
    {hint}
    """

    contents = []

    if image_for_vision and image_for_vision.exists():

        mime = mimetypes.guess_type(str(image_for_vision))[0] or "image/jpeg"

        contents.append(
            types.Part.from_bytes(
                data=image_for_vision.read_bytes(),
                mime_type=mime,
            )
        )

    contents.append(prompt)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            max_output_tokens=2048,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )

    finish_reason = response.candidates[0].finish_reason if response.candidates else None
    if finish_reason is not None and str(finish_reason) not in ("STOP", "FinishReason.STOP"):
        raise RuntimeError(
            f"Gemini response was cut off (finish_reason={finish_reason}) "
            f"instead of finishing naturally - discarding and retrying."
        )

    raw_text = response.text
    if not raw_text or not raw_text.strip():
        raise RuntimeError("Gemini returned an empty response.")
    caption = raw_text.strip()

    if caption.startswith("```"):
        caption = caption.replace("```markdown", "")
        caption = caption.replace("```text", "")
        caption = caption.replace("```", "").strip()

    bad_phrases = [
        "Final Polish",
        "Check constraints",
        "Refining Text",
        "Correct hashtags",
        "Connection invitation",
        "Output MUST",
        "JSON",
        "XML",
        "YAML",
    ]

    for phrase in bad_phrases:
        if phrase.lower() in caption.lower():
            raise RuntimeError(
                "Gemini returned prompt instructions instead of a caption."
            )

    return caption

def _linkedin_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": "202601",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }


def post_to_linkedin(media_file: Path, caption: str):
    token = os.environ["LINKEDIN_ACCESS_TOKEN"]
    person_urn = os.environ["LINKEDIN_PERSON_URN"]
    is_video = media_file.suffix.lower() in VIDEO_EXTS
    kind = "videos" if is_video else "images"

    init_resp = requests.post(
        f"https://api.linkedin.com/rest/{kind}?action=initializeUpload",
        headers=_linkedin_headers(token),
        json={"initializeUploadRequest": {"owner": person_urn}},
    )
    init_resp.raise_for_status()
    init_data = init_resp.json()["value"]
    upload_url = init_data["uploadUrl"]
    asset_urn = init_data[f"{'video' if is_video else 'image'}"]

    with open(media_file, "rb") as f:
        upload_resp = requests.put(upload_url, data=f.read())
    upload_resp.raise_for_status()

    post_body = {
        "author": person_urn,
        "commentary": caption,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {"media": {"id": asset_urn}},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    post_resp = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers=_linkedin_headers(token),
        json=post_body,
    )
    post_resp.raise_for_status()
    log("Posted to LinkedIn successfully.")


def archive_file(media_file: Path):
    dest_dir = POSTED_DIR / date.today().isoformat()
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(media_file), str(dest_dir / media_file.name))


def generate_caption_with_retries(media_file: Path, hint: str) -> str:
    """Try Gemini up to 3 times to survive transient errors (503s, cut-off
    responses, etc). Raises if all 3 attempts fail."""
    last_error = None
    for attempt in range(3):
        try:
            return generate_caption(media_file, hint)
        except Exception as e:
            last_error = e
            log(f"Caption generation attempt {attempt + 1} failed: {e}")
    raise last_error


def main():
    media_file = get_todays_file()
    if not media_file:
        log("No file in inbox/ today - nothing to post.")
        return

    hint = get_hint()

    while True:
        try:
            caption = generate_caption_with_retries(media_file, hint)
        except Exception as e:
            log(f"ERROR generating caption: {e}")
            return

        log("Caption generated successfully.")
        print("=" * 80)
        print(caption)
        print("=" * 80)

        choice = input(
            "\nPost this to LinkedIn? "
            "[y]es / [r]egenerate / [h]int + regenerate / [q]uit: "
        ).strip().lower()

        if choice in ("y", "yes"):
            break
        elif choice in ("r", "regenerate"):
            print("Regenerating with the same hint...")
            continue
        elif choice in ("h", "hint"):
            hint = get_hint()
            continue
        elif choice in ("q", "quit"):
            log("Cancelled by user - leaving file in inbox/ untouched.")
            return
        else:
            print("Didn't catch that - type y, r, h, or q.")
            continue

    try:
        post_to_linkedin(media_file, caption)
        archive_file(media_file)
    except Exception as e:
        log(f"ERROR posting to LinkedIn: {e}")
        log("Post failed - leaving file in inbox/ to retry tomorrow.")


if __name__ == "__main__":
    main()
