# app.py – Streamlit AI Video Ad Generator

"""
A simple 24‑hour‑style MVP that:
1. Accepts a product URL (Amazon/Shopify) from the user.
2. Scrapes product title, image, and description.
3. Uses the OpenAI API to create a 30‑second ad script.
4. Generates a basic video (image + text overlay) with MoviePy.
5. Displays the video in Streamlit and offers a download button.

To run locally:
$ pip install -r requirements.txt
$ streamlit run app.py
"""


import logging
import requests
import openai
import streamlit as st
from bs4 import BeautifulSoup
from moviepy import ImageClip, TextClip, CompositeVideoClip,AudioFileClip
from PIL import Image
from gtts import gTTS
import os
import uuid

# ---------- CONFIG ---------- #
openai.api_key = ""
TEMP_DIR = ''
os.makedirs(TEMP_DIR, exist_ok=True)
logger = logging.getLogger(__name__)
# ---------------------------- #


def extract_product_info(url: str):
    """Scrape product title, first image, and description (simple heuristics)."""
    logger.info("Scraping product info from: %s", url)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Fallbacks are simplistic — adjust per site in real use.
    title = soup.find("meta", property="og:title")
    if title:
        title = title.get("content", "Product")
    else:
        title = soup.title.string if soup.title else "Product"

    # description
    desc_tag = soup.find("meta", {"name": "description"}) or soup.find(
        "meta", property="og:description"
    )
    description = desc_tag.get("content", "No description provided") if desc_tag else "No description provided"

    img_tag = soup.find("img", id="landingImage") or soup.find("meta", property="og:image")
    img_url = img_tag["src"] if img_tag and img_tag.get("src") else (
        img_tag["content"] if img_tag and img_tag.get("content") else None
    )

    logger.info("Scraped title: %s", title)
    logger.info("Scraped image: %s", img_url)
    return title.strip(), description.strip(), img_url


def download_image(img_url: str) -> str:
    """Download product image locally and return the path."""
    logger.info("Downloading image from %s", img_url)
    resp = requests.get(img_url, timeout=15)
    resp.raise_for_status()
    ext = os.path.splitext(img_url)[1][:5] or ".jpg"
    img_path = os.path.join(TEMP_DIR, f"img_{uuid.uuid4().hex}{ext}")
    with open(img_path, "wb") as f:
        f.write(resp.content)
    # ensure RGB (MoviePy prefers)
    try:
        logger.info("Image saved to %s", img_path)
        im = Image.open(img_path).convert("RGB")
        im.save(img_path)
    except Exception:
        pass
    return img_path


def generate_ad_script(title: str, description: str) -> str:
    """Call OpenAI chat completion to get a 30-second ad script."""
    logger.info("Generating ad script with OpenAI for: %s", title)
    prompt = (
        "You are a creative marketing assistant. Write a short, 10‑second video ad script "
        "for the following product. Focus on 3 top benefits and a call‑to‑action.\n\n"
        f"Product name: {title}\n"
        f"Product description: {description}\n\n"
        "Return the script in one sentence per line (max 4 lines)."
    )
    response = openai.ChatCompletion.create(
        model="gpt-4o",  # fallback to gpt‑3.5‑turbo if needed
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )
    script = response.choices[0].message.content.strip()
    logger.info("Generated script: %s", script.replace("\n", " | "))
    return script


def create_video(img_path: str, script: str) -> str:
    """Generate a 10-second video with background image, text overlay, and voiceover."""
    duration = 10  # seconds
    width = 720

    # Generate TTS audio
    tts = gTTS(text=script, lang='en')
    audio_path = os.path.join(TEMP_DIR, f"audio_{uuid.uuid4().hex}.mp3")
    tts.save(audio_path)
    audio_clip = AudioFileClip(audio_path)

    # Create image clip
    img_clip = ImageClip(img_path, duration=duration).resized(width=width).with_position("center")

    # Create text clip (first line of script or whole script as caption)
    text_clip = TextClip(text=script, font_size=10, color="white", font="Arial.ttf", method="caption", size=(width - 40, None), duration=duration).with_position(("center", "bottom"))

    # Combine video and audio
    final = CompositeVideoClip([img_clip,text_clip]).with_audio(audio_clip)

    # Export video
    out_path = os.path.join(TEMP_DIR, f"video_{uuid.uuid4().hex}.mp4")
    final.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
    return out_path


# -------- Streamlit Interface -------- #
st.set_page_config(page_title="AI Video Ad Generator", layout="centered")
st.title("🛒 AI Video Ad Generator")

product_url = st.text_input("Enter Product URL (Amazon or Shopify):")

if st.button("Generate Video Ad") and product_url:
    with st.spinner("Extracting product details..."):
        try:
            logger.info("started video generation started")
            title, desc, img_url = extract_product_info(product_url)
            st.write(f"**Product:** {title}")
            st.image(img_url, width=300)
        except Exception as e:
            st.error(f"Failed to scrape product info: {e}")
            st.stop()

    with st.spinner("Generating ad script..."):
        try:
            script = generate_ad_script(title, desc)
            st.write("Script:")
            st.code(script, language="text")

        except openai.OpenAIError as e:
            print("OpenAI error: %s", e)
            st.error(f"OpenAI API error: {e}")
            st.stop()

    with st.spinner("Creating video..."):
        try:
            img_path = download_image(img_url)
            video_path = create_video(img_path, script)
        except Exception as e:
            print("Video generation error: %s", e)
            st.error(f"Failed to create video: {e}")
            st.stop()

    st.success("Video generated!")
    st.video(video_path)
    with open(video_path, "rb") as vid_file:
        st.download_button("Download Video", vid_file, file_name="ad.mp4", mime="video/mp4")

st.caption("Built with Streamlit, OpenAI GPT, and MoviePy ✨")
