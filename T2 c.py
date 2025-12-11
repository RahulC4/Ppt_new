# pages/3_❓_QnA.py
import streamlit as st
import json
from utils import text_client, get_env, safe_json_load, logger

st.set_page_config(page_title="3 - QnA", layout="wide")
st.title("3 — Q&A: Answer slide-specific questions")

selected_structs = st.session_state.get("selected_slide_structs", [])
if not selected_structs:
    st.warning("No slides selected. Go to Slide Selection (page 2).")
else:
    st.info("For each selected slide, answer the short, slide-specific questions. You can leave some answers blank to keep original text.")

def ask_llm_for_questions(slide_struct):
    """
    Ask the LLM to generate one question per editable shape.
    Return mapping {shape_id: question}
    """
    shape_list = slide_struct.get("editable_shapes", [])
    slide_title = ""
    # try to infer title from first shape
    if shape_list:
        slide_title = shape_list[0].get("text", "")[:200]

    sys_prompt = (
        "You are an assistant that generates concise, slide-specific questions. "
        "Given the slide title and a list of editable text boxes, return a JSON object mapping "
        "each shape_id to a single question that the user can answer. Questions must be focused, "
        "contextual, and not generic. Return JSON only."
    )

    user_block = {
        "slide_title": slide_title,
        "editable_shapes": [{ "shape_id": sh["shape_id"], "text": sh["text"] } for sh in shape_list]
    }

    messages = [
        {"role":"system", "content": sys_prompt},
        {"role":"user", "content": "Slide data (JSON):\n" + json.dumps(user_block, indent=2)}
    ]

    try:
        resp = text_client.chat.completions.create(
            model=get_env("CHAT_MODEL", required=True),
            messages=messages,
            max_completion_tokens=600,
            temperature=0.0
        )
        raw = resp.choices[0].message.content.strip()
        parsed = safe_json_load(raw)
        if isinstance(parsed, dict):
            return parsed
        # fallback: try to extract lines
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        out = {}
        for i, sh in enumerate(shape_list):
            q = lines[i] if i < len(lines) else f"What should be the new text for {sh['shape_id']}?"
            out[sh['shape_id']] = q
        return out
    except Exception as e:
        logger.exception("LLM questions generation failed")
        # fallback simple mapping
        return { sh["shape_id"]: f"What is the new text for: {sh['text'][:80]}" for sh in shape_list }

# generate questions once per slide and store
for s in selected_structs:
    qkey = f"questions_{s['slide_id']}"
    if qkey not in st.session_state:
        st.session_state[qkey] = ask_llm_for_questions(s)

# show each slide with questions
for s in selected_structs:
    st.markdown(f"### Reference: {s.get('slide_id')} — {s.get('ppt_path').split(os.sep)[-1]} (slide {s.get('slide_index')})")
    st.image(s.get("png_path"), use_column_width=True)
    qmap = st.session_state.get(f"questions_{s['slide_id']}", {})
    st.session_state.setdefault("answers_by_slide", {})
    st.session_state["answers_by_slide"].setdefault(s["slide_id"], {})

    for shape in s.get("editable_shapes", []):
        shape_id = shape["shape_id"]
        question = qmap.get(shape_id, f"Provide text for '{shape['text'][:80]}'")
        answer_key = f"ans_{s['slide_id']}_{shape_id}"
        val = st.text_area(question, key=answer_key, value=st.session_state["answers_by_slide"][s["slide_id"]].get(shape_id, ""))
        st.session_state["answers_by_slide"][s["slide_id"]][shape_id] = val

    st.markdown("---")

col1, col2 = st.columns([1,1])
with col1:
    if st.button("Generate PPT from answers"):
        # prepare data for generator: convert slide_id keyed answers to slide_index keyed mapping expected by generate_ppt
        answers_for_generator = {}
        for s in selected_structs:
            sid = s["slide_id"]
            idx = s["slide_index"]
            answers_for_generator[str(idx)] = st.session_state["answers_by_slide"].get(sid, {})
        st.session_state["generation_payload"] = {
            "selected_slides": selected_structs,
            "answers_map": answers_for_generator
        }
        st.success("Answers saved. Proceeding to generate the PPT.")
        st.switch_page("pages/4_Generate_PPT.py")

with col2:
    if st.button("Back to Selection"):
        st.switch_page("pages/2_🖼️_Slide_Selection.py")
