import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import time

if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.warning("กรุณาเข้าสู่ระบบก่อนเข้าใช้งาน")
    st.stop()

# ตรวจสอบสิทธิ์การเข้าใช้งานแต่ละหน้า
allowed_roles = {
    "main": ["owner"],
    "sell": ["owner", "staff"],
    "stock": ["owner", "staff"],
}

# ระบุชื่อหน้า (เช่น "main", "sell", หรือ "stock")
current_page = "main"  # เปลี่ยนให้ตรงกับแต่ละไฟล์

if st.session_state.role not in allowed_roles.get(current_page, []):
    st.error("คุณไม่มีสิทธิเข้าถึงหน้านี้")
    st.stop()

# ===== Google Sheets Config =====
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# === URL ของชีท ===
sheet_url = "https://docs.google.com/spreadsheets/d/10HLoJriPQZKqPOzXlmeV3l0wYHWz4QTLroZFsq9B9ns/edit?usp=sharing"
sheet = client.open_by_url(sheet_url)
product_ws = sheet.worksheet("products")
sales_ws = sheet.worksheet("sales")

# ===== Functions =====
def load_sales_data():
    data = sales_ws.get_all_records()
    df = pd.DataFrame(data)
    df.columns = df.columns.str.strip().str.lower()
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    return df

def load_product_data():
    df = pd.DataFrame(product_ws.get_all_records())
    df.columns = df.columns.str.strip().str.lower()
    return df

def calculate_profit(df_sales, df_products):
    df_sales_cleaned = df_sales.drop(columns=[col for col in ['price', 'cost'] if col in df_sales.columns])

    merged = df_sales_cleaned.merge(
        df_products,
        how='left',
        left_on='product_id',
        right_on='id',
        suffixes=('_sale', '_prod')
    )

    required_cols = ['cost', 'price', 'total']
    missing_cols = [col for col in required_cols if col not in merged.columns]
    if missing_cols:
        raise KeyError(f"ไม่พบคอลัมน์ {', '.join(missing_cols)} ใน DataFrame.\nคอลัมน์ทั้งหมด: {merged.columns.tolist()}")

    unmatched = merged[merged['id'].isnull()]
    if not unmatched.empty:
        st.warning(f"⚠️ พบ product_id ที่ไม่มีใน products: {unmatched['product_id'].unique().tolist()}")

    merged['qty_estimated'] = merged['total'] / merged['price']
    merged['cost_total'] = merged['qty_estimated'] * merged['cost']
    merged['profit'] = merged['total'] - merged['cost_total']
    return merged

# ===== กราฟแผนภูมิแท่ง (Bar Chart) =====
def plot_sales_per_day(sales_df):
    # สรุปยอดขายต่อวัน
    sales_daily = sales_df.groupby(sales_df['date'].dt.date)['total'].sum().reset_index()
    sales_daily.columns = ['date', 'total_sales']

    # สร้างแผนภูมิแท่ง
    fig = go.Figure(go.Bar(
        x=sales_daily['date'],  # วันที่
        y=sales_daily['total_sales'],  # ยอดขาย
        marker=dict(
            color=sales_daily['total_sales'],  # สีตามยอดขาย
            colorscale='Viridis',  # เลือกสีแบบ Viridis
            showscale=True  # แสดง scale ของสี
        ),
        text=sales_daily['total_sales'],  # แสดงยอดขายบนแต่ละแท่ง
        hoverinfo='x+text'  # เมื่อ hover จะแสดงวันที่และยอดขาย
    ))

    fig.update_layout(
        title="ยอดขายต่อวัน",
        xaxis_title="วันที่",
        yaxis_title="ยอดขาย (บาท)",
        template="plotly_dark",  # ใช้ธีม dark
        barmode='group',
        plot_bgcolor='rgba(0,0,0,0)',  # ทำให้พื้นหลังกราฟเป็นโปร่งใส
        xaxis=dict(
            showgrid=True,  # แสดงกริดบนแกน x
            showline=True,  # แสดงเส้นของแกน x
            tickangle=-45  # หมุนวันที่ให้เอียง
        ),
        yaxis=dict(
            showgrid=True,  # แสดงกริดบนแกน y
            showline=True  # แสดงเส้นของแกน y
        ),
    )

    return fig

