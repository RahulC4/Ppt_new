# app.py (updated)
import os
import tempfile
import streamlit as st
from datetime import datetime
from pptx import Presentation
from utils import logger, get_env, now_ts, text_client
from search_utils import semantic_search
from azure_blob_utils import (
    upload_source_ppt_to_blob,
    list_source_ppt_blobs,
    delete_source_ppt_from_blob,
    download_source_ppt_from_blob,
)
from ingestion_chroma import process_blob as ingest_process_blob, delete_ppt_from_chroma
from slide_extractor import download_blob_to_local, extract_slides_info_from_ppt
from generate_ppt import generate_presentation_from_selected

st.set_page_config(page_title="AI PPT Generator", layout="wide", page_icon="📊")

# session state init
if "generated_ppts" not in st.session_state:
    st.session_state["generated_ppts"] = []
if "preview_slides" not in st.session_state:
    st.session_state["preview_slides"] = []  # list of slide_info dicts
if "selected_slide_ids" not in st.session_state:
    st.session_state["selected_slide_ids"] = []
if "answers_by_slide" not in st.session_state:
    st.session_state["answers_by_slide"] = {}
if "mode" not in st.session_state:
    st.session_state["mode"] = "search"  # modes: search -> select -> qna -> generate

st.title("📊 AI PowerPoint Generator (Select & Clone Mode)")

SIMILARITY_THRESHOLD = float(get_env("SIMILARITY_THRESHOLD", "1.1"))

# Sidebar: upload & manage dataset
with st.sidebar:
    st.subheader("Upload sample PPTs (knowledge base)")
    uploaded_files = st.file_uploader("Upload .pptx files:", type=["pptx"], accept_multiple_files=True)
    if st.button("Add to KB") and uploaded_files:
        for upl in uploaded_files:
            try:
                bytes_data = upl.read()
                blob_name = upl.name
                upload_source_ppt_to_blob(bytes_data, blob_name)
                ingest_process_blob(blob_name)
                st.success(f"Indexed: {blob_name}")
            except Exception as e:
                logger.exception("Failed to upload & index")
                st.error(f"Error: {e}")
    st.markdown("---")
    st.subheader("Available KB PPTs")
    try:
        kb_files = list_source_ppt_blobs()
    except Exception as e:
        logger.exception("Failed listing KB")
        kb_files = []
    if kb_files:
        for b in kb_files:
            col1, col2 = st.columns([3,1])
            with col1:
                st.caption(b)
            with col2:
                if st.button("Delete", key=f"del_{b}"):
                    try:
                        delete_source_ppt_from_blob(b)
                        delete_ppt_from_chroma(b)
                        st.success(f"Deleted {b}")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")

st.markdown("---")

# Main: Step 1 - prompt & search
st.subheader("Create new presentation (Select slide designs from dataset)")
prompt = st.text_area("Enter your presentation prompt:", height=120)

col1, col2 = st.columns([2,1])
with col1:
    locate_btn = st.button("Search dataset for slides")

with col2:
    # user may still want to choose template mode, but for this flow we focus on select+clone
    pass

if locate_btn:
    if not prompt.strip():
        st.error("Please enter prompt")
    else:
        with st.spinner("Searching and loading slides..."):
            raw_refs = semantic_search(prompt, top_k=5) or []
            refs = [r for r in raw_refs if r.get("score") is None or r["score"] <= SIMILARITY_THRESHOLD]
            if not refs:
                st.warning("No relevant content found. Try different prompt or upload more sample PPTs.")
            else:
                # For each unique ppt_name found in refs, download and extract all slides
                # gather unique ppt names
                ppt_names = sorted({r.get("ppt_name") for r in refs if r.get("ppt_name")})
                st.session_state["preview_slides"] = []
                for ppt_name in ppt_names:
                    try:
                        tmp_local = os.path.join(tempfile.gettempdir(), ppt_name.replace("/", "_"))
                        download_source_ppt_from_blob(ppt_name, tmp_local)
                        slides_info = extract_slides_info_from_ppt(tmp_local)
                        # attach blob_name for later reference if needed
                        for s in slides_info:
                            s["source_blob"] = ppt_name
                        st.session_state["preview_slides"].extend(slides_info)
                    except Exception as e:
                        logger.exception(f"Failed processing {ppt_name}")
                if st.session_state["preview_slides"]:
                    st.session_state["mode"] = "select"
                    st.success(f"Loaded {len(st.session_state['preview_slides'])} slides from {len(ppt_names)} PPT(s).")

st.markdown("---")

# Step 2: Selection UI
if st.session_state["mode"] == "select":
    st.subheader("Select slides to use as design references")
    slides = st.session_state["preview_slides"]
    # show grid of thumbnails with checkboxes
    cols = st.columns(3)
    for i, s in enumerate(slides):
        col = cols[i % 3]
        with col:
            st.image(s["preview_image"], caption=f"{s['slide_id']}", use_column_width=True)
            chk = st.checkbox("Select", key=f"sel_{s['slide_id']}", value=(s['slide_id'] in st.session_state["selected_slide_ids"]))
            if chk and s['slide_id'] not in st.session_state["selected_slide_ids"]:
                st.session_state["selected_slide_ids"].append(s['slide_id'])
            if not chk and s['slide_id'] in st.session_state["selected_slide_ids"]:
                st.session_state["selected_slide_ids"].remove(s['slide_id'])

    if st.button("Continue to Q&A"):
        if not st.session_state["selected_slide_ids"]:
            st.error("Pick at least one slide to continue.")
        else:
            # build selected slide info list
            selected_infos = [s for s in slides if s['slide_id'] in st.session_state["selected_slide_ids"]]
            st.session_state["selected_infos"] = selected_infos
            st.session_state["mode"] = "qna"
            st.success("Entering Q&A for selected slides.")

