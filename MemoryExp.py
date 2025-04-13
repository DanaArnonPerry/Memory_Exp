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
    try:
        df = pd.read_csv("MemoryTest.csv", encoding='utf-8-sig')
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df.dropna(subset=['ChartNumber', 'Condition'], inplace=True)
        df['image_path'] = df['ImageFileName'].apply(lambda x: os.path.join("images", os.path.basename(str(x).strip())) if pd.notna(x) else '')
        return df
    except Exception as e:
        st.error(f"שגיאה בטעינת הקובץ CSV: {e}")
        return pd.DataFrame()

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

# בדיקת קיום תיקיית התמונות
if not os.path.exists("images"):
    st.error("תיקיית 'images' לא נמצאה. אנא צור תיקיה זו והוסף את התמונות הנדרשות.")
    st.stop()

df = load_data()

if df.empty:
    st.error("אין נתונים בקובץ MemoryTest.csv או שהקובץ לא נטען כראוי")
    st.stop()

if "variation" not in st.session_state:
    st.session_state.variation = random.choice(["V1", "V2", "V3", "V4"])
    st.session_state.filtered_df = df[df[st.session_state.variation] == 1].reset_index(drop=True)
    
    # בדיקה שיש נתונים לאחר הסינון
    if st.session_state.filtered_df.empty:
        st.error(f"אין נתונים בתנאי {st.session_state.variation}. אנא בדוק את קובץ ה-CSV.")
        st.stop()
        
    st.session_state.responses = []
    st.session_state.graph_index = 0
    st.session_state.stage = "welcome"
    log_event("Assigned Variation", st.session_state.variation)

if "display_start_time" not in st.session_state:
    st.session_state.display_start_time = None

if st.session_state.stage == "welcome":
    show_rtl_text("שלום וברוכ/ה הבא/ה לניסוי בזיכרון חזותי!", "h2")
    show_rtl_text("הניסוי יתבצע בשני חלקים, החלק הראשון יתבצע כעת והחלק השני יתבצע בעוד שעתיים. בחלק הראשון יוצגו 12 גרפים שעוסקים בנושאים שונים, כל גרף יוצג למשך חצי דקה ולאחריו תתבקש להעריך באיזו מידה תזכור את הנתונים לאחר שעתיים. בחלק השני יוצגו שאלות אמריקאיות שמתייחסות לגרפים שראית.")
    if st.button("המשך"):
        log_event("לחצן המשך - מסך פתיחה")
        st.session_state.stage = "context"
        st.rerun()

elif st.session_state.stage == "context":
    row = st.session_state.filtered_df.iloc[st.session_state.graph_index]
    st.session_state.current_row = row.to_dict()
    show_rtl_text("הקשר לגרף שיוצג:")
    show_rtl_text(row.get("TheContext", ""))
    show_rtl_text("להתחלת הניסוי לחץ 'המשך'")
    if st.button("המשך"):
        log_event("לחצן המשך - הצגת הקשר", row['ChartNumber'])
        st.session_state.stage = "image"
        st.session_state.display_start_time = time.time()
        st.rerun()

elif st.session_state.stage == "image":
    row = st.session_state.current_row
    
    # הגדרת זמן התצוגה - שנה זה ל-1 לפיתוח ול-30 לניסוי האמיתי
    DISPLAY_TIME = 1  # זמן תצוגה בשניות (שנה ל-30 לניסוי האמיתי)
    
    elapsed_time = time.time() - st.session_state.display_start_time
    remaining_time = max(0, DISPLAY_TIME - int(elapsed_time))
    
    show_rtl_text(f"הגרף יוצג למשך {remaining_time} שניות נוספות.")
    show_rtl_text(f"גרף מספר: {row['ChartNumber']} | תנאי: {row['Condition']}", "h4")
    
    image_path = row['image_path']
    if os.path.exists(image_path):
        st.image(image_path, use_container_width=True)
        log_event("הצגת גרף", row['ChartNumber'])
    else:
        show_rtl_text(f"תמונה לא נמצאה: {image_path}")
        log_event("תמונה חסרה", image_path)
    
    # אוטומטית למעבר לשלב הבא לאחר הזמן המוגדר
    if elapsed_time >= DISPLAY_TIME:
        st.session_state.stage = "eval"
        st.rerun()
    else:
        # הצגת כפתור רק כדי לאפשר רענון דף אוטומטי
        st.button("המתן...", disabled=True)
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
            
            # בדיקה אם זה הגרף האחרון
            if st.session_state.graph_index + 1 >= len(st.session_state.filtered_df):
                st.session_state.stage = "end"
            else:
                st.session_state.graph_index += 1
                st.session_state.stage = "context"
            
            st.rerun()

elif st.session_state.stage == "end":
    show_rtl_text("שלב א של הניסוי הסתיים, השלב הבא יחל בעוד שעתיים", "h2")
    
    # יצירת הקבצים והכנתם להורדה (מוסתר מהמשתתף)
    df_out = pd.DataFrame(st.session_state.responses)
    df_log = pd.DataFrame(st.session_state.log)
    
    # הוספת מידע נוסף לקובץ התוצאות
    df_out["variation"] = st.session_state.variation
    df_out["timestamp"] = datetime.now().isoformat()
    
    # שמירה אוטומטית של התוצאות
    results_dir = "experiment_results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    df_out.to_csv(f"{results_dir}/results_{timestamp}.csv", index=False)
    df_log.to_csv(f"{results_dir}/log_{timestamp}.csv", index=False)
    
    # לחצן להמשך לשלב ב' (ייעלם בהפעלה הסופית)
    # בדיקה אם זה מצב פיתוח/בדיקות
    is_dev_mode = st.sidebar.checkbox("מצב פיתוח", key="dev_mode", value=False)
    if is_dev_mode:
        if st.button("המשך לשלב ב' (לבדיקות בלבד)"):
            st.session_state.stage = "part2_start"
            st.rerun()
    
    # שמירת הנתונים למשתמש מיוחד (עם סיסמה או שם משתמש מסוים)
    if st.sidebar.checkbox("הצג כפתורי הורדה (למנהל מערכת בלבד)", key="admin_checkbox", value=False):
        admin_password = st.sidebar.text_input("סיסמת מנהל:", type="password", key="admin_password")
        if admin_password == "admin123":  # שנה לסיסמה שתבחר
            st.sidebar.download_button("הורד תוצאות (CSV)", df_out.to_csv(index=False), "results.csv", "text/csv")
            st.sidebar.download_button("הורד לוג מפורט (CSV)", df_log.to_csv(index=False), "log.csv", "text/csv")
            st.sidebar.success("ברוך הבא, מנהל המערכת!")
        elif admin_password:
            st.sidebar.error("סיסמה שגויה")
            
