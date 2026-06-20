import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Wedding Planner Dashboard", page_icon="💍", layout="wide")

# --- 2. AUTHENTICATION (SECURITY) ---
# แนะนำให้เปลี่ยนรหัสผ่าน หรือย้ายไปตั้งค่าใน .streamlit/secrets.toml สำหรับการ Deploy จริง
APP_PASSWORD = "wedding2026"

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #db2777;'>💍 Wedding Planner Dashboard</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.info("กรุณาใส่รหัสผ่านเพื่อเข้าสู่ระบบจัดการงานแต่งงาน")
        pwd = st.text_input("Password:", type="password")
        if st.button("เข้าสู่ระบบ", type="primary", use_container_width=True):
            if pwd == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ รหัสผ่านไม่ถูกต้อง")
    st.stop() # หยุดการทำงานชั่วคราวถ้ายังไม่ Login

# --- 3. GOOGLE SHEETS CONNECTION & DATA PIPELINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_budget():
    try:
        # ปรับ ttl=10 เพื่อลดคอขวดของการเรียก API
        df = conn.read(worksheet="Budget", usecols=[0], ttl=10)
        if not df.empty and pd.notna(df.iloc[0, 0]):
            return float(df.iloc[0, 0])
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถโหลดข้อมูลงบประมาณได้: {e}")
    return 190000.00 

def save_budget(amount):
    try:
        df = pd.DataFrame({"Total Budget": [amount]})
        conn.update(worksheet="Budget", data=df)
    except Exception as e:
        st.error(f"❌ บันทึกงบประมาณล้มเหลว: {e}")

def load_expenses():
    try:
        df = conn.read(worksheet="Expenses", ttl=10)
        if not df.empty:
            df = df.dropna(how="all")
            # จัดการ Default Values สำหรับ Schema Evolution
            if 'Status' not in df.columns: df['Status'] = 'ยังไม่ชำระเงิน'
            if 'Contact' not in df.columns: df['Contact'] = '' # ฟิลด์ใหม่
            if 'Amount' in df.columns:
                df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0.0)
            else:
                df['Amount'] = 0.0
            return df
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถโหลดข้อมูลค่าใช้จ่ายได้: {e}")
    return pd.DataFrame(columns=['Vendor', 'Category', 'Amount', 'Due Date', 'Status', 'Contact'])

def save_expenses(df):
    try:
        conn.update(worksheet="Expenses", data=df)
    except Exception as e:
        st.error(f"❌ บันทึกค่าใช้จ่ายล้มเหลว: {e}")

def load_todos():
    try:
        df = conn.read(worksheet="Todos", ttl=10)
        if not df.empty:
            df = df.dropna(how="all")
            if 'Detail' not in df.columns: df['Detail'] = ''
            if not df.empty and 'Deadline' in df.columns:
                df['Deadline'] = pd.to_datetime(df['Deadline']).dt.date 
                return df
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถโหลดข้อมูล To-Do ได้: {e}")
    return pd.DataFrame({
        'Status': ['ยังไม่ได้เริ่ม', 'ยังไม่ได้เริ่ม'],
        'Task': ['จองสถานที่จัดงาน', 'ลิสต์รายชื่อแขก'],
        'Deadline': [date(2026, 11, 24), date(2026, 12, 1)],
        'Detail': ['โรงแรม Centara หรือ สวนในเมือง', 'รวมญาติฝั่งเจ้าสาวและเจ้าบ่าว ประมาณ 200 คน']
    })

def save_todos(df):
    try:
        conn.update(worksheet="Todos", data=df)
    except Exception as e:
        st.error(f"❌ บันทึก To-Do ล้มเหลว: {e}")

def load_guests():
    try:
        df = conn.read(worksheet="Guests", ttl=10)
        if not df.empty:
            df = df.dropna(subset=['Guest Name'])
            # จัดการ Default Values
            if 'RSVP' not in df.columns: df['RSVP'] = 'รอการตอบรับ' # ฟิลด์ใหม่
            for col in df.columns:
                df[col] = df[col].astype(str).replace(['nan', 'None', '<NA>'], '')
            return df
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถโหลดข้อมูลรายชื่อแขกได้: {e}")
    return pd.DataFrame(columns=['Guest Name', 'Side', 'Group', 'Note', 'RSVP'])

