import streamlit as st
import json

# โหลดบัญชีผู้ใช้จากไฟล์ JSON
with open("users.json", "r") as f:
    users = json.load(f)

st.set_page_config(page_title="Login", page_icon="🔐", layout="centered")
st.title("🔐 Welcome Back")
st.subheader("Login Page")

email = st.text_input("Email address")
password = st.text_input("Password", type="password")

if st.button("Sign In"):
    # ตรวจสอบ email และ password
    user = next((u for u in users if u['email'] == email and u['password'] == password), None)

    if user:
        # ตั้งค่า session state เมื่อผู้ใช้ล็อกอิน
        st.session_state.logged_in = True
        st.session_state.role = user['role']
        st.session_state.name = user['email']

        st.success(f"🎉 Welcome {user['role']}!")

        # เปลี่ยนหน้าอัตโนมัติหลังจากล็อกอิน
        if user["role"] == "owner":
            st.session_state.page = "main"
            st.rerun()  # รีเฟรชหน้าใหม่
        elif user["role"] == "staff":
            st.session_state.page = "sell"
            st.rerun()  # รีเฟรชหน้าใหม่
        elif user["role"] == "stock":
            st.session_state.page = "stock"
            st.rerun()  # รีเฟรชหน้าใหม่
    else:
        st.error("❌ Email or password incorrect")
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.name = None
        st.session_state.page = None