# הוספת שלב ב' לבדיקות
elif st.session_state.stage == "part2_start":
    show_rtl_text("ברוכים הבאים לשלב ב' של הניסוי!", "h2")
    show_rtl_text("בשלב זה תתבקש לענות על שאלות הקשורות לגרפים שראית בשלב א'.")
    
    if st.button("התחל שלב ב'"):
        # איפוס משתני שלב ב'
        st.session_state.part2_graph_index = 0
        st.session_state.part2_question_index = 0
        st.session_state.part2_responses = []
        st.session_state.stage = "part2_questions"
        st.rerun()
        
elif st.session_state.stage == "part2_questions":
    if st.session_state.part2_graph_index >= len(st.session_state.filtered_df):
        st.session_state.stage = "part2_end"
        st.rerun()
    
    row = st.session_state.filtered_df.iloc[st.session_state.part2_graph_index]
    qn = st.session_state.part2_question_index + 1  # שאלות מתחילות מ-1
    
    question_col = f"Question{qn}Text"
    option_cols = [f"Q{qn}OptionA", f"Q{qn}OptionB", f"Q{qn}OptionC", f"Q{qn}OptionD"]
    
    if all(col in row for col in option_cols) and question_col in row:
        options = [row[f"Q{qn}OptionA"], row[f"Q{qn}OptionB"], row[f"Q{qn}OptionC"], row[f"Q{qn}OptionD"]]
        
        with st.form(key=f"part2_form_q{qn}_{row['ChartNumber']}"):
            show_rtl_text(f"גרף {row['ChartNumber']} - שאלה {qn}", "h3")
            show_rtl_text(row[question_col])
            
            start_time = time.time()
            answer = show_question(row[question_col], options, f"part2_a{qn}_{row['ChartNumber']}")
            confidence = show_confidence(f"part2_c{qn}_{row['ChartNumber']}")
            
            submit = st.form_submit_button("המשך")
            if submit:
                rt = round(time.time() - start_time, 2)
                log_event(f"תשובה לשאלה {qn} בשלב ב'", {"answer": answer, "confidence": confidence, "rt": rt})
                
                # שמירת התשובה
                st.session_state.part2_responses.append({
                    "ChartNumber": row["ChartNumber"],
                    "Condition": row["Condition"],
                    f"question{qn}": row[question_col],
                    f"answer{qn}": answer,
                    f"confidence{qn}": confidence,
                    f"rt{qn}": rt
                })
                
                # מעבר לשאלה הבאה או לגרף הבא
                st.session_state.part2_question_index += 1
                if st.session_state.part2_question_index >= 3:  # 3 שאלות לכל גרף
                    st.session_state.part2_graph_index += 1
                    st.session_state.part2_question_index = 0
                
                st.rerun()
    else:
        st.error(f"חסרים נתונים לשאלה {qn} בגרף {row['ChartNumber']}. בדוק את קובץ ה-CSV.")
        if st.button("דלג לשאלה הבאה"):
            st.session_state.part2_question_index += 1
            if st.session_state.part2_question_index >= 3:
                st.session_state.part2_graph_index += 1
                st.session_state.part2_question_index = 0
            st.rerun()

elif st.session_state.stage == "part2_end":
    show_rtl_text("הניסוי הסתיים, תודה על השתתפותך!", "h2")
    
    # יצירת הקבצים והכנתם להורדה (מוסתר מהמשתתף)
    if "part2_responses" in st.session_state:
        df_part2 = pd.DataFrame(st.session_state.part2_responses)
        df_log = pd.DataFrame(st.session_state.log)
        
        # הוספת מידע נוסף לקובץ התוצאות
        df_part2["variation"] = st.session_state.variation
        df_part2["timestamp"] = datetime.now().isoformat()
        
        # שמירה אוטומטית של התוצאות
        results_dir = "experiment_results"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        df_part2.to_csv(f"{results_dir}/results_part2_{timestamp}.csv", index=False)
        df_log.to_csv(f"{results_dir}/log_part2_{timestamp}.csv", index=False)
        
        # כפתורי הורדה למנהל מערכת
        if st.sidebar.checkbox("הצג כפתורי הורדה (למנהל מערכת בלבד)", key="admin_part2", value=False):
            admin_password = st.sidebar.text_input("סיסמת מנהל:", type="password", key="admin_password_part2")
            if admin_password == "admin123":
                st.sidebar.download_button("הורד תוצאות שלב ב' (CSV)", df_part2.to_csv(index=False), "results_part2.csv", "text/csv")
                st.sidebar.download_button("הורד לוג מפורט (CSV)", df_log.to_csv(index=False), "log_part2.csv", "text/csv")
                st.sidebar.success("ברוך הבא, מנהל המערכת!")