st.markdown("---")

# Step 3: Q&A flow
def generate_questions_from_slide_text(original_text, num_q=4):
    """
    Ask the LLM to produce a small set of questions to gather new content for this slide.
    Returns list of question strings.
    """
    try:
        sys_prompt = (
            "You are a helpful assistant. Given the text of a slide (title and bullets), "
            "produce 3-5 concise questions that gather the content needed to recreate the slide's text. "
            "Return the questions as plain text, each on a new line."
        )
        user_prompt = f"Slide content:\n{original_text}\n\nGenerate the questions."
        resp = text_client.chat.completions.create(
            model=get_env("CHAT_MODEL", required=True),
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=300,
            temperature=0.0,
        )
        raw = resp.choices[0].message.content.strip()
        questions = [q.strip() for q in raw.splitlines() if q.strip()]
        return questions[:5]
    except Exception as e:
        logger.exception("Question generation failed")
        # fallback default questions
        return [
            "What should be the new slide title?",
            "List 3–5 bullets for this slide (comma separated).",
            "Any specific data, metrics or examples to include?",
        ]

if st.session_state["mode"] == "qna":
    st.subheader("Content Q&A for each selected slide")
    selected_infos = st.session_state.get("selected_infos", [])
    # iterate slides and show generated questions + inputs
    for s in selected_infos:
        st.markdown(f"### Reference: {s['slide_id']} — {s.get('title','')}")
        # generate questions once and store in session_state
        q_key = f"questions_{s['slide_id']}"
        if q_key not in st.session_state:
            st.session_state[q_key] = generate_questions_from_slide_text(s.get("text", ""))

        answers_key = f"answers_{s['slide_id']}"
        if answers_key not in st.session_state:
            st.session_state[answers_key] = {}

        # Show each question with input
        for qi, q in enumerate(st.session_state[q_key]):
            ans = st.text_input(q, key=f"{s['slide_id']}_q_{qi}", value=st.session_state[answers_key].get(str(qi), ""))
            st.session_state[answers_key][str(qi)] = ans

        # Provide a convenience option to keep original slide text
        keep = st.checkbox("Keep original slide text for this reference", key=f"keep_{s['slide_id']}")
        st.session_state["answers_by_slide"].setdefault(s['slide_id'], {})
        if keep:
            # Mark raw_replacements empty meaning "no change"
            st.session_state["answers_by_slide"][s['slide_id']]["raw_replacements"] = {}
        else:
            # Build raw_replacements map: map original full text snippets -> replacement text
            # For simplicity, map the whole slide original text -> joined answers
            joined = "\n".join([v for v in st.session_state[f"answers_{s['slide_id']}"].values() if v])
            # fallback: if user left answers empty, keep original by setting replacements empty
            if not joined.strip():
                st.session_state["answers_by_slide"][s['slide_id']]["raw_replacements"] = {}
            else:
                # Map original complete text to new combined text (best-effort)
                original_text = s.get("text","").strip()
                st.session_state["answers_by_slide"][s['slide_id']]["raw_replacements"] = { original_text: joined }

    if st.button("Generate final PPT from selected slides"):
        # Prepare selected slides list and answers mapping
        selected_infos = st.session_state.get("selected_infos", [])
        answers_by_slide = st.session_state.get("answers_by_slide", {})

        with st.spinner("Generating slides from selected designs..."):
            try:
                out_path = generate_presentation_from_selected(selected_infos, answers_by_slide)
                # Upload result to generated container (reuse existing logic if you want)
                st.success("PPT generated successfully!")
                ppt_title = os.path.splitext(os.path.basename(out_path))[0]
                timestamp = datetime.now().strftime("%d_%b_%H-%M")
                display_name = f"{ppt_title}_{timestamp}.pptx"
                st.session_state["generated_ppts"].insert(0, {"path": out_path, "name": display_name, "created_at": datetime.now()})
                st.session_state["mode"] = "search"
            except Exception as e:
                logger.exception("Slide generation failed")
                st.error(f"Failed: {e}")

st.markdown("---")

# Session generated PPTs list & download
st.subheader("Generated PPTs this session")
if not st.session_state["generated_ppts"]:
    st.caption("No PPTs generated yet.")
else:
    for idx, item in enumerate(st.session_state["generated_ppts"]):
        col1, col2 = st.columns([4,2])
        with col1:
            st.write(f"{idx+1}. {item['name']}")
        with col2:
            try:
                with open(item["path"], "rb") as f:
                    st.download_button(label="Download", data=f, file_name=item["name"], mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")
            except Exception:
                st.caption("File unavailable")
