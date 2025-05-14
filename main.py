import streamlit as st
import cv2
import time
import pandas as pd
import pytesseract
import easyocr
from google.cloud import vision
from PIL import Image

# Initialize Google Vision client
client = vision.ImageAnnotatorClient()

# Function for Tesseract OCR
def ocr_tesseract(image):
    text = pytesseract.image_to_string(image)
    return text

# Function for EasyOCR
def ocr_easyocr(image):
    reader = easyocr.Reader(['en'])
    result = reader.readtext(image)
    return " ".join([r[1] for r in result])

# Function for Google Vision OCR
def ocr_googlevision(image):
    # Convert image to Google Cloud Vision format
    image_content = image.tobytes()
    google_image = vision.Image(content=image_content)
    
    # Perform text detection
    response = client.text_detection(image=google_image)
    texts = response.text_annotations
    if texts:
        return texts[0].description
    return ""

# Function to detect book positions and check for removal/addition
def detect_books_and_update_positions(frame):
    # Placeholder for the logic to detect books
    books_detected = {"Book1": (1, 2), "Book2": (3, 4)}  # Sample positions
    return books_detected

# Streamlit UI setup
st.title("Library Management with OCR")

# Timer setup
time_limit = 5 * 60  # 5 minutes
elapsed_time = 0

# Capture webcam feed
cap = cv2.VideoCapture(0)

if cap.isOpened():
    # Placeholder for image feed
    stframe = st.empty()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Update the frame
        stframe.image(frame, channels="BGR", use_column_width=True)

        # OCR Processing every 5 seconds
        if elapsed_time >= time_limit:
            # Perform OCR with all 3 methods
            tesseract_text = ocr_tesseract(frame)
            easyocr_text = ocr_easyocr(frame)
            googlevision_text = ocr_googlevision(Image.fromarray(frame))

            # Display OCR results
            st.write("Tesseract OCR Output:", tesseract_text)
            st.write("EasyOCR Output:", easyocr_text)
            st.write("Google Vision OCR Output:", googlevision_text)

            # Update the position of books and check for removal
            books_position = detect_books_and_update_positions(frame)
            st.write("Books Positions:", books_position)
            
            # Log into CSV
            df = pd.DataFrame(books_position.items(), columns=["Book Name", "Position"])
            df.to_csv('books_positions.csv', mode='a', header=False)

            # Reset timer
            elapsed_time = 0

        # Increase elapsed time
        elapsed_time += 1

        # Break out of loop on user exit
        time.sleep(1)

else:
    st.error("Could not open webcam.")

cap.release()
cv2.destroyAllWindows()
