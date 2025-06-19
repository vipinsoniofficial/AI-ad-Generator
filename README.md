# 🛍️ AI Video Ad Generator

This is a lightweight MVP application that automatically generates 30-second marketing video ads for products using AI. Just provide a product link (Amazon or Shopify), and the app will:

1. Scrape product title, image, and description.
2. Generate a 30-second ad script using OpenAI.
3. Create a video using the product image, animated captions, and AI-generated voiceover.
4. Display and allow you to download the final MP4 ad.

---

## 🧠 Technologies Used

- [Streamlit](https://streamlit.io/) – for the UI
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) – for scraping product details
- [OpenAI GPT](https://platform.openai.com/) – to generate the ad script
- [gTTS](https://pypi.org/project/gTTS/) – for voiceover
- [MoviePy](https://zulko.github.io/moviepy/) – to generate video
- [Pillow](https://pillow.readthedocs.io/) – image handling

---

## 🚀 Getting Started

### ✅ Prerequisites

Ensure you have the following:

- Python 3.8+
- OpenAI API key

### 📦 Install Dependencies

```bash
pip install -r requirements.txt

```
Run:
```
streamlit run app.py
