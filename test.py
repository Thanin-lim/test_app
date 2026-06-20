import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Wedding Planner Dashboard", page_icon="💍", layout="wide")

# --- 2. GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_budget():
    try:
        df = conn.read(worksheet="Budget", usecols=[0], ttl=0)
        if not df.empty and pd.notna(df.iloc[0, 0]):
            return float(df.iloc[0, 0])
    except:
        pass
    return 190000.00 

def save_budget(amount):
    df = pd.DataFrame({"Total Budget": [amount]})
    conn.update(worksheet="Budget", data=df)

def load_expenses():
    try:
        df = conn.read(worksheet="Expenses", ttl=0)
        if not df.empty:
            df = df.dropna(how="all")
            if 'Status' not in df.columns:
                df['Status'] = 'ยังไม่ชำระเงิน'
            if 'Amount' in df.columns:
                df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0.0)
            else:
                df['Amount'] = 0.0
            return df
    except:
        pass
    return pd.DataFrame(columns=['Vendor', 'Category', 'Amount', 'Due Date', 'Status'])

def save_expenses(df):
    conn.update(worksheet="Expenses", data=df)

def load_todos():
    try:
        df = conn.read(worksheet="Todos", ttl=0)
        if not df.empty:
            df = df.dropna(how="all")
            if 'Detail' not in df.columns:
                df['Detail'] = ''
            if not df.empty and 'Deadline' in df.columns:
                df['Deadline'] = pd.to_datetime(df['Deadline']).dt.date 
                return df
    except:
        pass
    return pd.DataFrame({
        'Status': ['ยังไม่ได้เริ่ม', 'ยังไม่ได้เริ่ม'],
        'Task': ['จองสถานที่จัดงาน', 'ลิสต์รายชื่อแขก'],
        'Deadline': [date(2026, 11, 24), date(2026, 12, 1)],
        'Detail': ['โรงแรม Centara หรือ สวนในเมือง', 'รวมญาติฝั่งเจ้าสาวและเจ้าบ่าว ประมาณ 200 คน']
    })

def save_todos(df):
    conn.update(worksheet="Todos", data=df)

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

# --- 3. INITIALIZE SESSION STATE ---
if 'expenses' not in st.session_state:
    st.session_state.expenses = load_expenses()

if 'total_budget' not in st.session_state:
    st.session_state.total_budget = load_budget()

if 'todos' not in st.session_state:
    st.session_state.todos = load_todos()

# --- CALLBACK FUNCTIONS FOR LIVE UPDATE ---
def on_expenses_edit():
    edited_rows = st.session_state.expense_editor["edited_rows"]
    deleted_rows = st.session_state.expense_editor["deleted_rows"]
    added_rows = st.session_state.expense_editor["added_rows"]
    
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
    edited_rows = st.session_state.todo_editor["edited_rows"]
    deleted_rows = st.session_state.todo_editor["deleted_rows"]
    
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

# --- 4. SIDEBAR NAVIGATION ---
st.sidebar.title("📌 Navigation")
page = st.sidebar.radio("เลือกหน้าต่างการทำงาน:", ["📊 Budget Tracker", "📝 สิ่งที่ต้องทำ (To-Do)"])
st.sidebar.markdown("---")

