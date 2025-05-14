import cv2
import pytesseract
import easyocr
from google.cloud import vision
from PIL import Image
import pandas as pd
import time
import datetime

# Initialize Google Vision client
client = vision.ImageAnnotatorClient()

# Path to Tesseract executable (Make sure you have Tesseract installed and configured)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Adjust if needed

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

# Function for Tesseract OCR
def ocr_tesseract(image):
    text = pytesseract.image_to_string(image)
    return text

# Function for EasyOCR
def ocr_easyocr(image):
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

# Function to detect book positions (example placeholder logic)
def detect_books_and_update_positions(frame):
    # Placeholder for logic to detect books' positions in the frame
    books_detected = {"Book1": (1, 2), "Book2": (3, 4)}  # Example positions
    return books_detected

# Function to log book positions into a CSV
def log_book_positions(books_detected):
    # Convert book positions into a pandas DataFrame
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {"Book Name": [], "Position": [], "Timestamp": []}
    
    for book_name, position in books_detected.items():
        data["Book Name"].append(book_name)
        data["Position"].append(position)
        data["Timestamp"].append(current_time)
    
    # Save or append to CSV
    df = pd.DataFrame(data)
    try:
        df.to_csv('books_positions.csv', mode='a', header=False, index=False)
    except FileNotFoundError:
        df.to_csv('books_positions.csv', mode='w', header=True, index=False)

# Function to check for book removal based on previous positions (simplified logic)
def check_for_removal_or_addition(current_positions, previous_positions):
    removed_books = []
    added_books = []
    
    for book_name in previous_positions:
        if book_name not in current_positions:
            removed_books.append(book_name)
    
    for book_name in current_positions:
        if book_name not in previous_positions:
            added_books.append(book_name)
    
    return added_books, removed_books

# Main backend logic for capturing and processing frames
def process_frame_and_update_positions(frame, previous_positions):
    # Perform OCR with all 3 methods
    tesseract_text = ocr_tesseract(frame)
    easyocr_text = ocr_easyocr(frame)
    googlevision_text = ocr_googlevision(Image.fromarray(frame))

    # Display OCR results (for debugging)
    print("Tesseract OCR Output:", tesseract_text)
    print("EasyOCR Output:", easyocr_text)
    print("Google Vision OCR Output:", googlevision_text)

    # Detect books' positions in the frame
    current_positions = detect_books_and_update_positions(frame)
    
    # Log the positions to CSV
    log_book_positions(current_positions)

    # Check for added or removed books
    added_books, removed_books = check_for_removal_or_addition(current_positions, previous_positions)

    # Return updated positions and any changes detected
    return current_positions, added_books, removed_books

# Backend code loop (called in a regular interval, e.g., every 5 minutes)
def track_books_in_library():
    cap = cv2.VideoCapture(0)  # Start webcam feed

    previous_positions = {}

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Process the frame and update positions
        current_positions, added_books, removed_books = process_frame_and_update_positions(frame, previous_positions)

        # If any books were added or removed, print those changes (or handle as needed)
        if added_books:
            print(f"Added Books: {added_books}")
        if removed_books:
            print(f"Removed Books: {removed_books}")

        # Update previous positions with the current positions for the next loop
        previous_positions = current_positions

        # Sleep for a defined time frame (e.g., 5 minutes)
        time.sleep(300)  # Sleep for 5 minutes (300 seconds)
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    track_books_in_library()
