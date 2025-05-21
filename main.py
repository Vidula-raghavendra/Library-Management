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
import ast # For safely evaluating string representation of list

# ------------- PAGE CONFIG (MUST BE FIRST STREAMLIT COMMAND) -------------
st.set_page_config(page_title="📚 Book OCR Dashboard", layout="wide")

# ------------- APP CONFIG & INITIALIZATIONS -------------
# --- Gemini API Configuration ---
# IMPORTANT: REPLACE THE LINE BELOW WITH YOUR ACTUAL GEMINI API KEY
# OR SET THE "GEMINI_API_KEY" ENVIRONMENT VARIABLE
API_KEY_FROM_CODE = ""  # <--- REPLACE THIS!!!
API_KEY = os.environ.get("GEMINI_API_KEY", API_KEY_FROM_CODE)

gemini_model = None
gemini_initialized_successfully = False
gemini_init_error_message = ""

if API_KEY == "YOUR_ACTUAL_GEMINI_API_KEY" and API_KEY != "": # Check if it's still the placeholder
    st.warning("⚠️ Please replace 'YOUR_ACTUAL_GEMINI_API_KEY' in the code with your real Gemini API key, or set the GEMINI_API_KEY environment variable for better security.")
    gemini_init_error_message = "Gemini API key is a placeholder."
elif not API_KEY:
    st.error("⛔ Gemini API Key is missing. Please set it in the code or as an environment variable (GEMINI_API_KEY). Gemini features will be disabled.")
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
# For other OS or custom paths, adjust or use environment variables
# TESSERACT_PATH_CONFIG = os.environ.get("TESSERACT_CMD", TESSERACT_PATH_CONFIG)
tesseract_configured = False
if os.path.exists(TESSERACT_PATH_CONFIG):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH_CONFIG
    tesseract_configured = True
else:
    st.warning(f"⚠️ Tesseract executable not found at '{TESSERACT_PATH_CONFIG}'. Tesseract OCR may not work. Please install Tesseract and/or update the path in the script.")

# --- CSV File Configuration ---
CSV_FILE = "books.csv"
CSV_COLUMNS = ["Title", "Inventory_Count", "Detected_In_Current_Scan", "Estimated_Borrowed", "Scan_Order_Index"]
if not os.path.exists(CSV_FILE):
    try:
        pd.DataFrame(columns=CSV_COLUMNS).to_csv(CSV_FILE, index=False)
    except Exception as e:
        st.error(f"🚨 Could not create or access {CSV_FILE}: {e}.")

# ------------- OCR & HELPER FUNCTIONS -------------
def extract_titles_with_gemini(pil_image):
    """Extracts all book titles from the full image using Gemini and returns a list of strings."""
    if not gemini_initialized_successfully or not gemini_model:
        # Return a list with the specific error message
        return [gemini_init_error_message if gemini_init_error_message else "Gemini model not configured or initialization failed."]
    
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            pil_image.save(temp_file.name, format="PNG")
            temp_path = temp_file.name

        if os.path.getsize(temp_path) == 0:
            return ["NO_TITLES_DETECTED (empty image)"]

        uploaded_file_response = genai.upload_file(path=temp_path)

        prompt = (
            "You are an expert at reading book spines from images. "
            "From the provided image, extract all clearly visible book titles written on the spines. "
            "Return these titles *only* as a Python list of strings. For example: `['Title One', 'Another Book Title', 'The Third Spine']`. "
            "If multiple copies of the exact same title are visible, list it multiple times, once for each visible copy. "
            "If no book titles are clearly visible or decipherable, return an empty Python list `[]`."
        )
        response = gemini_model.generate_content([prompt, uploaded_file_response])
        
        genai.delete_file(uploaded_file_response.name) 

        raw_text_response = response.text.strip()

        try:
            if raw_text_response.startswith("```python"):
                raw_text_response = raw_text_response.removeprefix("```python").strip()
            elif raw_text_response.startswith("```"):
                 raw_text_response = raw_text_response.removeprefix("```").strip()
            
            if raw_text_response.endswith("```"):
                raw_text_response = raw_text_response.removesuffix("```").strip()

            titles_list = ast.literal_eval(raw_text_response)
            if isinstance(titles_list, list):
                cleaned_titles = []
                for title in titles_list:
                    if isinstance(title, str) and title.strip() and title.strip().lower() not in ["no_title_detected", "unknown_title"]:
                        cleaned_titles.append(title.strip())
                return cleaned_titles if cleaned_titles else [] 
            else:
                if isinstance(raw_text_response, str) and raw_text_response and raw_text_response.lower() not in ["no_title_detected", "unknown_title", "[]", ""]:
                     return [f"Unexpected Gemini format: {raw_text_response}"] 
                return [] 
        except (ValueError, SyntaxError, TypeError) as e:
            if raw_text_response and raw_text_response.lower() not in ["no_title_detected", "unknown_title", "[]", ""]:
                 st.info(f"Gemini did not return a list, treating response as potential title(s): '{raw_text_response}' (Error: {e})")
                 return [line.strip() for line in raw_text_response.splitlines() if line.strip()]
            return [f"Error parsing Gemini list: {e}. Response: {raw_text_response}"]

    except Exception as e:
        print(f"Gemini OCR Error: {str(e)}") # Log to console for debugging
        return [f"Gemini API Error: {str(e)}"]
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@st.cache_resource
def get_easyocr_reader():
    try:
        return easyocr.Reader(['en'], gpu=False)
    except Exception as e:
        st.error(f"🚨 Failed to initialize EasyOCR Reader: {e}. EasyOCR will not work.")
        return None

