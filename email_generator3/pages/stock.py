import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime


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
current_page = "stock"  # เปลี่ยนให้ตรงกับแต่ละไฟล์

if st.session_state.role not in allowed_roles.get(current_page, []):
    st.error("คุณไม่มีสิทธิเข้าถึงหน้านี้")
    st.stop()

# ====== ตั้งค่า Google Sheets =======
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

sheet_url = "https://docs.google.com/spreadsheets/d/10HLoJriPQZKqPOzXlmeV3l0wYHWz4QTLroZFsq9B9ns/edit?usp=sharing"

@st.cache_resource
def get_sheets():
    sheet = client.open_by_url(sheet_url)
    return sheet

# กำหนด Worksheet ที่ต้องการใช้งาน
product_ws = get_sheets().worksheet("products")
sales_ws = get_sheets().worksheet("sales")

# ฟังก์ชันการดึงข้อมูลสินค้า
def get_products():
    return product_ws.get_all_records()

# ฟังก์ชันการค้นหาสินค้าตาม product_id
def find_product_by_id(product_id):
    products = get_products()
    for i, product in enumerate(products):
        if str(product['id']) == str(product_id):
            return product, i + 2  # +2 สำหรับ header และ index ที่เริ่มต้นที่ 1
    return None, None

# ฟังก์ชันการอัปเดตสต็อกสินค้า
def update_stock(row_index, new_stock):
    product_ws.update_cell(row_index, 5, new_stock)  # คอลัมน์ที่ 5 คือ stock

# ฟังก์ชันบันทึกการขาย
def log_sale(product_id, qty, total):
    product, row = find_product_by_id(product_id)
    if product:
        # คำนวณต้นทุนและบันทึกข้อมูล
        cost = product['cost']  # ใช้ข้อมูลต้นทุนที่มีใน sheet
        price = product['price']  # ราคาของสินค้า
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # เวลาปัจจุบัน
        sales_ws.append_row([product_id, product['name'], price, cost, date, total])  # เพิ่มข้อมูลในแผ่น 'sales'
        st.success("✅ ข้อมูลการขายบันทึกเรียบร้อยแล้ว")
        update_stock(row, product['stock'] - qty)  # อัปเดตสต็อกหลังการขาย

    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        st.warning("กรุณาเข้าสู่ระบบก่อนเข้าใช้งาน")
        st.stop()

if st.session_state.role not in ["owner", "staff"]:
    st.error("คุณไม่มีสิทธิเข้าถึงหน้านี้")
    st.stop()



# ===== UI หลัก =====
st.title("📦 เพิ่มสต็อกสินค้า และ บันทึกการขาย")

# ฟอร์มกรอกข้อมูล
col1, col2, col3 = st.columns(3)
with col1:
    product_id = st.text_input("📄 รหัสสินค้า (สแกน)")
with col2:
    name = st.text_input("ชื่อสินค้า")
with col3:
    price = st.number_input("ราคา", min_value=0.0, step=1.0)

cost = st.number_input("ต้นทุนต่อชิ้น", min_value=0.0, step=1.0)
qty = st.number_input("จำนวนสินค้าเพิ่ม", min_value=1, step=1)

# ฟังก์ชันเพิ่มหรืออัปเดตสินค้า
if st.button("➕ เพิ่มเข้าสต็อก"):
    if product_id and name and price and cost:
        product, row = find_product_by_id(product_id)
        if product:
            new_stock = product['stock'] + qty
            update_stock(row, new_stock)
        else:
            product_ws.append_row([product_id, name, price, cost, qty])
        st.success("✅ เพิ่ม/อัปเดตสินค้าเรียบร้อย")
    else:
        st.error("❌ กรุณากรอกข้อมูลให้ครบ")

# ฟังก์ชันบันทึกการขาย
if st.button("💰 บันทึกการขาย"):
    if product_id and qty > 0:
        product, _ = find_product_by_id(product_id)
        if product and product['stock'] >= qty:
            total = product['price'] * qty
            log_sale(product_id, qty, total)  # บันทึกการขาย
        else:
            st.error("❌ สินค้าหมดสต็อก หรือรหัสสินค้าผิดพลาด")
    else:
        st.error("❌ กรุณากรอกข้อมูลการขายให้ครบ")

# แสดงสินค้าทั้งหมดในสต็อก
st.header("📋 สินค้าในสต็อก")
st.table(get_products())