# ===== กราฟวงกลม (Pie Chart) แสดงกำไรต่อต้นทุน =====
def plot_profit_ratio(profit_df):
    # คำนวณกำไรต่อต้นทุน
    total_profit = profit_df['profit'].sum()
    total_cost = profit_df['cost_total'].sum()

    profit_ratio = total_profit / total_cost if total_cost != 0 else 0  # ป้องกันการหารด้วย 0

    # สร้างกราฟวงกลมที่แสดงกำไรต่อต้นทุน
    fig = go.Figure(go.Pie(
        labels=['กำไร', 'ต้นทุน'],
        values=[total_profit, total_cost],
        hoverinfo='label+percent',
        textinfo='label+percent',  # แสดงเปอร์เซ็นต์บนกราฟ
        marker=dict(colors=['#FF6666', '#66FF66'])  # สีของกราฟวงกลม
    ))

    fig.update_layout(
        title="กำไรต่อต้นทุนของทุกเดือน",
        template="plotly_dark",  # ใช้ธีม dark
    )

    return fig

# ===== UI =====
st.set_page_config(page_title="POS Dashboard", layout="wide")
st.title("📊 POS Dashboard")
st.info("ดูภาพรวมยอดขายและสถานะสินค้าในระบบ POS")

# ===== Load Data =====
sales_df = load_sales_data()
products_df = load_product_data()

if sales_df.empty:
    st.warning("ยังไม่มีข้อมูลการขาย")
else:
    today = datetime.now().date()
    this_month = today.strftime("%Y-%m")

    # === รายวัน ===
    sales_today = sales_df[sales_df['date'].dt.date == today]
    total_today = sales_today['total'].sum()

    # === รายเดือน ===
    sales_month = sales_df[sales_df['date'].dt.strftime("%Y-%m") == this_month]
    total_month = sales_month['total'].sum()
    total_customers = len(sales_month)

    # === กำไร ===
    try:
        profit_df = calculate_profit(sales_month, products_df)
        total_profit = profit_df['profit'].sum()

        # === แสดงผล ===
        col1, col2 = st.columns(2)  # สร้าง 2 คอลัมน์

        # แสดงกราฟแผนภูมิแท่งในคอลัมน์ที่ 1
        with col1:
            st.plotly_chart(plot_sales_per_day(sales_df), use_container_width=True)

        # แสดงกราฟวงกลมในคอลัมน์ที่ 2
        with col2:
            st.plotly_chart(plot_profit_ratio(profit_df), use_container_width=True)

        # แสดงข้อมูลเพิ่มเติม
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💸 ยอดขายวันนี้", f"{total_today:,.2f} บาท")
        col2.metric("📅 ยอดขายเดือนนี้", f"{total_month:,.2f} บาท")
        col3.metric("👥 ลูกค้าเดือนนี้", total_customers)
        col4.metric("💰 กำไรเดือนนี้", f"{total_profit:,.2f} บาท")

        st.subheader("📋 รายการขายเดือนนี้")
        st.dataframe(sales_month)

    except KeyError as e:
        st.error(f"เกิดข้อผิดพลาดในการคำนวณกำไร:\n\n{e}")

# ===== สินค้าใกล้หมด =====
st.subheader("⚠️ สินค้าใกล้หมด (น้อยกว่า 5 ชิ้น)")
if 'stock' in products_df.columns:
    low_stock = products_df[products_df['stock'] < 5]
    st.dataframe(low_stock)
else:
    st.warning("ไม่พบคอลัมน์ 'stock' ใน products")

# ===== สินค้าใหม่ =====
st.subheader("🆕 สินค้าใหม่ (เพิ่มในเดือนนี้)")
if 'date_added' in products_df.columns:
    new_products = products_df[products_df['date_added'] >= pd.to_datetime(today.replace(day=1))]
    st.dataframe(new_products)
else:
    st.warning("ไม่พบคอลัมน์ 'date_added' ใน products")

# ===== Auto Refresh =====
time.sleep(60)  # รอ 60 วินาที ก่อนจะรีเฟรช
st.rerun()
# หมายเหตุ: การใช้ time.sleep() ใน Streamlit อาจทำให้เกิดปัญหาในการรีเฟรชหน้า