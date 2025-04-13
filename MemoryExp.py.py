import streamlit as st
import pandas as pd
import os
import random
import time
from datetime import datetime
from PIL import Image

st.set_page_config(layout="wide", page_title="ניסוי זיכרון חזותי")
st.markdown("<style>body {direction: rtl; text-align: right;}</style>", unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_csv("MemoryTest.csv", encoding='utf-8-sig')
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.dropna(subset=['ChartNumber', 'Condition'], inplace=True)
    df['image_path'] = df['ImageFileName'].apply(lambda x: os.path.join("images", os.path.basename(str(x).strip())) if pd.notna(x) else '')
    return df

def log_event(action, extra=None):
    if "log" not in st.session_state:
        st.session_state.log = []
    st.session_state.log.append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "extra": extra
    })

def show_rtl_text(text, tag="p", size="18px"):
    st.markdown(f"<{tag} style='direction: rtl; text-align: right; font-size:{size};'>{text}</{tag}>", unsafe_allow_html=True)

def show_question(question, options, key_prefix):
    show_rtl_text(question)
    return st.radio("", options, key=key_prefix, index=None, format_func=lambda x: f"{chr(65 + options.index(x))}. {x}", label_visibility="collapsed")

def show_confidence(key, scale=5):
    show_rtl_text("באיזו מידה אתה בטוח בתשובתך? (1-5)")
    return st.slider("", 1, scale, step=1, key=key, label_visibility="collapsed")

df = load_data()

if "variation" not in st.session_state:
    st.session_state.variation = random.choice(["V1", "V2", "V3", "V4"])
    st.session_state.filtered_df = df[df[st.session_state.variation] == 1].reset_index(drop=True)
    st.session_state.responses = []
    st.session_state.graph_index = 0
    st.session_state.stage = "welcome"
    log_event("Assigned Variation", st.session_state.variation)

if st.session_state.stage == "welcome":
    show_rtl_text("שלום וברוכ/ה הבא/ה לניסוי בזיכרון חזותי!", "h2")
    show_rtl_text("הניסוי יתבצע בשני חלקים... יופיעו 12 גרפים... לאחר מכן 3 שאלות אמריקאיות.")
    if st.button("המשך"):
        log_event("לחצן המשך - מסך פתיחה")
        st.session_state.stage = "context"
        st.rerun()

elif st.session_state.stage == "context":
    row = st.session_state.filtered_df.iloc[st.session_state.graph_index]
    st.session_state.current_row = row.to_dict()
    show_rtl_text("הקשר לגרף שיוצג:")
    show_rtl_text(row.get("TheContext", ""))
    if st.button("המשך"):
        log_event("לחצן המשך - הצגת הקשר", row['ChartNumber'])
        st.session_state.stage = "image"
        st.rerun()

elif st.session_state.stage == "image":
    row = st.session_state.current_row
    show_rtl_text("הגרף יוצג למשך 30 שניות.")
    show_rtl_text(f"גרף מספר: {row['ChartNumber']} | תנאי: {row['Condition']}", "h4")
    if os.path.exists(row['image_path']):
        st.image(row['image_path'], use_container_width=True)
    else:
        show_rtl_text("תמונה לא נמצאה")
    log_event("הצגת גרף", row['ChartNumber'])
    time.sleep(30)
    st.session_state.stage = "eval"
    st.rerun()

elif st.session_state.stage == "eval":
    row = st.session_state.current_row
    with st.form(key=f"eval_form_{row['ChartNumber']}"):
        show_rtl_text("שאלת הערכה", "h3")
        show_rtl_text("באיזו מידה אתה חושב שתזכור את הנתונים? (1-5)")
        memory = st.slider("", 1, 5, step=1, key="memory_conf", label_visibility="collapsed")
        if st.form_submit_button("המשך"):
            log_event("הערכת זיכרון", {"chart": row["ChartNumber"], "estimate": memory})
            st.session_state.responses.append({
                "ChartNumber": row["ChartNumber"],
                "Condition": row["Condition"],
                "MemoryEstimate": memory
            })
            st.session_state.q_num = 1
            st.session_state.stage = "questions"
            st.rerun()

elif st.session_state.stage == "questions":
    row = st.session_state.current_row
    qn = st.session_state.q_num
    question_col = f"Question{qn}Text"
    options = [row[f"Q{qn}OptionA"], row[f"Q{qn}OptionB"], row[f"Q{qn}OptionC"], row[f"Q{qn}OptionD"]]

    with st.form(key=f"form_q{qn}"):
        show_rtl_text(f"שאלה {qn}", "h3")
        start_time = time.time()
        answer = show_question(row[question_col], options, f"a{qn}_{row['ChartNumber']}")
        confidence = show_confidence(f"c{qn}_{row['ChartNumber']}")
        submit = st.form_submit_button("המשך")
        if submit:
            rt = round(time.time() - start_time, 2)
            log_event(f"תשובה לשאלה {qn}", {"answer": answer, "confidence": confidence, "rt": rt})
            st.session_state.responses[-1].update({
                f"answer{qn}": answer,
                f"confidence{qn}": confidence,
                f"rt{qn}": rt
            })
            if qn < 3:
                st.session_state.q_num += 1
            else:
                st.session_state.graph_index += 1
                if st.session_state.graph_index < len(st.session_state.filtered_df):
                    st.session_state.stage = "context"
                else:
                    st.session_state.stage = "end"
            st.rerun()

elif st.session_state.stage == "end":
    show_rtl_text("הניסוי הסתיים, תודה על השתתפותך!", "h2")
    df_out = pd.DataFrame(st.session_state.responses)
    df_log = pd.DataFrame(st.session_state.log)
    st.download_button("הורד תוצאות (CSV)", df_out.to_csv(index=False), "results.csv", "text/csv")
    st.download_button("הורד לוג מפורט (CSV)", df_log.to_csv(index=False), "log.csv", "text/csv")
