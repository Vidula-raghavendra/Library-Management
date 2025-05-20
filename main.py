import streamlit as st
import cv2
import pandas as pd
import numpy as np
import pytesseract
from PIL import Image
import easyocr
import os
import tempfile
import google.generativeai as genai

# ------------- CONFIG -------------
# Set Gemini API key
API_KEY = ""  # <-- Replace with your Gemini API key
genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# CSV file
CSV_FILE = "books.csv"
if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=["Gemini", "Borrowed"]).to_csv(CSV_FILE, index=False)

# ------------- Gemini OCR FUNCTION -------------
def extract_with_gemini(pil_image):
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            pil_image.save(temp_file.name)
            temp_path = temp_file.name

        blob = genai.upload_file(temp_path)

        response = gemini_model.generate_content([
            "Extract book spine text exactly as it appears. Return only a Python list of book titles.",
            blob
        ])
        return response.text.strip()

    except Exception as e:
        return f"Error: {str(e)}"
    
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ------------- STREAMLIT UI -------------
st.set_page_config(page_title="📚 Book OCR Dashboard", layout="wide")
st.title("📚 Book Spine OCR Extractor")

# Upload option
uploaded_file = st.file_uploader("📤 Upload a book spine image (JPG/PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    # OCR: Tesseract
    st.subheader("🔤 Tesseract")
    tesseract_text = pytesseract.image_to_string(image)
    st.code(tesseract_text)

    # OCR: EasyOCR
    st.subheader("🧾 EasyOCR")
    reader = easyocr.Reader(['en'], gpu=False)
    easy_text = '\n'.join(reader.readtext(np.array(image), detail=0))
    st.code(easy_text)

    # OCR: Gemini
    st.subheader("🔮 Gemini")
    gemini_text = extract_with_gemini(image)
    st.code(gemini_text)

    # Save only Gemini output
    if st.button("✅ Save Gemini Output"):
        new_row = pd.DataFrame([[gemini_text, "No"]], columns=["Gemini", "Borrowed"])
        new_row.to_csv(CSV_FILE, mode="a", header=False, index=False)
        st.success("Saved Gemini output to books.csv!")

# ------------- Display Table -------------
st.divider()
st.subheader("📘 Saved Book Titles")
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    st.dataframe(df, use_container_width=True)
