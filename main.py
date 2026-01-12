import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import folium
from streamlit_folium import st_folium
import os
from datetime import datetime

# 1. PAGE CONFIG (Harus paling atas)
st.set_page_config(page_title="SIG-DOM POS", page_icon="🚚", layout="wide")

# 2. DATABASE ENGINE
def get_engine():
    # Mengambil langsung dari st.secrets (lebih stabil untuk Streamlit Cloud)
    if "DB_URL" not in st.secrets:
        st.error("DB_URL tidak ditemukan di Secrets!")
        return None
    try:
        url = st.secrets["DB_URL"]
        # Menggunakan pool_size untuk membatasi koneksi agar tidak kena limit Supabase
        return create_engine(
            url, 
            pool_size=5, 
            max_overflow=0, 
            pool_pre_ping=True
        )
    except Exception as e:
        st.error(f"Gagal Inisialisasi Database: {e}")
        return None

engine = get_engine()

# 3. AUTHENTICATION
def check_login(u, p):
    if not engine: return None
    # Gunakan try-except lokal agar error redacted bisa terlihat detailnya
    try:
        query = text("""
            SELECT id_kantor, username, nama_kantor, status 
            FROM users_dc 
            WHERE username = :u AND password_hash = :p AND status = 'aktif'
        """)
        with engine.connect() as conn:
            result = conn.execute(query, {"u": u, "p": p}).fetchone()
            if result:
                return {"id_kantor": result[0], "nama_kantor": result[2]}
            return "WRONG"
    except Exception as e:
        st.warning(f"Koneksi sedang sibuk atau bermasalah: {str(e)}")
        return None

# --- APP LOGIC ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    # --- HALAMAN LOGIN ---
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://upload.wikimedia.org/wikipedia/id/thumb/0/00/Pos_Indonesia_2012.svg/1200px-Pos_Indonesia_2012.svg.png", width=120)
        st.title("SIG-DOM Login")
        with st.form("form_login"):
            user_in = st.text_input("Username")
            pass_in = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk", use_container_width=True):
                res = check_login(user_in, pass_in)
                if res == "WRONG":
                    st.error("Kredensial salah!")
                elif res:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = res
                    st.rerun()
else:
    # --- HALAMAN DASHBOARD ---
    info = st.session_state['user_info']
    
    with st.sidebar:
        st.title("🚚 SIG-DOM")
        st.info(f"Kantor: {info['nama_kantor']}")
        menu = st.radio("Menu", ["🗺️ Zona Antaran", "📦 History Per Petugas"])
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()

    if menu == "🗺️ Zona Antaran":
        st.header("Visualisasi Wilayah Antaran")
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text("SELECT kodepos, nama_zona, ST_AsGeoJSON(geom)::json as geojson FROM zona_antaran"), conn)
            
            if not df.empty:
                m = folium.Map(location=[-6.9147, 107.6098], zoom_start=13)
                for _, row in df.iterrows():
                    folium.GeoJson(row['geojson'], tooltip=row['nama_zona']).add_to(m)
                st_folium(m, width="100%", height=600)
            else:
                st.info("Belum ada data zona.")
        except Exception as e:
            st.error(f"Error load peta: {e}")

    elif menu == "📦 History Per Petugas":
        st.header("History Jalur Kurir")
        # Filter petugas dan tanggal bisa ditambahkan di sini
        st.write("Silakan pilih filter untuk menampilkan rute.")

st.markdown("---")
st.caption(f"SIG-DOM v1.3 | PT Pos Indonesia | {datetime.now().year}")
