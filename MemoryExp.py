import streamlit as st 
import pandas as pd
import os
import random
import time
from datetime import datetime
from PIL import Image

###############################################
# הגדרות בסיס
###############################################
st.set_page_config(layout="wide", page_title="ניסוי זיכרון חזותי — גרסה 2")
st.markdown("""
<style>
  body {direction: rtl; text-align: right;}
  .rtl {direction: rtl; text-align: right;}
</style>
""", unsafe_allow_html=True)

###############################################
# פונקציות עזר
###############################################

def show_rtl_text(text, tag="p", size="18px"):
    st.markdown(f"<{tag} style='direction: rtl; text-align: right; font-size:{size};'>{text}</{tag}>", unsafe_allow_html=True)


def show_group_badge():
    """תגית קטנה בראש המסך שמציינת באיזו קבוצה אנו (נוח במצב פיתוח)."""
    st.markdown(
        f"<div style='direction:rtl;text-align:right;padding:6px 10px;border-radius:12px;display:inline-block;background:#F1F5F9;border:1px solid #E2E8F0;margin-bottom:8px;'>" \
        f"קבוצה: <b>{st.session_state.get('group','?')}</b></div>",
        unsafe_allow_html=True
    )


def show_timer_badge(seconds: int):
    """מציג טיימר ברור למעלה ככל האפשר."""
    st.markdown(
        f"<div style='direction:rtl;text-align:right;padding:8px 12px;border-radius:10px;display:inline-block;background:#EEF2FF;border:1px solid #CBD5E1;margin:6px 0;'>"
        f"⏱️ זמן שנותר: <b>{seconds}</b> שניות" 
        f"</div>",
        unsafe_allow_html=True
    )


def tick_and_rerun(delay: float = 1.0):
    """מונע לולאת rerun צפופה שיכולה לגרום לשגיאת 400 בדפדפן."""
    time.sleep(max(0.2, float(delay)))
    st.rerun()


@st.cache_data()
def load_data():
    try:
        df = pd.read_csv("MemoryTest.csv", encoding='utf-8-sig')
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        # עמודות חובה מינימליות
        required_cols = [
            'ChartNumber','Condition','ImageFileName','TheContext',
            'Question1Text','Q1OptionA','Q1OptionB','Q1OptionC','Q1OptionD',
            'Question2Text','Q2OptionA','Q2OptionB','Q2OptionC','Q2OptionD',
            'Question3Text','Q3OptionA','Q3OptionB','Q3OptionC','Q3OptionD'
        ]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error("חסרות עמודות בקובץ ה-CSV: " + ", ".join(missing))
            return pd.DataFrame()

        df.dropna(subset=['ChartNumber', 'Condition'], inplace=True)
        df['image_path'] = df['ImageFileName'].apply(lambda x: os.path.join("images", os.path.basename(str(x).strip())) if pd.notna(x) else '')
        # תמיכה בוריאציות קיימות (לא חובה)
        for v in ["V1","V2","V3","V4"]:
            if v not in df.columns:
                df[v] = 1  # ברירת מחדל—הכל מותר בכל וריאציה
        return df
    except Exception as e:
        st.error(f"שגיאה בטעינת הקובץ CSV: {e}")
        return pd.DataFrame()


def log_event(action, extra=None):
    if "log" not in st.session_state:
        st.session_state.log = []
    st.session_state.log.append({
        "timestamp": datetime.now().isoformat(),
        "stage": st.session_state.get("stage"),
        "group": st.session_state.get("group"),
        "graph_index": st.session_state.get("graph_index"),
        "question_index": st.session_state.get("question_index"),
        "action": action,
        "extra": extra
    })


def show_question(options, key_prefix):
    # החזרת תשובה בסקאלה של A-D עם הטקסט
    return st.radio(
        "",
        options,
        key=key_prefix,
        index=None,
        format_func=lambda x: f"{chr(65 + options.index(x))}. {x}",
        label_visibility="collapsed"
    )


def show_confidence(key, scale=5):
    show_rtl_text("באיזו מידה אתה בטוח/ה בתשובתך? (1-5)")
    return st.slider("", 1, scale, step=1, key=key, label_visibility="collapsed")


###############################################
# בדיקות ראשוניות
###############################################
if not os.path.exists("images"):
    st.error("תיקיית 'images' לא נמצאה. אנא צור תיקיה זו והוסף את התמונות הנדרשות.")
    st.stop()

# מצב פיתוח
is_dev_mode = st.sidebar.checkbox("מצב פיתוח", key="dev_mode", value=False)

###############################################
# טעינת נתונים
###############################################
df = load_data()
if df.empty:
    st.stop()

