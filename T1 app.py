# app.py  (Home Page)

import os
import tempfile
import streamlit as st
from search_utils import semantic_search
from azure_blob_utils import download_source_ppt_from_blob
from slide_renderer import export_slides_to_png
from utils import logger, get_env

# ---------- Streamlit Config ----------
st.set_page_config(
    page_title="AI PPT Generator",
    layout="wide",
    page_icon="📊"
)

# ---------- Session State Init ----------
if "slides_catalog" not in st.session_state:
    st.session_state["slides_catalog"] = []   # all slide entries extracted from matched PPTs

if "matched_slides" not in st.session_state:
    st.session_state["matched_slides"] = []   # raw matched slides from semantic search

if "selected_slides" not in st.session_state:
    st.session_state["selected_slides"] = []  # slides user selects in Page 2

if "answers" not in st.session_state:
    st.session_state["answers"] = {}          # QA answers per slide

# ---------- PAGE UI ----------
st.title("🏠 AI PPT Generator – Home")
st.write("Enter your presentation prompt below to begin searching your PPT dataset.")

prompt = st.text_area("Enter prompt:", height=150)

if st.button("🔍 Search Slides"):
    if not prompt.strip():
        st.error("Please enter a prompt.")
    else:
        with st.spinner("Searching dataset..."):

            # Step 1 — semantic search
            raw_refs = semantic_search(prompt, top_k=5)
            refs = raw_refs or []

            if not refs:
                st.warning("No matching slide content found in your PPT dataset.")
                st.stop()

            # Step 2 — Find all PPT files referenced
            ppt_names = sorted({r["ppt_name"] for r in refs})

            # Store them
            st.session_state["slides_catalog"] = []

            # Step 3 — Download each PPT → Render slides to PNG → Save paths
            for ppt_blob in ppt_names:
                try:
                    # Download source ppt to temp file
                    local_path = os.path.join(
                        tempfile.gettempdir(),
                        ppt_blob.replace("/", "_")
                    )
                    download_source_ppt_from_blob(ppt_blob, local_path)

                    # Export slides as PNG images using PowerPoint COM
                    png_list = export_slides_to_png(local_path)

                    for idx, png_path in enumerate(png_list):
                        st.session_state["slides_catalog"].append({
                            "ppt_path": local_path,
                            "slide_index": idx,
                            "slide_id": f"{ppt_blob}_slide_{idx}",
                            "image": png_path,
                            "ppt_blob": ppt_blob,
                        })

                except Exception as e:
                    logger.exception(f"Failed to process PPT {ppt_blob}")
                    st.error(f"Failed loading PPT: {ppt_blob}")

        # When everything is ready → navigate to Slide Selection page
        st.success(f"Found {len(st.session_state['slides_catalog'])} slides.")
        st.switch_page("pages/2_🖼️_Slide_Selection.py")