def save_guests(df):
    try:
        conn.update(worksheet="Guests", data=df)
    except Exception as e:
        st.error(f"❌ บันทึกรายชื่อแขกล้มเหลว: {e}")

def get_thai_month_year(date_val):
    try:
        d = pd.to_datetime(date_val)
        thai_months = [
            "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", 
            "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
        ]
        return f"{thai_months[d.month - 1]} {d.year}"
    except:
        return "ไม่ระบุ"

# --- 4. INITIALIZE SESSION STATE ---
if 'expenses' not in st.session_state: st.session_state.expenses = load_expenses()
if 'total_budget' not in st.session_state: st.session_state.total_budget = load_budget()
if 'todos' not in st.session_state: st.session_state.todos = load_todos()
if 'guests' not in st.session_state: st.session_state.guests = load_guests()
if 'page' not in st.session_state: st.session_state.page = "🏠 หน้าแรก"

# --- CALLBACK FUNCTIONS ---
def on_expenses_edit():
    edited_rows = st.session_state.expense_editor.get("edited_rows", {})
    deleted_rows = st.session_state.expense_editor.get("deleted_rows", [])
    added_rows = st.session_state.expense_editor.get("added_rows", [])
    
    if edited_rows or deleted_rows or added_rows:
        df = st.session_state.expenses.copy()
        if deleted_rows:
            df = df.drop(deleted_rows).reset_index(drop=True)
        for row_idx, changes in edited_rows.items():
            for col, val in changes.items():
                if col == 'Amount':
                    try: val = float(val)
                    except: val = 0.0
                df.at[int(row_idx), col] = val
        for row in added_rows:
            if 'Amount' in row:
                try: row['Amount'] = float(row['Amount'])
                except: row['Amount'] = 0.0
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            
        st.session_state.expenses = df
        save_expenses(df)

def on_todos_edit():
    edited_rows = st.session_state.todo_editor.get("edited_rows", {})
    deleted_rows = st.session_state.todo_editor.get("deleted_rows", [])
    
    if edited_rows or deleted_rows:
        df = st.session_state.todos.copy()
        if deleted_rows:
            df = df.drop(deleted_rows).reset_index(drop=True)
        for row_idx, changes in edited_rows.items():
            for col, val in changes.items():
                df.at[int(row_idx), col] = val
                
        df = df.dropna(subset=['Task'])
        st.session_state.todos = df
        save_todos(df)

def on_guests_edit():
    edited_rows = st.session_state.guest_editor.get("edited_rows", {})
    deleted_rows = st.session_state.guest_editor.get("deleted_rows", [])
    
    if edited_rows or deleted_rows:
        df = st.session_state.guests.copy()
        if deleted_rows:
            df = df.drop(deleted_rows).reset_index(drop=True)
        for row_idx, changes in edited_rows.items():
            for col, val in changes.items():
                df.at[int(row_idx), col] = val
        
        df = df.dropna(subset=['Guest Name'])
        st.session_state.guests = df
        save_guests(df)


