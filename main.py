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
import hashlib # To create a unique ID for uploaded images

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
API_KEY_FROM_CODE = "AIzaSyAUild_NvkhyMTqf_qM41DaG7tutMCfXjE"  # <--- REPLACE THIS!!!
API_KEY = os.environ.get("GEMINI_API_KEY", API_KEY_FROM_CODE)
gemini_model, gemini_initialized_successfully, gemini_init_error_message = None, False, ""
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
if 'last_processed_image_key' not in st.session_state: st.session_state.last_processed_image_key = None
if 'ocr_results_for_image' not in st.session_state: st.session_state.ocr_results_for_image = {}

# ------------- OCR & HELPER FUNCTIONS -------------
SIMILARITY_THRESHOLD = 0.80

def extract_titles_with_gemini(pil_image):
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
        ) # Simplified prompt
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            pil_image.save(temp_file.name, format="PNG")
            temp_path = temp_file.name
        if os.path.getsize(temp_path) == 0: return [{"error": "Empty image provided to Gemini"}]
        
        uploaded_file_response = genai.upload_file(path=temp_path)
        response = gemini_model.generate_content([prompt, uploaded_file_response])
        genai.delete_file(uploaded_file_response.name)
        
        raw_text_response = response.text.strip()
        try:
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
    try: return easyocr.Reader(['en'], gpu=False)
    except Exception as e: st.error(f"🚨 Failed to init EasyOCR: {e}.")
    return None

