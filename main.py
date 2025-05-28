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
# For potential string similarity if you implement Idea 2 later
# from Levenshtein import ratio as levenshtein_ratio # pip install python-Levenshtein
# import difflib

# ------------- PAGE CONFIG (MUST BE FIRST STREAMLIT COMMAND) -------------
st.set_page_config(page_title="📚 Advanced Book OCR & Inventory", layout="wide")

# ------------- APP CONFIG & INITIALIZATIONS -------------
# --- Gemini API Configuration ---
API_KEY_FROM_CODE = "AIzaSyAUild_NvkhyMTqf_qM41DaG7tutMCfXjE"  # <--- REPLACE THIS!!! e.g., "AIza..."
API_KEY = os.environ.get("GEMINI_API_KEY", API_KEY_FROM_CODE)

gemini_model = None
gemini_initialized_successfully = False
gemini_init_error_message = ""

if API_KEY == "YOUR_ACTUAL_GEMINI_API_KEY" and API_KEY_FROM_CODE != "": # Check if it's still the placeholder
    st.warning("⚠️ Please replace 'YOUR_ACTUAL_GEMINI_API_KEY' in the code with your real Gemini API key, or set the GEMINI_API_KEY environment variable.")
    gemini_init_error_message = "Gemini API key is a placeholder."
elif not API_KEY:
    st.error("⛔ Gemini API Key is missing. Please set it in the code or as an environment variable (GEMINI_API_KEY).")
    gemini_init_error_message = "Gemini API key is missing."
else:
    try:
        genai.configure(api_key=API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        gemini_initialized_successfully = True
    except Exception as e:
        gemini_init_error_message = f"Failed to initialize Gemini Model: {e}"
        st.error(f"🚫 {gemini_init_error_message} Gemini features will be disabled.")

# --- Tesseract Configuration ---
TESSERACT_PATH_CONFIG = r"C:\Program Files\Tesseract-OCR\tesseract.exe" # Windows default
# For other OS, Tesseract might be in PATH, or you might need different paths
# if not os.path.exists(TESSERACT_PATH_CONFIG) and os.name != 'nt':
#     TESSERACT_PATH_CONFIG = "tesseract" # Common on Linux/macOS if in PATH

tesseract_configured = False
if os.path.exists(TESSERACT_PATH_CONFIG) or (os.name != 'nt' and os.system("tesseract --version > /dev/null 2>&1") == 0) : # Check if tesseract command works
    if os.path.exists(TESSERACT_PATH_CONFIG):
         pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH_CONFIG
    tesseract_configured = True
else:
    st.warning(f"⚠️ Tesseract not found or not configured. Tesseract OCR will be skipped. Searched at: '{TESSERACT_PATH_CONFIG}'. Ensure Tesseract is installed and in your system PATH or update TESSERACT_PATH_CONFIG.")


# --- CSV File Configuration ---
CSV_FILE = "books_inventory.csv" # Changed name slightly for clarity
CSV_COLUMNS = ["Title", "Inventory_Count", "Detected_In_Current_Scan", "Estimated_Borrowed", "Matrix_Position", "Last_Accuracy_Rating"] # Added accuracy rating
if not os.path.exists(CSV_FILE):
    try:
        pd.DataFrame(columns=CSV_COLUMNS).to_csv(CSV_FILE, index=False)
    except Exception as e:
        st.error(f"🚨 Could not create or access {CSV_FILE}: {e}.")

if 'last_processed_image_id' not in st.session_state:
    st.session_state.last_processed_image_id = None
if 'ocr_times' not in st.session_state:
    st.session_state.ocr_times = {}
if 'accuracy_feedback' not in st.session_state:
    st.session_state.accuracy_feedback = {}


# ------------- OCR & HELPER FUNCTIONS -------------
def extract_titles_with_gemini(pil_image):
    if not gemini_initialized_successfully or not gemini_model:
        return [{"error": gemini_init_error_message if gemini_init_error_message else "Gemini model not configured or initialization failed."}]
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
            "7. Strive for accuracy. If a title is partially obscured or blurry, make your best guess or indicate uncertainty if the format allows, but prefer returning a guess over nothing if some text is legible."
        )
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            pil_image.save(temp_file.name, format="PNG")
            temp_path = temp_file.name
        if os.path.getsize(temp_path) == 0: return [{"title": "NO_TITLES_DETECTED (empty image)", "row":0, "col":0}] # Should be list of dicts
        
        uploaded_file_response = genai.upload_file(path=temp_path)
        response = gemini_model.generate_content([prompt, uploaded_file_response])
        genai.delete_file(uploaded_file_response.name) # Clean up Gemini storage
        
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
                        # Ensure row/col are integers, default to 0 if None or invalid
                        item['row'] = int(item['row']) if isinstance(item['row'], int) and item['row'] is not None else 0
                        item['col'] = int(item['col']) if isinstance(item['col'], int) and item['col'] is not None else 0
                        
                        # Filter out common non-titles
                        if item['title'].strip() and item['title'].strip().lower() not in ["no_title_detected", "unknown_title", "n/a", ""]:
                            valid_items.append(item)
                return valid_items
            else:
                # This means Gemini didn't return a list as requested.
                return [{"error": f"Unexpected Gemini format. Expected list of dicts, but got: {type(parsed_response).__name__}", "response": raw_text_response}]
        except (ValueError, SyntaxError, TypeError) as e:
            # This means the string from Gemini wasn't valid Python list/dict syntax
            return [{"error": f"Error parsing Gemini's structured response: {e}", "response": raw_text_response}]

    except Exception as e: # Catch other potential API errors or issues
        return [{"error": f"Gemini API or processing error: {str(e)}"}]
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@st.cache_resource
def get_easyocr_reader():
    try: return easyocr.Reader(['en'], gpu=False) # Consider gpu=True if you have a compatible GPU
    except Exception as e: st.error(f"🚨 Failed to initialize EasyOCR Reader: {e}. EasyOCR will be skipped.")
    return None

