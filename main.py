import streamlit as st

# Cek apakah library sudah terinstall sebelum lanjut
try:
    import pg8000
    import sqlalchemy
except ImportError:
    st.error("Library database belum terinstall sepenuhnya. Silakan klik 'Reboot App' di menu Streamlit Cloud.")
    st.stop()

import pandas as pd
from sqlalchemy import create_engine, text
import folium
from streamlit_folium import st_folium
import os

# --- KONFIGURASI ENGINE ---
@st.cache_resource
def get_engine():
    # Mengambil langsung dari Secrets
    if "DB_URL" not in st.secrets:
        st.error("Konfigurasi DB_URL tidak ditemukan di Secrets!")
        return None
    try:
        # Gunakan driver pg8000 (Pure Python)
        return create_engine(
            st.secrets["DB_URL"],
            pool_pre_ping=True
        )
    except Exception as e:
        st.error(f"Gagal Inisialisasi Database: {e}")
        return None

engine = get_engine()

# --- SISANYA ADALAH KODE DASHBOARD ANDA ---
st.title("🚚 SIG-DOM POS INDONESIA")

if engine:
    # Coba tes koneksi sederhana
    try:
        with engine.connect() as conn:
            st.success("Koneksi ke Supabase Berhasil!")
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
