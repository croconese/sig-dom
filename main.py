import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os

# 1. PAGE CONFIG
st.set_page_config(page_title="SIG-DOM POS", layout="wide")

# 2. DATABASE ENGINE
@st.cache_resource
def get_engine():
    if "DB_URL" not in st.secrets:
        st.error("Konfigurasi DB_URL tidak ditemukan di Secrets!")
        return None
    
    db_url = st.secrets["DB_URL"]
    try:
        # Gunakan koneksi langsung dengan timeout agar tidak gantung
        return create_engine(
            db_url, 
            pool_pre_ping=True,
            connect_args={'connect_timeout': 10}
        )
    except Exception as e:
        st.error(f"Gagal Inisialisasi Engine: {e}")
        return None

engine = get_engine()

# 3. UI UTAMA
st.title("🚚 SIG-DOM PT POS INDONESIA")
st.markdown("---")

if engine:
    try:
        # Mencoba melakukan koneksi
        with engine.connect() as conn:
            # Tes query sederhana
            result = conn.execute(text("SELECT 1")).fetchone()
            
            if result:
                st.success("✅ KONEKSI BERHASIL! Database Supabase terhubung.")
                
                # Cek apakah tabel user sudah ada
                try:
                    user_check = conn.execute(text("SELECT COUNT(*) FROM users_dc")).fetchone()
                    st.info(f"Tabel 'users_dc' ditemukan dengan {user_check[0]} data.")
                except Exception:
                    st.warning("⚠️ Koneksi OK, tapi tabel 'users_dc' belum dibuat. Silakan jalankan script SQL di Supabase.")
            
    except Exception as e:
        st.error("❌ GAGAL TERHUBUNG")
        st.code(str(e)) # Menampilkan error mentah agar mudah diidentifikasi
        
        st.markdown("""
        ### Cara Memperbaiki:
        1. Pastikan **Password** di Secrets benar.
        2. Pastikan di Supabase (Settings > Database), **IPv4** sudah diizinkan (biasanya default).
        3. Jika masih gagal, coba ganti port ke `5432` di URL Secrets.
        """)

# FOOTER
st.caption("SIG-DOM v1.4 | Debug Mode")
