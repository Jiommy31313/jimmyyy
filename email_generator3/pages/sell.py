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
current_page = "sell"  # เปลี่ยนให้ตรงกับแต่ละไฟล์

if st.session_state.role not in allowed_roles.get(current_page, []):
    st.error("คุณไม่มีสิทธิเข้าถึงหน้านี้")
    st.stop()

# Set page config
st.set_page_config(page_title="POS ขายสินค้า", layout="wide")

# Hide menu/footer
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Google Sheets config
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Sheet setup
sheet_url = "https://docs.google.com/spreadsheets/d/10HLoJriPQZKqPOzXlmeV3l0wYHWz4QTLroZFsq9B9ns/edit?usp=sharing"
sheet = client.open_by_url(sheet_url)
product_ws = sheet.worksheet("products")
sales_ws = sheet.worksheet("sales")

# Get product list
def get_products():
    return product_ws.get_all_records()

# Find product by ID
def find_product_by_id(product_id):
    products = get_products()
    for i, product in enumerate(products):
        if str(product['id']) == str(product_id):
            return product, i + 2
    return None, None

# Update stock
def update_stock(row_index, new_stock):
    product_ws.update_cell(row_index, 5, new_stock)

# Save sale to sheet with error handling
def log_sale(product_id, qty, total):
    try:
        product, row_index = find_product_by_id(product_id)
        if product:
            cost = product['cost']
            name = product['name']
            price = product['price']
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            record = [product_id, name, price, cost, timestamp, total]
            st.write("📄 กำลังบันทึกข้อมูล:", record)

            sales_ws.append_row(record)
            update_stock(row_index, product['stock'] - qty)
            st.success("✅ บันทึกสำเร็จลง Google Sheet แล้ว")
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดขณะบันทึก: {e}")

    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        st.warning("กรุณาเข้าสู่ระบบก่อนเข้าใช้งาน")
        st.stop()

if st.session_state.role not in ["owner", "staff"]:
    st.error("คุณไม่มีสิทธิเข้าถึงหน้านี้")
    st.stop()



# UI เริ่มต้น
st.title("🛒 ระบบขายสินค้า")

col1, col2 = st.columns([2, 1])
with col1:
    product_id = st.text_input("🔍 สแกนรหัสสินค้า", key="input", help="พิมพ์หรือสแกนรหัสสินค้า", label_visibility="visible")
with col2:
    st.markdown("")

# Session cart
if 'cart' not in st.session_state:
    st.session_state.cart = []

# เพิ่มสินค้าเข้าตะกร้า
if product_id:
    product, _ = find_product_by_id(product_id)
    if product:
        found = any(item['id'] == product_id for item in st.session_state.cart)
        if not found:
            st.session_state.cart.append({
                "id": product_id,
                "name": product['name'],
                "price": product['price'],
                "qty": 1,
                "total": product['price']
            })

# แสดงตะกร้า
if st.session_state.cart:
    st.subheader("🧾 รายการในตะกร้า")
    st.table(st.session_state.cart)

    total_all = sum(item['total'] for item in st.session_state.cart)

    col3, col4, col5 = st.columns([2, 1, 1])
    with col3:
        st.markdown(f"💵 **รวมทั้งหมด:** `{total_all:.2f} บาท`")
    with col4:
        cash_received = st.number_input("💸 เงินที่รับ", min_value=0.0, step=1.0, format="%.2f")
    with col5:
        if st.button("✅ ชำระเงิน"):
            if cash_received < total_all:
                st.error("❌ เงินไม่พอ กรุณารับเงินใหม่")
            else:
                change = cash_received - total_all
                for item in st.session_state.cart:
                    product, row = find_product_by_id(item['id'])
                    if product and product['stock'] >= item['qty']:
                        log_sale(item['id'], item['qty'], item['total'])
                st.success(f"✅ ชำระเงินสำเร็จ | เงินทอน: {change:.2f} บาท")
                st.session_state.cart = []
else:
    st.info("📭 ยังไม่มีสินค้าในตะกร้า")
