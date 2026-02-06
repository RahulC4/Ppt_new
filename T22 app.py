# app.py  (acts as Home page)

import os
import sys
import tempfile
import streamlit as st
from pptx import Presentation

# --------------------------------------------------
# 🔑 FIX: Ensure backend/ is importable
# --------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

# --------------------------------------------------
# Backend imports (UNCHANGED)
# --------------------------------------------------
from backend.search_utils import collection, semantic_search
from backend.azure_blob_utils import download_source_ppt_from_blob
from backend.slide_renderer import extract_slide_structure
from backend.utils import logger

# --------------------------------------------------
# Streamlit config
# --------------------------------------------------
st.set_page_config(page_title="AI PPT Generator", layout="wide")
st.title("Step 1 — Start Your Presentation")

# --------------------------------------------------
# Session state init
# --------------------------------------------------
st.session_state.setdefault("slides_catalog", [])
st.session_state.setdefault("selected_slides", [])
st.session_state.setdefault("ppt_theme", "auto")

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def get_slide_title_from_chroma(ppt_name, slide_index):
    if ppt_name is None or slide_index is None:
        return None

    try:
        res = collection.get(
            where={
                "$and": [
                    {"ppt_name": ppt_name},
                    {"slide_index": slide_index}
                ]
            }
        )

        metas = res.get("metadatas", [])
        if metas and metas[0].get("title"):
            return metas[0]["title"].strip()

    except Exception:
        logger.exception("Failed to fetch slide title from Chroma")

    return None

# --------------------------------------------------
# UI Inputs
# --------------------------------------------------
prompt = st.text_area(
    "Enter presentation prompt:",
    height=120,
    placeholder="Example: Create a presentation about global design transformation"
)

theme = st.selectbox(
    "Select Presentation Theme",
    ["auto", "cognizant"],
    index=0
)
st.session_state["ppt_theme"] = theme

# --------------------------------------------------
# Main Action
# --------------------------------------------------
if st.button("Search dataset & Load Slides"):
    if not prompt.strip():
        st.error("Please enter a prompt.")
        st.stop()

    with st.spinner("Searching dataset and loading relevant slides..."):
        st.session_state["slides_catalog"] = []
        st.session_state["selected_slides"] = []

        # --------------------------------------------------
        # Semantic search ONLY (keyword mapping removed)
        # --------------------------------------------------
        refs = semantic_search(prompt, top_k=12)

        if not refs:
            st.warning("No relevant slides found.")
            st.stop()

        for r in refs:
            try:
                ppt_blob = r["ppt_name"]
                slide_index = r["slide_index"]

                local_ppt = os.path.join(
                    tempfile.gettempdir(),
                    ppt_blob.replace("/", "_")
                )

                if not os.path.exists(local_ppt):
                    download_source_ppt_from_blob(ppt_blob, local_ppt)

                slide_struct = extract_slide_structure(local_ppt, slide_index)

                slide_struct["ppt_blob"] = ppt_blob
                slide_struct["slide_id"] = r["slide_id"]

                st.session_state["slides_catalog"].append(slide_struct)

            except Exception as e:
                logger.exception(f"Failed loading slide: {e}")

        if not st.session_state["slides_catalog"]:
            st.warning("No slides loaded.")
            st.stop()

        st.success(
            f"Loaded {len(st.session_state['slides_catalog'])} reference slides"
        )

        # 👉 Navigate to slide selection
        st.switch_page("pages/2_🖼️_Slide_Selection.py")