def calculate_ocr_accuracy_and_positions(ocr_outputs, ground_truth_for_image, ocr_method_name="OCR"):
    if not ground_truth_for_image: # ground_truth_for_image is the list of GT book dicts for the current image
        return {"metrics": {"Method": ocr_method_name, "message": "No ground truth for this image."}, "processed_ocr_for_display": []}

    true_positives_title = 0
    false_positives_title = 0
    gt_titles_found_indices = set() # Tracks indices of GT items that have been matched

    # Each item in ground_truth_for_image is a dict for one expected book instance
    gt_items_count = len(ground_truth_for_image)

    parsed_ocr_data = [] # Will store: {"detected_title_lower": ..., "detected_row": ..., "detected_col": ...}
    if ocr_method_name == "Gemini":
        for item in ocr_outputs: # ocr_outputs is list of dicts from Gemini
            if isinstance(item, dict) and "title" in item and item.get("title","").strip():
                parsed_ocr_data.append({
                    "detected_title_lower": item["title"].strip().lower(),
                    "detected_row": item.get("row", 0),
                    "detected_col": item.get("col", 0),
                    "original_ocr_item": item # Keep original for reference if needed
                })
    else: # Tesseract or EasyOCR (ocr_outputs is a string)
        if isinstance(ocr_outputs, str):
            lines = [line.strip() for line in ocr_outputs.split('\n') if line.strip()]
            for line in lines:
                parsed_ocr_data.append({
                    "detected_title_lower": line.lower(),
                    "detected_row": 0, "detected_col": 0, # No structured pos from these OCRs here
                    "original_ocr_item": line
                })
    
    total_ocr_detections = len(parsed_ocr_data)

    # If OCR found nothing, but there was GT
    if not parsed_ocr_data:
        metrics = {
            "Method": ocr_method_name, "True Positives (Titles)": 0, "False Positives (Titles)": 0,
            "False Negatives (Titles)": gt_items_count, "Total GT Titles": gt_items_count,
            "Total OCR Detections": 0, "Precision (Titles)": "0.00%",
            "Recall (Titles)": "0.00%", "F1-Score (Titles)": "0.00%" }
        return {"metrics": metrics, "processed_ocr_for_display": []}

    # Match OCR detections to GT
    # Each ocr_item in parsed_ocr_data will get additional keys:
    # is_correct_title, matched_gt_title, shelf_letter_assigned, is_correct_position
    
    # Create a mutable list of GT indices to ensure one GT item isn't matched multiple times by different OCR items
    available_gt_indices = list(range(gt_items_count))

    for ocr_item in parsed_ocr_data:
        ocr_title_lower = ocr_item["detected_title_lower"]
        best_similarity = -1.0 # Ensure any positive similarity is better
        best_matching_gt_local_idx = -1 # Index within available_gt_indices
        best_matching_gt_original_idx = -1 # Index in the original ground_truth_for_image

        for current_available_idx, original_gt_idx in enumerate(available_gt_indices):
            gt_book = ground_truth_for_image[original_gt_idx]
            gt_title_lower = gt_book["title"].lower()
            
            similarity = difflib.SequenceMatcher(None, ocr_title_lower, gt_title_lower).ratio()

            if similarity > best_similarity:
                best_similarity = similarity
                best_matching_gt_local_idx = current_available_idx
                best_matching_gt_original_idx = original_gt_idx
        
        if best_similarity >= SIMILARITY_THRESHOLD and best_matching_gt_original_idx != -1:
            true_positives_title += 1
            gt_titles_found_indices.add(best_matching_gt_original_idx) # Mark this GT original index as found
            
            # Assign details from the matched GT item
            matched_gt_item = ground_truth_for_image[best_matching_gt_original_idx]
            ocr_item["is_correct_title"] = True
            ocr_item["matched_gt_title"] = matched_gt_item["title"]
            ocr_item["shelf_letter_assigned"] = matched_gt_item["shelf_letter"]
            
            if ocr_method_name == "Gemini":
                ocr_item["is_correct_position"] = (
                    ocr_item["detected_row"] == matched_gt_item["expected_row"] and
                    ocr_item["detected_col"] == matched_gt_item["expected_col"]
                )
            else:
                ocr_item["is_correct_position"] = "N/A" # Tesseract/EasyOCR don't provide structured pos here
            
            # Remove the matched GT item from further consideration for other OCR items (if strict 1-to-1 desired for FP calc)
            # For now, let's allow multiple OCR items to match same GT (for FP, it's about OCR items not GT items)
            # but gt_titles_found_indices tracks unique GTs found for recall.
        else:
            # This OCR item did not find a good match in the (remaining) GT
            false_positives_title += 1
            ocr_item["is_correct_title"] = False
            ocr_item["matched_gt_title"] = "No Match"
            ocr_item["shelf_letter_assigned"] = "N/A"
            ocr_item["is_correct_position"] = "N/A"

    false_negatives_title = gt_items_count - len(gt_titles_found_indices)
    
    precision_title = true_positives_title / total_ocr_detections if total_ocr_detections > 0 else 0
    recall_title = true_positives_title / gt_items_count if gt_items_count > 0 else 0
    f1_title = 2 * (precision_title * recall_title) / (precision_title + recall_title) if (precision_title + recall_title) > 0 else 0

    metrics = {
        "Method": ocr_method_name,
        "True Positives (Titles)": true_positives_title,
        "False Positives (Titles)": false_positives_title, # OCR items that didn't match any GT well
        "False Negatives (Titles)": false_negatives_title, # GT items that weren't matched by any OCR item
        "Total GT Book Instances": gt_items_count,
        "Total OCR Detections": total_ocr_detections,
        "Precision (Titles)": f"{precision_title:.2%}",
        "Recall (Titles)": f"{recall_title:.2%}",
        "F1-Score (Titles)": f"{f1_title:.2%}",
    }
    if ocr_method_name == "Gemini":
        correct_positions = sum(1 for item in parsed_ocr_data if item.get("is_correct_title") and item.get("is_correct_position") == True)
        metrics["Correct Positions (of matched titles)"] = correct_positions

    return {"metrics": metrics, "processed_ocr_for_display": parsed_ocr_data}

# ------------- MAIN APP LOGIC -------------
st.title("📚 Fixed Set Book OCR & Accuracy Analysis")
st.markdown("Upload one of the predefined images (1.jpg - 5.jpg) to see OCR performance.")

