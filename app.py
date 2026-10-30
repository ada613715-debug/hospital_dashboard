import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 1. ตั้งค่าหัวข้อหน้าเว็บและรูปแบบการจัดวาง (Layout แบบกว้าง)
st.set_page_config(
    page_title="แดชบอร์ดวิเคราะห์การให้บริการโรงพยาบาล",
    page_icon="🏥",
    layout="wide"
)

# 2. ฟังก์ชันสำหรับโหลดข้อมูลจากไฟล์ CSV
FILE_PATH = "outpatient_visits_cleaned.csv"

@st.cache_data
def load_data(file_path):
    # ตรวจสอบว่ามีไฟล์อยู่ในโฟลเดอร์จริงหรือไม่
    if not os.path.exists(file_path):
        return None
    
    # อ่านไฟล์ CSV
    df = pd.read_csv(file_path)
    
    # แปลงคอลัมน์วัน-เวลาให้เป็นรูปแบบ Datetime ของ Pandas
    date_cols = [
        'arrival_at', 'registration_completed_at', 'triage_completed_at',
        'consultation_started_at', 'consultation_ended_at', 'checkout_completed_at'
    ]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
    # สกัดเฉพาะวันที่ (YYYY-MM-DD) ไว้ทำกราฟแนวโน้มรายวัน
    if 'arrival_at' in df.columns:
        df['visit_date'] = df['arrival_at'].dt.date
        
    return df

# เรียกใช้งานฟังก์ชันโหลดข้อมูลเก็บไว้ในตัวแปร df
df = load_data(FILE_PATH)

# 3. ตรวจสอบความปลอดภัย: หากไม่พบไฟล์ ให้แสดงข้อความแจ้งเตือนสีแดงและหยุดทำงาน
if df is None:
    st.error(f"❌ ไม่พบไฟล์ `{FILE_PATH}` กรุณาย้ายไฟล์มาไว้ในโฟลเดอร์เดียวกับ `app.py` ครับ")
    st.stop()

# 4. แสดงส่วนหัวข้อหลักของเว็บไซต์
st.title("🏥 แดชบอร์ดวิเคราะห์การให้บริการผู้ป่วยนอก (OPD)")
st.markdown("ยินดีต้อนรับสู่ระบบแสดงผลข้อมูลการให้บริการโรงพยาบาลแบบโต้ตอบ")

# แสดงข้อความแจ้งเตือนเมื่อโหลดข้อมูลสำเร็จ
st.success(f"โหลดข้อมูลสำเร็จ! จำนวนข้อมูลทั้งหมด: {len(df):,} แถว")

# ==========================================
# 4. ตัวกรองข้อมูล (Sidebar Filters)
# ==========================================
st.sidebar.header("🔍 ตัวกรองข้อมูล (Filters)")

# ตัวกรองที่ 1: สถานะการรับบริการ
status_list = df['visit_status'].unique().tolist()
selected_status = st.sidebar.multiselect(
    "เลือกสถานะการรับบริการ:",
    options=status_list,
    default=status_list
)

# ตัวกรองที่ 2: ประเภทการมารับบริการ
type_list = df['visit_type'].unique().tolist()
selected_type = st.sidebar.multiselect(
    "เลือกประเภทการมารับบริการ:",
    options=type_list,
    default=type_list
)

# ตัวกรองที่ 3: แผนก
dept_list = sorted(df['department_id'].unique().tolist())
selected_dept = st.sidebar.multiselect(
    "เลือกแผนก (Department ID):",
    options=dept_list,
    default=dept_list
)

# กรองข้อมูลตามที่ผู้ใช้เลือกใน Sidebar
df_filtered = df[
    (df['visit_status'].isin(selected_status)) &
    (df['visit_type'].isin(selected_type)) &
    (df['department_id'].isin(selected_dept))
]

# แจ้งเตือนเมื่อไม่พบข้อมูลหลังใช้ตัวกรอง
if df_filtered.empty:
    st.warning("⚠️ ไม่พบข้อมูลตามเงื่อนไขที่เลือก กรุณาปรับเปลี่ยนตัวกรองใหม่อีกครั้ง")
    st.stop()

