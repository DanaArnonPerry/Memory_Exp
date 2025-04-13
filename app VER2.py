import streamlit as st
import pandas as pd
import os
import random
import time
from PIL import Image

st.set_page_config(layout="wide", page_title="ניסוי זיכרון חזותי")
st.markdown("<style>body {direction: rtl; text-align: right;}</style>", unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_csv("MemoryTest.csv", encoding='utf-8-sig')
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.dropna(subset=['ChartNumber', 'Condition'], inplace=True)
    df['full_image_path'] = df['ImageFileName'].apply(lambda x: os.path.join("images", os.path.basename(x.strip())) if pd.notna(x) else '')
    return df

def show_rtl_text(text, tag="p", size="18px"):
    st.markdown(f"<{tag} style='direction: rtl; text-align: right; font-size:{size};'>{text}</{tag}>", unsafe_allow_html=True)

def show_question(question, options, key_prefix):
    show_rtl_text(question)
    return st.radio("", options, key=key_prefix, format_func=lambda x: f"{chr(65 + options.index(x))}. {x}", label_visibility="collapsed")

def show_confidence(key):
    show_rtl_text("באיזו מידה אתה בטוח בתשובתך? (0-100, בקפיצות של 10)")
    return st.slider("", 0, 100, 50, 10, key=key, label_visibility="collapsed")

df = load_data()

if "stage" not in st.session_state:
    st.session_state.stage = "welcome"
    st.session_state.responses = []
    st.session_state.chosen = random.sample(df['ChartNumber'].unique().tolist(), 10)

if st.session_state.stage == "welcome":
    show_rtl_text("שלום וברוכ/ה הבא/ה לניסוי בזיכרון חזותי!", "h2")
    show_rtl_text("הניסוי יתבצע בשני חלקים: החלק הראשון יתבצע כעת והחלק השני יתבצע בעוד שעתיים.")
    show_rtl_text("בכל חלק יוצג גרף עם כותרת למשך חצי דקה ולאחר מכן יופיעו שלוש שאלות אמריקאיות.")
    if st.button("המשך"):
        st.session_state.stage = 0
        st.experimental_rerun()

elif isinstance(st.session_state.stage, int) and st.session_state.stage < len(st.session_state.chosen):
    chart_idx = st.session_state.stage
    chart = st.session_state.chosen[chart_idx]
    condition = random.choice(df[df['ChartNumber'] == chart]['Condition'].dropna().unique().tolist())
    row = df[(df['ChartNumber'] == chart) & (df['Condition'] == condition)].iloc[0]

    if "step" not in st.session_state:
        st.session_state.step = "image"

    if st.session_state.step == "image":
        show_rtl_text(f"גרף מספר: {row['ChartNumber']} | תנאי: {row['Condition']}", "h4")
        show_rtl_text(f"{row['Title']}", "h5")
        if os.path.exists(row['full_image_path']):
            st.image(Image.open(row['full_image_path']), use_container_width=True)
        else:
            show_rtl_text("קובץ הגרף לא נמצא")
        st.markdown("הגרף יוצג למשך **30 שניות**. אנא התבוננ/י בו היטב.")
        time.sleep(30)
        st.session_state.step = "q1"
        st.experimental_rerun()

    elif st.session_state.step.startswith("q"):
        q_num = int(st.session_state.step[1])
        question_col = f"Question{q_num}Text"
        options = [row[f"Q{q_num}OptionA"], row[f"Q{q_num}OptionB"],
                   row[f"Q{q_num}OptionC"], row[f"Q{q_num}OptionD"]]

        with st.form(key=f"form_q{q_num}"):
            show_rtl_text(f"שאלה {q_num}", "h3")
            answer = show_question(row[question_col], options, f"a{q_num}_{chart_idx}")
            confidence = show_confidence(f"c{q_num}_{chart_idx}")
            if st.form_submit_button("המשך"):
                if "answers" not in st.session_state:
                    st.session_state.answers = {}
                st.session_state.answers[f"answer{q_num}"] = answer
                st.session_state.answers[f"confidence{q_num}"] = confidence
                if q_num < 3:
                    st.session_state.step = f"q{q_num+1}"
                else:
                    st.session_state.responses.append({
                        "ChartNumber": row["ChartNumber"],
                        "Condition": row["Condition"],
                        **st.session_state.answers
                    })
                    del st.session_state.answers
                    st.session_state.stage += 1
                    del st.session_state.step
                st.experimental_rerun()

else:
    show_rtl_text("שלב א של הניסוי הסתיים, השלב הבא יחל בעוד שעתיים", "h2")
    df_out = pd.DataFrame(st.session_state.responses)
    st.download_button("הורד תוצאות כקובץ CSV", df_out.to_csv(index=False), "results.csv", "text/csv")
