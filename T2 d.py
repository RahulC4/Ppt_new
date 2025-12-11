# pages/4_Generate_PPT.py
import os
import streamlit as st
from generate_ppt import generate_presentation
from azure_blob_utils import upload_ppt_to_blob
from utils import logger, now_ts

st.set_page_config(page_title="4 - Generate PPT", layout="wide")
st.title("4 — Generate & Download")

payload = st.session_state.get("generation_payload")
if not payload:
    st.warning("No generation payload found. Complete Q&A first.")
else:
    selected_slides = payload["selected_slides"]
    answers_map = payload["answers_map"]

    st.write("Generating final PPT from your selected slides and answers...")

    try:
        out_path = generate_presentation(selected_slides, answers_map)
        st.success("PPT generated successfully!")
        st.markdown(f"**File:** `{os.path.basename(out_path)}`")

        # Offer upload to blob (optional)
        if st.button("Upload to Azure Blob"):
            try:
                fname = os.path.basename(out_path)
                upload_ppt_to_blob(out_path, fname)
                st.success("Uploaded to blob container.")
            except Exception as e:
                logger.exception("Upload failed")
                st.error(f"Upload failed: {e}")

        # Download button
        try:
            with open(out_path, "rb") as f:
                st.download_button("⬇️ Download PPT", f, file_name=os.path.basename(out_path), mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")
        except Exception:
            st.error("Failed to open generated file for download.")
    except Exception as e:
        logger.exception("Generation failed")
        st.error(f"Failed to generate PPT: {e}")

    if st.button("Back to Home"):
        st.switch_page("pages/1_Home.py")