###############################################
# קביעת וריאציה וסינון
###############################################
if "variation" not in st.session_state:
    st.session_state.variation = random.choice(["V1","V2","V3","V4"])
    log_event("Assigned Variation", st.session_state.variation)

if "filtered_df" not in st.session_state:
    st.session_state.filtered_df = df[df[st.session_state.variation] == 1].reset_index(drop=True)
    if st.session_state.filtered_df.empty:
        st.error(f"אין נתונים בתנאי {st.session_state.variation}. אנא בדוק את קובץ ה-CSV.")
        st.stop()

###############################################
# פרמטרים לניסוי
###############################################
DISPLAY_TIME_GRAPH = st.sidebar.number_input("זמן תצוגת גרף (שניות)", min_value=1, max_value=60, value=5) if is_dev_mode else 5
QUESTION_MAX_TIME = st.sidebar.number_input("זמן מירבי לשאלה (שניות)", min_value=10, max_value=600, value=120) if is_dev_mode else 120

###############################################
# בחירת קבוצה (תנאי)
###############################################
# קבוצות:
# G1 — הקשר > גרף 5ש׳ > שאלה1 (עד 2 דק׳) > שאלה2 (עד 2 דק׳) , וחוזר לכל גרף
# G2 — (הקשר) > שלוש שאלות ללא גרף
# G3 — תחילה מציגים את כל הגרפים (5ש׳ + הערכת זכירה), ואז לאחר שסיימנו את כולם—36 שאלות (3 לכל גרף)

if "group" not in st.session_state:
    # אפשרות לקבע קבוצה דרך פרמטר ב-URL (?group=G1/G2/G3)
    try:
        qp = st.query_params
        group_param = qp.get("group", None)
    except Exception:
        qp = st.experimental_get_query_params()
        group_param = qp.get("group", [None])[0]

    if group_param in ("G1", "G2", "G3"):
        st.session_state.group = group_param
    else:
        # ברירת מחדל—מוקצה רנדומית למשתתף
        st.session_state.group = random.choice(["G1","G2","G3"])  
    log_event("Assigned Group", st.session_state.group)

# בורר לקבוצה במצב פיתוח
if is_dev_mode:
    new_group = st.sidebar.selectbox("בחר קבוצה (תנאי)", ["G1","G2","G3"], index=["G1","G2","G3"].index(st.session_state.group))
    if new_group != st.session_state.group and st.sidebar.button("החל קבוצה"):
        st.session_state.group = new_group
        st.session_state.stage = "welcome"
        st.session_state.graph_index = 0
        st.session_state.question_index = 0
        st.session_state.responses = []
        st.session_state.phase = None
        st.session_state.display_start_time = None
        st.session_state.q_start_time = None
        log_event("Changed Group", new_group)
        st.rerun()

###############################################
# אתחול מצב
###############################################
if "stage" not in st.session_state:
    st.session_state.stage = "welcome"
if "graph_index" not in st.session_state:
    st.session_state.graph_index = 0
if "question_index" not in st.session_state:
    st.session_state.question_index = 0  # 0->Q1, 1->Q2, 2->Q3
if "responses" not in st.session_state:
    st.session_state.responses = []  # נשמור כאן הכל (כולל הערכות זכירה)
if "phase" not in st.session_state:
    st.session_state.phase = None  # בשימוש ב-G3 כדי להבדיל בין שלב הצגת גרפים לשלב השאלות
if "display_start_time" not in st.session_state:
    st.session_state.display_start_time = None
if "q_start_time" not in st.session_state:
    st.session_state.q_start_time = None

###############################################
# ווידג'טים מסייעים למצב פיתוח
###############################################
if is_dev_mode:
    st.sidebar.markdown(f"### גרף נוכחי: {st.session_state.graph_index+1}/{len(st.session_state.filtered_df)}")
    jump_idx = st.sidebar.number_input("דלג לגרף #", min_value=1, max_value=len(st.session_state.filtered_df), value=st.session_state.graph_index+1)
    if st.sidebar.button("דלג"):
        st.session_state.graph_index = jump_idx - 1
        st.session_state.stage = "context" if st.session_state.group in ["G1","G2"] else "g3_show"
        st.rerun()

###############################################
# פונקציות זרימה לכל קבוצה
###############################################

