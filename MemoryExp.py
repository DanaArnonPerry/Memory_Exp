import streamlit as st 
import pandas as pd
import os
import random
import time
from datetime import datetime
from PIL import Image
import matplotlib.pyplot as plt

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
# פונקציות עזר להצגה
###############################################

def show_rtl_text(text, tag="p", size="18px"):
    st.markdown(f"<{tag} style='direction: rtl; text-align: right; font-size:{size};'>{text}</{tag}>", unsafe_allow_html=True)


def show_group_badge():
    st.markdown(
        f"<div style='direction:rtl;text-align:right;padding:6px 10px;border-radius:12px;display:inline-block;background:#F1F5F9;border:1px solid #E2E8F0;margin-bottom:8px;'>"
        f"קבוצה: <b>{st.session_state.get('group','?')}</b></div>",
        unsafe_allow_html=True
    )


def show_timer_badge(seconds: int):
    st.markdown(
        f"<div style='direction:rtl;text-align:right;padding:8px 12px;border-radius:10px;display:inline-block;background:#EEF2FF;border:1px solid #CBD5E1;margin:6px 0;'>"
        f"⏱️ זמן שנותר: <b>{seconds}</b> שניות"
        f"</div>",
        unsafe_allow_html=True
    )


def tick_and_rerun(delay: float = 1.0):
    time.sleep(max(0.2, float(delay)))
    st.rerun()

###############################################
# טעינת נתוני הניסוי ונתוני הגרפים
###############################################

@st.cache_data()
def load_memory_test():
    try:
        df = pd.read_csv("MemoryTest.csv", encoding='utf-8-sig')
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        # עמודות חובה מינימליות (ללא תמונות)
        required_cols = [
            'ChartNumber','Condition','TheContext',
            'Question1Text','Q1OptionA','Q1OptionB','Q1OptionC','Q1OptionD',
            'Question2Text','Q2OptionA','Q2OptionB','Q2OptionC','Q2OptionD',
            'Question3Text','Q3OptionA','Q3OptionB','Q3OptionC','Q3OptionD'
        ]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error("חסרות עמודות בקובץ ה-CSV: " + ", ".join(missing))
            return pd.DataFrame()
        df.dropna(subset=['ChartNumber', 'Condition'], inplace=True)
        for v in ["V1","V2","V3","V4"]:
            if v not in df.columns:
                df[v] = 1
        return df
    except Exception as e:
        st.error(f"שגיאה בטעינת הקובץ MemoryTest.csv: {e}")
        return pd.DataFrame()

@st.cache_data()
def load_graph_db():
    try:
        db = pd.read_csv("graph_DB.csv", encoding='utf-8-sig')
        db = db.loc[:, ~db.columns.str.contains('^Unnamed')]
        # ניקוי מספרים (מסיר פסיקים ואחוזים)
        def _to_num(x):
            try:
                if pd.isna(x):
                    return None
                s = str(x).replace(',', '').replace('%','').strip()
                return float(s)
            except:
                return None
        for col in [c for c in db.columns if c.lower().startswith('values')]:
            db[col] = db[col].apply(_to_num)
        # המרה של מזהה לגרף למספר שלם אם אפשר
        if 'ID' in db.columns:
            db['ID'] = pd.to_numeric(db['ID'], errors='coerce').astype('Int64')
        return db
    except Exception as e:
        st.error(f"שגיאה בטעינת הקובץ graph_DB.csv: {e}")
        return pd.DataFrame()


def current_graph_id(row_dict):
    """מאחזר מזהה גרף לפי סדר עדיפויות: GraphID/ChartID/ID/ChartNumber"""
    for key in ("GraphID","ChartID","ID","ChartNumber"):
        val = row_dict.get(key)
        if pd.notna(val):
            try:
                return int(float(val))
            except:
                pass
    return None


def get_graph_slice(graph_db: pd.DataFrame, graph_id: int):
    if graph_db.empty or graph_id is None:
        return pd.DataFrame()
    if 'ID' not in graph_db.columns:
        return pd.DataFrame()
    sub = graph_db[graph_db['ID'] == graph_id].copy()
    return sub


