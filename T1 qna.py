# pages/3_❓_QnA.py
import streamlit as st
from utils import text_client, get_env

st.title("❓ Slide Q&A")

slides = st.session_state.get("selected_slides", [])
answers = st.session_state.get("answers", {})

def create_questions(text):
    sys = "Generate 3–5 questions to recreate this slide content."
    usr = f"Slide content:\n{text}\nGenerate questions only."
    resp = text_client.chat.completions.create(
        model=get_env("CHAT_MODEL"),
        messages=[{"role":"system","content":sys},{"role":"user","content":usr}],
    )
    return resp.choices[0].message.content.strip().split("\n")

for slide in slides:
    st.header(slide["slide_id"])

    # Extract original text (use slide image? or extract text separately)
    original_text = "Slide content placeholder"

    q_key = f"q_{slide['slide_id']}"

    if q_key not in st.session_state:
        st.session_state[q_key] = create_questions(original_text)

    st.subheader("Answer below:")
    ans_list = []
    for i, q in enumerate(st.session_state[q_key]):
        ans = st.text_input(q, key=f"ans_{slide['slide_id']}_{i}")
        ans_list.append(ans)

    answers[slide["slide_id"]] = ans_list

st.session_state["answers"] = answers

if st.button("Generate PPT"):
    st.switch_page("pages/4_📥_Generated_PPTs.py")