# ==========================================
# 🏠 หน้าแรก: เลือกหมวดหมู่ 
# ==========================================
if st.session_state.page == "🏠 หน้าแรก":
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #db2777;'>💍 Wedding Planner Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #4b5563; font-size: 18px;'>ยินดีต้อนรับสู่ระบบจัดการงานแต่งงาน กรุณาเลือกหมวดหมู่ที่ต้องการทำงานด้านล่างนี้ค่ะ</p>", unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background-color: #f0fdf4; padding: 24px; border-radius: 12px; border: 1px solid #bbf7d0; text-align: center; min-height: 200px;">
            <h2 style="color: #16a34a; margin-top: 0;">📊 Budget Tracker</h2>
            <p style="color: #4b5563;">จัดการงบประมาณ บันทึกค่าใช้จ่าย ตรวจสอบสถานะการจ่ายเงินร้านค้า และช่องทางติดต่อ</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("💰 เปิดระบบงบประมาณ", use_container_width=True, type="primary"):
            st.session_state.page = "📊 Budget Tracker"
            st.rerun()
            
    with col2:
        st.markdown("""
        <div style="background-color: #fffbeb; padding: 24px; border-radius: 12px; border: 1px solid #fef08a; text-align: center; min-height: 200px;">
            <h2 style="color: #d97706; margin-top: 0;">📝 To-Do List</h2>
            <p style="color: #4b5563;">ติดตามและอัปเดตสิ่งสำคัญที่ต้องทำ จัดกลุ่มกำหนดการแยกรายเดือนเพื่อไม่ให้พลาดทุกดีเทลงาน</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("✏️ เปิดรายการสิ่งที่ต้องทำ", use_container_width=True, type="primary"):
            st.session_state.page = "📝 สิ่งที่ต้องทำ (To-Do)"
            st.rerun()
            
    with col3:
        st.markdown("""
        <div style="background-color: #fdf2f8; padding: 24px; border-radius: 12px; border: 1px solid #fbcfe8; text-align: center; min-height: 200px;">
            <h2 style="color: #db2777; margin-top: 0;">👥 Guest List</h2>
            <p style="color: #4b5563;">จัดการรายชื่อแขก แยกกลุ่มญาติ/เพื่อน และติดตามสถานะการตอบรับ (RSVP)</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🤝 เปิดระบบจัดการแขก", use_container_width=True, type="primary"):
            st.session_state.page = "👥 รายชื่อแขก (Guest List)"
            st.rerun()


# ==========================================
# PAGE 1: BUDGET TRACKER 
# ==========================================
elif st.session_state.page == "📊 Budget Tracker":
    if st.button("⬅️ กลับหน้าหลัก", type="secondary"):
        st.session_state.page = "🏠 หน้าแรก"
        st.rerun()
        
    st.title("💍 Wedding Budget Dashboard")
    st.markdown("---")

    set_col, add_col = st.columns(2)
    
    with set_col:
        st.markdown("### ⚙️ ตั้งค่างบประมาณ")
        new_budget = st.number_input("ตั้งงบประมาณทั้งหมด (บาท):", min_value=0.0, value=st.session_state.total_budget, step=1000.0)
        if new_budget != st.session_state.total_budget:
            st.session_state.total_budget = new_budget
            save_budget(new_budget)
            
    with add_col:
        st.markdown("### ➕ เพิ่มค่าใช้จ่ายใหม่")
        with st.form("add_expense_form_main", clear_on_submit=True):
            v_col1, v_col2 = st.columns(2)
            vendor = v_col1.text_input("ชื่อร้านค้า/บริการ (Vendor)", placeholder="เช่น โรงแรม, ช่างภาพ...")
            category = v_col2.selectbox("หมวดหมู่", ["Venue (สถานที่จัดงานแต่ง)", "Food & Beverage (อาหารและเครื่องดื่ม)", "Attire (ชุดในงานแต่งงาน)", "Photography & Video (ช่างภาพ/วิดีโอ)", "Entertainment (ความบันเทิง)", "Other (อื่นๆ)"])
            
            v_col3, v_col4 = st.columns(2)
            amount = v_col3.number_input("จำนวนเงิน (บาท)", min_value=0.0, step=1000.0)
            due_date = v_col4.date_input("กำหนดชำระเงิน", min_value=date.today())
            
            v_col5, v_col6 = st.columns(2)
            contact_info = v_col5.text_input("ช่องทางติดต่อ (เบอร์/Line)")
            payment_status = v_col6.selectbox("สถานะการจ่ายเงิน", ["ยังไม่ชำระเงิน", "ชำระเงินแล้ว"])
            
            submit_button = st.form_submit_button("💾 เพิ่มลงในบัญชี")
            
            if submit_button and vendor and amount > 0:
                new_row = pd.DataFrame([{'Vendor': vendor, 'Category': category, 'Amount': float(amount), 'Due Date': due_date.strftime("%d %B %Y"), 'Status': payment_status, 'Contact': contact_info}])
                st.session_state.expenses = pd.concat([st.session_state.expenses, new_row], ignore_index=True)
                save_expenses(st.session_state.expenses)
                st.success("เพิ่มค่าใช้จ่ายเรียบร้อยแล้ว!")
                st.rerun()

    st.markdown("---")
    
    total_spent = st.session_state.expenses['Amount'].sum() if not st.session_state.expenses.empty else 0.0
    remaining_budget = st.session_state.total_budget - total_spent

    if not st.session_state.expenses.empty:
        paid_amount = st.session_state.expenses[st.session_state.expenses['Status'] == 'ชำระเงินแล้ว']['Amount'].sum()
        unpaid_amount = total_spent - paid_amount
    else:
        paid_amount, unpaid_amount = 0.0, 0.0

    st.markdown("### 💰 สรุปสถานะการเงิน")
    m1, m2, m3 = st.columns(3)
    m1.metric("งบประมาณทั้งหมด", f"฿ {st.session_state.total_budget:,.0f}")
    m2.metric("ยอดรวมค่าใช้จ่ายทั้งหมด", f"฿ {total_spent:,.0f}", f"{(total_spent/st.session_state.total_budget)*100:.1f}%" if st.session_state.total_budget > 0 else "")
    m3.metric("งบประมาณคงเหลือ", f"฿ {remaining_budget:,.0f}")
    
    s1, s2 = st.columns(2)
    s1.metric("🟢 จ่ายเงินแล้วทั้งหมด", f"฿ {paid_amount:,.0f}")
    s2.metric("🔴 ยังไม่จ่ายทั้งหมด", f"฿ {unpaid_amount:,.0f}")

    st.markdown("---")
    tab_chart, tab_table = st.tabs(["📊 สัดส่วนค่าใช้จ่าย", "📝 ประวัติและการเปลี่ยนสถานะ"])
    
    with tab_chart:
        if not st.session_state.expenses.empty:
            fig = px.pie(st.session_state.expenses, values='Amount', names='Category', hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.add_annotation(text=f"<b>฿ {total_spent:,.0f}</b><br>Total Cost", x=0.5, y=0.5, font_size=18, showarrow=False)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("กรุณาเพิ่มค่าใช้จ่ายด้านบนก่อนเพื่อดูแผนภูมิ")

    with tab_table:
        if not st.session_state.expenses.empty:
            st.markdown(f"**📊 รายการค่าใช้จ่ายในระบบ (มีทั้งหมด {len(st.session_state.expenses)} รายการ):**")
            def highlight_payment_status(val):
                if val == 'ชำระเงินแล้ว': return 'background-color: #dcfce7; color: #166534;'
                elif val == 'ยังไม่ชำระเงิน': return 'background-color: #fee2e2; color: #991b1b;'
                return ''
            styled_expenses = st.session_state.expenses.style.map(highlight_payment_status, subset=['Status'])
            st.data_editor(
                styled_expenses,
                column_config={
                    "Vendor": st.column_config.TextColumn("ร้านค้า", width="medium"),
                    "Contact": st.column_config.TextColumn("📞 ช่องทางติดต่อ", width="medium"),
                    "Category": None, "Due Date": None,  
                    "Amount": st.column_config.NumberColumn("จำนวนเงิน (บาท)", format="%d", min_value=0, default=0, required=True, width="medium"),
                    "Status": st.column_config.SelectboxColumn("📌 Status", options=["ยังไม่ชำระเงิน", "ชำระเงินแล้ว"], required=True, width="medium")
                },
                hide_index=False, width='stretch', num_rows="dynamic", key="expense_editor", on_change=on_expenses_edit
            )


# ==========================================
# PAGE 2: TO-DO LIST 
# ==========================================
elif st.session_state.page == "📝 สิ่งที่ต้องทำ (To-Do)":
    if st.button("⬅️ กลับหน้าหลัก", type="secondary"):
        st.session_state.page = "🏠 หน้าแรก"
        st.rerun()
        
    st.title("📝 เตรียมสิ่งที่ต้องทำ (To-Do List)")
    st.markdown("---")

    st.markdown("### ➕ เพิ่มงานที่ต้องทำใหม่")
    with st.form("add_task_form_main", clear_on_submit=True):
        t_col1, t_col2 = st.columns([2, 1])
        task_name = t_col1.text_input("ชื่องานที่ต้องเตรียม", placeholder="เช่น เตรียมของชำร่วย, มัดจำชุดแต่งงาน...")
        task_deadline = t_col2.date_input("กำหนดการเสร็จสิ้น", min_value=date.today())
        task_detail = st.text_area("รายละเอียด/สถานที่/โน้ตเพิ่มเติม", placeholder="ระบุรายละเอียดงานช่วยจำตรงนี้...")
        add_task_btn = st.form_submit_button("💾 เพิ่มงาน")
        
        if add_task_btn and task_name:
            new_task = pd.DataFrame([{'Status': 'ยังไม่ได้เริ่ม', 'Task': task_name, 'Deadline': task_deadline, 'Detail': task_detail}])
            st.session_state.todos = pd.concat([st.session_state.todos, new_task], ignore_index=True)
            save_todos(st.session_state.todos) 
            st.rerun()

    st.markdown("---")
    
    if not st.session_state.todos.empty:
        status_counts = st.session_state.todos['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        total_tasks = len(st.session_state.todos)
        completed_tasks = len(st.session_state.todos[st.session_state.todos['Status'] == 'เสร็จแล้ว'])
        color_map = {'ยังไม่ได้เริ่ม': '#9ca3af', 'อยู่ระหว่างดำเนินการ': '#fbbf24', 'หยุดไว้ชั่วคราว': '#fb923c', 'ไม่จำเป็น': '#f87171', 'เสร็จแล้ว': '#4ade80'}
        fig_todo = px.pie(status_counts, values='Count', names='Status', hole=0.6, color='Status', color_discrete_map=color_map)
        fig_todo.add_annotation(text=f"<b>{completed_tasks} / {total_tasks}</b><br>ทำเสร็จแล้ว", x=0.5, y=0.5, font_size=18, showarrow=False)
        fig_todo.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)) 
        st.plotly_chart(fig_todo, width='stretch')
        st.markdown("---")

    tab_edit, tab_view = st.tabs(["✏️ อัปเดตสถานะและรายละเอียด", "📌 ภาพรวมรายเดือน"])
    
    with tab_edit:
        if not st.session_state.todos.empty:
            st.markdown(f"**📋 รายการสิ่งที่ต้องทำในตาราง (กดปุ่มถังขยะเพื่อลบ หรือเปลี่ยนสถานะได้ทันที):**")
            def highlight_status(val):
                colors = {
                    'ยังไม่ได้เริ่ม': '#f3f4f6', 
                    'อยู่ระหว่างดำเนินการ': '#fef3c7', 
                    'หยุดไว้ชั่วคราว': '#ffedd5', 
                    'ไม่จำเป็น': '#fee2e2', 
                    'เสร็จแล้ว': '#dcfce7'
                }
                bg_color = colors.get(val, '')
                return f"background-color: {bg_color}; color: #1f2937;"

            styled_todos = st.session_state.todos.style.map(highlight_status, subset=['Status'])
            st.data_editor(
                styled_todos,
                column_config={
                    "Status": st.column_config.SelectboxColumn("📌 สถานะ", options=["ยังไม่ได้เริ่ม", "อยู่ระหว่างดำเนินการ", "หยุดไว้ชั่วคราว", "ไม่จำเป็น", "เสร็จแล้ว"], required=True, width="medium"),
                    "Task": st.column_config.TextColumn("📋 งาน", width="medium"), 
                    "Deadline": st.column_config.DateColumn("📅 กำหนด", format="DD/MM/YYYY", width="small"),
                    "Detail": st.column_config.TextColumn("🏠 รายละเอียด", width="large")
                },
                hide_index=False, width='stretch', num_rows="dynamic", key="todo_editor", on_change=on_todos_edit
            )

    with tab_view:
        if not st.session_state.todos.empty:
            col_left, col_right = st.columns([1.2, 1.0]) 
            with col_left:
                st.markdown("### 📅 รายการงานรายเดือน")
                view_df = st.session_state.todos.copy()
                view_df['SortDate'] = pd.to_datetime(view_df['Deadline'])
                view_df = view_df.sort_values('SortDate')
                view_df['MonthGroup'] = view_df['SortDate'].apply(get_thai_month_year)
                
                html_content = ""
                for month_group in view_df['MonthGroup'].unique():
                    html_content += f"<h4 style='color: #4b5563; border-bottom: 2px solid #e5e7eb; padding-bottom: 4px; margin-top: 20px; font-size: 16px;'>📅 {month_group}</h4>"
                    month_tasks = view_df[view_df['MonthGroup'] == month_group]
                    for _, row in month_tasks.iterrows():
                        display_date = row['SortDate'].strftime("%d/%m/%Y")
                        detail_val = row['Detail'] if pd.notna(row['Detail']) and row['Detail'] != "" else "-"
                        html_content += f"""<div style="padding: 12px; margin-bottom: 8px; border-radius: 8px; border: 1px solid #e5e7eb; background-color: #fafafa;">
<div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px; margin-bottom: 6px;">
<span style="font-weight: 600; font-size: 14px;">{row['Task']}</span>
</div>
<div style="color: #6b7280; font-size: 12px; margin-bottom: 4px;">📅 ครบกำหนด: {display_date}</div>
<div style="color: #4b5563; font-size: 13px; background-color: #f3f4f6; padding: 6px; border-radius: 4px; margin-top: 4px;">🏠 รายละเอียด: {detail_val}</div>
</div>"""
                st.markdown(html_content, unsafe_allow_html=True)
                
            with col_right:
                st.markdown("### 🔍 ตรวจสอบรายละเอียดรายชิ้น")
                task_list = st.session_state.todos['Task'].tolist()
                selected_task = st.selectbox("เลือกงานเพื่อดู Note ตัวโตๆ:", task_list, index=0 if task_list else None)
                if selected_task:
                    filtered_todo = st.session_state.todos[st.session_state.todos['Task'] == selected_task]
                    if not filtered_todo.empty:
                        task_info = filtered_todo.iloc[0]
                        detail_text = task_info['Detail'] if pd.notna(task_info['Detail']) and task_info['Detail'] != "" else "ไม่มีการระบุรายละเอียด"
                        st.info(f"**📋 ชื่องาน:** {task_info['Task']} \n\n**📅 วันครบกำหนด:** {task_info['Deadline'].strftime('%d/%m/%Y') if hasattr(task_info['Deadline'], 'strftime') else task_info['Deadline']} \n\n**📌 สถานะปัจจุบัน:** {task_info['Status']} \n\n**🏠 รายละเอียด/Note สำคัญ:** {detail_text}")


# ==========================================
# PAGE 3: GUEST LIST (มีระบบ RSVP)
# ==========================================
elif st.session_state.page == "👥 รายชื่อแขก (Guest List)":
    if st.button("⬅️ กลับหน้าหลัก", type="secondary"):
        st.session_state.page = "🏠 หน้าแรก"
        st.rerun()
        
    st.title("👥 ระบบจัดการและเพิ่มรายชื่อแขก")
    st.write("บันทึกรายชื่อแขก แยกฝั่งเจ้าสาว/เจ้าบ่าว และติดตามสถานะการตอบรับเข้าร่วมงาน")

    total_guests = len(st.session_state.guests)
    rsvp_confirmed = len(st.session_state.guests[st.session_state.guests['RSVP'] == 'ยืนยันเข้าร่วม'])
    rsvp_declined = len(st.session_state.guests[st.session_state.guests['RSVP'] == 'ไม่สามารถเข้าร่วมได้'])

    st.markdown("### 📊 สรุปจำนวนแขกปัจจุบัน")
    g1, g2, g3 = st.columns(3)
    g1.metric("จำนวนแขกในลิสต์ทั้งหมด", f"{total_guests} คน")
    g2.metric("✅ ยืนยันเข้าร่วมแล้ว", f"{rsvp_confirmed} คน")
    g3.metric("❌ ไม่สามารถเข้าร่วมได้", f"{rsvp_declined} คน")

    st.markdown("---")

    tab_guest_edit, tab_guest_view = st.tabs(["✏️ เพิ่ม/ลบ/แก้ไข รายชื่อทั้งหมด", "🔍 ค้นหาและดูการ์ดชื่อแขก"])

    with tab_guest_edit:
        st.markdown("### ➕ เพิ่มชื่อแขกใหม่")
        with st.form("add_guest_form_main", clear_on_submit=True):
            f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
            guest_name = f_col1.text_input("ชื่อ-นามสกุล ของแขก", placeholder="พิมพ์ชื่อตรงนี้...")
            guest_side = f_col2.selectbox("แขกฝั่งไหน?", ["ฝั่งเจ้าสาว", "ฝั่งเจ้าบ่าว", "แขกส่วนกลาง"])
            guest_group = f_col3.selectbox("กลุ่มบุคคล", ["ญาติผู้ใหญ่", "เพื่อนสนิท", "เพื่อนที่ทำงาน", "เพื่อนสมัยเรียน", "อื่นๆ"])
            
            f_col4, f_col5 = st.columns([2, 1])
            guest_note = f_col4.text_input("หมายเหตุเพิ่มเติม (เช่น มา 2 ท่าน, ทานมังสวิรัติ)", placeholder="ระบุโน้ตเพิ่มเติม (ถ้ามี)")
            guest_rsvp = f_col5.selectbox("สถานะการตอบรับ", ["รอการตอบรับ", "ยืนยันเข้าร่วม", "ไม่สามารถเข้าร่วมได้"])
            
            add_guest_btn = st.form_submit_button("💾 กดบันทึกรายชื่อแขก")
            
            if add_guest_btn and guest_name:
                new_guest = pd.DataFrame([{'Guest Name': guest_name, 'Side': guest_side, 'Group': guest_group, 'Note': guest_note, 'RSVP': guest_rsvp}])
                st.session_state.guests = pd.concat([st.session_state.guests, new_guest], ignore_index=True)
                save_guests(st.session_state.guests)
                st.success(f"บันทึกคุณ '{guest_name}' ลงระบบเรียบร้อย!")
                st.rerun()

        st.markdown("---")
        
        if not st.session_state.guests.empty:
            st.markdown(f"**📋 รายชื่อแขกทั้งหมดในระบบ (แก้ไขข้อมูลหรือสถานะ RSVP ในตารางได้เลย):**")
            
            def highlight_rsvp(val):
                if val == 'ยืนยันเข้าร่วม': return 'background-color: #dcfce7;'
                elif val == 'ไม่สามารถเข้าร่วมได้': return 'background-color: #fee2e2;'
                return ''
                
            styled_guests = st.session_state.guests.style.map(highlight_rsvp, subset=['RSVP'])
            
            st.data_editor(
                styled_guests,
                column_config={
                    "Guest Name": st.column_config.TextColumn("📝 ชื่อแขก", required=True, width="medium"),
                    "Side": st.column_config.SelectboxColumn("👥 ฝั่ง", options=["ฝั่งเจ้าสาว", "ฝั่งเจ้าบ่าว", "แขกส่วนกลาง"], width="medium"),
                    "Group": st.column_config.SelectboxColumn("📂 กลุ่ม", options=["ญาติผู้ใหญ่", "เพื่อนสนิท", "เพื่อนที่ทำงาน", "เพื่อนสมัยเรียน", "อื่นๆ"], width="small"),
                    "RSVP": st.column_config.SelectboxColumn("💌 การตอบรับ", options=["รอการตอบรับ", "ยืนยันเข้าร่วม", "ไม่สามารถเข้าร่วมได้"], width="medium"),
                    "Note": st.column_config.TextColumn("📌 หมายเหตุ", width="medium")
                },
                hide_index=False, width='stretch', num_rows="dynamic", key="guest_editor", on_change=on_guests_edit
            )
        else:
            st.info("ยังไม่มีการบันทึกรายชื่อแขก")

    with tab_guest_view:
        if not st.session_state.guests.empty:
            st.markdown("### 🔍 ค้นหาและดูรายละเอียดแขก")
            search_query = st.text_input("พิมพ์ชื่อแขกเพื่อค้นหา (รองรับทั้งชื่อและนามสกุล):", placeholder="พิมพ์ชื่อตรงนี้...")
            
            v_col1, v_col2, v_col3 = st.columns(3)
            filter_side = v_col1.selectbox("ตัวกรองฝั่ง:", ["ทั้งหมด", "ฝั่งเจ้าสาว", "ฝั่งเจ้าบ่าว", "แขกส่วนกลาง"])
            filter_group = v_col2.selectbox("ตัวกรองกลุ่ม:", ["ทั้งหมด", "ญาติผู้ใหญ่", "เพื่อนสนิท", "เพื่อนที่ทำงาน", "เพื่อนสมัยเรียน", "อื่นๆ"])
            filter_rsvp = v_col3.selectbox("สถานะตอบรับ:", ["ทั้งหมด", "รอการตอบรับ", "ยืนยันเข้าร่วม", "ไม่สามารถเข้าร่วมได้"])
            
            display_df = st.session_state.guests.copy()
            if search_query:
                display_df = display_df[display_df['Guest Name'].str.contains(search_query, case=False, na=False)]
            if filter_side != "ทั้งหมด":
                display_df = display_df[display_df['Side'] == filter_side]
            if filter_group != "ทั้งหมด":
                display_df = display_df[display_df['Group'] == filter_group]
            if filter_rsvp != "ทั้งหมด":
                display_df = display_df[display_df['RSVP'] == filter_rsvp]
                
            st.markdown(f"**💡 ค้นพบแขกทั้งหมด {len(display_df)} ท่านที่ตรงกับเงื่อนไข:**")
            
            guest_html = ""
            for _, row in display_df.iterrows():
                side_icon = "👰" if row['Side'] == "ฝั่งเจ้าสาว" else "🤵" if row['Side'] == "ฝั่งเจ้าบ่าว" else "👥"
                note_val = row['Note'] if pd.notna(row['Note']) and row['Note'] != "" else "-"
                rsvp_color = "#10b981" if row['RSVP'] == "ยืนยันเข้าร่วม" else "#ef4444" if row['RSVP'] == "ไม่สามารถเข้าร่วมได้" else "#f59e0b"
                
                guest_html += f"""
                <div style="padding: 12px; margin-bottom: 8px; border-radius: 8px; border-left: 5px solid {rsvp_color}; background-color: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <div style="display: flex; justify-content: space-between;">
                        <div style="font-weight: 600; font-size: 15px; color: #111827;">{row['Guest Name']}</div>
                        <div style="font-size: 12px; color: {rsvp_color}; font-weight: bold;">{row['RSVP']}</div>
                    </div>
                    <div style="display: flex; gap: 8px; margin-top: 4px; font-size: 12px;">
                        <span style="background-color: #fce7f3; color: #9d174d; padding: 2px 6px; border-radius: 4px;">{side_icon} {row['Side']}</span>
                        <span style="background-color: #f3f4f6; color: #374151; padding: 2px 6px; border-radius: 4px;">📂 {row['Group']}</span>
                    </div>
                    <div style="margin-top: 6px; font-size: 13px; color: #4b5563;"><span style="color: #9ca3af;">📌 หมายเหตุ:</span> {note_val}</div>
                </div>
                """
            st.markdown(guest_html, unsafe_allow_html=True)
        else:
            st.info("ยังไม่มีข้อมูลรายชื่อแขกในระบบ")