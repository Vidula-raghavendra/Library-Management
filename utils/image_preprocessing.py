import cv2
import numpy as np

def split_rows(image_np_rgb, num_rows=2):
    """Split the image (NumPy RGB array) horizontally into N rows."""
    height = image_np_rgb.shape[0]
    row_height = height // num_rows
    rows = []
    for i in range(num_rows):
        start_y = i * row_height
        # For the last row, ensure it goes to the end of the image to avoid missing pixels
        end_y = (i + 1) * row_height if i < num_rows - 1 else height
        rows.append(image_np_rgb[start_y:end_y, :])
    return rows

def detect_books_in_row(row_image_np_rgb, min_area=1000, aspect_ratio_threshold_min=0.1, aspect_ratio_threshold_max=1.0):
    """Detect book spines in a row image (NumPy RGB array) using contour detection.
    Returns a list of (x, y, w, h) bounding boxes relative to the row_image.
    """
    if row_image_np_rgb is None or row_image_np_rgb.size == 0:
        return []
        
    gray = cv2.cvtColor(row_image_np_rgb, cv2.COLOR_RGB2GRAY)
    
    # Apply some preprocessing
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 30, 150) # Adjusted thresholds for potentially more robust edge detection

    # Find contours
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    book_boxes = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        aspect_ratio = float(w) / h if h > 0 else 0

        # Filter criteria:
        # 1. Area large enough
        # 2. Taller than wide (typical for spines, but allow some flexibility)
        #    or width is not excessively larger than height.
        #    aspect_ratio_threshold_min < w/h < aspect_ratio_threshold_max
        #    For vertical spines, w/h is small.
        if area > min_area and h > 0 and w > 0: # Basic check
            if (h > w) or (aspect_ratio >= aspect_ratio_threshold_min and aspect_ratio <= aspect_ratio_threshold_max) :
                 # Further check: contour area vs bounding box area to filter out L-shapes
                contour_area = cv2.contourArea(cnt)
                if contour_area / float(area) > 0.4: # Contour should fill a good portion of its bounding box
                    book_boxes.append((x, y, w, h))

    # Sort detected book boxes from left to right
    book_boxes = sorted(book_boxes, key=lambda box: box[0])
    return book_boxes