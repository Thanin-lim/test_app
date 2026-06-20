import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection
import hashlib

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Wedding Planner Dashboard", page_icon="💍", layout="wide")

# --- 💅 CUSTOM CSS (UI/UX UPGRADE) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600&display=swap');
        html, body, [class*="css"] { font-family: 'Kanit', sans-serif; }
        div.stButton > button { border-radius: 20px; font-weight: 500; transition: all 0.3s ease; border: 1px solid #fbcfe8; }
        div.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 10px rgba(219, 39, 119, 0.15); border-color: #f472b6; }
        div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #fce7f3; padding: 15px 20px; border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); transition: transform 0.2s ease; }
        div[data-testid="metric-container"]:hover { transform: scale(1.02); }
        h1, h2, h3 { color: #db2777; }
        div[data-testid="stForm"] { background-color: #fffafc; border-radius: 16px; border: 1px solid #fbcfe8; padding: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. AUTHENTICATION (SECURITY) ---
APP_PASSWORD_HASH = hashlib.sha256("imukko".encode('utf-8')).hexdigest()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #db2777; font-size: 3em;'>💍 Wedding Planner</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6b7280;'>Welcome to your magical journey</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='background-color: white; padding: 30px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #fce7f3;'>", unsafe_allow_html=True)
        pwd = st.text_input("🔑 รหัสผ่านเข้าสู่ระบบ:", type="password", placeholder="Enter your password...")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("เข้าสู่ระบบ 🤍", type="primary", use_container_width=True):
            pwd_hash = hashlib.sha256(pwd.encode('utf-8')).hexdigest()
            if pwd_hash == APP_PASSWORD_HASH:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 3. GOOGLE SHEETS CONNECTION & DATA PIPELINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_budget():
    try:
        df = conn.read(worksheet="Budget", usecols=[0], ttl=10)
        if not df.empty and pd.notna(df.iloc[0, 0]): return float(df.iloc[0, 0])
    except Exception: pass
    return 190000.00 

def save_budget(amount):
    try:
        df = pd.DataFrame({"Total Budget": [amount]})
        conn.update(worksheet="Budget", data=df)
    except Exception as e: st.error(f"❌ บันทึกล้มเหลว: {e}")

def load_expenses():
    try:
        df = conn.read(worksheet="Expenses", ttl=10)
        if not df.empty:
            df = df.dropna(how="all")
            if 'Status' not in df.columns: df['Status'] = 'ยังไม่ชำระเงิน'
            if 'Contact' not in df.columns: df['Contact'] = '' 
            if 'Amount' in df.columns: df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0.0)
            else: df['Amount'] = 0.0
            return df
    except Exception: pass
    return pd.DataFrame(columns=['Vendor', 'Category', 'Amount', 'Due Date', 'Status', 'Contact'])

def save_expenses(df):
    try: conn.update(worksheet="Expenses", data=df)
    except Exception as e: st.error(f"❌ บันทึกล้มเหลว: {e}")

def load_todos():
    try:
        df = conn.read(worksheet="Todos", ttl=10)
        if not df.empty:
            df = df.dropna(how="all")
            if 'Detail' not in df.columns: df['Detail'] = ''
            if not df.empty and 'Deadline' in df.columns:
                df['Deadline'] = pd.to_datetime(df['Deadline']).dt.date 
                return df
    except Exception: pass
    return pd.DataFrame({
        'Status': ['ยังไม่ได้เริ่ม', 'ยังไม่ได้เริ่ม'], 'Task': ['จองสถานที่จัดงาน', 'ลิสต์รายชื่อแขก'],
        'Deadline': [date(2026, 11, 24), date(2026, 12, 1)], 'Detail': ['โรงแรม หรือ สวนในเมือง', 'รวมญาติฝั่งเจ้าสาวและเจ้าบ่าว']
    })

def save_todos(df):
    try: conn.update(worksheet="Todos", data=df)
    except Exception as e: st.error(f"❌ บันทึกล้มเหลว: {e}")

def load_guests():
    try:
        df = conn.read(worksheet="Guests", ttl=10)
        if not df.empty:
            df = df.dropna(subset=['Guest Name'])
            if 'RSVP' not in df.columns: df['RSVP'] = 'รอการตอบรับ'
            if 'Table' not in df.columns: df['Table'] = '-' 
            for col in df.columns: df[col] = df[col].astype(str).replace(['nan', 'None', '<NA>'], '')
            return df
    except Exception: pass
    return pd.DataFrame(columns=['Guest Name', 'Side', 'Group', 'Note', 'RSVP', 'Table'])

def save_guests(df):
    try: conn.update(worksheet="Guests", data=df)
    except Exception as e: st.error(f"❌ บันทึกล้มเหลว: {e}")

def load_itinerary():
    try:
        df = conn.read(worksheet="Itinerary", ttl=10)
        if not df.empty:
            df = df.dropna(how="all")
            for col in ['Time', 'Activity', 'Location', 'PIC', 'Note']:
                if col not in df.columns: df[col] = ''
            return df
    except Exception: pass
    return pd.DataFrame(columns=['Time', 'Activity', 'Location', 'PIC', 'Note'])

def save_itinerary(df):
    try: conn.update(worksheet="Itinerary", data=df)
    except Exception as e: st.error(f"❌ บันทึกล้มเหลว: {e}")

# --- 4. INITIALIZE SESSION STATE & URL SYNC (Swipe to Go Back) ---
if 'page' not in st.query_params:
    st.query_params["page"] = "🏠 หน้าแรก (Dashboard)"

# ซิงค์หน้าปัจจุบันกับ URL Parameter เสมอ
st.session_state.page = st.query_params["page"]

# ฟังก์ชันสำหรับการเปลี่ยนหน้า (เพื่อดักจับ URL)
def navigate_to(page_name):
    st.query_params["page"] = page_name
    st.session_state.page = page_name
    st.rerun()

if 'expenses' not in st.session_state: st.session_state.expenses = load_expenses()
if 'total_budget' not in st.session_state: st.session_state.total_budget = load_budget()
if 'todos' not in st.session_state: st.session_state.todos = load_todos()
if 'guests' not in st.session_state: st.session_state.guests = load_guests()
if 'itinerary' not in st.session_state: st.session_state.itinerary = load_itinerary()

# --- 5. SIDEBAR NAVIGATION (แถบสไลด์เมนูด้านข้าง) ---
with st.sidebar:
    st.markdown("## 💍 Wedding Menu")
    menu_options = [
        "🏠 หน้าแรก (Dashboard)", 
        "📊 Budget Tracker", 
        "📝 สิ่งที่ต้องทำ (To-Do)", 
        "👥 รายชื่อแขก (Guest List)", 
        "⏱️ ตารางรันคิว (Itinerary)"
    ]
    
    selected_page = st.radio("เลือกหน้าการทำงาน:", menu_options, index=menu_options.index(st.session_state.page))
    if selected_page != st.session_state.page:
        navigate_to(selected_page)
        
    st.markdown("---")
    if st.button("🚪 ออกจากระบบ", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# --- CALLBACK FUNCTIONS ---
def on_expenses_edit():
    edited_rows = st.session_state.expense_editor.get("edited_rows", {})
    deleted_rows = st.session_state.expense_editor.get("deleted_rows", [])
    if edited_rows or deleted_rows:
        df = st.session_state.expenses.copy()
        if deleted_rows: df = df.drop(deleted_rows).reset_index(drop=True)
        for row_idx, changes in edited_rows.items():
            for col, val in changes.items():
                if col == 'Amount':
                    try: val = float(val)
                    except: val = 0.0
                df.at[int(row_idx), col] = val
        st.session_state.expenses = df; save_expenses(df)

def on_todos_edit():
    edited_rows = st.session_state.todo_editor.get("edited_rows", {})
    deleted_rows = st.session_state.todo_editor.get("deleted_rows", [])
    if edited_rows or deleted_rows:
        df = st.session_state.todos.copy()
        if deleted_rows: df = df.drop(deleted_rows).reset_index(drop=True)
        for row_idx, changes in edited_rows.items():
            for col, val in changes.items(): df.at[int(row_idx), col] = val
        df = df.dropna(subset=['Task'])
        st.session_state.todos = df; save_todos(df)

def on_guests_edit():
    edited_rows = st.session_state.guest_editor.get("edited_rows", {})
    deleted_rows = st.session_state.guest_editor.get("deleted_rows", [])
    if edited_rows or deleted_rows:
        df = st.session_state.guests.copy()
        if deleted_rows: df = df.drop(deleted_rows).reset_index(drop=True)
        for row_idx, changes in edited_rows.items():
            for col, val in changes.items(): df.at[int(row_idx), col] = val
        df = df.dropna(subset=['Guest Name'])
        st.session_state.guests = df; save_guests(df)

def on_itinerary_edit():
    edited_rows = st.session_state.itin_editor.get("edited_rows", {})
    deleted_rows = st.session_state.itin_editor.get("deleted_rows", [])
    if edited_rows or deleted_rows:
        df = st.session_state.itinerary.copy()
        if deleted_rows: df = df.drop(deleted_rows).reset_index(drop=True)
        for row_idx, changes in edited_rows.items():
            for col, val in changes.items(): df.at[int(row_idx), col] = val
        df = df.dropna(subset=['Activity'])
        st.session_state.itinerary = df; save_itinerary(df)


# ==========================================
# 🏠 หน้าแรก: EXECUTIVE DASHBOARD
# ==========================================
if st.session_state.page == "🏠 หน้าแรก (Dashboard)":
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #db2777;'>✨ Wedding Planner Dashboard ✨</h1>", unsafe_allow_html=True)
    
    total_spent = st.session_state.expenses['Amount'].sum() if not st.session_state.expenses.empty else 0.0
    budget_pct = min((total_spent / st.session_state.total_budget) * 100, 100) if st.session_state.total_budget > 0 else 0
    total_todos = len(st.session_state.todos)
    done_todos = len(st.session_state.todos[st.session_state.todos['Status'] == 'เสร็จแล้ว']) if total_todos > 0 else 0
    todo_pct = (done_todos / total_todos) * 100 if total_todos > 0 else 0
    total_guests = len(st.session_state.guests)
    rsvp_done = len(st.session_state.guests[st.session_state.guests['RSVP'] == 'ยืนยันเข้าร่วม']) if total_guests > 0 else 0
    guest_pct = (rsvp_done / total_guests) * 100 if total_guests > 0 else 0

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📈 สรุปภาพรวมการเตรียมงาน")
    dash1, dash2, dash3 = st.columns(3)
    with dash1:
        st.markdown(f"**💰 งบประมาณที่ใช้ไป ({budget_pct:.1f}%)**")
        st.progress(int(budget_pct))
        st.caption(f"ใช้ไป: ฿{total_spent:,.0f} / ฿{st.session_state.total_budget:,.0f}")
    with dash2:
        st.markdown(f"**✅ งานที่ทำเสร็จแล้ว ({todo_pct:.1f}%)**")
        st.progress(int(todo_pct))
        st.caption(f"เสร็จ: {done_todos} / {total_todos} รายการ")
    with dash3:
        st.markdown(f"**💌 แขกที่ยืนยันเข้าร่วม ({guest_pct:.1f}%)**")
        st.progress(int(guest_pct))
        st.caption(f"ตอบรับ: {rsvp_done} / {total_guests} ท่าน")

    st.markdown("<br><hr style='border: 1px solid #fce7f3;'><br>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>🗂️ เลือกหมวดหมู่การทำงาน</h3><br>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("💰 ระบบงบประมาณ", use_container_width=True): navigate_to("📊 Budget Tracker")
    with col2:
        if st.button("📝 สิ่งที่ต้องทำ", use_container_width=True): navigate_to("📝 สิ่งที่ต้องทำ (To-Do)")
    with col3:
        if st.button("👥 รายชื่อ & จัดโต๊ะ", use_container_width=True): navigate_to("👥 รายชื่อแขก (Guest List)")
    with col4:
        if st.button("⏱️ ตารางรันคิว", use_container_width=True): navigate_to("⏱️ ตารางรันคิว (Itinerary)")

# ==========================================
# PAGE 1: BUDGET TRACKER 
# ==========================================
elif st.session_state.page == "📊 Budget Tracker":
    if st.button("⬅️ กลับหน้าหลัก", type="secondary"): navigate_to("🏠 หน้าแรก (Dashboard)")
    st.title("💰 Wedding Budget Dashboard")
    st.markdown("---")

    set_col, add_col = st.columns([1, 2.5])
    with set_col:
        st.markdown("### ⚙️ ตั้งค่างบประมาณ")
        new_budget = st.number_input("ตั้งงบประมาณ (บาท):", min_value=0.0, value=st.session_state.total_budget, step=1000.0)
        if new_budget != st.session_state.total_budget:
            st.session_state.total_budget = new_budget
            save_budget(new_budget)
            
    with add_col:
        st.markdown("### ➕ เพิ่มค่าใช้จ่ายใหม่")
        with st.form("add_expense_form_main", clear_on_submit=True):
            v_col1, v_col2 = st.columns(2)
            vendor = v_col1.text_input("ชื่อร้านค้า/บริการ (Vendor)")
            category = v_col2.selectbox("หมวดหมู่", ["สถานที่", "อาหารและเครื่องดื่ม", "ชุด/แต่งหน้า", "ช่างภาพ/วิดีโอ", "ตกแต่ง/รันคิว", "อื่นๆ"])
            v_col3, v_col4 = st.columns(2)
            amount = v_col3.number_input("จำนวนเงิน (บาท)", min_value=0.0, step=1000.0)
            due_date = v_col4.date_input("กำหนดชำระเงิน", min_value=date.today())
            v_col5, v_col6 = st.columns(2)
            contact_info = v_col5.text_input("ช่องทางติดต่อ (เบอร์/Line)")
            payment_status = v_col6.selectbox("สถานะการจ่ายเงิน", ["ยังไม่ชำระเงิน", "ชำระเงินแล้ว"])
            
            if st.form_submit_button("💾 เพิ่มลงในบัญชี") and vendor and amount > 0:
                new_row = pd.DataFrame([{'Vendor': vendor, 'Category': category, 'Amount': float(amount), 'Due Date': due_date.strftime("%d %B %Y"), 'Status': payment_status, 'Contact': contact_info}])
                st.session_state.expenses = pd.concat([st.session_state.expenses, new_row], ignore_index=True)
                save_expenses(st.session_state.expenses); st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if not st.session_state.expenses.empty:
        def highlight_payment_status(val):
            return 'background-color: #dcfce7; color: #166534;' if val == 'ชำระเงินแล้ว' else 'background-color: #fee2e2; color: #991b1b;'
        st.data_editor(st.session_state.expenses.style.map(highlight_payment_status, subset=['Status']), hide_index=False, width='stretch', key="expense_editor", on_change=on_expenses_edit)

# ==========================================
# PAGE 2: TO-DO LIST 
# ==========================================
elif st.session_state.page == "📝 สิ่งที่ต้องทำ (To-Do)":
    if st.button("⬅️ กลับหน้าหลัก", type="secondary"): navigate_to("🏠 หน้าแรก (Dashboard)")
    st.title("📝 เตรียมสิ่งที่ต้องทำ (To-Do List)")
    st.markdown("---")

    with st.form("add_task_form_main", clear_on_submit=True):
        t_col1, t_col2 = st.columns([2, 1])
        task_name = t_col1.text_input("ชื่องานที่ต้องเตรียม")
        task_deadline = t_col2.date_input("กำหนดการเสร็จสิ้น", min_value=date.today())
        task_detail = st.text_area("รายละเอียด/สถานที่/โน้ตเพิ่มเติม")
        if st.form_submit_button("💾 เพิ่มงาน") and task_name:
            new_task = pd.DataFrame([{'Status': 'ยังไม่ได้เริ่ม', 'Task': task_name, 'Deadline': task_deadline, 'Detail': task_detail}])
            st.session_state.todos = pd.concat([st.session_state.todos, new_task], ignore_index=True)
            save_todos(st.session_state.todos); st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if not st.session_state.todos.empty:
        st.data_editor(
            st.session_state.todos,
            column_config={"Status": st.column_config.SelectboxColumn("📌 สถานะ", options=["ยังไม่ได้เริ่ม", "อยู่ระหว่างดำเนินการ", "หยุดไว้ชั่วคราว", "ไม่จำเป็น", "เสร็จแล้ว"])},
            hide_index=False, width='stretch', key="todo_editor", on_change=on_todos_edit
        )

# ==========================================
# PAGE 3: GUEST LIST & SEATING 
# ==========================================
elif st.session_state.page == "👥 รายชื่อแขก (Guest List)":
    if st.button("⬅️ กลับหน้าหลัก", type="secondary"): navigate_to("🏠 หน้าแรก (Dashboard)")
    st.title("👥 จัดการรายชื่อแขกและผังที่นั่ง")

    total_guests = len(st.session_state.guests)
    rsvp_confirmed = len(st.session_state.guests[st.session_state.guests['RSVP'] == 'ยืนยันเข้าร่วม']) if total_guests > 0 else 0
    rsvp_pending = len(st.session_state.guests[st.session_state.guests['RSVP'] == 'รอการตอบรับ']) if total_guests > 0 else 0
    rsvp_declined = len(st.session_state.guests[st.session_state.guests['RSVP'] == 'ไม่สามารถเข้าร่วมได้']) if total_guests > 0 else 0

    st.markdown("### 📊 สรุปจำนวนแขก")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("จำนวนแขกในลิสต์", f"{total_guests} คน")
    g2.metric("✅ ยืนยันเข้าร่วม", f"{rsvp_confirmed} คน")
    g3.metric("⏳ รอการตอบรับ", f"{rsvp_pending} คน")
    g4.metric("❌ ไม่ร่วมงาน", f"{rsvp_declined} คน")

    st.markdown("---")

    tab_edit, tab_seat = st.tabs(["✏️ จัดการรายชื่อ & RSVP", "🪑 จัดผังที่นั่ง (Seating)"])

    with tab_edit:
        with st.form("add_guest_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            guest_name = c1.text_input("ชื่อ-นามสกุล ของแขก")
            guest_side = c2.selectbox("ฝั่ง", ["ฝั่งเจ้าสาว", "ฝั่งเจ้าบ่าว", "แขกส่วนกลาง"])
            guest_group = c3.selectbox("กลุ่มบุคคล", ["ญาติผู้ใหญ่", "เพื่อนสนิท", "ที่ทำงาน", "อื่นๆ"])
            c4, c5, c6 = st.columns([2, 1, 1])
            guest_note = c4.text_input("หมายเหตุ (เช่น ทานมังสวิรัติ)")
            guest_rsvp = c5.selectbox("การตอบรับ", ["รอการตอบรับ", "ยืนยันเข้าร่วม", "ไม่สามารถเข้าร่วมได้"])
            guest_table = c6.text_input("หมายเลขโต๊ะ (เว้นไว้ก่อนได้)", value="-")
            
            if st.form_submit_button("💾 เพิ่มรายชื่อ") and guest_name:
                new_guest = pd.DataFrame([{'Guest Name': guest_name, 'Side': guest_side, 'Group': guest_group, 'Note': guest_note, 'RSVP': guest_rsvp, 'Table': guest_table}])
                st.session_state.guests = pd.concat([st.session_state.guests, new_guest], ignore_index=True)
                save_guests(st.session_state.guests); st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        if not st.session_state.guests.empty:
            st.data_editor(
                st.session_state.guests,
                column_config={
                    "RSVP": st.column_config.SelectboxColumn("💌 RSVP", options=["รอการตอบรับ", "ยืนยันเข้าร่วม", "ไม่สามารถเข้าร่วมได้"]),
                    "Side": st.column_config.SelectboxColumn("👥 ฝั่ง", options=["ฝั่งเจ้าสาว", "ฝั่งเจ้าบ่าว", "แขกส่วนกลาง"])
                },
                width='stretch', key="guest_editor", on_change=on_guests_edit
            )

    with tab_seat:
        st.markdown("### 🪑 ลิสต์จัดโต๊ะ (เฉพาะแขกที่ยืนยันเข้าร่วม)")
        if not st.session_state.guests.empty:
            confirmed_guests = st.session_state.guests[st.session_state.guests['RSVP'] == 'ยืนยันเข้าร่วม']
            if not confirmed_guests.empty:
                st.info("💡 ทริค: จัดกลุ่มแขกด้วยการพิมพ์ชื่อโต๊ะลงในคอลัมน์ Table เช่น 'VIP-1', 'Friend-A'")
                seat_df = confirmed_guests[['Guest Name', 'Group', 'Side', 'Table', 'Note']]
                st.dataframe(seat_df, width=1000)
                
                st.markdown("#### 📊 สรุปจำนวนโต๊ะ")
                table_summary = confirmed_guests[confirmed_guests['Table'] != '-']['Table'].value_counts().reset_index()
                table_summary.columns = ['Table Number / Name', 'Guest Count']
                st.table(table_summary)
            else:
                st.warning("ยังไม่มีแขกที่ยืนยันเข้าร่วมงาน (RSVP = ยืนยันเข้าร่วม)")

# ==========================================
# PAGE 4: ITINERARY (ตารางรันคิว)
# ==========================================
elif st.session_state.page == "⏱️ ตารางรันคิว (Itinerary)":
    if st.button("⬅️ กลับหน้าหลัก", type="secondary"): navigate_to("🏠 หน้าแรก (Dashboard)")
    st.title("⏱️ ตารางรันคิววันงาน")
    st.markdown("จัดเรียงลำดับพิธีการ สถานที่ และผู้รับผิดชอบ เพื่อให้ทุกฝ่ายทำงานตรงกัน")
    st.markdown("---")

    with st.form("add_itin_form", clear_on_submit=True):
        i1, i2 = st.columns([1, 3])
        time_val = i1.text_input("เวลา (เช่น 07:09 หรือ 07:00 - 08:00)")
        activity_val = i2.text_input("กิจกรรม / พิธีการ (เช่น แห่ขันหมาก, สวมแหวน)")
        
        i3, i4, i5 = st.columns([2, 1, 2])
        location_val = i3.text_input("สถานที่ (เช่น ห้องโถง A, สวนหน้าบ้าน)")
        pic_val = i4.text_input("ผู้รับผิดชอบ (PIC)")
        note_val = i5.text_input("สิ่งที่ต้องเตรียม / โน้ต")
        
        if st.form_submit_button("💾 เพิ่มคิวงาน") and activity_val:
            new_itin = pd.DataFrame([{'Time': time_val, 'Activity': activity_val, 'Location': location_val, 'PIC': pic_val, 'Note': note_val}])
            st.session_state.itinerary = pd.concat([st.session_state.itinerary, new_itin], ignore_index=True)
            save_itinerary(st.session_state.itinerary); st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if not st.session_state.itinerary.empty:
        st.data_editor(st.session_state.itinerary, width='stretch', key="itin_editor", on_change=on_itinerary_edit)