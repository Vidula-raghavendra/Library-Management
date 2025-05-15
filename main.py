import streamlit as st
import cv2
from PIL import Image
import numpy as np
import pytesseract

# Replace with the actual path where you installed Tesseract
pytesseract.pytesseract.tesseract_cmd = r'"C:\Users\ragha\Downloads\tesseract-ocr-w64-setup-5.5.0.20241111.exe"'

import easyocr
import os
import pandas as pd
from database import extract_with_gemini

# SET TESSERACT PATH (Windows users)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.title("📚 Live Book Spine Text Extractor")

# Camera Capture
st.subheader("🎥 Live Camera Feed")

FRAME_WINDOW = st.image([])

camera = cv2.VideoCapture(0)

run = st.checkbox("Start Camera")

if run:
    st.write("Press the 'Capture & Extract' button to extract book titles.")
    capture = st.button("📸 Capture & Extract")

    while run:
        ret, frame = camera.read()
        if not ret:
            st.error("Failed to grab frame.")
            break

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        FRAME_WINDOW.image(frame)

        if capture:
            image_pil = Image.fromarray(frame)

            st.subheader("🧠 OCR Outputs")

            # Tesseract
            tesseract_text = pytesseract.image_to_string(image_pil)
            st.markdown("**🔤 Tesseract Output:**")
            st.code(tesseract_text)

            # EasyOCR
            reader = easyocr.Reader(['en'])
            easy_text = reader.readtext(np.array(image_pil), detail=0)
            st.markdown("**🧾 EasyOCR Output:**")
            st.code('\n'.join(easy_text))

            # Gemini
            with st.spinner("Gemini is analyzing the image..."):
                gemini_text = extract_with_gemini(image_pil)

            st.markdown("**🔮 Gemini Output:**")
            st.code(gemini_text)

            # Save only Gemini output to CSV
            try:
                if gemini_text and gemini_text.startswith('['):
                    book_list = eval(gemini_text)
                    if isinstance(book_list, list):
                        df = pd.DataFrame(book_list, columns=["Book Title"])
                        if os.path.exists("books.csv"):
                            df.to_csv("books.csv", mode="a", header=False, index=False)
                        else:
                            df.to_csv("books.csv", index=False)
                        st.success("✅ Gemini titles added to books.csv")
                    else:
                        st.warning("⚠️ Gemini response not a valid list.")
                else:
                    st.warning("⚠️ Gemini output format is unexpected.")
            except Exception as e:
                st.error(f"Error saving to CSV: {str(e)}")

            break

else:
    st.info("Check the box above to start the camera.")
