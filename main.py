import streamlit as st
import pandas as pd  # Ubah dari 'import pd' menjadi 'import pandas as pd'
from sqlalchemy import create_engine, text
import folium
from streamlit_folium import st_folium
from datetime import datetime
import random

# --- CONFIG & ENGINE ---
st.set_page_config(page_title="SIG-DOM POS", layout="wide")

@st.cache_resource
def get_engine():
    return create_engine(st.secrets["DB_URL"], pool_pre_ping=True)

engine = get_engine()

# --- PALET WARNA (Global) ---
VIBRANT_PALETTE = [
    "#FF5733", "#33FF57", "#3357FF", "#F333FF", "#FF33A1",
    "#33FFF5", "#FFD700", "#ADFF2F", "#FF8C00", "#00FF00",
    "#00BFFF", "#FF00FF", "#7B68EE", "#FFA07A", "#00FA9A",
    "#FF1493", "#1E90FF", "#FFFF00", "#FF4500", "#8A2BE2",
    "#00CED1", "#9ACD32", "#FF6347", "#40E0D0", "#EE82EE",
    "#00FF7F", "#4169E1", "#D2691E", "#32CD32", "#FF69B4"
]

def get_bright_color(kodepos):
    random.seed(int(kodepos)) 
    return random.choice(VIBRANT_PALETTE)

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

# --- FUNGSI LOGIN ---
def login_ui():
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        # Menambahkan Logo di Halaman Login
        st.image("Logo Posind Biru.png", width=80, align="center") 
        st.title("Login SIG-DOM")
        st.subheader("PT Pos Indonesia (Persero)")
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk", use_container_width=True):
                try:
                    with engine.connect() as conn:
                        query = text("SELECT id_kantor, nama_kantor FROM users_dc WHERE username = :u AND password_hash = :p")
                        res = conn.execute(query, {"u": u, "p": p}).fetchone()
                        if res:
                            st.session_state.logged_in = True
                            st.session_state.user_info = {"id": res[0], "nama": res[1]}
                            st.rerun()
                        else:
                            st.error("Username atau Password salah!")
                except Exception as e:
                    st.error(f"Error Database: {e}")

# --- MENU UTAMA ---
def main_app():
    user = st.session_state.user_info
    
    # SIDEBAR NAVIGASI
    st.sidebar.image("Logo Posind Biru.png", use_container_width=True, width=30) # Logo di Sidebar
    st.sidebar.markdown("---")
    st.sidebar.title("SIG-DOM Dashboard")
    st.sidebar.info(f"📍 {user['nama']}")
    
    menu = st.sidebar.selectbox("Pilih Menu:", [
        "🗺️ Peta Wilayah Antaran", 
        "📦 Data Riwayat Antaran", 
    ])
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.rerun()

    # --- KONTEN MENU ---
    if menu == "🗺️ Peta Wilayah Antaran":
        st.header("Visualisasi Spasial Wilayah Antaran")
        
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text("""
                    SELECT kodepos, kecamatan, kelurahan, ST_AsGeoJSON(geom)::json as geo 
                    FROM zona_antaran
                """), conn)
            
            if not df.empty:
                m = folium.Map(location=[-6.9147, 107.6098], zoom_start=12)
                
                for _, row in df.iterrows():
                    color = get_bright_color(row['kodepos'])
                    
                    folium.GeoJson(
                        row['geo'],
                        style_function=lambda x, color=color: {
                            'fillColor': color,
                            'color': 'white',
                            'weight': 2,
                            'fillOpacity': 0.7,
                        },
                        tooltip=folium.Tooltip(f"Kodepos : {row['kodepos']} <br>Kecamatan : {row['kecamatan']} <br> Kelurahan : {row['kelurahan']} ")
                    ).add_to(m)

                st_folium(m, width="100%", height=600)
                
                st.markdown("### 📋 Keterangan Warna")
                cols = st.columns(5)
                for idx, row in df.iterrows():
                    with cols[idx % 5]:
                        warna = get_bright_color(row['kodepos'])
                        st.markdown(f"""
                            <div style="background-color:{warna}; padding:10px; border-radius:5px; 
                            text-align:center; color:white; font-weight:bold; text-shadow: 1px 1px 2px black;">
                                {row['kodepos']}
                            </div>
                            <div style="text-align:center; font-size:12px; margin-bottom:10px;">{row['kecamatan']}</div>
                        """, unsafe_allow_html=True)
            else:
                st.info("Belum ada data geometri di database.")
        except Exception as e:
            st.error(f"Gagal memuat peta: {e}")

    elif menu == "📦 Data Riwayat Antaran":
        st.header("Data Riwayat Antaran")
        data_dummy = {
            'No Resi': ['P24001', 'P24002'],
            'Status': ['Selesai', 'Selesai'],
            'Waktu': [datetime.now(), datetime.now()]
        }
        st.table(pd.DataFrame(data_dummy))

# --- JALANKAN APLIKASI ---
if not st.session_state.logged_in:
    login_ui()
else:
    main_app()