# ------------- STREAMLIT UI -------------
st.title("📚 Book Spine OCR Extractor & Inventory")
st.caption("Upload an image of book spines. OCR will be performed on the full image.")

# --- File Uploader ---
uploaded_file = st.file_uploader("📤 Upload a book spine image (JPG/PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    pil_image = Image.open(uploaded_file)
    st.image(pil_image, caption="Uploaded Image", use_column_width=True)

    st.header("🔍 OCR Results (Full Image)")
    cv_image_rgb = np.array(pil_image.convert('RGB'))
    ocr_results = {"tesseract": "N/A", "easyocr": "N/A", "gemini_titles": []}

    with st.spinner("Performing OCR on the image... (this may take a while)"):
        if tesseract_configured:
            try:
                tess_text = pytesseract.image_to_string(pil_image)
                ocr_results["tesseract"] = tess_text if tess_text.strip() else "No text detected by Tesseract."
            except Exception as e:
                ocr_results["tesseract"] = f"Tesseract Error: {e}"
        else:
            ocr_results["tesseract"] = "Tesseract not configured."
        st.text_area("Tesseract Output", ocr_results["tesseract"], height=100)

        easyocr_reader = get_easyocr_reader()
        if easyocr_reader:
            try:
                easy_text_list = easyocr_reader.readtext(cv_image_rgb, detail=0, paragraph=True)
                easy_text = '\n'.join(easy_text_list)
                ocr_results["easyocr"] = easy_text if easy_text.strip() else "No text detected by EasyOCR."
            except Exception as e:
                ocr_results["easyocr"] = f"EasyOCR Error: {e}"
        else:
            ocr_results["easyocr"] = "EasyOCR not initialized."
        st.text_area("EasyOCR Output", ocr_results["easyocr"], height=100)
        
        if gemini_initialized_successfully and gemini_model:
            gemini_titles_list = extract_titles_with_gemini(pil_image)
            ocr_results["gemini_titles"] = gemini_titles_list
            if gemini_titles_list:
                st.subheader("💎 Gemini Extracted Titles:")
                # Filter out known error messages before displaying
                displayable_gemini_titles = [
                    t for t in gemini_titles_list 
                    if not any(t.startswith(err_prefix) for err_prefix in ["Gemini API Error:", "Error parsing Gemini list:", "Unexpected Gemini format:"]) and \
                       t not in ["NO_TITLES_DETECTED (empty image)", gemini_init_error_message, "Gemini model not configured or initialization failed."]]
                
                if displayable_gemini_titles:
                    for i, title in enumerate(displayable_gemini_titles):
                        st.markdown(f"- {title}")
                elif any(err in str(gemini_titles_list) for err in ["Gemini API Error:", "Error parsing Gemini list:", "Unexpected Gemini format:", gemini_init_error_message]):
                     st.warning(f"Gemini returned an error or unexpected format: {gemini_titles_list}")
                else:
                     st.info("Gemini processed the image but did not detect any distinct book titles or returned an empty list.")
            else: # Empty list returned from extract_titles_with_gemini
                st.info("Gemini processed the image but did not detect any distinct book titles or returned an empty list.")

        elif gemini_init_error_message: # If Gemini failed to initialize earlier
             st.warning(f"Gemini not configured: {gemini_init_error_message}. Cannot extract titles with Gemini.")
             ocr_results["gemini_titles"] = [gemini_init_error_message] # Store error for processing logic
        else: # Should not happen if logic is correct, but as a fallback
             st.warning("Gemini status unknown. Cannot extract titles with Gemini.")
             ocr_results["gemini_titles"] = ["Gemini status unknown"]


    # --- Prepare Data for CSV based on Gemini's output ---
    scanned_titles_data_for_csv = {}
    gemini_output_titles = ocr_results.get("gemini_titles", [])
    
    # Define a list of known error messages or prefixes to filter out
    known_error_indicators = [
        "Gemini API Error:", 
        "Error parsing Gemini list:",
        "Gemini model not configured or initialization failed.",
        "Gemini API key is a placeholder.",
        "Gemini API key is missing.",
        "Failed to initialize Gemini Model", # Prefix
        "Unexpected Gemini format:",
        "NO_TITLES_DETECTED (empty image)",
        "Gemini status unknown"
    ]
    if gemini_init_error_message and gemini_init_error_message not in known_error_indicators: # Add specific init error if not generic
        known_error_indicators.append(gemini_init_error_message)


    valid_gemini_titles = []
    for t in gemini_output_titles:
        is_error = False
        for indicator in known_error_indicators:
            if indicator in t: # Use 'in' for prefixes or full matches
                is_error = True
                break
        if not is_error and t.strip(): # Also ensure it's not just whitespace
            valid_gemini_titles.append(t)


    if valid_gemini_titles:
        for idx, title_from_scan in enumerate(valid_gemini_titles):
            clean_title = ' '.join(word.capitalize() for word in title_from_scan.split())
            if clean_title not in scanned_titles_data_for_csv:
                scanned_titles_data_for_csv[clean_title] = {"count": 0, "indices": []}
            scanned_titles_data_for_csv[clean_title]["count"] += 1
            scanned_titles_data_for_csv[clean_title]["indices"].append(idx + 1)

        st.subheader("📊 Aggregated Gemini Titles for Inventory")
        display_scan_data = []
        for title, data in scanned_titles_data_for_csv.items():
            display_scan_data.append({
                "Title": title, 
                "Detected Count": data["count"], 
                "Scan Order Indices": ", ".join(map(str, data["indices"]))
            })
        if display_scan_data:
            st.dataframe(pd.DataFrame(display_scan_data), use_container_width=True, hide_index=True)
        # No "else" here, as the message for no valid titles is handled by the next block
    
    # This message will show if valid_gemini_titles is empty
    if not valid_gemini_titles and uploaded_file: # Only show if a file was uploaded
        if any(err_indicator in str(gemini_output_titles) for err_indicator in known_error_indicators):
             st.warning("Could not process titles for inventory due to Gemini configuration issues or errors during extraction.")
        else:
             st.info("No valid book titles were extracted by Gemini to process for inventory.")


    # --- Save to CSV Button & Logic ---
    # Disable button if there are no valid titles to save
    disable_save_button = not bool(scanned_titles_data_for_csv) 
    if st.button("💾 Process and Save Gemini Titles to CSV", type="primary", disabled=disable_save_button):
        try:
            if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
                df_csv = pd.read_csv(CSV_FILE)
                for col in CSV_COLUMNS:
                    if col not in df_csv.columns: # Add missing columns with default values
                        df_csv[col] = 0 if col in ["Inventory_Count", "Detected_In_Current_Scan", "Estimated_Borrowed"] else ""
                df_csv = df_csv.reindex(columns=CSV_COLUMNS) # Ensure correct order and fill missing from reindex
            else:
                df_csv = pd.DataFrame(columns=CSV_COLUMNS)
        except Exception as e:
            st.error(f"Error reading {CSV_FILE}: {e}")
            df_csv = pd.DataFrame(columns=CSV_COLUMNS) 

        df_csv["_found_in_scan"] = False 

        for title_from_scan, data_from_scan in scanned_titles_data_for_csv.items():
            detected_count = data_from_scan["count"]
            scan_indices_str = ", ".join(map(str,sorted(data_from_scan["indices"])))
            existing_rows = df_csv[df_csv["Title"].str.lower() == title_from_scan.lower()]

            if not existing_rows.empty:
                idx = existing_rows.index[0]
                
                old_inventory_val = df_csv.loc[idx, "Inventory_Count"]
                old_inventory = pd.to_numeric(old_inventory_val, errors='coerce')
                if pd.isna(old_inventory): 
                    old_inventory = 0
                else:
                    old_inventory = int(old_inventory)

                new_inventory = max(old_inventory, detected_count)
                df_csv.loc[idx, "Inventory_Count"] = new_inventory
                df_csv.loc[idx, "Detected_In_Current_Scan"] = detected_count
                df_csv.loc[idx, "Estimated_Borrowed"] = new_inventory - detected_count
                df_csv.loc[idx, "Scan_Order_Index"] = scan_indices_str
                df_csv.loc[idx, "_found_in_scan"] = True
            else:
                new_row_dict = {col: "" for col in CSV_COLUMNS} # Initialize with defaults
                new_row_dict.update({
                    "Title": title_from_scan,
                    "Inventory_Count": detected_count,
                    "Detected_In_Current_Scan": detected_count,
                    "Estimated_Borrowed": 0,
                    "Scan_Order_Index": scan_indices_str,
                })
                new_row_dict["_found_in_scan"] = True # Add temp column
                
                new_row_df = pd.DataFrame([new_row_dict])
                df_csv = pd.concat([df_csv, new_row_df], ignore_index=True)


        for idx, row in df_csv.iterrows():
            if not row["_found_in_scan"]:
                df_csv.loc[idx, "Detected_In_Current_Scan"] = 0
                
                inventory_val_on_row = df_csv.loc[idx, "Inventory_Count"]
                inventory_val = pd.to_numeric(inventory_val_on_row, errors='coerce')
                if pd.isna(inventory_val):
                    inventory_val = 0
                else:
                    inventory_val = int(inventory_val)
                
                df_csv.loc[idx, "Estimated_Borrowed"] = inventory_val
                df_csv.loc[idx, "Scan_Order_Index"] = "Not seen in this scan"
        
        if "_found_in_scan" in df_csv.columns:
            df_csv = df_csv.drop(columns=["_found_in_scan"])
        
        df_csv = df_csv.fillna({
            "Inventory_Count": 0, 
            "Detected_In_Current_Scan": 0, 
            "Estimated_Borrowed": 0, 
            "Scan_Order_Index": ""
        })
        for col_to_int in ["Inventory_Count", "Detected_In_Current_Scan", "Estimated_Borrowed"]:
            if col_to_int in df_csv.columns:
                 df_csv[col_to_int] = pd.to_numeric(df_csv[col_to_int], errors='coerce').fillna(0).astype(int)

        try:
            df_csv.to_csv(CSV_FILE, index=False)
            st.success(f"✅ Book data processed and saved to {CSV_FILE}!")
            st.rerun() 
        except Exception as e:
            st.error(f"🚨 Error saving to {CSV_FILE}: {e}")

# ------------- Display Table -------------
st.divider()
st.subheader("📘 Saved Book Titles Inventory")
if os.path.exists(CSV_FILE):
    try:
        df_display = pd.read_csv(CSV_FILE)
        if not df_display.empty:
            for col in CSV_COLUMNS: # Ensure all columns for display
                if col not in df_display.columns:
                    df_display[col] = "" 
            df_display = df_display[CSV_COLUMNS] 
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info(f"{CSV_FILE} is empty. Upload an image and save results.")
    except pd.errors.EmptyDataError:
        st.info(f"{CSV_FILE} is empty or cannot be read properly.")
    except Exception as e:
        st.error(f"Error loading CSV for display: {e}")
else:
    st.info(f"{CSV_FILE} not found. Upload an image and save results to create it.")