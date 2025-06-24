import os
import uuid
import json
import re
import requests
import openai
import streamlit as st
from bs4 import BeautifulSoup
from PIL import Image
from gtts import gTTS
from moviepy.video.fx import FadeIn
from moviepy import (
    ImageClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    AudioFileClip,
)

# -------------- CONFIG ---------------- #
openai.api_key = ""
TEMP_DIR = ''
os.makedirs(TEMP_DIR, exist_ok=True)
# ------------------------------------- #

def extract_product_info(url: str):
    """Scrape product title, description, and clean product images."""
    print(f"[INFO] Scraping: {url}")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to load page: {e}")
        raise

    soup = BeautifulSoup(response.text, "html.parser")

    # -------- TITLE -------- #
    title_tag = soup.find("span", id="productTitle") or soup.find("meta", property="og:title")
    title = title_tag.get_text(strip=True) if title_tag else "Product Title Not Found"
    print(f"[INFO] Title: {title}")

    # -------- DESCRIPTION -------- #
    desc_tag = soup.find("meta", {"name": "description"}) or soup.find("meta", property="og:description")
    description = desc_tag.get("content", "No description found.") if desc_tag else "No description found."
    print(f"[INFO] Description: {description[:100]}...")

    # -------- IMAGES -------- #
    img_urls = []
    seen = set()
    dynamic_imgs = soup.find_all("img", attrs={"data-a-dynamic-image": True})
    for img in dynamic_imgs:
        data = img.get("data-a-dynamic-image")
        try:
            json_data = json.loads(data)
            for k in json_data.keys():
                base_url = re.sub(r"\._[^.]+\.", ".", k)
                if base_url not in seen and len(img_urls) < 4:
                    img_urls.append(k)
                    seen.add(base_url)
        except Exception:
            continue

    return title.strip(), description.strip(), img_urls


def generate_ai_images(prompt: str, count=2):
    """Generate fallback images using OpenAI DALL·E."""
    print(f"[INFO] Generating fallback AI images for: {prompt}")
    try:
        response = openai.Image.create(prompt=prompt, n=count, size="1024x1024")
        return [img["url"] for img in response["data"]]
    except Exception as e:
        print(f"[ERROR] AI image generation failed: {e}")
        return []


def generate_ad_script(title: str, description: str) -> str:
    prompt = (
        "You are a marketing assistant. Write a short 4-line video ad script "
        "for the following product. Each line should highlight a benefit or call to action.\n\n"
        f"Product name: {title}\n"
        f"Product description: {description}\n\n"
        "Format it as 4 short lines."
    )
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )
    return response.choices[0].message.content.strip()


def download_image(url: str) -> str:
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        ext = os.path.splitext(url)[1][:5] or ".jpg"
        path = os.path.join(TEMP_DIR, f"img_{uuid.uuid4().hex}{ext}")
        with open(path, "wb") as f:
            f.write(resp.content)
        img = Image.open(path).convert("RGB")
        img.save(path)
        return path
    except Exception as e:
        print(f"[ERROR] Failed to download image: {url} | {e}")
        return None



def download_images(urls: list) -> list:
    return [download_image(url) for url in urls if url]


def create_video(img_paths: list, script_lines: list) -> str:
    clips = []
    width = 720
    duration = 2.5

    tts = gTTS(" ".join(script_lines), lang="en")
    audio_path = os.path.join(TEMP_DIR, f"audio_{uuid.uuid4().hex}.mp3")
    tts.save(audio_path)
    audio = AudioFileClip(audio_path)
    print('creating video function status: 0')
    for i, img_path in enumerate(img_paths[:len(script_lines)]):
        text = script_lines[i]
        img_clip = ImageClip(img_path).resized(width=width).with_duration(duration) #.fadein(0.5)
        txt_clip = (
            TextClip(text=text, font_size=40, color="white", font="Arial.ttf", method="caption", size=(width - 40, None))
            .with_position(("center", "bottom"))
            .with_duration(duration)
            #.fadein(0.5)
        )
        clips.append(CompositeVideoClip([img_clip, txt_clip]))

    print('creating video function status: 1')
    try:
        final = concatenate_videoclips(clips).with_audio(audio)
    except Exception as e:
        print("Exception:",e)
    print('creating video function status: 2')
    out_path = os.path.join(TEMP_DIR, f"video_{uuid.uuid4().hex}.mp4")
    final.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
    return out_path


# -------- Streamlit UI -------- #
st.set_page_config(page_title="AI Video Ad Generator", layout="centered")
st.title("🎬 AI Video Ad Generator")

product_url = st.text_input("Paste a product URL (Amazon or Shopify):")

if st.button("Generate Ad") and product_url:
    with st.spinner("Scraping product info..."):
        try:
            title, desc, img_urls = extract_product_info(product_url)
            print('img_urls: 0', img_urls)
            if not img_urls:
                img_urls = generate_ai_images(f"Product showcase of: {title}", count=3)
            print('img_urls: 1', img_urls)
            st.subheader(title)
            st.write(desc)
        except Exception as e:
            st.error(f"Failed to scrape product: {e}")
            st.stop()

    selected_urls = []
    for i, img_url in enumerate(img_urls):
        st.image(img_url, width=300)
        selected_urls.append(img_url)

    with st.spinner("Generating ad script..."):
        try:
            script = generate_ad_script(title, desc)
            script_lines = script.split("\n")
            st.code(script)
        except Exception as e:
            st.error(f"OpenAI error: {e}")
            st.stop()

    with st.spinner("Creating video..."):
        try:
            print('status 0')
            img_paths = download_images(selected_urls)
            print('img_paths:', img_paths)
            print('status 1')
            video_path = create_video(img_paths, script_lines)
            print('status 2')
        except Exception as e:
            st.error(f"Video creation failed: {e}")
            st.stop()

    st.success("🎉 Video generated!")
    st.video(video_path)
    with open(video_path, "rb") as f:
        st.download_button("⬇️ Download Video", f, file_name="ai_ad.mp4", mime="video/mp4")

st.caption("Built with OpenAI, DALL·E, Streamlit, and MoviePy 🚀")
