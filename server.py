# server.py
#
# Production-grade Vizard MCP Server
# Full parameter coverage based on:
# - SKILL.md
# - api-reference.md
#
# Compatible with:
# - Hermes
# - Claude Desktop
# - LobeHub
# - Cursor
# - OpenClaw (future MCP adapters)
#
# Run:
#   pip install -r requirements.txt
#   python server.py
#
# Environment:
#   VIZARD_API_KEY=xxxx

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

import os
import httpx
import asyncio
from typing import Optional, List, Dict, Any


# =========================================================
# Load ENV
# =========================================================

load_dotenv()

API_KEY = os.getenv("VIZARD_API_KEY")

BASE_URL = os.getenv(
    "VIZARD_BASE_URL",
    "https://elb-api.vizard.ai/hvizard-server-front/open-api/v1"
)

if not API_KEY:
    raise RuntimeError("Missing VIZARD_API_KEY")


# =========================================================
# MCP Server
# =========================================================

mcp = FastMCP("vizard-mcp")


# =========================================================
# Shared HTTP Client
# =========================================================

HEADERS = {
    "Content-Type": "application/json",
    "VIZARDAI_API_KEY": API_KEY
}


client = httpx.AsyncClient(
    timeout=httpx.Timeout(120.0)
)


# =========================================================
# Error Handling
# =========================================================

ERROR_CODES = {
    1000: "Still processing",

    2000: "Success",

    4001: "Invalid API key",
    4002: "Clipping failed or no speech detected",
    4003: "Rate limit exceeded",
    4004: "Unsupported video format or plan upgrade required",
    4005: "Invalid URL or video too long",
    4006: "Illegal parameter",
    4007: "Insufficient account credits",
    4008: "Failed to download video",
    4009: "The video URL specified in request is invalid",
    4010: "Can not detect the spoken language in video. Try changing the language parameter from auto to a specific language code",
    4011: "Invalid social account ID",
}


class VizardAPIError(Exception):
    pass


def handle_api_response(data: Dict[str, Any]) -> Dict[str, Any]:
    code = data.get("code")

    if code in (2000, 1000):
        return data

    message = ERROR_CODES.get(code, f"Unknown error code: {code}")

    raise VizardAPIError(message)


# =========================================================
# Utils
# =========================================================

def detect_video_ratio(aspect_ratio: str) -> int:
    """
    Auto-detect video ratio.
    """

    if "9:16" in aspect_ratio:
        return 1 

    if "1:1" in aspect_ratio:
        return 2 

    if "4:5" in aspect_ratio:
        return 3 

    if "16:9" in aspect_ratio:
        return 4 

    return 1

def detect_video_type(video_url: str) -> int:
    """
    Auto-detect video source platform.
    """

    url = video_url.lower()

    if "youtube.com" in url or "youtu.be" in url:
        return 2

    if "drive.google.com" in url:
        return 3

    if "vimeo.com" in url:
        return 4

    if "streamyard.com" in url:
        return 5

    if "tiktok.com" in url:
        return 6

    if "twitter.com" in url or "x.com" in url:
        return 7

    if "twitch.tv" in url:
        return 9

    if "loom.com" in url:
        return 10

    if "facebook.com" in url:
        return 11

    if "linkedin.com" in url:
        return 12

    return 1


async def api_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = await client.post(
        f"{BASE_URL}{path}",
        headers=HEADERS,
        json=payload
    )

    data = resp.json()

    return handle_api_response(data)


async def api_get(path: str) -> Dict[str, Any]:
    resp = await client.get(
        f"{BASE_URL}{path}",
        headers=HEADERS
    )

    data = resp.json()

    return handle_api_response(data)


# =========================================================
# Polling Helper
# =========================================================

