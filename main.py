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
import ast
import time

# ------------- PAGE CONFIG (MUST BE FIRST STREAMLIT COMMAND) -------------
st.set_page_config(page_title="📚 Fixed Set Book OCR & Accuracy Analysis", layout="wide")

# ------------- PREDEFINED GROUND TRUTH & SHELF LETTERS -------------
IMAGE_GROUND_TRUTH = {
    "1.jpg": [
        {"title": "Microwave & Radar Engineering", "expected_row": 1, "expected_col": 1},
        # If there are multiple copies of this book in 1.jpg at different positions, list them:
        # {"title": "Microwave & Radar Engineering", "expected_row": 1, "expected_col": 2},
    ],
    "2.jpg": [
        {"title": "DIGITAL IMAGE PROCESSING", "expected_row": 1, "expected_col": 1},
        {"title": "Discrete Time Signal Processing", "expected_row": 1, "expected_col": 2},
        {"title": "DIGITAL COMMUNICATION", "expected_row": 1, "expected_col": 3}, # Assuming this is a third distinct book
    ],
    "3.jpg": [
        {"title": "Indian Government and Politics", "expected_row": 1, "expected_col": 1},
    ],
    "4.jpg": [
        {"title": "SATELLITE COMMUNICATIONS", "expected_row": 1, "expected_col": 1},
        {"title": "Communication Systems", "expected_row": 1, "expected_col": 2},
    ],
    "5.jpg": [
        {"title": "Database System Concepts", "expected_row": 1, "expected_col": 1},
    ]
}

# Auto-assign shelf letters based on distinct titles
ALL_DISTINCT_GT_TITLES = sorted(list(set(
    book["title"] for img_gt in IMAGE_GROUND_TRUTH.values() for book in img_gt
)))

TITLE_TO_SHELF_LETTER = {
    title: chr(ord('A') + i) for i, title in enumerate(ALL_DISTINCT_GT_TITLES)
}

# Update IMAGE_GROUND_TRUTH with systematic shelf letters
for img_id, books in IMAGE_GROUND_TRUTH.items():
    for book_info in books:
        if book_info["title"] in TITLE_TO_SHELF_LETTER:
            book_info["shelf_letter"] = TITLE_TO_SHELF_LETTER[book_info["title"]]
        else:
            st.error(f"Error: Title '{book_info['title']}' not found for shelf letter assignment. Check GT definition.")


# ------------- APP CONFIG & INITIALIZATIONS -------------
# --- Gemini API Configuration ---
API_KEY_FROM_CODE = ""  # <--- REPLACE THIS!!!
API_KEY = os.environ.get("GEMINI_API_KEY", API_KEY_FROM_CODE)

gemini_model = None
gemini_initialized_successfully = False
gemini_init_error_message = ""

if API_KEY == "YOUR_ACTUAL_GEMINI_API_KEY" and API_KEY != "":
    st.warning("⚠️ Please replace 'YOUR_ACTUAL_GEMINI_API_KEY' in the code with your real Gemini API key...")
    gemini_init_error_message = "Gemini API key is a placeholder."
elif not API_KEY:
    st.error("⛔ Gemini API Key is missing...")
    gemini_init_error_message = "Gemini API key is missing."