def save_and_advance_graph():
    """עובר לגרף הבא או לשלב הסיום/הבא לפי הקבוצה."""
    if st.session_state.graph_index + 1 >= len(st.session_state.filtered_df):
        # עברנו את כל הגרפים
        if st.session_state.group == "G3" and st.session_state.phase == "show":
            # מסיימים שלב הצגת הגרפים + הערכות, מתחילים שלב שאלות
            st.session_state.phase = "questions"
            st.session_state.stage = "g3_questions"
            st.session_state.graph_index = 0
            st.session_state.question_index = 0
        else:
            st.session_state.stage = "end"
    else:
        st.session_state.graph_index += 1
        if st.session_state.group == "G1":
            st.session_state.stage = "context"
        elif st.session_state.group == "G2":
            st.session_state.stage = "context"
        else:  # G3
            st.session_state.stage = "g3_show"


def record_answer(row, qn, answer, confidence, rt):
    payload = {
        "ChartNumber": row["ChartNumber"],
        "Condition": row["Condition"],
        "group": st.session_state.group,
        "variation": st.session_state.variation,
        "timestamp": datetime.now().isoformat(),
        "question": int(qn),
        "question_text": row[f"Question{qn}Text"],
        "answer": answer,
        "rt": rt,
        "phase": st.session_state.phase
    }
    if confidence is not None:
        payload["confidence"] = confidence
    st.session_state.responses.append(payload)

###############################################
# מסך פתיחה
###############################################
if st.session_state.stage == "welcome":
    show_group_badge()
    show_rtl_text("שלום וברוכ/ה הבא/ה לניסוי בזיכרון חזותי!", "h2")
    if st.session_state.group == "G1":
        show_rtl_text("בתנאי זה יוצג תחילה הקשר, לאחר מכן גרף ל-5 שניות, ואז שתי שאלות (כל אחת עד 2 דקות).")
    elif st.session_state.group == "G2":
        show_rtl_text("בתנאי זה יוצג הקשר ולאחריו שלוש שאלות על הגרף — ללא הצגת הגרף עצמו.")
    else:
        show_rtl_text("בתנאי זה כל הגרפים יוצגו ל-5 שניות כל אחד, לאחר כל גרף שאלה להערכת זכירה; לבסוף, תענו על כל 36 השאלות (3 לכל גרף) ללא הצגת הגרפים.")

    if st.button("התחל"):
        log_event("Start Experiment", {"group": st.session_state.group})
        if st.session_state.group in ["G1","G2"]:
            st.session_state.stage = "context"
        else:
            st.session_state.phase = "show"  # שלב הצגה והערכות
            st.session_state.stage = "g3_show"
        st.rerun()

###############################################
# G1 — הקשר > גרף > Q1 > Q2 (בלי שאלת ביטחון; הגרף מעל השאלה; טיימר בראש)
###############################################
elif st.session_state.group == "G1":
    row = st.session_state.filtered_df.iloc[st.session_state.graph_index]

    if st.session_state.stage == "context":
        show_group_badge()
        st.session_state.question_index = 0
        show_rtl_text("הקשר לגרף הבא:", "h3")
        show_rtl_text(row.get("TheContext", ""))
        if st.button("המשך לגרף"):
            st.session_state.stage = "image"
            st.session_state.display_start_time = time.time()
            log_event("Show Context", {"chart": row['ChartNumber']})
            st.rerun()

    elif st.session_state.stage == "image":
        show_group_badge()
        elapsed = time.time() - st.session_state.display_start_time
        remaining = max(0, int(DISPLAY_TIME_GRAPH - elapsed))
        show_timer_badge(remaining)
        show_rtl_text(f"גרף #{row['ChartNumber']} | תנאי: {row['Condition']}")
        if os.path.exists(row['image_path']):
            st.image(row['image_path'], use_container_width=True)
        else:
            st.error(f"תמונה לא נמצאה: {row['image_path']}")
        if elapsed >= DISPLAY_TIME_GRAPH:
            st.session_state.stage = "q1"
            st.session_state.q_start_time = time.time()
            st.rerun()
        else:
            tick_and_rerun(1.0)

    elif st.session_state.stage in ["q1","q2"]:
        show_group_badge()
        qn = 1 if st.session_state.stage == "q1" else 2
        qtxt = row[f"Question{qn}Text"]
        opts = [row[f"Q{qn}OptionA"], row[f"Q{qn}OptionB"], row[f"Q{qn}OptionC"], row[f"Q{qn}OptionD"]]

        elapsed = time.time() - (st.session_state.q_start_time or time.time())
        remaining = max(0, int(QUESTION_MAX_TIME - elapsed))
        show_timer_badge(remaining)

        # הגרף מעל השאלה
        if os.path.exists(row['image_path']):
            st.image(row['image_path'], use_container_width=True)

        with st.form(key=f"g1_q{qn}_{row['ChartNumber']}"):
            show_rtl_text(f"גרף {row['ChartNumber']} — שאלה {qn}", "h3")
            show_rtl_text(qtxt)
            answer = show_question(opts, f"g1_a{qn}_{row['ChartNumber']}")
            submitted = st.form_submit_button("המשך")

        if submitted or elapsed >= QUESTION_MAX_TIME:
            rt = round(elapsed, 2)
            # ללא שאלה על ביטחון בקבוצה 1
            record_answer(row, qn, answer, None, rt)
            log_event(f"Answer Q{qn}", {"chart": row['ChartNumber'], "rt": rt})
            if st.session_state.stage == "q1":
                st.session_state.stage = "q2"
                st.session_state.q_start_time = time.time()
            else:
                save_and_advance_graph()
            st.rerun()
        else:
            tick_and_rerun(1.0)