async def wait_for_project(
    project_id: int,
    poll_interval: int = 30,
    max_wait_seconds: int = 1800
):
    """
    Wait until Vizard processing completes.
    """

    max_attempts = max_wait_seconds // poll_interval

    for _ in range(max_attempts):

        await asyncio.sleep(poll_interval)

        result = await query_project(project_id)

        if result["code"] == 2000 and result.get("videos"):
            return result

        if result["code"] not in (1000, 2000):
            return result

    raise TimeoutError("Vizard processing timeout")


# =========================================================
# 1. Create Clips (Simple)
# =========================================================

@mcp.tool()
async def create_clips(
    video_url: str,
    lang: str = "auto"
):
    """
    Create AI clips from long-form video.

    Best for:
    - Podcasts
    - Interviews
    - Webinars
    - YouTube videos
    """

    video_type = detect_video_type(video_url)

    payload = {
        "videoUrl": video_url,
        "videoType": video_type,
        "lang": lang,
        "preferLength": [0]
    }

    return await api_post(
        "/project/create",
        payload
    )


# =========================================================
# 2. Create Clips (Advanced Full Coverage)
# =========================================================

@mcp.tool()
async def create_clips_advanced(
    video_url: str,
    video_type: Optional[int] = None,
    lang: str = "auto",
    ext: Optional[str] = None,
    prefer_length: List[int] = [0],
    get_clips: int = 1,
    project_name: Optional[str] = None,
    webhook_url: Optional[str] = None,
    ratio_of_clip: str = "9:16",   
    removeSilenceSwitch: int =0,   
    keyword: Optional[str] = None,
    subtitleSwitch: int = 1,
    headlineSwitch: int = 1,
    template_id: Optional[int] = None

):
    """
    Full-parameter long-video clipping tool.

    Supports:
    - YouTube
    - Vimeo
    - TikTok
    - Twitch
    - LinkedIn
    - Google Drive
    - Direct MP4 uploads
    """

    if video_type is None:
        video_type = detect_video_type(video_url)

    ratioOfClip = detect_video_ratio(ratio_of_clip)
    
    payload = {
        "videoUrl": video_url,
        "videoType": video_type,
        "lang": lang,
        "preferLength": prefer_length,
        "maxClipNumber": get_clips,
        "ratioOfClip": ratioOfClip,
        # "ratioOfClip": 4,
        "removeSilenceSwitch": removeSilenceSwitch,
        "keyword": keyword,
        "subtitleSwitch": subtitleSwitch,
        "headlineSwitch": headlineSwitch
    }

    if ext:
        payload["ext"] = ext

    if template_id:
        payload["templateId"] = template_id

    if project_name:
        payload["projectName"] = project_name

    if webhook_url:
        payload["webhookUrl"] = webhook_url

    return await api_post(
        "/project/create",
        payload
    )


# =========================================================
# 3. Edit Short Video (Full Coverage)
# =========================================================

@mcp.tool()
async def edit_short_video(
    video_url: str,

    video_type: Optional[int] = None,

    ext: str = "mp4",

    lang: str = "auto",
    ratio_of_clip: str = "9:16",  
    subtitle_switch: int = 1,

    emoji_switch: int = 0,

    highlight_switch: int = 0,

    auto_broll_switch: int = 0,

    headline_switch: int = 1,

    remove_silence_switch: int = 0,

    template_id: Optional[int] = None,

    project_name: Optional[str] = None
):
    """
    AI-enhance short videos (<=3 min).

    Features:
    - Subtitles
    - AI B-roll
    - Headline hooks
    - Emoji subtitles
    - Silence removal
    - Branding templates
    """

    if video_type is None:
        video_type = detect_video_type(video_url)

    ratioOfClip = detect_video_ratio(ratio_of_clip)

    payload = {
        "videoUrl": video_url,
        "videoType": video_type,
        "ext": ext,
        "lang": lang,
        "getClips": 0,
        "ratioOfClip": ratioOfClip,
        "subtitleSwitch": subtitle_switch,
        "emojiSwitch": emoji_switch,
        "highlightSwitch": highlight_switch,
        "autoBrollSwitch": auto_broll_switch,
        "headlineSwitch": headline_switch,
        "removeSilenceSwitch": remove_silence_switch
    }

    if template_id:
        payload["templateId"] = template_id

    if project_name:
        payload["projectName"] = project_name

    return await api_post(
        "/project/create",
        payload
    )