def process_and_save_to_csv(scanned_data_for_saving, accuracy_data):
    if not scanned_data_for_saving:
        # st.sidebar.caption("Auto-save: No new data to save.") # Can be too verbose
        return

    current_df_csv = pd.DataFrame(columns=CSV_COLUMNS) # Default empty
    try:
        if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
            current_df_csv = pd.read_csv(CSV_FILE)
            # Validate and fix columns
            missing_cols = [col for col in CSV_COLUMNS if col not in current_df_csv.columns]
            if missing_cols:
                st.warning(f"CSV file '{CSV_FILE}' is missing columns: {missing_cols}. Adding them.")
                for col in missing_cols:
                    default_val = 0 if col in ["Inventory_Count", "Detected_In_Current_Scan", "Estimated_Borrowed"] else ("N/A" if col == "Last_Accuracy_Rating" else "")
                    current_df_csv[col] = default_val
            current_df_csv = current_df_csv.reindex(columns=CSV_COLUMNS) # Ensure order and all columns present
        else: # File doesn't exist or is empty
            current_df_csv = pd.DataFrame(columns=CSV_COLUMNS)
    except pd.errors.EmptyDataError:
        st.info(f"'{CSV_FILE}' is empty. Initializing a new inventory.")
        current_df_csv = pd.DataFrame(columns=CSV_COLUMNS)
    except Exception as e:
        st.error(f"Error reading '{CSV_FILE}' for auto-save: {e}. Using a new DataFrame.")
        current_df_csv = pd.DataFrame(columns=CSV_COLUMNS)

    df_csv_to_update = current_df_csv.copy()
    if "Title" not in df_csv_to_update.columns: df_csv_to_update["Title"] = ""
    df_csv_to_update["Title"] = df_csv_to_update["Title"].astype(str)

    df_csv_to_update["_found_in_scan"] = False
    changes_made = False

    for title_from_scan, data_from_scan in scanned_data_for_saving.items():
        detected_count = data_from_scan["count"]
        matrix_positions_str = data_from_scan["matrix_position_str"]
        # Normalize title for matching (e.g., case-insensitive)
        normalized_title_scan = title_from_scan.strip().lower()

        # Find existing rows matching the normalized title
        existing_rows = df_csv_to_update[df_csv_to_update["Title"].str.strip().str.lower() == normalized_title_scan]

        if not existing_rows.empty:
            idx = existing_rows.index[0] # Take the first match
            
            # Ensure numeric columns are numeric before comparison/calculation
            for col_num in ["Inventory_Count", "Detected_In_Current_Scan", "Estimated_Borrowed"]:
                df_csv_to_update[col_num] = pd.to_numeric(df_csv_to_update[col_num], errors='coerce').fillna(0)

            old_inventory = int(df_csv_to_update.loc[idx, "Inventory_Count"])
            new_inventory = max(old_inventory, detected_count)

            # Check if any relevant data changed
            if (int(df_csv_to_update.loc[idx, "Detected_In_Current_Scan"]) != detected_count or
                new_inventory != old_inventory or
                str(df_csv_to_update.loc[idx, "Matrix_Position"]) != matrix_positions_str or
                (title_from_scan in accuracy_data and str(df_csv_to_update.loc[idx, "Last_Accuracy_Rating"]) != str(accuracy_data[title_from_scan]))):
                changes_made = True

            df_csv_to_update.loc[idx, "Inventory_Count"] = new_inventory
            df_csv_to_update.loc[idx, "Detected_In_Current_Scan"] = detected_count
            df_csv_to_update.loc[idx, "Estimated_Borrowed"] = new_inventory - detected_count
            df_csv_to_update.loc[idx, "Matrix_Position"] = matrix_positions_str
            if title_from_scan in accuracy_data:
                df_csv_to_update.loc[idx, "Last_Accuracy_Rating"] = accuracy_data[title_from_scan]
            df_csv_to_update.loc[idx, "_found_in_scan"] = True
        else: # New title
            changes_made = True
            new_row_dict = {col: "" for col in CSV_COLUMNS} # Initialize all columns
            new_row_dict.update({
                "Title": title_from_scan, "Inventory_Count": detected_count,
                "Detected_In_Current_Scan": detected_count, "Estimated_Borrowed": 0,
                "Matrix_Position": matrix_positions_str,
                "Last_Accuracy_Rating": accuracy_data.get(title_from_scan, "N/A")
            })
            new_row_df = pd.DataFrame([new_row_dict], columns=CSV_COLUMNS) # Ensure columns align
            new_row_df["_found_in_scan"] = True # Temporary marker
            df_csv_to_update = pd.concat([df_csv_to_update, new_row_df], ignore_index=True)

    # Process titles in CSV but not in current scan
    for idx, row in df_csv_to_update.iterrows():
        if not row["_found_in_scan"]:
            if int(pd.to_numeric(df_csv_to_update.loc[idx, "Detected_In_Current_Scan"], errors='coerce').fillna(0)) != 0:
                changes_made = True # It was detected before, now it's not
            df_csv_to_update.loc[idx, "Detected_In_Current_Scan"] = 0
            inventory_val = int(pd.to_numeric(df_csv_to_update.loc[idx, "Inventory_Count"], errors='coerce').fillna(0))
            df_csv_to_update.loc[idx, "Estimated_Borrowed"] = inventory_val
            # df_csv_to_update.loc[idx, "Matrix_Position"] = "Not seen in this scan" # Or keep last known
    
    if "_found_in_scan" in df_csv_to_update.columns:
        df_csv_to_update = df_csv_to_update.drop(columns=["_found_in_scan"])
    
    if changes_made:
        # Ensure all columns exist and fill NaNs appropriately before type conversion
        for col in CSV_COLUMNS:
            if col not in df_csv_to_update.columns:
                default_val = 0 if col in ["Inventory_Count", "Detected_In_Current_Scan", "Estimated_Borrowed"] else ("N/A" if col == "Last_Accuracy_Rating" else "")
                df_csv_to_update[col] = default_val
        
        df_csv_to_update.fillna({
            "Inventory_Count": 0, "Detected_In_Current_Scan": 0,
            "Estimated_Borrowed": 0, "Matrix_Position": "N/A", "Last_Accuracy_Rating": "N/A"
        }, inplace=True)

        for col_to_int in ["Inventory_Count", "Detected_In_Current_Scan", "Estimated_Borrowed"]:
            if col_to_int in df_csv_to_update.columns:
                 df_csv_to_update[col_to_int] = pd.to_numeric(df_csv_to_update[col_to_int], errors='coerce').fillna(0).astype(int)
        try:
            df_csv_to_update[CSV_COLUMNS].to_csv(CSV_FILE, index=False) # Save only defined columns
            st.success(f"✅ Inventory auto-updated and saved to '{CSV_FILE}'")
            st.session_state.inventory_df_display_key = time.time() # Force refresh of displayed table
        except Exception as e:
            st.error(f"🚨 Error auto-saving to '{CSV_FILE}': {e}")
    # else:
    #     st.sidebar.caption("Auto-save: No changes to inventory detected.")