###############################################
# G2 — הקשר > Q1 > Q2 > Q3 (ללא הצגת הגרף)
###############################################
elif st.session_state.group == "G2":
    row = st.session_state.filtered_df.iloc[st.session_state.graph_index]

    if st.session_state.stage == "context":
        show_group_badge()
        st.session_state.question_index = 0
        show_rtl_text("הקשר לשאלות הבאות:", "h3")
        show_rtl_text(row.get("TheContext", ""))
        if st.button("המשך לשאלות"):
            st.session_state.stage = "g2_q"
            st.session_state.q_start_time = time.time()
            log_event("Show Context (G2)", {"chart": row['ChartNumber']})
            st.rerun()

    elif st.session_state.stage == "g2_q":
        show_group_badge()
        qn = st.session_state.question_index + 1  # 1..3
        qtxt = row[f"Question{qn}Text"]
        opts = [row[f"Q{qn}OptionA"], row[f"Q{qn}OptionB"], row[f"Q{qn}OptionC"], row[f"Q{qn}OptionD"]]
        elapsed = time.time() - (st.session_state.q_start_time or time.time())
        remaining = max(0, int(QUESTION_MAX_TIME - elapsed))
        show_timer_badge(remaining)

        with st.form(key=f"g2_q{qn}_{row['ChartNumber']}"):
            show_rtl_text(f"גרף {row['ChartNumber']} — שאלה {qn}", "h3")
            show_rtl_text(qtxt)
            answer = show_question(opts, f"g2_a{qn}_{row['ChartNumber']}")
            confidence = show_confidence(f"g2_c{qn}_{row['ChartNumber']}")
            submitted = st.form_submit_button("המשך")

        if submitted or elapsed >= QUESTION_MAX_TIME:
            rt = round(elapsed, 2)
            record_answer(row, qn, answer, confidence, rt)
            log_event(f"Answer Q{qn} (G2)", {"chart": row['ChartNumber'], "rt": rt})
            st.session_state.question_index += 1
            if st.session_state.question_index >= 3:
                st.session_state.question_index = 0
                save_and_advance_graph()
            else:
                st.session_state.q_start_time = time.time()
            st.rerun()
        else:
            tick_and_rerun(1.0)

