# pages/2_🖼️_Slide_Selection.py
import streamlit as st

st.title("🖼️ Select Slides as Design References")

slides = st.session_state.get("slides_catalog", [])

selected = []

cols = st.columns(3)
for i, slide in enumerate(slides):
    col = cols[i % 3]
    with col:
        st.image(slide["image"], use_column_width=True)
        if st.checkbox("Select", key=slide["slide_id"]):
            selected.append(slide)

st.session_state["selected_slides"] = selected

if st.button("Continue to Q&A"):
    if not selected:
        st.error("Select at least 1 slide.")
    else:
        st.switch_page("pages/3_❓_QnA.py")
