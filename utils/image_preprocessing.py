import cv2

def split_rows(image, num_rows=2):
    """Split the image horizontally into N rows (default: 2)."""
    height = image.shape[0]
    row_height = height // num_rows
    rows = []
    for i in range(num_rows):
        start_y = i * row_height
        end_y = (i + 1) * row_height if i < num_rows - 1 else height
        rows.append(image[start_y:end_y])
    return rows

def detect_books_in_row(row_image, min_area=1000):
    """Detect book spines in a row image using contour detection."""
    gray = cv2.cvtColor(row_image, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    book_boxes = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if area > min_area and h > w:  # vertical book-like region
            book_boxes.append((x, y, w, h))

    # Sort left to right
    book_boxes = sorted(book_boxes, key=lambda box: box[0])
    return book_boxes
