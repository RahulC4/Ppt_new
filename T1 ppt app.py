# pages/4_📥_Generated_PPTs.py
import streamlit as st
from generate_ppt import generate_presentation_from_selected
from utils import now_ts

st.title("📥 Download Generated PPT")

slides = st.session_state.get("selected_slides", [])
answers = st.session_state.get("answers", {})

# Convert answers into replacement dict format
repl_map = {}
for slide in slides:
    sid = slide["slide_id"]
    original_text = "Placeholder original text"

    new_text = "\n".join(answers.get(sid, []))
    repl_map[sid] = {"raw_replacements": {original_text: new_text}}

ppt_path = generate_presentation_from_selected(slides, repl_map)

st.success("PPT created successfully!")

with open(ppt_path, "rb") as f:
    st.download_button("Download PPT", f, file_name="generated.pptx")