###############################################
# G3 — שלב הצגת כל הגרפים + הערכת זכירה, ואז כל השאלות (36)
###############################################
elif st.session_state.group == "G3":
    row = st.session_state.filtered_df.iloc[st.session_state.graph_index]

    # שלב הצגה + הערכה
    if st.session_state.stage == "g3_show" and st.session_state.phase == "show":
        show_group_badge()
        elapsed = 0 if st.session_state.display_start_time is None else time.time() - st.session_state.display_start_time
        remaining = max(0, int(DISPLAY_TIME_GRAPH - elapsed))
        show_timer_badge(remaining)
        show_rtl_text(f"גרף #{row['ChartNumber']} — יוצג {DISPLAY_TIME_GRAPH} שניות", "h3")
        if os.path.exists(row['image_path']):
            st.image(row['image_path'], use_container_width=True)
        else:
            st.error(f"תמונה לא נמצאה: {row['image_path']}")

        if st.session_state.display_start_time is None:
            st.session_state.display_start_time = time.time()
            log_event("Show Graph (G3)", {"chart": row['ChartNumber']})
        elapsed = time.time() - st.session_state.display_start_time

        if elapsed >= DISPLAY_TIME_GRAPH:
            st.session_state.stage = "g3_eval"
            st.session_state.display_start_time = None
            st.rerun()
        else:
            tick_and_rerun(1.0)

    elif st.session_state.stage == "g3_eval" and st.session_state.phase == "show":
        show_group_badge()
        with st.form(key=f"g3_eval_{row['ChartNumber']}"):
            show_rtl_text("שאלת הערכה: באיזו מידה את/ה חושב/ת שתזכור/י את הנתונים בעוד כשעתיים? (1-5)", "h3")
            memory = st.slider("", 1, 5, step=1, key=f"g3_mem_{row['ChartNumber']}", label_visibility="collapsed")
            submitted = st.form_submit_button("המשך")
        if submitted:
            st.session_state.responses.append({
                "ChartNumber": row["ChartNumber"],
                "Condition": row["Condition"],
                "group": st.session_state.group,
                "variation": st.session_state.variation,
                "timestamp": datetime.now().isoformat(),
                "phase": "show",
                "memory_estimate": memory
            })
            log_event("Memory Estimate (G3)", {"chart": row['ChartNumber'], "estimate": memory})
            save_and_advance_graph()
            st.rerun()

    # שלב השאלות — לאחר שכל הגרפים הוצגו
    elif st.session_state.stage == "g3_questions" and st.session_state.phase == "questions":
        show_group_badge()
        qn = st.session_state.question_index + 1
        qtxt = row[f"Question{qn}Text"]
        opts = [row[f"Q{qn}OptionA"], row[f"Q{qn}OptionB"], row[f"Q{qn}OptionC"], row[f"Q{qn}OptionD"]]

        if st.session_state.q_start_time is None:
            st.session_state.q_start_time = time.time()
        elapsed = time.time() - st.session_state.q_start_time
        remaining = max(0, int(QUESTION_MAX_TIME - elapsed))
        show_timer_badge(remaining)

        with st.form(key=f"g3_q{qn}_{row['ChartNumber']}"):
            show_rtl_text(f"שאלות סופיות — גרף {row['ChartNumber']} — שאלה {qn}/3", "h3")
            show_rtl_text(qtxt)
            answer = show_question(opts, f"g3_a{qn}_{row['ChartNumber']}")
            confidence = show_confidence(f"g3_c{qn}_{row['ChartNumber']}")
            submitted = st.form_submit_button("המשך")

        if submitted or elapsed >= QUESTION_MAX_TIME:
            rt = round(elapsed, 2)
            record_answer(row, qn, answer, confidence, rt)
            log_event(f"Answer Q{qn} (G3-final)", {"chart": row['ChartNumber'], "rt": rt})
            st.session_state.question_index += 1
            if st.session_state.question_index >= 3:
                st.session_state.question_index = 0
                if st.session_state.graph_index + 1 >= len(st.session_state.filtered_df):
                    st.session_state.stage = "end"
                else:
                    st.session_state.graph_index += 1
                    st.session_state.q_start_time = None
            else:
                st.session_state.q_start_time = time.time()
            st.rerun()
        else:
            tick_and_rerun(1.0)

###############################################
# סיום ושמירה
###############################################
if st.session_state.stage == "end":
    show_group_badge()
    show_rtl_text("הניסוי הסתיים, תודה רבה!", "h2")

    df_out = pd.DataFrame(st.session_state.responses)
    df_log = pd.DataFrame(st.session_state.log)

    results_dir = "experiment_results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    res_path = f"{results_dir}/results_{timestamp}.csv"
    log_path = f"{results_dir}/log_{timestamp}.csv"
    df_out.to_csv(res_path, index=False)
    df_log.to_csv(log_path, index=False)

    st.success("הקבצים נשמרו לתיקייה experiment_results.")

    # כפתורי הורדה למנהל מערכת בלבד
    if st.sidebar.checkbox("הצג כפתורי הורדה (למנהל מערכת בלבד)", key="admin_download", value=False):
        admin_password = st.sidebar.text_input("סיסמת מנהל:", type="password", key="admin_pw")
        if admin_password == "admin123":
            st.sidebar.download_button("הורד תוצאות (CSV)", df_out.to_csv(index=False), "results.csv", "text/csv")
            st.sidebar.download_button("הורד לוג (CSV)", df_log.to_csv(index=False), "log.csv", "text/csv")
            st.sidebar.success("ברוך/ה הבא/ה, מנהל/ת!")
        elif admin_password:
            st.sidebar.error("סיסמה שגויה")

###############################################
# הערות:
# * בקבוצה 1 הוסרה שאלת הביטחון, והגרף מוצג מעל השאלה. הטיימר מופיע בראש.
# * נוספה המתנה לפני rerun (tick_and_rerun) בכל המקומות עם טיימרים כדי למנוע שגיאות 400.
# * תמיכה בפרמטר URL לקביעה מראש של קבוצה (?group=G1/G2/G3).
# * הלוג והתוצאות נשמרים אוטומטית בתיקייה experiment_results.