# ==========================================
# 5. ตัวเลขสรุปสำคัญ (KPI Cards)
# ==========================================
st.subheader("📊 ตัวชี้วัดสำคัญ (Key Performance Indicators)")

col1, col2, col3, col4 = st.columns(4)

total_visits = len(df_filtered)
completed_visits = len(df_filtered[df_filtered['visit_status'] == 'รับบริการเสร็จสิ้น'])
avg_waiting = df_filtered['waiting_time_minutes'].mean()
avg_total_duration = df_filtered['total_duration_minutes'].mean()

col1.metric("จำนวนผู้ป่วยทั้งหมด", f"{total_visits:,} ราย")
col2.metric("รับบริการเสร็จสิ้น", f"{completed_visits:,} ราย")
col3.metric("ระยะเวลารอเฉลี่ย (ก่อนพบแพทย์)", f"{avg_waiting:.1f} นาที" if pd.notnull(avg_waiting) else "N/A")
col4.metric("เวลารวมเฉลี่ยทั้งสิ้น", f"{avg_total_duration:.1f} นาที" if pd.notnull(avg_total_duration) else "N/A")

st.divider()
# ==========================================
# 6. กราฟวิเคราะห์ข้อมูล (Plotly Visualizations)
# ==========================================
st.subheader("📈 กราฟวิเคราะห์ข้อมูลเชิงลึก")

col_chart1, col_chart2 = st.columns(2)

# กราฟที่ 1: แผนภูมิแท่งแสดงระยะเวลารอคอยเฉลี่ยแยกตามแผนก
with col_chart1:
    st.markdown("##### ⏱️ ระยะเวลารอก่อนพบแพทย์เฉลี่ย (แยกตามแผนก)")
    dept_wait = df_filtered.groupby('department_id')['waiting_time_minutes'].mean().reset_index()
    
    fig_bar = px.bar(
        dept_wait,
        x='department_id',
        y='waiting_time_minutes',
        text_auto='.1f',
        labels={'department_id': 'รหัสแผนก', 'waiting_time_minutes': 'เวลารอเฉลี่ย (นาที)'},
        color='waiting_time_minutes',
        color_continuous_scale='Reds'
    )
    fig_bar.update_layout(xaxis_title="รหัสแผนก", yaxis_title="นาที", showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

# กราฟที่ 2: แผนภูมิเส้นแสดงแนวโน้มจำนวนผู้ป่วยรายวัน
with col_chart2:
    st.markdown("##### 📅 แนวโน้มจำนวนผู้ป่วยมารับบริการรายวัน")
    if 'visit_date' in df_filtered.columns:
        daily_visits = df_filtered.groupby('visit_date').size().reset_index(name='visit_count')
        
        fig_line = px.line(
            daily_visits,
            x='visit_date',
            y='visit_count',
            labels={'visit_date': 'วันที่', 'visit_count': 'จำนวนผู้ป่วย (ราย)'},
            markers=False
        )
        fig_line.update_traces(line_color='#1f77b4')
        fig_line.update_layout(xaxis_title="วันที่", yaxis_title="จำนวนผู้ป่วย (ราย)")
        st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# ==========================================
# 7. สรุปข้อค้นพบจากข้อมูลจริง (Insights) & ตารางข้อมูล
# ==========================================
st.subheader("💡 สรุปข้อค้นพบสำคัญจากข้อมูลจริง")
st.info("""
* **แผนกที่มีระยะเวลารอคอยสูง**: แผนก **D01** และ **D08** มีระยะเวลารอก่อนพบแพทย์เฉลี่ยสูงที่สุด (ประมาณ 71 นาที) ซึ่งสูงกว่าแผนกอื่นๆ อย่างชัดเจน
* **การกระจายตัวของสถานะ**: ผู้ป่วยที่ไม่รอพบแพทย์ (ออกก่อนพบแพทย์) สัมพันธ์กับช่วงเวลาและแผนกที่มีความแออัด
""")

with st.expander("🔍 คลิกเพื่อเปิดดูตารางข้อมูลรายละเอียด (Raw Data)"):
    st.dataframe(df_filtered.head(100), use_container_width=True)
    st.caption(f"แสดงตัวอย่าง 100 รายการแรก จากข้อมูลที่ผ่านการกรองทั้งหมด {len(df_filtered):,} รายการ")