# ==========================================
# PAGE 1: BUDGET TRACKER
# ==========================================
if page == "📊 Budget Tracker":
    st.title("💍 Wedding Budget Dashboard")
    
    st.sidebar.header("⚙️ ตั้งค่างบประมาณ")
    new_budget = st.sidebar.number_input("Set Total Budget (THB):", min_value=0.0, value=st.session_state.total_budget, step=1000.0)
    
    if new_budget != st.session_state.total_budget:
        st.session_state.total_budget = new_budget
        save_budget(new_budget)

    st.sidebar.subheader("➕ เพิ่มค่าใช้จ่าย")
    with st.sidebar.form("add_expense_form", clear_on_submit=True):
        vendor = st.text_input("ชื่อร้านค้า/บริการ (Vendor)")
        category = st.selectbox("หมวดหมู่", [
            "Venue (สถานที่จัดงานแต่ง)", 
            "Food & Beverage (อาหารและเครื่องดื่ม)", 
            "Attire (ชุดในงานแต่งงาน)", 
            "Photography & Video (ช่างภาพ/วิดีโอ)", 
            "Entertainment (ความบันเทิง)", 
            "Other (อื่นๆ)"
        ])
        amount = st.number_input("จำนวนเงิน (THB)", min_value=0.0, step=1000.0)
        due_date = st.date_input("กำหนดชำระเงิน", min_value=date.today())
        payment_status = st.selectbox("สถานะ", ["ยังไม่ชำระเงิน", "ชำระเงินแล้ว"])
        
        submit_button = st.form_submit_button("เพิ่มลงในบัญชี")
        
        if submit_button and vendor and amount > 0:
            new_row = pd.DataFrame([{
                'Vendor': vendor, 
                'Category': category, 
                'Amount': float(amount), 
                'Due Date': due_date.strftime("%d %B %Y"),
                'Status': payment_status
            }])
            st.session_state.expenses = pd.concat([st.session_state.expenses, new_row], ignore_index=True)
            save_expenses(st.session_state.expenses)
            st.success("เพิ่มค่าใช้จ่ายเรียบร้อยแล้ว!")
            st.rerun()

    total_spent = st.session_state.expenses['Amount'].sum() if not st.session_state.expenses.empty else 0.0
    remaining_budget = st.session_state.total_budget - total_spent

    if not st.session_state.expenses.empty:
        paid_amount = st.session_state.expenses[st.session_state.expenses['Status'] == 'ชำระเงินแล้ว']['Amount'].sum()
        unpaid_amount = total_spent - paid_amount
    else:
        paid_amount = 0.0
        unpaid_amount = 0.0

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
            fig = px.pie(
                st.session_state.expenses, 
                values='Amount', 
                names='Category', 
                hole=0.6,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.add_annotation(text=f"<b>฿ {total_spent:,.0f}</b><br>Total Cost", x=0.5, y=0.5, font_size=18, showarrow=False)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("เพิ่มค่าใช้จ่ายที่แถบด้านข้างเพื่อดูแผนภูมิ")

    with tab_table:
        if not st.session_state.expenses.empty:
            st.markdown(f"**📊 รายการค่าใช้จ่ายในระบบ (มีทั้งหมด {len(st.session_state.expenses)} รายการ):**")
            
            def highlight_payment_status(val):
                if val == 'ชำระเงินแล้ว':
                    return 'background-color: #dcfce7; color: #166534;'
                elif val == 'ยังไม่ชำระเงิน':
                    return 'background-color: #fee2e2; color: #991b1b;'
                return ''

            styled_expenses = st.session_state.expenses.style.map(highlight_payment_status, subset=['Status'])
            
            st.data_editor(
                styled_expenses,
                column_config={
                    "Vendor": st.column_config.TextColumn("ร้านค้า", width="medium"),
                    "Category": None,  
                    "Due Date": None,  
                    "Amount": st.column_config.NumberColumn("จำนวนเงิน (บาท)", format="%d", min_value=0, default=0, required=True, width="medium"),
                    "Status": st.column_config.SelectboxColumn("📌 สถานะ", options=["ยังไม่ชำระเงิน", "ชำระเงินแล้ว"], required=True, width="medium")
                },
                hide_index=False,
                width='stretch',
                num_rows="dynamic",
                key="expense_editor",
                on_change=on_expenses_edit
            )
        else:
            st.info("ยังไม่มีการบันทึกการชำระเงิน")

# ==========================================
# PAGE 2: TO-DO LIST
# ==========================================
elif page == "📝 สิ่งที่ต้องทำ (To-Do)":
    st.title("📝 เตรียมสิ่งที่ต้องทำ (To-Do List)")
    st.write("บันทึกและติดตามความคืบหน้าของงาน แยกตามเดือน")
    
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
    
    def get_status_badge(status):
        colors = {
            'ยังไม่ได้เริ่ม': ('#f3f4f6', '#374151', 'border: 1px solid #d1d5db;'),
            'อยู่ระหว่างดำเนินการ': ('#fef3c7', '#92400e', 'border: 1px solid #fde68a;'),
            'หยุดไว้ชั่วคราว': ('#ffedd5', '#9a3412', 'border: 1px solid #fdba74;'),
            'ไม่จำเป็น': ('#fee2e2', '#991b1b', 'border: 1px solid #fca5a5;'),
            'เสร็จแล้ว': ('#dcfce7', '#166534', 'border: 1px solid #86efac;')
        }
        bg_color, text_color, border = colors.get(status, ('#ffffff', '#000000', ''))
        return f'<span style="background-color: {bg_color}; color: {text_color}; {border} padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; display: inline-block; text-align: center;">{status}</span>'

    def highlight_status(val):
        bg_colors = {'ยังไม่ได้เริ่ม': '#f3f4f6', 'อยู่ระหว่างดำเนินการ': '#fef3c7', 'หยุดไว้ชั่วคราว': '#ffedd5', 'ไม่จำเป็น': '#fee2e2', 'เสร็จแล้ว': '#dcfce7'}
        color = bg_colors.get(val, '')
        return f'background-color: {color}; color: #1f2937;'

    st.sidebar.header("➕ เพิ่มงานที่ต้องทำ")
    with st.sidebar.form("add_task_form", clear_on_submit=True):
        task_name = st.text_input("ชื่องาน (เช่น เตรียมของชำร่วย)")
        task_deadline = st.date_input("กำหนดการเสร็จสิ้น", min_value=date.today())
        task_detail = st.text_area("รายละเอียด/สถานที่/โน้ตเพิ่มเติม")
        add_task_btn = st.form_submit_button("เพิ่มงาน")
        
        if add_task_btn and task_name:
            new_task = pd.DataFrame([{
                'Status': 'ยังไม่ได้เริ่ม', 
                'Task': task_name,
                'Deadline': task_deadline,
                'Detail': task_detail
            }])
            st.session_state.todos = pd.concat([st.session_state.todos, new_task], ignore_index=True)
            save_todos(st.session_state.todos) 
            st.rerun()

    tab_edit, tab_view = st.tabs(["✏️ อัปเดตสถานะและรายละเอียด", "📌 ภาพรวมรายเดือน"])

    with tab_edit:
        if not st.session_state.todos.empty:
            st.markdown(f"**📋 รายการสิ่งที่ต้องทำในตาราง (มีทั้งหมด {len(st.session_state.todos)} รายการ):**")
            
            styled_todos = st.session_state.todos.style.map(highlight_status, subset=['Status'])
            
            st.data_editor(
                styled_todos,
                column_config={
                    "Status": st.column_config.SelectboxColumn("📌 สถานะ", options=["ยังไม่ได้เริ่ม", "อยู่ระหว่างดำเนินการ", "หยุดไว้ชั่วคราว", "ไม่จำเป็น", "เสร็จแล้ว"], required=True, width="medium"),
                    "Task": st.column_config.TextColumn("📋 งาน (แก้ไขชื่องานได้)", disabled=False, width="medium"), 
                    "Deadline": st.column_config.DateColumn("📅 กำหนด", disabled=False, format="DD/MM/YYYY", width="small"),
                    "Detail": st.column_config.TextColumn("🏠 รายละเอียด/Note (กดแก้ไขได้)", disabled=False, width="large")
                },
                hide_index=False, 
                width='stretch',
                num_rows="dynamic",
                key="todo_editor",
                on_change=on_todos_edit
            )
        else:
            st.info("ยังไม่มีรายการสิ่งที่ต้องทำ")

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
                        badge = get_status_badge(row['Status'])
                        display_date = row['SortDate'].strftime("%d/%m/%Y")
                        detail_val = row['Detail'] if pd.notna(row['Detail']) and row['Detail'] != "" else "-"
                        
                        html_content += f"""<div style="padding: 12px; margin-bottom: 8px; border-radius: 8px; border: 1px solid #e5e7eb; background-color: #fafafa;">
<div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px; margin-bottom: 6px;">
<span style="font-weight: 600; font-size: 14px;">{row['Task']}</span>
{badge}
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
                        
                        st.info(f"""
                        **📋 ชื่องาน:** {task_info['Task']}  
                        **📅 วันครบกำหนด:** {task_info['Deadline'].strftime('%d/%m/%Y') if hasattr(task_info['Deadline'], 'strftime') else task_info['Deadline']}  
                        **📌 สถานะปัจจุบัน:** {task_info['Status']}  
                        **🏠 รายละเอียด/Note สำคัญ:** {detail_text}
                        """)
                        
                        # --- ฟีเจอร์อัปเดตใหม่ล่าสุด: ปุ่มกดเพิ่มรายชื่อแขก ---
                        if "แขก" in task_info['Task'] or "รายชื่อ" in task_info['Task']:
                            st.success("💡 พบงานเกี่ยวกับรายชื่อแขก! คุณสามารถกดปุ่มด้านล่างเพื่อเปิดหน้าจัดการรายชื่อได้ทันที:")
                            # สามารถนำ URL หน้า Google Sheets หรือฟอร์มกรอกชื่อแขกของคุณมาใส่แทนที่ลิ้งก์ข้างล่างนี้ได้เลยครับ
                            st.link_button("➕ กดตรงนี้เพื่อไปเพิ่มชื่อแขก", "https://docs.google.com", width='stretch')
        else:
            st.write("-")

    st.markdown("---")
    if not st.session_state.todos.empty:
        if st.button("🗑️ ลบงานที่ 'เสร็จแล้ว' และ 'ไม่จำเป็น'"):
            st.session_state.todos = st.session_state.todos[
                ~st.session_state.todos['Status'].isin(['เสร็จแล้ว', 'ไม่จำเป็น'])
            ]
            save_todos(st.session_state.todos)
            st.rerun()