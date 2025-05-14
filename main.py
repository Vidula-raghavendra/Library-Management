import streamlit as st
import cv2
import numpy as np
import time
import pandas as pd
import pytesseract
import easyocr
from google.cloud import vision
from PIL import Image
from io import BytesIO

# Initialize Google Vision client
client = vision.ImageAnnotatorClient()

# Set page config
st.set_page_config(page_title="Library OCR", layout="wide")

# OCR Functions
def ocr_tesseract(image):
    return pytesseract.image_to_string(image)

def ocr_easyocr(image):
    reader = easyocr.Reader(['en'], gpu=False)
    result = reader.readtext(np.array(image))
    return " ".join([r[1] for r in result])

#def ocr_googlevision(image):
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    content = buffer.getvalue()
    google_image = vision.Image(content=content)
    response = client.text_detection(image=google_image)
    texts = response.text_annotations
    return texts[0].description if texts else ""

def log_to_csv(book_name, position):
    df = pd.DataFrame([[book_name, position, time.strftime("%Y-%m-%d %H:%M:%S")]],
                      columns=["Book Name", "Position", "Timestamp"])
    df.to_csv("books_positions.csv", mode='a', index=False, header=not pd.io.common.file_exists("books_positions.csv"))

def load_csv_data():
    try:
        return pd.read_csv("books_positions.csv")
    except FileNotFoundError:
        return pd.DataFrame(columns=["Book Name", "Position", "Timestamp"])

# Sidebar Navigation
page = st.sidebar.selectbox("Navigation", ["Home", "View Log", "Insert", "Delete"])

if page == "Home":
    st.title("Library Management with OCR")
    
    col1, col2 = st.columns(2)

    with col1:
        st.header("Camera Feed")
        img_file_buffer = st.camera_input("Take a picture")

    with col2:
        st.header("OCR Outputs")
        if img_file_buffer is not None:
            image = Image.open(img_file_buffer)
            st.image(image, caption="Captured Image", use_column_width=True)

            tess_text = ocr_tesseract(image)
            easy_text = ocr_easyocr(image)
            #google_text = ocr_googlevision(image)

            st.subheader("1. Tesseract")
            st.text(tess_text)
            
            st.subheader("2. EasyOCR")
            st.text(easy_text)

            st.subheader("3. Google Vision")
            st.text(google_text)

            # Log Google Vision output into CSV
            #log_to_csv("Detected Book", google_text)

elif page == "View Log":
    st.title("Book Detection Log")
    data = load_csv_data()
    st.dataframe(data)

elif page == "Insert":
    st.title("Insert Record Manually")
    with st.form("insert_form"):
        book_name = st.text_input("Book Name")
        position = st.text_input("Position")
        submitted = st.form_submit_button("Insert")
        if submitted and book_name and position:
            log_to_csv(book_name, position)
            st.success("Record inserted successfully!")

elif page == "Delete":
    st.title("Delete Records")
    data = load_csv_data()
    if not data.empty:
        book_names = data["Book Name"].unique()
        book_to_delete = st.selectbox("Select Book to Delete", book_names)
        if st.button("Delete"):
            updated_df = data[data["Book Name"] != book_to_delete]
            updated_df.to_csv("books_positions.csv", index=False)
            st.success(f"Records for '{book_to_delete}' deleted.")
    else:
        st.info("No records to delete.")