# =========================================================
# 4. Query Project
# =========================================================

@mcp.tool()
async def query_project(project_id: int):
    """
    Query project processing status and clips.
    """

    return await api_get(
        f"/project/query/{project_id}"
    )


# =========================================================
# 5. Wait Until Finished
# =========================================================

@mcp.tool()
async def wait_for_project_completion(
    project_id: int,

    poll_interval: int = 30,

    max_wait_seconds: int = 1800
):
    """
    Poll until Vizard finishes processing.
    """

    return await wait_for_project(
        project_id,
        poll_interval,
        max_wait_seconds
    )


# =========================================================
# 6. Create + Wait Workflow
# =========================================================

@mcp.tool()
async def create_clips_and_wait(
    video_url: str,

    lang: str = "auto",

    prefer_length: List[int] = [0]
):
    """
    Full workflow:
    submit video -> wait -> return clips
    """

    result = await create_clips_advanced(
        video_url=video_url,
        lang=lang,
        prefer_length=prefer_length
    )

    project_id = result["projectId"]

    return await wait_for_project(project_id)


# =========================================================
# 7. List Social Accounts
# =========================================================

@mcp.tool()
async def list_social_accounts():
    """
    List connected social media accounts.
    """

    return await api_get(
        "/project/social-accounts"
    )


# =========================================================
# 8. Publish Video
# =========================================================

@mcp.tool()
async def publish_video(
    final_video_id: int,

    social_account_id: str,

    post: str = "",

    publish_time: Optional[int] = None,

    title: Optional[str] = None
):
    """
    Publish video clip to social platforms.

    Supports:
    - TikTok
    - Instagram
    - LinkedIn
    - YouTube
    - Twitter/X
    """

    payload = {
        "finalVideoId": final_video_id,
        "socialAccountId": social_account_id,
        "post": post
    }

    if publish_time:
        payload["publishTime"] = publish_time

    if title:
        payload["title"] = title

    return await api_post(
        "/project/publish-video",
        payload
    )


# =========================================================
# 9. Generate AI Caption
# =========================================================

@mcp.tool()
async def generate_social_caption(
    final_video_id: int,

    ai_social_platform: int = 4,

    tone: int = 2,

    voice: int = 0
):
    """
    Generate AI social caption + hashtags.

    Platforms:
    1 = General
    2 = TikTok
    3 = Instagram
    4 = YouTube
    5 = Facebook
    6 = LinkedIn
    7 = Twitter/X
    """

    payload = {
        "finalVideoId": final_video_id,
        "aiSocialPlatform": ai_social_platform,
        "tone": tone,
        "voice": voice
    }

    return await api_post(
        "/project/ai-social",
        payload
    )


# =========================================================
# 10. Viral Pipeline Workflow
# =========================================================

@mcp.tool()
async def viral_pipeline(
    video_url: str,

    lang: str = "auto"
):
    """
    Complete viral-content workflow:

    1. Submit video
    2. Wait for clips
    3. Rank by viral score
    4. Return best clips
    """

    result = await create_clips_advanced(
        video_url=video_url,
        lang=lang
    )

    project_id = result["projectId"]

    final_result = await wait_for_project(project_id)

    videos = final_result.get("videos", [])

    ranked = sorted(
        videos,
        key=lambda x: float(x.get("viralScore", 0)),
        reverse=True
    )

    return {
        "project_id": project_id,
        "best_clip": ranked[0] if ranked else None,
        "all_clips": ranked
    }


# =========================================================
# Start MCP Server
# =========================================================

if __name__ == "__main__":
    print("Starting Vizard MCP Server...")
    mcp.run(transport="stdio")