# ------------- MAIN APP LOGIC -------------
st.title("📚 Advanced Book OCR & Inventory Dashboard")
st.markdown("Upload an image or use your webcam to detect book titles and manage your inventory. Provide feedback on OCR accuracy!")

# Initialize session state for accuracy feedback if not present for the current image
if st.session_state.last_processed_image_id not in st.session_state.accuracy_feedback:
    st.session_state.accuracy_feedback[st.session_state.last_processed_image_id] = {}


input_method = st.radio("Select Image Source:", ("Upload File", "Live Webcam Capture"), horizontal=True, key="input_method_radio")
uploaded_image_pil = None
current_image_unique_id = None # Will be file_id or timestamp

if input_method == "Upload File":
    uploaded_file_buffer = st.file_uploader("Upload an image of book spines", type=["jpg", "jpeg", "png"], key="file_uploader_widget")
    if uploaded_file_buffer:
        uploaded_image_pil = Image.open(uploaded_file_buffer)
        current_image_unique_id = uploaded_file_buffer.file_id
elif input_method == "Live Webcam Capture":
    img_file_buffer_cam = st.camera_input("Capture an image from your webcam", key="camera_input_widget")
    if img_file_buffer_cam:
        uploaded_image_pil = Image.open(img_file_buffer_cam)
        current_image_unique_id = img_file_buffer_cam.file_id # camera_input also provides file_id