else:
    try:
        genai.configure(api_key=API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        gemini_initialized_successfully = True
    except Exception as e:
        gemini_init_error_message = f"Failed to initialize Gemini Model: {e}"
        st.error(f"🚫 {gemini_init_error_message}")

# --- Tesseract Configuration ---
TESSERACT_PATH_CONFIG = r"C:\Program Files\Tesseract-OCR\tesseract.exe" # Windows default
# For other OS, Tesseract might be in PATH, or you might need different paths
# if not os.path.exists(TESSERACT_PATH_CONFIG) and os.name != 'nt':
#     TESSERACT_PATH_CONFIG = "tesseract" # Common on Linux/macOS if in PATH

tesseract_configured = False
if os.path.exists(TESSERACT_PATH_CONFIG):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH_CONFIG
    tesseract_configured = True
else:
    st.warning(f"⚠️ Tesseract executable not found at '{TESSERACT_PATH_CONFIG}'.")


# --- CSV File Configuration ---
CSV_FILE = "books.csv"
CSV_COLUMNS = ["Title", "Inventory_Count", "Detected_In_Current_Scan", "Estimated_Borrowed", "Matrix_Position"]
if not os.path.exists(CSV_FILE):
    try:
        pd.DataFrame(columns=CSV_COLUMNS).to_csv(CSV_FILE, index=False)
    except Exception as e:
        st.error(f"🚨 Could not create or access {CSV_FILE}: {e}.")

if 'last_processed_image_id' not in st.session_state:
    st.session_state.last_processed_image_id = None

# ------------- OCR & HELPER FUNCTIONS -------------
SIMILARITY_THRESHOLD = 0.80

def extract_titles_with_gemini(pil_image):
    if not gemini_initialized_successfully or not gemini_model:
        return [{"error": gemini_init_error_message or "Gemini model not configured."}]
    temp_path = None
    try:
        prompt = (
            "You are an advanced visual analysis AI specializing in library inventory.\n"
            "Analyze the provided image which shows book spines on shelves.\n"
            "Your task is to:\n"
            "1. Identify each distinct book title visible on a spine.\n"
            "2. For each identified title, determine its physical location using a matrix-style coordinate:\n"
            "    - Row Number (row): Starting from 1 for the topmost visible shelf/row of books, incrementing downwards.\n"
            "    - Position in Row (col): Starting from 1 for the leftmost book in that specific row, incrementing to the right.\n"
            "3. If multiple copies of the exact same title are visible, create a separate entry for each copy with its unique coordinates.\n"
            "4. Return your findings *only* as a Python list of dictionaries. Each dictionary *must* contain three keys: 'title' (string), 'row' (integer), and 'col' (integer for position in row).\n"
            "   Example: `[{'title': 'The Great Gatsby', 'row': 1, 'col': 1}, {'title': 'Moby Dick', 'row': 1, 'col': 2}, {'title': 'The Great Gatsby', 'row': 2, 'col': 3}]`\n"
            "5. If you cannot confidently determine a row or column for a title, you may use 0 for those specific integer fields, but always include the keys. Ensure 'title' is always a string.\n"
            "6. If no book titles are clearly visible or decipherable, return an empty Python list: `[]`."
        )
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            pil_image.save(temp_file.name, format="PNG")
            temp_path = temp_file.name
        if os.path.getsize(temp_path) == 0: return [{"title": "NO_TITLES_DETECTED (empty image)", "row":0, "col":0}]
        uploaded_file_response = genai.upload_file(path=temp_path)
        response = gemini_model.generate_content([prompt, uploaded_file_response])
        genai.delete_file(uploaded_file_response.name)
        raw_text_response = response.text.strip()

        # Attempt to parse the response
        try:
            # Clean known prefixes/suffixes
            if raw_text_response.startswith("```python"): raw_text_response = raw_text_response.removeprefix("```python").strip()
            elif raw_text_response.startswith("```"): raw_text_response = raw_text_response.removeprefix("```").strip()
            if raw_text_response.endswith("```"): raw_text_response = raw_text_response.removesuffix("```").strip()

            if not raw_text_response or raw_text_response.lower() == "[]": return []
            
            parsed_response = ast.literal_eval(raw_text_response)
            
            if isinstance(parsed_response, list):
                valid_items = []
                for item in parsed_response:
                    if isinstance(item, dict) and \
                       'title' in item and isinstance(item['title'], str) and \
                       'row' in item and isinstance(item['row'], (int, type(None))) and \
                       'col' in item and isinstance(item['col'], (int, type(None))):
                        item['row'] = item['row'] if item['row'] is not None else 0
                        item['col'] = item['col'] if item['col'] is not None else 0
                        if item['title'].strip() and item['title'].strip().lower() not in ["no_title_detected", "unknown_title"]:
                            valid_items.append(item)
                return valid_items
            else: return [{"error": f"Unexpected Gemini format. Expected list of dicts, got: {type(parsed_response)}", "response": raw_text_response}]
        except (ValueError, SyntaxError, TypeError) as e: return [{"error": f"Error parsing Gemini's structured response: {e}", "response": raw_text_response}]
    except Exception as e: return [{"error": f"Gemini API Error: {str(e)}"}]
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@st.cache_resource
def get_easyocr_reader():
    try: return easyocr.Reader(['en'], gpu=False)
    except Exception as e: st.error(f"🚨 Failed to initialize EasyOCR Reader: {e}.")
    return None

def process_and_save_to_csv(scanned_data_for_saving):
    if not scanned_data_for_saving:
        st.sidebar.caption("Auto-save: No new data to save.")
        return

    current_df_csv = None
    try:
        if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
            current_df_csv = pd.read_csv(CSV_FILE)
            if not all(col in current_df_csv.columns for col in CSV_COLUMNS) or \
               not all(col in CSV_COLUMNS for col in current_df_csv.columns):
                st.warning(f"{CSV_FILE} has mismatched columns. Re-initializing with schema: {CSV_COLUMNS}")
                current_df_csv = pd.DataFrame(columns=CSV_COLUMNS)
                current_df_csv.to_csv(CSV_FILE, index=False) 
            else:
                 for col in CSV_COLUMNS:
                    if col not in current_df_csv.columns:
                        current_df_csv[col] = 0 if col in ["Inventory_Count", "Detected_In_Current_Scan", "Estimated_Borrowed"] else ""
                 current_df_csv = current_df_csv.reindex(columns=CSV_COLUMNS)
        else:
            current_df_csv = pd.DataFrame(columns=CSV_COLUMNS)
            current_df_csv.to_csv(CSV_FILE, index=False)
    except pd.errors.EmptyDataError:
        st.info(f"{CSV_FILE} is empty. Initializing fresh inventory DataFrame.")
        current_df_csv = pd.DataFrame(columns=CSV_COLUMNS)
        current_df_csv.to_csv(CSV_FILE, index=False)
    except Exception as e:
        st.error(f"Error reading {CSV_FILE} for auto-save: {e}. Using new DataFrame.")
        current_df_csv = pd.DataFrame(columns=CSV_COLUMNS)

    df_csv_to_update = current_df_csv.copy()
    df_csv_to_update["_found_in_scan"] = False
    changes_made = False

    for title_from_scan, data_from_scan in scanned_data_for_saving.items():
        detected_count = data_from_scan["count"]
        matrix_positions_str = data_from_scan["matrix_position_str"]
        if not isinstance(title_from_scan, str): continue
        if "Title" not in df_csv_to_update.columns: df_csv_to_update["Title"] = ""
        df_csv_to_update["Title"] = df_csv_to_update["Title"].astype(str)
        existing_rows = df_csv_to_update[df_csv_to_update["Title"].str.lower() == title_from_scan.lower()]

        if not existing_rows.empty:
            idx = existing_rows.index[0]
            for col_check in ["Inventory_Count", "Detected_In_Current_Scan", "Matrix_Position"]:
                if col_check not in df_csv_to_update.columns: df_csv_to_update[col_check] = 0 if col_check != "Matrix_Position" else ""
            old_inventory_val = df_csv_to_update.loc[idx, "Inventory_Count"]
            old_inventory = pd.to_numeric(old_inventory_val, errors='coerce')
            old_inventory = 0 if pd.isna(old_inventory) else int(old_inventory)

            if (df_csv_to_update.loc[idx, "Detected_In_Current_Scan"] != detected_count or
                old_inventory < detected_count or 
                str(df_csv_to_update.loc[idx, "Matrix_Position"]) != matrix_positions_str):
                changes_made = True

            new_inventory = max(old_inventory, detected_count)
            df_csv_to_update.loc[idx, "Inventory_Count"] = new_inventory
            df_csv_to_update.loc[idx, "Detected_In_Current_Scan"] = detected_count
            df_csv_to_update.loc[idx, "Estimated_Borrowed"] = new_inventory - detected_count
            df_csv_to_update.loc[idx, "Matrix_Position"] = matrix_positions_str
            df_csv_to_update.loc[idx, "_found_in_scan"] = True
        else:
            changes_made = True
            new_row_dict = {col: "" for col in CSV_COLUMNS}
            new_row_dict.update({
                "Title": title_from_scan, "Inventory_Count": detected_count,
                "Detected_In_Current_Scan": detected_count, "Estimated_Borrowed": 0,
                "Matrix_Position": matrix_positions_str,
            })
            new_row_df = pd.DataFrame([new_row_dict])
            new_row_df["_found_in_scan"] = True
            df_csv_to_update = pd.concat([df_csv_to_update, new_row_df], ignore_index=True)

    for idx, row in df_csv_to_update.iterrows():
        if not row["_found_in_scan"]: 
            previously_detected_val = row.get("Detected_In_Current_Scan")
            previously_detected_numeric = pd.to_numeric(previously_detected_val, errors='coerce')
            if pd.isna(previously_detected_numeric): 
                previously_detected_numeric = 0
            else:
                previously_detected_numeric = int(previously_detected_numeric)

            if previously_detected_numeric != 0:
                changes_made = True
            df_csv_to_update.loc[idx, "Detected_In_Current_Scan"] = 0
            
            inventory_val_on_row = row.get("Inventory_Count",0)
            inventory_val = pd.to_numeric(inventory_val_on_row, errors='coerce')
            if pd.isna(inventory_val): 
                inventory_val = 0
            else:
                inventory_val = int(inventory_val)
            df_csv_to_update.loc[idx, "Estimated_Borrowed"] = inventory_val
            pass 
    
    if "_found_in_scan" in df_csv_to_update.columns:
        df_csv_to_update = df_csv_to_update.drop(columns=["_found_in_scan"])
    
    if changes_made:
        for col in CSV_COLUMNS:
            if col not in df_csv_to_update.columns: df_csv_to_update[col] = ""
        df_csv_to_update = df_csv_to_update.fillna({
            "Inventory_Count": 0, "Detected_In_Current_Scan": 0, 
            "Estimated_Borrowed": 0, "Matrix_Position": "N/A"
        })
        for col_to_int in ["Inventory_Count", "Detected_In_Current_Scan", "Estimated_Borrowed"]:
            if col_to_int in df_csv_to_update.columns:
                 df_csv_to_update[col_to_int] = pd.to_numeric(df_csv_to_update[col_to_int], errors='coerce').fillna(0).astype(int)
        try:
            df_csv_to_update[CSV_COLUMNS].to_csv(CSV_FILE, index=False)
            st.success(f"✅ Inventory auto-updated: {CSV_FILE}")
        except Exception as e:
            st.error(f"🚨 Error auto-saving to {CSV_FILE}: {e}")

# ------------- MAIN APP LOGIC -------------
st.title("📚 Advanced Book OCR & Inventory")

input_method = st.radio("Select Image Source:", ("Upload File", "Live Webcam Capture"), horizontal=True, key="input_method_radio")
uploaded_image_pil = None
current_image_unique_id = None

if input_method == "Upload File":
    uploaded_file_buffer = st.file_uploader("Image of book spines", type=["jpg", "jpeg", "png"], key="file_uploader_widget")
    if uploaded_file_buffer:
        uploaded_image_pil = Image.open(uploaded_file_buffer)
        current_image_unique_id = uploaded_file_buffer.file_id
elif input_method == "Live Webcam Capture":
    img_file_buffer_cam = st.camera_input("Capture from webcam", key="camera_input_widget")
    if img_file_buffer_cam:
        uploaded_image_pil = Image.open(img_file_buffer_cam)
        current_image_unique_id = img_file_buffer_cam.file_id

if uploaded_image_pil and \
   (st.session_state.get('last_processed_image_id') != current_image_unique_id or \
    st.session_state.get('last_processed_image_id') is None):

    if current_image_unique_id: st.session_state.last_processed_image_id = current_image_unique_id
    else: st.session_state.last_processed_image_id = f"processed_at_{time.time()}" 
    st.image(uploaded_image_pil, caption="Current Image for Processing", use_column_width=True)
    st.header("🔍 OCR Results (Full Image)")
    cv_image_rgb = np.array(uploaded_image_pil.convert('RGB'))
    tesseract_full_text = "N/A"
    easyocr_full_text = "N/A"
    gemini_extracted_data = [] 

    with st.spinner("Performing OCR... (this may take a while)"):
        if tesseract_configured:
            try: 
                tesseract_full_text = pytesseract.image_to_string(uploaded_image_pil)
                if not tesseract_full_text.strip(): tesseract_full_text = "No text detected by Tesseract."
            except Exception as e: tesseract_full_text = f"Tesseract Error: {e}"
        else: tesseract_full_text = "Tesseract not configured."
        st.text_area("Tesseract Output (Full Image)", tesseract_full_text, height=100, key="tess_out_full")

        easyocr_reader = get_easyocr_reader()
        if easyocr_reader:
            try:
                easy_text_list = easyocr_reader.readtext(cv_image_rgb, detail=0, paragraph=True)
                easyocr_full_text = '\n'.join(easy_text_list)
                if not easyocr_full_text.strip(): easyocr_full_text = "No text detected by EasyOCR."
            except Exception as e: easyocr_full_text = f"EasyOCR Error: {e}"
        else: easyocr_full_text = "EasyOCR not initialized."
        st.text_area("EasyOCR Output (Full Image)", easyocr_full_text, height=100, key="easy_out_full")
        
        if gemini_initialized_successfully and gemini_model:
            gemini_extracted_data = extract_titles_with_gemini(pil_image=uploaded_image_pil)
            st.subheader("💎 Gemini Extracted Titles & Positions:")
            if gemini_extracted_data:
                is_error_response = len(gemini_extracted_data) == 1 and isinstance(gemini_extracted_data[0], dict) and "error" in gemini_extracted_data[0]
                if is_error_response:
                    st.warning(f"Gemini processing error: {gemini_extracted_data[0].get('error')}")
                    if "response" in gemini_extracted_data[0]: st.code(f"Raw Gemini Response:\n{gemini_extracted_data[0]['response']}")
                else:
                    has_valid_entries = False
                    for item in gemini_extracted_data:
                        if isinstance(item, dict) and item.get("title"):
                            title = item.get('title', "N/A")
                            row = item.get('row', 0)
                            col = item.get('col', 0)
                            st.markdown(f"- **{title}** at A[{row}x{col}]")
                            has_valid_entries = True
                    if not has_valid_entries and not is_error_response:
                        st.info("Gemini processed image but found no valid titles/positions.")
            else: st.info("Gemini processed image but found no titles/positions or returned an empty list.")
        elif gemini_init_error_message: st.warning(f"Gemini not configured: {gemini_init_error_message}.")
        else: st.warning("Gemini status unknown.")

    scanned_titles_data_for_csv = {}
    valid_gemini_items = [item for item in gemini_extracted_data if isinstance(item, dict) and "error" not in item and "title" in item]

    if valid_gemini_items:
        for item in valid_gemini_items:
            title = item.get("title", "Unknown Title").strip()
            row = item.get("row", 0) 
            col = item.get("col", 0) 
            if not title or title.lower() == "unknown title" or not isinstance(row, int) or not isinstance(col, int) or row <= 0 or col <= 0:
                continue
            clean_title = ' '.join(word.capitalize() for word in title.split())
            if clean_title not in scanned_titles_data_for_csv:
                scanned_titles_data_for_csv[clean_title] = {"count": 0, "positions_by_row": {}}
            scanned_titles_data_for_csv[clean_title]["count"] += 1
            if row not in scanned_titles_data_for_csv[clean_title]["positions_by_row"]:
                scanned_titles_data_for_csv[clean_title]["positions_by_row"][row] = []
            scanned_titles_data_for_csv[clean_title]["positions_by_row"][row].append(col)

        st.subheader("📊 Aggregated Gemini Data for Inventory")
        display_scan_data = []
        for title, data in scanned_titles_data_for_csv.items():
            position_strings = []
            for row_num, cols in sorted(data["positions_by_row"].items()):
                sorted_cols = sorted(list(set(cols))) 
                if sorted_cols: 
                    position_strings.append(f"A[{row_num},({','.join(map(str, sorted_cols))})]")
            final_position_str = "; ".join(position_strings) if position_strings else "Position N/A"
            display_scan_data.append({
                "Title": title, "Detected Count": data["count"], "Matrix Positions": final_position_str 
            })
        if display_scan_data: 
            st.dataframe(pd.DataFrame(display_scan_data), use_container_width=True, hide_index=True, key="agg_titles_df_matrix")
        
        data_for_saving = {}
        for title, data in scanned_titles_data_for_csv.items():
            position_strings = []
            for row_num, cols in sorted(data["positions_by_row"].items()):
                sorted_cols = sorted(list(set(cols)))
                if sorted_cols: position_strings.append(f"A[{row_num},({','.join(map(str, sorted_cols))})]")
            final_position_str = "; ".join(position_strings) if position_strings else "Position N/A"
            data_for_saving[title] = {"count": data["count"], "matrix_position_str": final_position_str}
        process_and_save_to_csv(data_for_saving)
    
    elif uploaded_image_pil:
        is_error_response_check = len(gemini_extracted_data) == 1 and isinstance(gemini_extracted_data[0], dict) and "error" in gemini_extracted_data[0]
        if is_error_response_check: pass
        elif not gemini_extracted_data: st.info("No processable book data (titles/positions) extracted by Gemini from the current image.")
        else: st.warning("Could not process titles for inventory due to Gemini issues or an unexpected response format.")

st.divider()
st.header("📘 Book Inventory")
df_inventory = pd.DataFrame(columns=CSV_COLUMNS)
if os.path.exists(CSV_FILE):
    try:
        df_inventory = pd.read_csv(CSV_FILE)
        if df_inventory.empty and os.path.getsize(CSV_FILE) == 0: 
            st.info(f"{CSV_FILE} is empty. Upload an image to populate.", icon="ℹ️")
        elif df_inventory.empty and os.path.getsize(CSV_FILE) > 0: 
             st.warning(f"{CSV_FILE} might be corrupted or only contains headers. Try deleting it if issues persist.", icon="⚠️")
             df_inventory = pd.DataFrame(columns=CSV_COLUMNS)
        else: 
            for col_csv in CSV_COLUMNS:
                if col_csv not in df_inventory.columns: df_inventory[col_csv] = ""
            df_inventory = df_inventory[CSV_COLUMNS]
    except pd.errors.EmptyDataError: 
        st.info(f"{CSV_FILE} is empty or could not be parsed by pandas. Will be created/overwritten on next save.", icon="ℹ️")
        df_inventory = pd.DataFrame(columns=CSV_COLUMNS)
    except Exception as e: 
        st.error(f"Error loading inventory from {CSV_FILE}: {e}", icon="🚨")
        df_inventory = pd.DataFrame(columns=CSV_COLUMNS)

search_query = st.text_input("Search for a book title in the inventory:", key="inventory_search_input")
if not df_inventory.empty:
    if search_query:
        mask = df_inventory["Title"].astype(str).str.contains(search_query, case=False, na=False)
        df_to_display = df_inventory[mask]
        if df_to_display.empty: st.caption(f"No books found matching '{search_query}'.")
        else: st.caption(f"Found {len(df_to_display)} match(es) for '{search_query}':")
    else:
        df_to_display = df_inventory
    st.dataframe(df_to_display, use_container_width=True, hide_index=True, key="inventory_df")
elif search_query:
    st.caption("Inventory is empty. Cannot search.")
else: 
    if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) == 0 : 
        pass 
    elif not os.path.exists(CSV_FILE):
        st.info(f"{CSV_FILE} does not exist. It will be created on the first successful scan.", icon="ℹ️")