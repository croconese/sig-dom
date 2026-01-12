import streamlit as st
import os

# 1. Cek Library (Debugging)
try:
    import sqlalchemy
    import pandas as pd
    # Jika menggunakan pg8000, aktifkan baris bawah:
    # import pg8000 
except ImportError as e:
    st.error(f"Library tidak ditemukan: {e}. Silakan Reboot App di Dashboard Streamlit.")
    st.stop()

from sqlalchemy import create_engine, text

# 2. Page Config
st.set_page_config(page_title="SIG-DOM POS", layout="wide")

# 3. Database Engine
@st.cache_resource
def get_engine():
    if "DB_URL" not in st.secrets:
        st.error("Gagal: DB_URL tidak ada di Secrets!")
        return None
    try:
        # Gunakan pool_pre_ping agar koneksi ke Supabase tetap hidup
        return create_engine(st.secrets["DB_URL"], pool_pre_ping=True)
    except Exception as e:
        st.error(f"Engine Error: {e}")
        return None

engine = get_engine()

# 4. UI Sederhana untuk Tes
st.title("🚚 SIG-DOM POS INDONESIA")

if engine:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            st.success("✅ Koneksi Database Berhasil!")
    except Exception as e:
        st.error(f"❌ Koneksi Gagal: {e}")
