# pages/1_Home.py
import os
import tempfile
import streamlit as st
from pptx import Presentation
from search_utils import semantic_search
from azure_blob_utils import download_source_ppt_from_blob
from slide_renderer import extract_slide_structure
from utils import logger, get_env

st.set_page_config(page_title="1 - Home", layout="wide")
st.title("1 — Home: Enter prompt and load slides")

if "slides_catalog" not in st.session_state:
    st.session_state["slides_catalog"] = []  # list of slide_structs
if "selected_slides" not in st.session_state:
    st.session_state["selected_slides"] = []
if "preview_loaded" not in st.session_state:
    st.session_state["preview_loaded"] = False

prompt = st.text_area("Enter presentation prompt:", height=140)

col1, col2 = st.columns([3,1])
with col1:
    if st.button("Search dataset & Load Slides"):
        if not prompt.strip():
            st.error("Please enter a prompt.")
        else:
            with st.spinner("Searching and loading slides..."):
                raw_refs = semantic_search(prompt, top_k=10) or []
                if not raw_refs:
                    st.warning("No matches found in dataset.")
                else:
                    # Unique ppt names
                    ppt_names = sorted({r.get("ppt_name") for r in raw_refs if r.get("ppt_name")})
                    st.session_state["slides_catalog"] = []
                    for ppt_blob in ppt_names:
                        try:
                            local_ppt = os.path.join(tempfile.gettempdir(), ppt_blob.replace("/", "_"))
                            download_source_ppt_from_blob(ppt_blob, local_ppt)

                            # load ppt to know slide count
                            prs = Presentation(local_ppt)
                            for idx in range(len(prs.slides)):
                                try:
                                    slide_struct = extract_slide_structure(local_ppt, idx)
                                    # attach metadata
                                    slide_struct["ppt_blob"] = ppt_blob
                                    slide_struct["slide_id"] = f"{ppt_blob}_slide_{idx}"
                                    st.session_state["slides_catalog"].append(slide_struct)
                                except Exception as e:
                                    logger.exception(f"Failed extract slide {idx} from {ppt_blob}: {e}")
                        except Exception as e:
                            logger.exception(f"Failed to download/process {ppt_blob}: {e}")

                    if st.session_state["slides_catalog"]:
                        st.session_state["preview_loaded"] = True
                        st.success(f"Loaded {len(st.session_state['slides_catalog'])} slides from {len(ppt_names)} PPT(s).")
                        # navigate to selection
                        st.rerun()

with col2:
    st.write("Quick actions")
    if st.button("Go to Slide Selection") and st.session_state.get("slides_catalog"):
        st.switch_page("pages/2_🖼️_Slide_Selection.py")

st.markdown("---")
st.subheader("Loaded slide count: " + str(len(st.session_state.get("slides_catalog", []))))
st.info("After loading, go to Slide Selection (page 2) to pick slides.")
