import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Wedding Planner Dashboard", page_icon="💍", layout="wide")

# --- 2. GOOGLE SHEETS CONNECTION ---
# สร้างตัวเชื่อมต่อกับ Google Sheets
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
            return df.dropna(how="all")
    except:
        pass
    return pd.DataFrame(columns=['Vendor', 'Category', 'Amount', 'Due Date'])

def save_expenses(df):
    conn.update(worksheet="Expenses", data=df)

def load_todos():
    try:
        df = conn.read(worksheet="Todos", ttl=0)
        if not df.empty:
            df = df.dropna(how="all")
            if not df.empty and 'Deadline' in df.columns:
                df['Deadline'] = pd.to_datetime(df['Deadline']).dt.date 
                return df
    except:
        pass
    return pd.DataFrame({
        'Status': ['ยังไม่ได้เริ่ม', 'ยังไม่ได้เริ่ม'],
        'Task': ['จองสถานที่จัดงาน', 'ลิสต์รายชื่อแขก'],
        'Deadline': [date(2026, 11, 24), date(2026, 12, 1)] 
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
        
        submit_button = st.form_submit_button("เพิ่มลงในบัญชี")
        
        if submit_button and vendor and amount > 0:
            new_row = pd.DataFrame([{
                'Vendor': vendor, 
                'Category': category, 
                'Amount': amount, 
                'Due Date': due_date.strftime("%d %B %Y")
            }])
            st.session_state.expenses = pd.concat([st.session_state.expenses, new_row], ignore_index=True)
            save_expenses(st.session_state.expenses)
            st.success("เพิ่มค่าใช้จ่ายเรียบร้อยแล้ว!")

    total_spent = st.session_state.expenses['Amount'].sum()
    remaining_budget = st.session_state.total_budget - total_spent

    col1, col2, col3 = st.columns(3)
    col1.metric("งบประมาณทั้งหมด 💰", f"฿ {st.session_state.total_budget:,.2f}")
    col2.metric("ใช้จ่ายไปแล้ว 💸", f"฿ {total_spent:,.2f}", f"{(total_spent/st.session_state.total_budget)*100:.1f}% used" if st.session_state.total_budget > 0 else "")
    col3.metric("งบประมาณคงเหลือ 🏦", f"฿ {remaining_budget:,.2f}")

    st.markdown("---")

    col_chart, col_table = st.columns([1, 1.5])
    with col_chart:
        st.subheader("📊 สัดส่วนค่าใช้จ่าย")
        if not st.session_state.expenses.empty:
            fig = px.pie(
                st.session_state.expenses, 
                values='Amount', 
                names='Category', 
                hole=0.6,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.add_annotation(text=f"<b>฿ {total_spent:,.0f}</b><br>Total Cost", x=0.5, y=0.5, font_size=20, showarrow=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("เพิ่มค่าใช้จ่ายที่แถบด้านข้างเพื่อดูแผนภูมิ")

    with col_table:
        st.subheader("📝 ประวัติการชำระเงิน")
        if not st.session_state.expenses.empty:
            st.dataframe(st.session_state.expenses, use_container_width=True, hide_index=True)
        else:
            st.info("ยังไม่มีการบันทึกการชำระเงิน")

# ==========================================
# PAGE 2: TO-DO LIST
# ==========================================
elif page == "📝 สิ่งที่ต้องทำ (To-Do)":
    st.title("📝 เตรียมสิ่งที่ต้องทำ (To-Do List)")
    st.write("บันทึกและติดตามความคืบหน้าของงานที่ต้องเตรียม แยกตามเดือน")
    
    if not st.session_state.todos.empty:
        status_counts = st.session_state.todos['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        
        total_tasks = len(st.session_state.todos)
        completed_tasks = len(st.session_state.todos[st.session_state.todos['Status'] == 'เสร็จแล้ว'])
        
        color_map = {
            'ยังไม่ได้เริ่ม': '#9ca3af',
            'อยู่ระหว่างดำเนินการ': '#fbbf24',
            'หยุดไว้ชั่วคราว': '#fb923c',
            'ไม่จำเป็น': '#f87171',
            'เสร็จแล้ว': '#4ade80'
        }
        
        fig_todo = px.pie(
            status_counts, 
            values='Count', 
            names='Status', 
            hole=0.6,
            color='Status',
            color_discrete_map=color_map
        )
        fig_todo.add_annotation(text=f"<b>{completed_tasks} / {total_tasks}</b><br>ทำเสร็จแล้ว", x=0.5, y=0.5, font_size=20, showarrow=False)
        fig_todo.update_layout(margin=dict(t=0, b=0, l=0, r=0)) 
        
        col_space1, col_pie, col_space2 = st.columns([1, 1.5, 1])
        with col_pie:
            st.plotly_chart(fig_todo, use_container_width=True)
            
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
        return f'<span style="background-color: {bg_color}; color: {text_color}; {border} padding: 4px 12px; border-radius: 16px; font-size: 13px; font-weight: 600; display: inline-block; text-align: center;">{status}</span>'

    def highlight_status(val):
        bg_colors = {
            'ยังไม่ได้เริ่ม': '#f3f4f6',
            'อยู่ระหว่างดำเนินการ': '#fef3c7',
            'หยุดไว้ชั่วคราว': '#ffedd5',
            'ไม่จำเป็น': '#fee2e2',
            'เสร็จแล้ว': '#dcfce7'
        }
        color = bg_colors.get(val, '')
        return f'background-color: {color}; color: #1f2937;'

    st.sidebar.header("➕ เพิ่มงานที่ต้องทำ")
    with st.sidebar.form("add_task_form", clear_on_submit=True):
        task_name = st.text_input("ชื่องาน (เช่น เตรียมของชำร่วย)")
        task_deadline = st.date_input("กำหนดการเสร็จสิ้น", min_value=date.today())
        add_task_btn = st.form_submit_button("เพิ่มงาน")
        
        if add_task_btn and task_name:
            new_task = pd.DataFrame([{
                'Status': 'ยังไม่ได้เริ่ม', 
                'Task': task_name,
                'Deadline': task_deadline 
            }])
            st.session_state.todos = pd.concat([st.session_state.todos, new_task], ignore_index=True)
            save_todos(st.session_state.todos) 
            st.rerun()

    col_edit, col_view = st.columns([1.2, 1])

    with col_edit:
        st.markdown("### ✏️ อัปเดตสถานะงาน")
        if not st.session_state.todos.empty:
            styled_todos = st.session_state.todos.style.map(highlight_status, subset=['Status'])
            edited_df = st.data_editor(
                styled_todos,
                column_config={
                    "Status": st.column_config.SelectboxColumn(
                        "📌 Status",
                        options=["ยังไม่ได้เริ่ม", "อยู่ระหว่างดำเนินการ", "หยุดไว้ชั่วคราว", "ไม่จำเป็น", "เสร็จแล้ว"],
                        required=True
                    ),
                    "Task": st.column_config.TextColumn("📋 สิ่งที่ต้องทำ", disabled=True),
                    "Deadline": st.column_config.DateColumn(
                        "📅 กำหนดการ", 
                        disabled=False, 
                        format="DD/MM/YYYY" 
                    )
                },
                hide_index=True,
                use_container_width=True
            )
            
            if not edited_df.equals(st.session_state.todos):
                st.session_state.todos = edited_df
                save_todos(st.session_state.todos) 
                st.rerun() 
            
        else:
            st.info("ยังไม่มีรายการสิ่งที่ต้องทำ")

    with col_view:
        st.markdown("### 📌 ภาพรวมงานแยกตามเดือน")
        if not st.session_state.todos.empty:
            view_df = st.session_state.todos.copy()
            view_df['SortDate'] = pd.to_datetime(view_df['Deadline'])
            view_df = view_df.sort_values('SortDate')
            view_df['MonthGroup'] = view_df['SortDate'].apply(get_thai_month_year)
            
            html_content = ""
            for month_group in view_df['MonthGroup'].unique():
                html_content += f"<h4 style='color: #4b5563; border-bottom: 2px solid #e5e7eb; padding-bottom: 4px; margin-top: 20px;'>📅 {month_group}</h4>"
                month_tasks = view_df[view_df['MonthGroup'] == month_group]
                
                for _, row in month_tasks.iterrows():
                    badge = get_status_badge(row['Status'])
                    display_date = row['SortDate'].strftime("%d/%m/%Y")
                    
                    html_content += f"""<div style="padding: 12px; margin-bottom: 8px; border-radius: 8px; border: 1px solid #e5e7eb; background-color: #fafafa;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
<span style="font-weight: 600; font-size: 15px;">{row['Task']}</span>
{badge}
</div>
<div style="color: #6b7280; font-size: 13px;">ครบกำหนด: {display_date}</div>
</div>"""
            st.markdown(html_content, unsafe_allow_html=True)
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