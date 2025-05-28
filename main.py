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
import difflib # Using built-in difflib for string comparison
import hashlib

# ------------- PAGE CONFIG (MUST BE FIRST STREAMLIT COMMAND) -------------
st.set_page_config(page_title="📚 Book OCR: Fixed Set Analysis & Live View", layout="wide")

# ------------- PREDEFINED GROUND TRUTH & SHELF LETTERS (FOR FIXED SET ANALYSIS) -------------
IMAGE_GROUND_TRUTH = {
    "1.jpg": [
        {"title": "Microwave & Radar Engineering", "expected_row": 1, "expected_col": 1},
    ],
    "2.jpg": [
        {"title": "DIGITAL IMAGE PROCESSING", "expected_row": 1, "expected_col": 1},
        {"title": "Discrete Time Signal Processing", "expected_row": 1, "expected_col": 2},
        {"title": "DIGITAL COMMUNICATION", "expected_row": 1, "expected_col": 3},
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

ALL_DISTINCT_GT_TITLES = sorted(list(set(
    book["title"] for img_gt in IMAGE_GROUND_TRUTH.values() for book in img_gt
)))

TITLE_TO_SHELF_LETTER = { # Used for ALL images, including live camera if title matches
    title.lower().strip(): chr(ord('A') + i) for i, title in enumerate(ALL_DISTINCT_GT_TITLES)
}

# Update IMAGE_GROUND_TRUTH with systematic shelf letters
for img_id, books in IMAGE_GROUND_TRUTH.items():
    for book_info in books:
        normalized_title = book_info["title"].lower().strip()
        if normalized_title in TITLE_TO_SHELF_LETTER:
            book_info["shelf_letter"] = TITLE_TO_SHELF_LETTER[normalized_title]
        else: # This case should ideally not be hit if logic is correct
            new_letter = chr(ord('A') + len(TITLE_TO_SHELF_LETTER))
            TITLE_TO_SHELF_LETTER[normalized_title] = new_letter
            book_info["shelf_letter"] = new_letter
            st.warning(f"Dynamically added shelf letter '{new_letter}' for title '{book_info['title']}' from GT. Ensure all GT titles are covered initially.")


# ------------- APP CONFIG & INITIALIZATIONS -------------
# --- Gemini API Configuration ---
API_KEY_FROM_CODE = "AIzaSyAUild_NvkhyMTqf_qM41DaG7tutMCfXjE"  # <--- REPLACE THIS!!!
API_KEY = os.environ.get("GEMINI_API_KEY", API_KEY_FROM_CODE)
gemini_model, gemini_initialized_successfully, gemini_init_error_message = None, False, ""
# ... (Keep your Gemini init logic)
if API_KEY == "YOUR_ACTUAL_GEMINI_API_KEY" and API_KEY_FROM_CODE != "" and API_KEY_FROM_CODE not in [None, ""]:
    st.warning("⚠️ Please replace 'YOUR_ACTUAL_GEMINI_API_KEY' in the code or set GEMINI_API_KEY env var.")
    gemini_init_error_message = "Gemini API key is a placeholder."
elif not API_KEY:
    st.error("⛔ Gemini API Key is missing.")
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
TESSERACT_PATH_CONFIG = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
tesseract_configured = False
# ... (Keep your Tesseract init logic)
try:
    pytesseract.get_tesseract_version()
    tesseract_configured = True
    if os.name == 'nt' and os.path.exists(TESSERACT_PATH_CONFIG):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH_CONFIG
except pytesseract.TesseractNotFoundError:
    if os.name == 'nt' and os.path.exists(TESSERACT_PATH_CONFIG):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH_CONFIG
        try:
            pytesseract.get_tesseract_version(); tesseract_configured = True
        except: st.warning(f"⚠️ Tesseract at '{TESSERACT_PATH_CONFIG}' problem.")
    else: st.warning("⚠️ Tesseract not found in system PATH.")
except Exception as e: st.warning(f"⚠️ Tesseract check error: {e}")


# --- Session State Initialization ---
if 'last_processed_image_unique_id' not in st.session_state: st.session_state.last_processed_image_unique_id = None
if 'ocr_results_for_session_image' not in st.session_state: st.session_state.ocr_results_for_session_image = {}


# ------------- OCR & HELPER FUNCTIONS -------------
SIMILARITY_THRESHOLD = 0.80

def extract_titles_with_gemini(pil_image):
    # ... (Keep your existing extract_titles_with_gemini function - it's good)
    if not gemini_initialized_successfully or not gemini_model:
        return [{"error": gemini_init_error_message or "Gemini model not configured."}]
    temp_path = None
    try:
        prompt = (
            "Analyze the provided image of book spines.\n"
            "Identify each distinct book title visible.\n"
            "For each title, determine its physical location as row and column numbers (integers, starting from 1 for top/left).\n"
            "Return findings *only* as a Python list of dictionaries: `[{'title': 'Detected Title', 'row': 1, 'col': 1}, ...]`.\n"
            "If no titles are clear or decipherable, return an empty Python list `[]`."
        )
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            pil_image.save(temp_file.name, format="PNG")
            temp_path = temp_file.name
        if os.path.getsize(temp_path) == 0: return [{"error": "Empty image provided to Gemini"}]
        
        uploaded_file_response = genai.upload_file(path=temp_path)
        response = gemini_model.generate_content([prompt, uploaded_file_response])
        genai.delete_file(uploaded_file_response.name)
        
        raw_text_response = response.text.strip()
        try: # Robust parsing
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
                        item['row'] = int(item['row']) if isinstance(item['row'], int) and item['row'] is not None else 0
                        item['col'] = int(item['col']) if isinstance(item['col'], int) and item['col'] is not None else 0
                        if item['title'].strip() and item['title'].strip().lower() not in ["no_title_detected", "unknown_title", "n/a", ""]:
                            valid_items.append(item)
                return valid_items
            else: return [{"error": f"Unexpected Gemini format. Expected list, got: {type(parsed_response).__name__}", "response": raw_text_response}]
        except (ValueError, SyntaxError, TypeError) as e: return [{"error": f"Error parsing Gemini's structured response: {e}", "response": raw_text_response}]
    except Exception as e: return [{"error": f"Gemini API or processing error: {str(e)}"}]
    finally:
        if temp_path and os.path.exists(temp_path): os.remove(temp_path)


@st.cache_resource
def get_easyocr_reader():
    # ... (Keep your get_easyocr_reader function)
    try: return easyocr.Reader(['en'], gpu=False)
    except Exception as e: st.error(f"🚨 Failed to init EasyOCR: {e}.")
    return None

def calculate_ocr_accuracy_and_positions(ocr_outputs, ground_truth_for_image, ocr_method_name="OCR"):
    # ... (Keep your calculate_ocr_accuracy_and_positions function from the previous full code - it's designed for GT comparison)
    # This function remains unchanged as it's specific to when ground_truth_for_image is available.
    if not ground_truth_for_image:
        return {"metrics": {"Method": ocr_method_name, "message": "No ground truth for this image."}, "processed_ocr_for_display": []}

    true_positives_title = 0; false_positives_title = 0
    gt_titles_found_indices = set()
    gt_items_count = len(ground_truth_for_image)
    parsed_ocr_data = []

    if ocr_method_name == "Gemini":
        for item in ocr_outputs:
            if isinstance(item, dict) and "title" in item and item.get("title","").strip():
                parsed_ocr_data.append({
                    "detected_title_lower": item["title"].strip().lower(),
                    "detected_row": item.get("row", 0), "detected_col": item.get("col", 0),
                    "original_ocr_item": item })
    else:
        lines = []
        if isinstance(ocr_outputs, str): lines = [ln.strip() for ln in ocr_outputs.split('\n') if ln.strip()]
        elif isinstance(ocr_outputs, list): lines = [str(t).strip() for t in ocr_outputs if str(t).strip()]
        for line in lines:
            parsed_ocr_data.append({ "detected_title_lower": line.lower(), "detected_row": 0, "detected_col": 0, "original_ocr_item": line })
    
    total_ocr_detections = len(parsed_ocr_data)
    if not parsed_ocr_data:
        metrics = { "Method": ocr_method_name, "True Positives (Titles)": 0, "False Positives (Titles)": 0,
                    "False Negatives (Titles)": gt_items_count, "Total GT Book Instances": gt_items_count,
                    "Total OCR Detections": 0, "Precision (Titles)": "0.00%", "Recall (Titles)": "0.00%", "F1-Score (Titles)": "0.00%" }
        return {"metrics": metrics, "processed_ocr_for_display": []}

    for ocr_item in parsed_ocr_data:
        ocr_title_lower = ocr_item["detected_title_lower"]
        best_similarity, best_matching_gt_original_idx = -1.0, -1
        for original_gt_idx, gt_book in enumerate(ground_truth_for_image): # Iterate using original index
            gt_title_lower = gt_book["title"].lower()
            similarity = difflib.SequenceMatcher(None, ocr_title_lower, gt_title_lower).ratio()
            if similarity > best_similarity:
                best_similarity, best_matching_gt_original_idx = similarity, original_gt_idx
        
        if best_similarity >= SIMILARITY_THRESHOLD and best_matching_gt_original_idx != -1:
            true_positives_title += 1
            gt_titles_found_indices.add(best_matching_gt_original_idx)
            matched_gt_item = ground_truth_for_image[best_matching_gt_original_idx]
            ocr_item.update({ "is_correct_title": True, "matched_gt_title": matched_gt_item["title"],
                              "shelf_letter_assigned": matched_gt_item["shelf_letter"] })
            if ocr_method_name == "Gemini":
                ocr_item["is_correct_position"] = ( ocr_item["detected_row"] == matched_gt_item["expected_row"] and \
                                                    ocr_item["detected_col"] == matched_gt_item["expected_col"] )
            else: ocr_item["is_correct_position"] = "N/A"
        else:
            false_positives_title += 1
            ocr_item.update({ "is_correct_title": False, "matched_gt_title": "No Match",
                              "shelf_letter_assigned": "N/A", "is_correct_position": "N/A" })

    false_negatives_title = gt_items_count - len(gt_titles_found_indices)
    precision_title = true_positives_title / total_ocr_detections if total_ocr_detections > 0 else 0
    recall_title = true_positives_title / gt_items_count if gt_items_count > 0 else 0
    f1_title = 2 * (precision_title * recall_title) / (precision_title + recall_title) if (precision_title + recall_title) > 0 else 0

    metrics = { "Method": ocr_method_name, "True Positives (Titles)": true_positives_title,
                "False Positives (Titles)": false_positives_title, "False Negatives (Titles)": false_negatives_title,
                "Total GT Book Instances": gt_items_count, "Total OCR Detections": total_ocr_detections,
                "Precision (Titles)": f"{precision_title:.2%}", "Recall (Titles)": f"{recall_title:.2%}",
                "F1-Score (Titles)": f"{f1_title:.2%}" }
    if ocr_method_name == "Gemini":
        correct_positions = sum(1 for item in parsed_ocr_data if item.get("is_correct_title") and item.get("is_correct_position") == True)
        metrics["Correct Positions (of matched titles)"] = correct_positions
    return {"metrics": metrics, "processed_ocr_for_display": parsed_ocr_data}


# ------------- MAIN APP LOGIC -------------
st.title("📚 Book OCR: Fixed Set Analysis & Live View")

input_method = st.radio("Select Image Source:", ("Upload File (for Fixed Set Analysis)", "Live Webcam Capture (General OCR)"), horizontal=True, key="input_method_radio_main")

uploaded_image_pil = None
current_image_unique_id = None # Will be filename for uploads, or a hash/timestamp for camera
is_fixed_set_image = False
current_ground_truth_for_fixed_set = None

if input_method == "Upload File (for Fixed Set Analysis)":
    uploaded_file_buffer = st.file_uploader("Upload an image (1.jpg - 5.jpg for analysis, or any for general OCR)", type=["jpg", "jpeg", "png"], key="file_uploader_widget_main")
    if uploaded_file_buffer:
        uploaded_image_pil = Image.open(uploaded_file_buffer)
        current_image_unique_id = uploaded_file_buffer.name # Use filename as ID
        if current_image_unique_id in IMAGE_GROUND_TRUTH:
            is_fixed_set_image = True
            current_ground_truth_for_fixed_set = IMAGE_GROUND_TRUTH[current_image_unique_id]
        else:
            st.info(f"'{current_image_unique_id}' is not in the predefined set (1.jpg-5.jpg). General OCR will be performed without accuracy table.")

elif input_method == "Live Webcam Capture (General OCR)":
    img_file_buffer_cam = st.camera_input("Capture an image from your webcam", key="camera_input_widget_main")
    if img_file_buffer_cam:
        uploaded_image_pil = Image.open(img_file_buffer_cam)
        # Create a unique ID for camera captures, e.g., using a hash
        current_image_unique_id = f"cam_{hashlib.md5(uploaded_image_pil.tobytes()).hexdigest()[:8]}"
        is_fixed_set_image = False # Camera captures are not part of the fixed set for accuracy table

# --- Main Processing Block (only if new image) ---
if uploaded_image_pil and \
   (st.session_state.get('last_processed_image_unique_id') != current_image_unique_id or \
    st.session_state.get('last_processed_image_unique_id') is None):

    st.session_state.last_processed_image_unique_id = current_image_unique_id
    st.session_state.ocr_results_for_session_image = { # Reset results for new image
        "image_id": current_image_unique_id,
        "ocr_data": {}, # Stores raw and processed OCR outputs
        "accuracy_summary": [] # Only populated for fixed set images
    }

    st.image(uploaded_image_pil, caption=f"Processing: {current_image_unique_id}", width=400)
    cv_image_rgb = np.array(uploaded_image_pil.convert('RGB'))

    if is_fixed_set_image and current_ground_truth_for_fixed_set:
        st.sidebar.subheader(f"Ground Truth for {current_image_unique_id}")
        st.sidebar.markdown(f"**Expected Book Instances: {len(current_ground_truth_for_fixed_set)}**")
        for i, gt_item_display in enumerate(current_ground_truth_for_fixed_set):
            st.sidebar.caption(f"{i+1}. Shelf {gt_item_display.get('shelf_letter','N/A')}: {gt_item_display['title']} @ (R{gt_item_display['expected_row']}, C{gt_item_display['expected_col']})")
    elif is_fixed_set_image and not current_ground_truth_for_fixed_set: # Should not happen if logic is correct
         st.error("Mismatch: Image identified as fixed set but no GT loaded.")


    # --- Perform OCR for ALL image types ---
    all_ocr_metrics_for_fixed_set = []
    ocr_display_data_for_session = {}

    # --- Tesseract ---
    if tesseract_configured:
        with st.spinner("Tesseract is reading..."):
            start_time = time.time(); t_text = ""
            try: t_text = pytesseract.image_to_string(uploaded_image_pil)
            except Exception as e: t_text = f"Tesseract Error: {e}"
            t_time = time.time() - start_time
        if is_fixed_set_image:
            res_tess = calculate_ocr_accuracy_and_positions(t_text, current_ground_truth_for_fixed_set, "Tesseract")
            res_tess["metrics"]["Time (s)"] = f"{t_time:.2f}"
            all_ocr_metrics_for_fixed_set.append(res_tess["metrics"])
            ocr_display_data_for_session["Tesseract"] = {"raw": t_text, "processed": res_tess["processed_ocr_for_display"], "time": t_time}
        else:
            ocr_display_data_for_session["Tesseract"] = {"raw": t_text, "processed": [], "time": t_time} # No GT for general images
    else:
        if is_fixed_set_image: all_ocr_metrics_for_fixed_set.append({"Method":"Tesseract", "Status":"Not Configured", "Time (s)": "N/A"})
        ocr_display_data_for_session["Tesseract"] = {"raw": "Not Configured", "processed": [], "time": 0.0}


    # --- EasyOCR ---
    easyocr_reader = get_easyocr_reader()
    if easyocr_reader:
        with st.spinner("EasyOCR is reading..."):
            start_time = time.time(); e_text = ""
            try: e_list = easyocr_reader.readtext(cv_image_rgb, detail=0, paragraph=True); e_text = '\n'.join(e_list)
            except Exception as e: e_text = f"EasyOCR Error: {e}"
            e_time = time.time() - start_time
        if is_fixed_set_image:
            res_easy = calculate_ocr_accuracy_and_positions(e_text, current_ground_truth_for_fixed_set, "EasyOCR")
            res_easy["metrics"]["Time (s)"] = f"{e_time:.2f}"
            all_ocr_metrics_for_fixed_set.append(res_easy["metrics"])
            ocr_display_data_for_session["EasyOCR"] = {"raw": e_text, "processed": res_easy["processed_ocr_for_display"], "time": e_time}
        else:
            ocr_display_data_for_session["EasyOCR"] = {"raw": e_text, "processed": [], "time": e_time}
    else:
        if is_fixed_set_image: all_ocr_metrics_for_fixed_set.append({"Method":"EasyOCR", "Status":"Not Initialized", "Time (s)": "N/A"})
        ocr_display_data_for_session["EasyOCR"] = {"raw": "Not Initialized", "processed": [], "time": 0.0}

    # --- Gemini ---
    if gemini_initialized_successfully and gemini_model:
        with st.spinner("Gemini is analyzing..."):
            start_time = time.time(); g_data = []
            g_data = extract_titles_with_gemini(pil_image=uploaded_image_pil)
            g_time = time.time() - start_time
        
        is_gem_error = g_data and isinstance(g_data[0], dict) and "error" in g_data[0]
        if is_gem_error:
            error_msg_gem = g_data[0]['error']
            if is_fixed_set_image: all_ocr_metrics_for_fixed_set.append({"Method": "Gemini", "Time (s)": f"{g_time:.2f}", "Status": f"Error: {str(error_msg_gem)[:100]}"})
            ocr_display_data_for_session["Gemini"] = {"raw": f"Error: {error_msg_gem}", "response_if_error": g_data[0].get("response"), "processed": [], "time": g_time}
        else:
            if is_fixed_set_image:
                res_gem = calculate_ocr_accuracy_and_positions(g_data, current_ground_truth_for_fixed_set, "Gemini")
                res_gem["metrics"]["Time (s)"] = f"{g_time:.2f}"
                all_ocr_metrics_for_fixed_set.append(res_gem["metrics"])
                ocr_display_data_for_session["Gemini"] = {"raw": g_data, "processed": res_gem["processed_ocr_for_display"], "time": g_time}
            else: # General image, no GT comparison, just process for shelf letters
                processed_gemini_general = []
                for item in g_data:
                    if isinstance(item, dict) and item.get("title","").strip():
                        title_lower = item["title"].strip().lower()
                        shelf_letter = TITLE_TO_SHELF_LETTER.get(title_lower, "N/A (New Title)")
                        processed_gemini_general.append({
                            "detected_title_lower": title_lower,
                            "detected_row": item.get("row",0),
                            "detected_col": item.get("col",0),
                            "shelf_letter_assigned": shelf_letter,
                            "original_ocr_item": item
                        })
                ocr_display_data_for_session["Gemini"] = {"raw": g_data, "processed": processed_gemini_general, "time": g_time}
    else:
        status_msg = gemini_init_error_message or "Not Initialized"
        if is_fixed_set_image: all_ocr_metrics_for_fixed_set.append({"Method":"Gemini", "Status": status_msg, "Time (s)": "N/A"})
        ocr_display_data_for_session["Gemini"] = {"raw": status_msg, "processed": [], "time": 0.0}

    if is_fixed_set_image:
        st.session_state.ocr_results_for_session_image["accuracy_summary"] = all_ocr_metrics_for_fixed_set
    st.session_state.ocr_results_for_session_image["ocr_data"] = ocr_display_data_for_session


# --- Display Results (always displayed if available in session state for the current unique image ID) ---
if st.session_state.ocr_results_for_session_image and \
   st.session_state.ocr_results_for_session_image.get("image_id") == current_image_unique_id:

    st.header(f"OCR Results for: {current_image_unique_id}")

    # Display Accuracy Summary Table ONLY for fixed set images
    if is_fixed_set_image:
        st.subheader("📊 Accuracy & Performance Summary (Fixed Set)")
        summary_data = st.session_state.ocr_results_for_session_image.get("accuracy_summary", [])
        if summary_data:
            summary_df = pd.DataFrame(summary_data).fillna("N/A")
            cols_order = ["Method", "Time (s)", "Precision (Titles)", "Recall (Titles)", "F1-Score (Titles)",
                          "True Positives (Titles)", "False Positives (Titles)", "False Negatives (Titles)",
                          "Total GT Book Instances", "Total OCR Detections", "Status"]
            if "Correct Positions (of matched titles)" in summary_df.columns:
                 cols_order.insert(5, "Correct Positions (of matched titles)")
            display_cols = [col for col in cols_order if col in summary_df.columns]
            st.dataframe(summary_df[display_cols], hide_index=True, use_container_width=True)
        else: st.info("Accuracy summary data not available for this fixed set image.")
    else: # General image (live camera or non-fixed upload)
        st.subheader("⏱️ OCR Performance Times (General Image)")
        times_data = []
        for method, data in st.session_state.ocr_results_for_session_image.get("ocr_data", {}).items():
            times_data.append({"Method": method, "Time (s)": f"{data.get('time', 0.0):.2f}"})
        if times_data: st.dataframe(pd.DataFrame(times_data), hide_index=True)


    st.subheader("🔍 Detailed OCR Outputs & Shelf Assignments")
    ocr_data_to_show = st.session_state.ocr_results_for_session_image.get("ocr_data", {})

    for method_name_disp, data_disp in ocr_data_to_show.items():
        with st.expander(f"{method_name_disp} Details", expanded=False):
            st.caption(f"Response Time: {data_disp.get('time', 0.0):.2f} seconds")
            st.text("Raw Output:")
            if method_name_disp == "Gemini" and isinstance(data_disp["raw"], list) and data_disp.get("response_if_error") is None :
                st.json(data_disp["raw"], expanded=False)
            elif method_name_disp == "Gemini" and data_disp.get("response_if_error"): # Show raw error response
                st.code(f"Gemini Raw Error Response:\n{data_disp.get('response_if_error')}")
            else:
                st.text_area(f"{method_name_disp} Raw", str(data_disp["raw"]), height=100, disabled=True, key=f"{method_name_disp}_raw_disp_{current_image_unique_id}")
            
            st.text("Processed Detections & Mapping:")
            if data_disp["processed"]: # This will exist for general images too for Gemini
                df_proc_disp = pd.DataFrame(data_disp["processed"])
                
                # Define columns for display based on whether it's fixed set analysis or general
                proc_cols_to_display = ["detected_title_lower", "shelf_letter_assigned"]
                if is_fixed_set_image: # Add accuracy columns for fixed set
                    proc_cols_to_display.extend(["is_correct_title", "matched_gt_title"])
                
                if method_name_disp == "Gemini":
                    proc_cols_to_display.extend(["detected_row", "detected_col"])
                    if is_fixed_set_image: # Add positional accuracy for Gemini in fixed set
                        proc_cols_to_display.append("is_correct_position")
                
                # Ensure all selected columns actually exist in the dataframe before trying to display
                final_display_cols = [col for col in proc_cols_to_display if col in df_proc_disp.columns]
                if final_display_cols:
                    st.dataframe(df_proc_disp[final_display_cols], hide_index=True, key=f"{method_name_disp}_proc_disp_{current_image_unique_id}")
                else:
                    st.caption(f"No relevant processed columns to display for {method_name_disp}.")
            else:
                st.caption(f"No items processed or error for {method_name_disp}.")
elif not uploaded_image_pil:
    st.info("Upload an image or use the webcam to begin analysis.")