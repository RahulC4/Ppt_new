# pages/2_🖼️_Slide_Selection.py
import streamlit as st
from utils import logger

st.set_page_config(page_title="2 - Slide Selection", layout="wide")
st.title("2 — Slide Selection (choose reference slides)")

slides = st.session_state.get("slides_catalog", [])
if not slides:
    st.warning("No slides loaded. Go to Home (page 1) and run a search.")
else:
    st.write("Select slides to use as design references. The number you select = number of generated slides.")
    cols = st.columns(3)
    for i, s in enumerate(slides):
        col = cols[i % 3]
        with col:
            st.image(s.get("png_path"), use_column_width=True)
            caption = f"{s.get('ppt_blob')} — slide {s.get('slide_index')}"
            st.caption(caption)
            key = f"sel_{s.get('slide_id')}"
            checked = st.checkbox("Select", key=key, value=(s.get("slide_id") in st.session_state.get("selected_slides", [])))
            if checked:
                if s["slide_id"] not in st.session_state["selected_slides"]:
                    st.session_state["selected_slides"].append(s["slide_id"])
            else:
                if s["slide_id"] in st.session_state["selected_slides"]:
                    st.session_state["selected_slides"].remove(s["slide_id"])

    st.markdown("---")
    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("Continue to Q&A"):
            if not st.session_state["selected_slides"]:
                st.error("Select at least one slide.")
            else:
                # build selected slide list to keep their full struct
                selected = [s for s in slides if s["slide_id"] in st.session_state["selected_slides"]]
                st.session_state["selected_slide_structs"] = selected
                st.session_state["answers_by_slide"] = {}  # will hold answers keyed by slide_id -> {shape_id: text}
                st.switch_page("pages/3_❓_QnA.py")

    with col2:
        if st.button("Back to Home"):
            st.switch_page("pages/1_Home.py")