def draw_bar_chart(sub: pd.DataFrame, title: str | None = None, height: int = 300):
    if sub.empty:
        st.warning("לא נמצאו נתונים לגרף המבוקש בקובץ graph_DB.csv")
        return
    labels = sub['Labels'].astype(str).tolist() if 'Labels' in sub.columns else [str(i) for i in range(len(sub))]
    has_b = 'ValuesB' in sub.columns and sub['ValuesB'].notna().any()
    vals_a = sub['ValuesA'].fillna(0).tolist() if 'ValuesA' in sub.columns else [0]*len(labels)
    vals_b = sub['ValuesB'].fillna(0).tolist() if has_b else None
    colors_a = sub['ColorA'].tolist() if 'ColorA' in sub.columns else None
    colors_b = sub['ColorB'].tolist() if 'ColorB' in sub.columns else None

    n = len(labels)
    x = range(n)
    if has_b:
        width = 0.38
    else:
        width = 0.55

    fig, ax = plt.subplots(figsize=(min(14, max(8, n*0.8)), height/96))
    if has_b:
        ax.bar([i - width/2 for i in x], vals_a, width, color=colors_a)
        ax.bar([i + width/2 for i in x], vals_b, width, color=colors_b)
    else:
        ax.bar(x, vals_a, width, color=colors_a)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=0, ha='center', fontsize=11)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.25)
    if title:
        ax.set_title(title, fontsize=14, pad=12)

    # אנוטציות מעל עמודות
    def _annotate(xs, ys):
        for xi, yi in zip(xs, ys):
            ax.text(xi, yi, f"{yi:.0f}", ha='center', va='bottom', fontsize=10)
    if has_b:
        _annotate([i - width/2 for i in x], vals_a)
        _annotate([i + width/2 for i in x], vals_b)
    else:
        _annotate(list(x), vals_a)

    st.pyplot(fig, clear_figure=True)


###############################################
# טעינה
###############################################

# תיקיית תמונות כבר לא חובה
is_dev_mode = st.sidebar.checkbox("מצב פיתוח", key="dev_mode", value=False)

df = load_memory_test()
if df.empty:
    st.stop()

graph_db = load_graph_db()
if graph_db.empty:
    st.warning("קובץ graph_DB.csv לא נטען — הצגת הגרפים תוגבל.")

###############################################
# קביעת וריאציה וסינון
###############################################
if "variation" not in st.session_state:
    st.session_state.variation = random.choice(["V1","V2","V3","V4"])
    # אין כאן log_event עדיין כי stage לא מאותחל

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
if "group" not in st.session_state:
    try:
        qp = st.query_params
        group_param = qp.get("group", None)
    except Exception:
        qp = st.experimental_get_query_params()
        group_param = qp.get("group", [None])[0]
    st.session_state.group = group_param if group_param in ("G1","G2","G3") else random.choice(["G1","G2","G3"])  

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
        st.rerun()

###############################################
# אתחול מצב
###############################################
if "stage" not in st.session_state:
    st.session_state.stage = "welcome"
if "graph_index" not in st.session_state:
    st.session_state.graph_index = 0
if "question_index" not in st.session_state:
    st.session_state.question_index = 0
if "responses" not in st.session_state:
    st.session_state.responses = []
if "phase" not in st.session_state:
    st.session_state.phase = None
if "display_start_time" not in st.session_state:
    st.session_state.display_start_time = None
if "q_start_time" not in st.session_state:
    st.session_state.q_start_time = None

###############################################
# לוג
###############################################

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

###############################################
# ווידג'טים מסייעים
###############################################
if is_dev_mode:
    st.sidebar.markdown(f"### גרף נוכחי: {st.session_state.graph_index+1}/{len(st.session_state.filtered_df)}")
    jump_idx = st.sidebar.number_input("דלג לגרף #", min_value=1, max_value=len(st.session_state.filtered_df), value=st.session_state.graph_index+1)
    if st.sidebar.button("דלג"):
        st.session_state.graph_index = jump_idx - 1
        st.session_state.stage = "context" if st.session_state.group in ["G1","G2"] else "g3_show"
        st.rerun()

###############################################
# פונקציות זרימה
###############################################

def save_and_advance_graph():
    if st.session_state.graph_index + 1 >= len(st.session_state.filtered_df):
        if st.session_state.group == "G3" and st.session_state.phase == "show":
            st.session_state.phase = "questions"
            st.session_state.stage = "g3_questions"
            st.session_state.graph_index = 0
            st.session_state.question_index = 0
        else:
            st.session_state.stage = "end"
    else:
        st.session_state.graph_index += 1
        st.session_state.stage = "context" if st.session_state.group in ("G1","G2") else "g3_show"


