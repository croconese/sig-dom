import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import folium
from streamlit_folium import st_folium
from datetime import datetime

# --- CONFIG & ENGINE ---
st.set_page_config(page_title="SIG-DOM POS", layout="wide")

@st.cache_resource
def get_engine():
    return create_engine(st.secrets["DB_URL"], pool_pre_ping=True)

engine = get_engine()

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- FUNGSI LOGIN ---
def login_ui():
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.image("https://upload.wikimedia.org/wikipedia/id/thumb/0/00/Pos_Indonesia_2012.svg/1200px-Pos_Indonesia_2012.svg.png", width=120)
        st.title("Login SIG-DOM")
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk", use_container_width=True):
                with engine.connect() as conn:
                    query = text("SELECT id_kantor, nama_kantor FROM users_dc WHERE username = :u AND password_hash = :p")
                    res = conn.execute(query, {"u": u, "p": p}).fetchone()
                    if res:
                        st.session_state.logged_in = True
                        st.session_state.user_info = {"id": res[0], "nama": res[1]}
                        st.rerun()
                    else:
                        st.error("Username atau Password salah!")

# --- MENU UTAMA ---
def main_app():
    user = st.session_state.user_info
    
    # SIDEBAR NAVIGASI
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/id/thumb/0/00/Pos_Indonesia_2012.svg/1200px-Pos_Indonesia_2012.svg.png", width=80)
    st.sidebar.title("SIG-DOM Dashboard")
    st.sidebar.info(f"📍 {user['nama']}")
    
    menu = st.sidebar.selectbox("Pilih Menu:", [
        "🏠 Dashboard & Statistik", 
        "🗺️ Peta Wilayah Antaran", 
        "📦 Data Titikan Paket", 
        "⚙️ Manajemen User"
    ])
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- KONTEN MENU ---
    if menu == "🏠 Dashboard & Statistik":
        st.header("Dashboard Utama")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Zona", "12 Zona")
        col2.metric("Titikan Hari Ini", "450 Paket")
        col3.metric("Kurir Aktif", "8 Petugas")
        
        st.markdown("---")
        st.subheader("Grafik Antaran Mingguan")
        # Placeholder grafik
        chart_data = pd.DataFrame([10, 25, 45, 30, 50], columns=["Paket"])
        st.line_chart(chart_data)

    elif menu == "🗺️ Peta Wilayah Antaran":
        st.header("Visualisasi Spasial Wilayah")
        st.write("Menampilkan pembagian zona berdasarkan kodepos.")
        
        # Koordinat default Bandung (Sesuaikan dengan wilayah Anda)
        m = folium.Map(location=[-6.9147, 107.6098], zoom_start=13)
        
        # Ambil data spasial dari Neon
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text("SELECT kodepos, nama_zona, ST_AsGeoJSON(geom)::json as geo FROM zona_antaran"), conn)
                for _, row in df.iterrows():
                    folium.GeoJson(row['geo'], tooltip=row['nama_zona']).add_to(m)
        except:
            st.info("Belum ada data geometri zona (Polygon) di database.")

        st_folium(m, width="100%", height=500)

    elif menu == "📦 Data Titikan Paket":
        st.header("Data Riwayat Antaran")
        st.write("Daftar koordinat paket yang telah diantarkan oleh kurir.")
        # Contoh tabel data
        data_dummy = {
            'No Resi': ['P24001', 'P24002'],
            'Status': ['Selesai', 'Selesai'],
            'Waktu': [datetime.now(), datetime.now()]
        }
        st.table(pd.DataFrame(data_dummy))

    elif menu == "⚙️ Manajemen User":
        st.header("Pengaturan Pengguna")
        with engine.connect() as conn:
            df_users = pd.read_sql(text("SELECT username, nama_kantor, status FROM users_dc"), conn)
            st.dataframe(df_users, use_container_width=True)

# --- JALANKAN APLIKASI ---
if not st.session_state.logged_in:
    login_ui()
else:
    main_app()