# Only process if new image or first load
if uploaded_image_pil and \
   (st.session_state.get('last_processed_image_id') != current_image_unique_id or \
    st.session_state.get('last_processed_image_id') is None):

    # Reset/initialize for new image
    st.session_state.last_processed_image_id = current_image_unique_id if current_image_unique_id else f"ts_{time.time()}"
    st.session_state.ocr_times = {} # Reset times for new image
    current_img_feedback_key = st.session_state.last_processed_image_id
    if current_img_feedback_key not in st.session_state.accuracy_feedback:
         st.session_state.accuracy_feedback[current_img_feedback_key] = {}


    st.image(uploaded_image_pil, caption="Current Image for Processing", use_column_width=True)
    
    st.header("🔍 OCR Results (Full Image)")
    cv_image_rgb = np.array(uploaded_image_pil.convert('RGB')) # For EasyOCR
    
    # --- Tesseract OCR ---
    tesseract_full_text = "N/A"
    if tesseract_configured:
        st.subheader("🅰️ Tesseract OCR")
        with st.spinner("Tesseract is reading..."):
            start_time = time.time()
            try:
                tesseract_full_text = pytesseract.image_to_string(uploaded_image_pil)
                if not tesseract_full_text.strip(): tesseract_full_text = "No text detected by Tesseract."
            except Exception as e: tesseract_full_text = f"Tesseract Error: {e}"
            st.session_state.ocr_times['Tesseract'] = time.time() - start_time
        st.text_area("Tesseract Output (Full Image)", tesseract_full_text, height=100, key=f"tess_out_{current_image_unique_id}")
        st.caption(f"Response Time: {st.session_state.ocr_times.get('Tesseract', 0):.2f} seconds")
    else:
        st.subheader("🅰️ Tesseract OCR")
        st.info("Tesseract not configured or enabled.")

    # --- EasyOCR ---
    easyocr_full_text = "N/A"
    st.subheader("🇪 EasyOCR")
    easyocr_reader = get_easyocr_reader()
    if easyocr_reader:
        with st.spinner("EasyOCR is reading..."):
            start_time = time.time()
            try:
                easy_text_list = easyocr_reader.readtext(cv_image_rgb, detail=0, paragraph=True)
                easyocr_full_text = '\n'.join(easy_text_list)
                if not easyocr_full_text.strip(): easyocr_full_text = "No text detected by EasyOCR."
            except Exception as e: easyocr_full_text = f"EasyOCR Error: {e}"
            st.session_state.ocr_times['EasyOCR'] = time.time() - start_time
        st.text_area("EasyOCR Output (Full Image)", easyocr_full_text, height=100, key=f"easy_out_{current_image_unique_id}")
        st.caption(f"Response Time: {st.session_state.ocr_times.get('EasyOCR', 0):.2f} seconds")
    else:
        st.info("EasyOCR not initialized or enabled.")
    
    # --- Gemini OCR ---
    gemini_extracted_data = []
    st.subheader("💎 Gemini Vision API (Titles & Positions)")
    if gemini_initialized_successfully and gemini_model:
        with st.spinner("Gemini is analyzing the image... (this may take a moment)"):
            start_time = time.time()
            gemini_extracted_data = extract_titles_with_gemini(pil_image=uploaded_image_pil)
            st.session_state.ocr_times['Gemini'] = time.time() - start_time
        
        st.caption(f"Response Time: {st.session_state.ocr_times.get('Gemini', 0):.2f} seconds")

        if gemini_extracted_data:
            is_error_response = len(gemini_extracted_data) == 1 and isinstance(gemini_extracted_data[0], dict) and "error" in gemini_extracted_data[0]
            if is_error_response:
                st.warning(f"Gemini processing error: {gemini_extracted_data[0].get('error')}")
                if "response" in gemini_extracted_data[0]: st.code(f"Raw Gemini Response:\n{gemini_extracted_data[0]['response']}", language="json")
            else:
                st.markdown("**Extracted Items & Accuracy Feedback:**")
                has_valid_entries_for_feedback = False
                for idx, item in enumerate(gemini_extracted_data):
                    if isinstance(item, dict) and item.get("title"):
                        has_valid_entries_for_feedback = True
                        title = item.get('title', "N/A")
                        row_pos = item.get('row', 0)
                        col_pos = item.get('col', 0)
                        
                        feedback_key_prefix = f"feedback_{current_img_feedback_key}_{idx}"

                        with st.expander(f"'{title}' at A[{row_pos}x{col_pos}] - Rate Accuracy", expanded=False):
                            st.markdown(f"**Gemini Output:** `{title}` at `A[{row_pos}x{col_pos}]`")
                            
                            # User correction input
                            corrected_title = st.text_input("Corrected Title (if needed):", value=title, key=f"{feedback_key_prefix}_title")
                            # User rating
                            rating_options = ["N/A", "⭐ (Poor)", "⭐⭐ (Fair)", "⭐⭐⭐ (Good)", "⭐⭐⭐⭐ (Very Good)", "⭐⭐⭐⭐⭐ (Perfect)"]
                            current_rating = st.session_state.accuracy_feedback[current_img_feedback_key].get(title, {}).get("rating", "N/A")

                            selected_rating = st.selectbox("Rate Accuracy:", rating_options, 
                                                           index=rating_options.index(current_rating) if current_rating in rating_options else 0,
                                                           key=f"{feedback_key_prefix}_rating")

                            # Store feedback in session state
                            st.session_state.accuracy_feedback[current_img_feedback_key][title] = {
                                "original_gemini": title,
                                "corrected_by_user": corrected_title if corrected_title != title else None,
                                "rating": selected_rating,
                                "original_pos": f"A[{row_pos}x{col_pos}]"
                            }
                if not has_valid_entries_for_feedback and not is_error_response:
                    st.info("Gemini processed the image but found no valid titles/positions to display for feedback.")
        else: # Empty list from Gemini
            st.info("Gemini processed the image but returned no data (empty list). This might mean no books were confidently identified according to the prompt.")
    elif gemini_init_error_message: st.warning(f"Gemini not available: {gemini_init_error_message}.")
    else: st.warning("Gemini status unknown. OCR will not be performed.")

    # --- Aggregate and Save to CSV ---
    scanned_titles_data_for_csv = {}
    user_accuracy_ratings_for_save = {} # For saving the latest rating

    # Use the potentially corrected titles from feedback for aggregation
    # If no feedback given for an item, use original Gemini output
    
    processed_gemini_items = []
    if gemini_extracted_data and not (len(gemini_extracted_data) == 1 and "error" in gemini_extracted_data[0]):
        for idx, original_item in enumerate(gemini_extracted_data):
            if isinstance(original_item, dict) and "title" in original_item:
                feedback = st.session_state.accuracy_feedback.get(current_img_feedback_key, {}).get(original_item["title"], {})
                
                title_to_use = feedback.get("corrected_by_user") if feedback.get("corrected_by_user") else original_item["title"]
                rating_to_use = feedback.get("rating", "N/A")
                
                processed_gemini_items.append({
                    "title": title_to_use,
                    "row": original_item.get("row", 0),
                    "col": original_item.get("col", 0)
                })
                # Store the rating for the title_to_use for saving
                if title_to_use: # Ensure title is not empty
                    user_accuracy_ratings_for_save[title_to_use.strip()] = rating_to_use


    if processed_gemini_items:
        for item in processed_gemini_items:
            title = item.get("title", "Unknown Title").strip()
            row = item.get("row", 0)
            col = item.get("col", 0)
            if not title or title.lower() == "unknown title" or not isinstance(row, int) or not isinstance(col, int): # Row/Col 0 is allowed by prompt
                continue
            
            # Normalize the title for aggregation (e.g., title case)
            clean_title = ' '.join(word.capitalize() for word in title.split())
            if not clean_title: continue


            if clean_title not in scanned_titles_data_for_csv:
                scanned_titles_data_for_csv[clean_title] = {"count": 0, "positions_by_row": {}}
            
            scanned_titles_data_for_csv[clean_title]["count"] += 1
            if row not in scanned_titles_data_for_csv[clean_title]["positions_by_row"]:
                scanned_titles_data_for_csv[clean_title]["positions_by_row"][row] = []
            scanned_titles_data_for_csv[clean_title]["positions_by_row"][row].append(col)

        st.subheader("📊 Aggregated Data for Inventory (from Gemini, potentially user-corrected)")
        display_scan_data = []
        for title, data in scanned_titles_data_for_csv.items():
            position_strings = []
            for row_num, cols_in_row in sorted(data["positions_by_row"].items()):
                sorted_cols = sorted(list(set(cols_in_row)))
                if sorted_cols:
                    position_strings.append(f"A[{row_num},({','.join(map(str, sorted_cols))})]")
            final_position_str = "; ".join(position_strings) if position_strings else "Position N/A"
            display_scan_data.append({
                "Title": title, "Detected Count": data["count"], "Matrix Positions": final_position_str
            })
        
        if display_scan_data:
            st.dataframe(pd.DataFrame(display_scan_data), use_container_width=True, hide_index=True, key=f"agg_titles_df_{current_image_unique_id}")
        
        # Prepare data for saving (using the potentially corrected titles and their aggregated data)
        data_for_saving_to_csv = {}
        for title, data in scanned_titles_data_for_csv.items(): # title here is already clean_title
            position_strings = []
            for row_num, cols_in_row in sorted(data["positions_by_row"].items()):
                sorted_cols = sorted(list(set(cols_in_row)))
                if sorted_cols: position_strings.append(f"A[{row_num},({','.join(map(str, sorted_cols))})]")
            final_position_str = "; ".join(position_strings) if position_strings else "Position N/A"
            data_for_saving_to_csv[title] = {"count": data["count"], "matrix_position_str": final_position_str}
        
        # Auto-save
        process_and_save_to_csv(data_for_saving_to_csv, user_accuracy_ratings_for_save)
    
    elif uploaded_image_pil: # No processable items from Gemini, but an image was uploaded
        is_error_response_check = len(gemini_extracted_data) == 1 and isinstance(gemini_extracted_data[0], dict) and "error" in gemini_extracted_data[0]
        if is_error_response_check:
            pass # Error already shown
        elif not gemini_extracted_data: # Empty list was returned
            st.info("No processable book data (titles/positions) extracted by Gemini from the current image to update inventory.")
        else: # Some other unexpected format
            st.warning("Could not process titles for inventory due to unexpected Gemini response format after initial parsing.")


