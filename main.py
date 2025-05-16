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

# -------------------- SETUP --------------------

# Configure Gemini API
API_KEY = ""
genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# CSV file for storing results
CSV_FILE = "books.csv"
if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=["Tesseract", "EasyOCR", "Gemini"]).to_csv(CSV_FILE, index=False)

# -------------------- GEMINI OCR FUNCTION --------------------
def extract_with_gemini(pil_image):
    try:
        # Save PIL image to temporary file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            pil_image.save(temp_file.name)
            temp_path = temp_file.name

        # Upload image as a Blob to Gemini
        blob = genai.upload_file(temp_path)

        # Call Gemini model with uploaded image blob
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

# -------------------- STREAMLIT UI --------------------
st.set_page_config(page_title="📚 Book OCR Dashboard", layout="wide")
st.title("📚 Live Book Spine OCR Extractor")

# Load existing data
data_df = pd.read_csv(CSV_FILE)

# Live camera capture
col1, col2 = st.columns([1, 2])

with col1:
    st.header("🎥 Live Camera Feed")
    FRAME_WINDOW = st.image([])
    camera = cv2.VideoCapture(0)
    run = st.checkbox("Start Camera")
    capture = st.button("📸 Capture & Extract")

with col2:
    st.header("🔍 OCR Outputs")
    output_col1, output_col2, output_col3 = st.columns(3)

    if run:
        while True:
            ret, frame = camera.read()
            if not ret:
                st.error("Failed to grab frame.")
                break

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            FRAME_WINDOW.image(frame)

            if capture:
                image_pil = Image.fromarray(frame)

                # Tesseract OCR
                tesseract_text = pytesseract.image_to_string(image_pil)
                output_col1.subheader("🔤 Tesseract")
                output_col1.code(tesseract_text)

                # EasyOCR
                reader = easyocr.Reader(['en'], gpu=False)
                easy_text = reader.readtext(np.array(image_pil), detail=0)
                easy_text_combined = '\n'.join(easy_text)
                output_col2.subheader("🧾 EasyOCR")
                output_col2.code(easy_text_combined)

                # Gemini OCR
                gemini_text = extract_with_gemini(image_pil)
                output_col3.subheader("🔮 Gemini")
                output_col3.code(gemini_text)

                # Save to CSV
                new_data = pd.DataFrame([[tesseract_text, easy_text_combined, gemini_text]],
                                        columns=["Tesseract", "EasyOCR", "Gemini"])
                new_data.to_csv(CSV_FILE, mode="a", header=False, index=False)
                st.success("✅ Text saved to books.csv")

                break

# -------------------- DATA DISPLAY --------------------
st.divider()
st.header("📘 Extracted Books Table")
search_query = st.text_input("🔎 Search Book Titles")

filtered_df = data_df.copy()
if search_query:
    filtered_df = filtered_df[filtered_df.apply(
        lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

st.dataframe(filtered_df, use_container_width=True)