uploaded_file_buffer = st.file_uploader("Upload an image (1.jpg - 5.jpg)", type=["jpg", "jpeg", "png"], key="file_uploader_widget_fixed")

if uploaded_file_buffer:
    uploaded_image_pil = Image.open(uploaded_file_buffer)
    image_key_for_gt = uploaded_file_buffer.name # e.g., "1.jpg"

    if st.session_state.get('last_processed_image_key') != image_key_for_gt:
        st.session_state.last_processed_image_key = image_key_for_gt
        st.session_state.ocr_results_for_image = {
            "image_id": image_key_for_gt, "ocr_data": {}, "accuracy_summary": []
        }

        st.image(uploaded_image_pil, caption=f"Processing: {image_key_for_gt}", width=350)
        cv_image_rgb = np.array(uploaded_image_pil.convert('RGB'))
        current_ground_truth = IMAGE_GROUND_TRUTH.get(image_key_for_gt)

        if not current_ground_truth:
            st.error(f"No GT for '{image_key_for_gt}'. Check `IMAGE_GROUND_TRUTH`.")
            st.stop()

        st.sidebar.subheader(f"Ground Truth for {image_key_for_gt}")
        st.sidebar.markdown(f"**Expected Book Instances: {len(current_ground_truth)}**") # Display count
        for i, gt_item_display in enumerate(current_ground_truth):
            st.sidebar.caption(f"{i+1}. Shelf {gt_item_display.get('shelf_letter','N/A')}: {gt_item_display['title']} @ (R{gt_item_display['expected_row']}, C{gt_item_display['expected_col']})")

        all_ocr_metrics, ocr_display_data_dict = [], {}

        # --- Tesseract OCR ---
        if tesseract_configured:
            with st.spinner("Tesseract is reading..."):
                start_time = time.time(); tesseract_full_text = ""
                try: tesseract_full_text = pytesseract.image_to_string(uploaded_image_pil)
                except Exception as e: tesseract_full_text = f"Tesseract Error: {e}"
                t_time = time.time() - start_time
            res_tess = calculate_ocr_accuracy_and_positions(tesseract_full_text, current_ground_truth, "Tesseract")
            res_tess["metrics"]["Time (s)"] = f"{t_time:.2f}"
            all_ocr_metrics.append(res_tess["metrics"])
            ocr_display_data_dict["Tesseract"] = {"raw": tesseract_full_text, "processed": res_tess["processed_ocr_for_display"]}
        else: all_ocr_metrics.append({"Method":"Tesseract", "Status":"Not Configured", "Time (s)": "N/A"})


        # --- EasyOCR ---
        easyocr_reader = get_easyocr_reader()
        if easyocr_reader:
            with st.spinner("EasyOCR is reading..."):
                start_time = time.time(); easyocr_full_text = ""
                try:
                    easy_list = easyocr_reader.readtext(cv_image_rgb, detail=0, paragraph=True)
                    easyocr_full_text = '\n'.join(easy_list)
                except Exception as e: easyocr_full_text = f"EasyOCR Error: {e}"
                e_time = time.time() - start_time
            res_easy = calculate_ocr_accuracy_and_positions(easyocr_full_text, current_ground_truth, "EasyOCR")
            res_easy["metrics"]["Time (s)"] = f"{e_time:.2f}"
            all_ocr_metrics.append(res_easy["metrics"])
            ocr_display_data_dict["EasyOCR"] = {"raw": easyocr_full_text, "processed": res_easy["processed_ocr_for_display"]}
        else: all_ocr_metrics.append({"Method":"EasyOCR", "Status":"Not Initialized", "Time (s)": "N/A"})


        # --- Gemini OCR ---
        if gemini_initialized_successfully and gemini_model:
            with st.spinner("Gemini is analyzing..."):
                start_time = time.time(); gemini_extracted_data = []
                gemini_extracted_data = extract_titles_with_gemini(pil_image=uploaded_image_pil)
                g_time = time.time() - start_time
            
            is_gem_error = gemini_extracted_data and isinstance(gemini_extracted_data[0], dict) and "error" in gemini_extracted_data[0]
            if is_gem_error:
                error_msg_gem = gemini_extracted_data[0]['error']
                all_ocr_metrics.append({"Method": "Gemini", "Time (s)": f"{g_time:.2f}", "Status": f"Error: {str(error_msg_gem)[:100]}"})
                ocr_display_data_dict["Gemini"] = {"raw": f"Error: {error_msg_gem}", "processed": []}
            else:
                res_gem = calculate_ocr_accuracy_and_positions(gemini_extracted_data, current_ground_truth, "Gemini")
                res_gem["metrics"]["Time (s)"] = f"{g_time:.2f}"
                all_ocr_metrics.append(res_gem["metrics"])
                ocr_display_data_dict["Gemini"] = {"raw": gemini_extracted_data, "processed": res_gem["processed_ocr_for_display"]}
        else: all_ocr_metrics.append({"Method":"Gemini", "Status": gemini_init_error_message or "Not Initialized", "Time (s)": "N/A"})

        st.session_state.ocr_results_for_image["accuracy_summary"] = all_ocr_metrics
        st.session_state.ocr_results_for_image["ocr_data"] = ocr_display_data_dict

    # --- Display Results (from session state) ---
    if st.session_state.ocr_results_for_image and st.session_state.ocr_results_for_image.get("image_id") == image_key_for_gt:
        st.header(f"OCR Performance for: {image_key_for_gt}")
        st.subheader("📊 Accuracy & Performance Summary")
        if st.session_state.ocr_results_for_image["accuracy_summary"]:
            summary_df = pd.DataFrame(st.session_state.ocr_results_for_image["accuracy_summary"]).fillna("N/A")
            cols_order = ["Method", "Time (s)", "Precision (Titles)", "Recall (Titles)", "F1-Score (Titles)",
                          "True Positives (Titles)", "False Positives (Titles)", "False Negatives (Titles)",
                          "Total GT Book Instances", "Total OCR Detections", "Status"]
            if "Correct Positions (of matched titles)" in summary_df.columns:
                 cols_order.insert(5, "Correct Positions (of matched titles)")
            
            display_cols = [col for col in cols_order if col in summary_df.columns]
            st.dataframe(summary_df[display_cols], hide_index=True, use_container_width=True)

        st.subheader("🔍 Detailed OCR Outputs & Shelf Assignments")
        ocr_data_to_show = st.session_state.ocr_results_for_image.get("ocr_data", {})
        for method_name, data in ocr_data_to_show.items():
            with st.expander(f"{method_name} Details", expanded=False):
                st.text("Raw Output:")
                if isinstance(data["raw"], list) or isinstance(data["raw"], dict): # For Gemini
                    st.json(data["raw"], expanded=False)
                else: # For Tesseract/EasyOCR string output
                    st.text_area(f"{method_name} Raw", str(data["raw"]), height=100, disabled=True, key=f"{method_name}_raw_disp_{image_key_for_gt}")
                
                st.text("Processed Detections & Mapping:")
                if data["processed"]:
                    df_proc = pd.DataFrame(data["processed"])
                    proc_cols_order = ["detected_title_lower", "is_correct_title", "matched_gt_title", "shelf_letter_assigned"]
                    if method_name == "Gemini":
                        proc_cols_order.extend(["detected_row", "detected_col", "is_correct_position"])
                    
                    display_proc_cols = [col for col in proc_cols_order if col in df_proc.columns]
                    st.dataframe(df_proc[display_proc_cols], hide_index=True, key=f"{method_name}_proc_disp_{image_key_for_gt}")
                else:
                    st.caption(f"No items processed or error for {method_name}.")
else:
    st.info("Upload one of the specified images (1.jpg - 5.jpg) to begin analysis.")