# ------------- Display Inventory Table -------------
st.divider()
st.header("📘 Book Inventory")

# Force table refresh if data was saved
df_inventory_display_key = st.session_state.get('inventory_df_display_key', time.time())

df_inventory = pd.DataFrame(columns=CSV_COLUMNS) # Default empty
if os.path.exists(CSV_FILE):
    try:
        df_inventory = pd.read_csv(CSV_FILE)
        if df_inventory.empty and os.path.getsize(CSV_FILE) == 0:
            st.info(f"Inventory file '{CSV_FILE}' is empty. Scan an image to populate.", icon="ℹ️")
        elif df_inventory.empty and os.path.getsize(CSV_FILE) > 0:
             st.warning(f"Inventory file '{CSV_FILE}' might be corrupted or only contains headers. Try deleting it if issues persist.", icon="⚠️")
        else:
            # Ensure all defined columns are present for display
            for col_csv in CSV_COLUMNS:
                if col_csv not in df_inventory.columns: df_inventory[col_csv] = "N/A" if col_csv == "Last_Accuracy_Rating" else ""
            df_inventory = df_inventory[CSV_COLUMNS] # Reorder/select
    except pd.errors.EmptyDataError:
        st.info(f"Inventory file '{CSV_FILE}' is empty or could not be parsed. It will be created/overwritten on the next successful scan.", icon="ℹ️")
    except Exception as e:
        st.error(f"Error loading inventory from '{CSV_FILE}': {e}", icon="🚨")

# Search/Filter
search_query = st.text_input("Search inventory by title:", key="inventory_search_input")
if not df_inventory.empty:
    df_to_display = df_inventory.copy()
    if search_query:
        mask = df_to_display["Title"].astype(str).str.contains(search_query, case=False, na=False)
        df_to_display = df_to_display[mask]
        if df_to_display.empty: st.caption(f"No books found in inventory matching '{search_query}'.")
        # else: st.caption(f"Displaying {len(df_to_display)} match(es) for '{search_query}':")

    st.dataframe(df_to_display, use_container_width=True, hide_index=True, key=f"inventory_df_{df_inventory_display_key}")
elif search_query:
    st.caption("Inventory is currently empty. Cannot perform search.")
else:
    if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) == 0 :
        pass # Message already shown
    elif not os.path.exists(CSV_FILE):
        st.info(f"Inventory file '{CSV_FILE}' does not exist. It will be created on the first successful scan.", icon="ℹ️")