def record_answer(row, qn, answer, confidence, rt):
    payload = {
        "ChartNumber": row.get("ChartNumber"),
        "Condition": row.get("Condition"),
        "GraphID": current_graph_id(row),
        "group": st.session_state.group,
        "variation": st.session_state.variation,
        "timestamp": datetime.now().isoformat(),
        "question": int(qn),
        "question_text": row.get(f"Question{qn}Text"),
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
        show_rtl_text("בתנאי זה יוצג תחילה הקשר, לאחר מכן גרף ל-5 שניות, ואז שתי שאלות (כל אחת עד 2 דקות) עם הגרף מעל השאלה.")
    elif st.session_state.group == "G2":
        show_rtl_text("בתנאי זה יוצג הקשר, יוצג הגרף ל‑5 שניות, ואז שלוש שאלות ללא הצגת הגרף.")
    else:
        show_rtl_text("בתנאי זה כל הגרפים יוצגו ל-5 שניות כל אחד עם שאלת הערכת זכירה; בסוף תענו על כל 36 השאלות ללא הצגת הגרפים.")

    if st.button("התחל"):
        log_event("Start Experiment", {"group": st.session_state.group})
        if st.session_state.group in ["G1","G2"]:
            st.session_state.stage = "context"
        else:
            st.session_state.phase = "show"
            st.session_state.stage = "g3_show"
        st.rerun()

###############################################
# G1 — הקשר > גרף (מ-db) > Q1 > Q2 (עם הגרף מעל השאלה)
###############################################
elif st.session_state.group == "G1":
    row = st.session_state.filtered_df.iloc[st.session_state.graph_index]
    graph_id = current_graph_id(row)
    sub = get_graph_slice(graph_db, graph_id)

    if st.session_state.stage == "context":
        show_group_badge()
        show_rtl_text("הקשר לגרף הבא:", "h3")
        show_rtl_text(row.get("TheContext", ""))
        if st.button("המשך לגרף"):
            st.session_state.stage = "image"
            st.session_state.display_start_time = time.time()
            log_event("Show Context", {"chart": row['ChartNumber'], "graph_id": graph_id})
            st.rerun()

    elif st.session_state.stage == "image":
        show_group_badge()
        elapsed = time.time() - st.session_state.display_start_time
        remaining = max(0, int(DISPLAY_TIME_GRAPH - elapsed))
        show_timer_badge(remaining)
        draw_bar_chart(sub, title=f"גרף {row['ChartNumber']}")
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
        draw_bar_chart(sub)
        with st.form(key=f"g1_q{qn}_{row['ChartNumber']}"):
            show_rtl_text(f"גרף {row['ChartNumber']} — שאלה {qn}", "h3")
            show_rtl_text(qtxt)
            answer = st.radio("", opts, key=f"g1_a{qn}_{row['ChartNumber']}", index=None, label_visibility="collapsed",
                              format_func=lambda x: f"{chr(65 + opts.index(x))}. {x}")
            submitted = st.form_submit_button("המשך")
        if submitted or elapsed >= QUESTION_MAX_TIME:
            rt = round(elapsed, 2)
            record_answer(row, qn, answer, None, rt)  # ללא שאלת ביטחון בקבוצה 1
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
# G2 — הקשר > גרף (מ-db, 5ש') > Q1..Q3 (ללא הגרף)
###############################################
elif st.session_state.group == "G2":
    row = st.session_state.filtered_df.iloc[st.session_state.graph_index]
    graph_id = current_graph_id(row)
    sub = get_graph_slice(graph_db, graph_id)

    if st.session_state.stage == "context":
        show_group_badge()
        st.session_state.question_index = 0
        show_rtl_text("הקשר לגרף הבא:", "h3")
        show_rtl_text(row.get("TheContext", ""))
        if st.button("המשך לגרף"):
            st.session_state.stage = "g2_image"
            st.session_state.display_start_time = time.time()
            log_event("Show Context (G2)", {"chart": row['ChartNumber'], "graph_id": graph_id})
            st.rerun()

    elif st.session_state.stage == "g2_image":
        show_group_badge()
        elapsed = time.time() - st.session_state.display_start_time
        remaining = max(0, int(DISPLAY_TIME_GRAPH - elapsed))
        show_timer_badge(remaining)
        draw_bar_chart(sub, title=f"גרף {row['ChartNumber']}")
        if elapsed >= DISPLAY_TIME_GRAPH:
            st.session_state.stage = "g2_q"
            st.session_state.q_start_time = time.time()
            st.rerun()
        else:
            tick_and_rerun(1.0)

    elif st.session_state.stage == "g2_q":
        show_group_badge()
        qn = st.session_state.question_index + 1
        qtxt = row[f"Question{qn}Text"]
        opts = [row[f"Q{qn}OptionA"], row[f"Q{qn}OptionB"], row[f"Q{qn}OptionC"], row[f"Q{qn}OptionD"]]
        elapsed = time.time() - (st.session_state.q_start_time or time.time())
        remaining = max(0, int(QUESTION_MAX_TIME - elapsed))
        show_timer_badge(remaining)
        with st.form(key=f"g2_q{qn}_{row['ChartNumber']}"):
            show_rtl_text(f"גרף {row['ChartNumber']} — שאלה {qn}", "h3")
            show_rtl_text(qtxt)
            answer = st.radio("", opts, key=f"g2_a{qn}_{row['ChartNumber']}", index=None, label_visibility="collapsed",
                              format_func=lambda x: f"{chr(65 + opts.index(x))}. {x}")
            submitted = st.form_submit_button("המשך")
        if submitted or elapsed >= QUESTION_MAX_TIME:
            rt = round(elapsed, 2)
            record_answer(row, qn, answer, None, rt)  # אין שאלת ביטחון בקבוצה 2
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
# G3 — הצגת כל הגרפים (מ-db) + הערכת זכירה, ואז כל השאלות
###############################################
elif st.session_state.group == "G3":
    row = st.session_state.filtered_df.iloc[st.session_state.graph_index]
    graph_id = current_graph_id(row)
    sub = get_graph_slice(graph_db, graph_id)

    if st.session_state.stage == "g3_show" and st.session_state.phase == "show":
        show_group_badge()
        elapsed = 0 if st.session_state.display_start_time is None else time.time() - st.session_state.display_start_time
        remaining = max(0, int(DISPLAY_TIME_GRAPH - elapsed))
        show_timer_badge(remaining)
        draw_bar_chart(sub, title=f"גרף {row['ChartNumber']}")
        if st.session_state.display_start_time is None:
            st.session_state.display_start_time = time.time()
            log_event("Show Graph (G3)", {"chart": row['ChartNumber'], "graph_id": graph_id})
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
                "GraphID": graph_id,
                "group": st.session_state.group,
                "variation": st.session_state.variation,
                "timestamp": datetime.now().isoformat(),
                "phase": "show",
                "memory_estimate": memory
            })
            log_event("Memory Estimate (G3)", {"chart": row['ChartNumber'], "estimate": memory})
            save_and_advance_graph()
            st.rerun()

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
            answer = st.radio("", opts, key=f"g3_a{qn}_{row['ChartNumber']}", index=None, label_visibility="collapsed",
                              format_func=lambda x: f"{chr(65 + opts.index(x))}. {x}")
            confidence = st.slider("", 1, 5, step=1, key=f"g3_c{qn}_{row['ChartNumber']}", label_visibility="collapsed")
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
    df_log = pd.DataFrame(st.session_state.log if 'log' in st.session_state else [])
    results_dir = "experiment_results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    df_out.to_csv(f"{results_dir}/results_{timestamp}.csv", index=False)
    df_log.to_csv(f"{results_dir}/log_{timestamp}.csv", index=False)
    st.success("הקבצים נשמרו לתיקייה experiment_results.")

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
# * מעבר לשימוש בגרפים מתוך graph_DB.csv לפי עמודת ID (תמיכה גם ב-GraphID/ChartID/ID/ChartNumber ממסך השאלות).
# * בקבוצה 1 הגרף מוצג גם מעל השאלות; בקבוצה 2 הגרף מוצג רק לפני השאלות; בקבוצה 3 רק בשלב ההצגה.
# * ללא שימוש בתמונות; ImageFileName אינו נדרש עוד.
# * הוספת טיימר עליון וברענון עדין למניעת שגיאות 400.
