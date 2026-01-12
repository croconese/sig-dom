import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import folium
from streamlit_folium import st_folium
import os
from dotenv import load_dotenv
from datetime import datetime

# 1. LOAD KONFIGURASI
load_dotenv()

# 2. FUNGSI KONEKSI DATABASE
def get_engine():
    db_url = os.getenv("DB_URL")
    if not db_url:
        return None
    try:
        # Menggunakan koneksi pooling untuk kestabilan di Cloud
        return create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        st.error(f"Koneksi Database Gagal: {e}")
        return None

engine = get_engine()

# 3. FUNGSI AUTHENTIKASI
def check_login(username, password):
    if not engine: return None
    query = text("""
        SELECT id_kantor, username, nama_kantor, status 
        FROM users_dc 
        WHERE username = :u AND password_hash = :p AND status = 'aktif'
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"u": username, "p": password}).fetchone()
        return result

# --- SESSION STATE UNTUK LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

# --- HALAMAN LOGIN ---
if not st.session_state['logged_in']:
    st.set_page_config(page_title="Login SIG-DOM", page_icon="🔐")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://upload.wikimedia.org/wikipedia/id/thumb/0/00/Pos_Indonesia_2012.svg/1200px-Pos_Indonesia_2012.svg.png", width=150)
        st.title("SIG-DOM Login")
        st.subheader("Sistem Informasi Geografis - Delivery Operation")
        
        with st.form("login_box"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Masuk Ke Dashboard", use_container_width=True)
            
            if submitted:
                user_data = check_login(u, p)
                if user_data:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user_data
                    st.success("Login Berhasil!")
                    st.rerun()
                else:
                    st.error("Username/Password salah atau akun dinonaktifkan.")

# --- HALAMAN DASHBOARD UTAMA ---
else:
    user = st.session_state['user_info']
    
    st.set_page_config(page_title=f"SIG-DOM - {user.nama_kantor}", layout="wide")

    # SIDEBAR
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/id/thumb/0/00/Pos_Indonesia_2012.svg/1200px-Pos_Indonesia_2012.svg.png", width=80)
        st.title("Menu Utama")
        st.write(f"📍 **{user.nama_kantor}**")
        st.markdown("---")
        
        menu = st.radio(
            "Navigasi:",
            ["🗺️ Visualisasi Zona", "📦 History Antaran Per Petugas"]
        )
        
        st.markdown("---")
        if st.button("🚪 Keluar Aplikasi", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- MENU 1: VISUALISASI ZONA ---
    if menu == "🗺️ Visualisasi Zona":
        st.header(f"Peta Zona Antaran - {user.nama_kantor}")
        
        if engine:
            with engine.connect() as conn:
                df_zona = pd.read_sql(text("""
                    SELECT kodepos, nama_zona, ST_AsGeoJSON(geom)::json as geojson 
                    FROM zona_antaran
                """), conn)

            if not df_zona.empty:
                m = folium.Map(location=[-6.9147, 107.6098], zoom_start=13)
                
                # Warna Otomatis per Kodepos
                colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'cadetblue', 'darkgreen']
                
                for i, row in df_zona.iterrows():
                    color = colors[i % len(colors)]
                    folium.GeoJson(
                        row['geojson'],
                        name=row['kodepos'],
                        style_function=lambda x, c=color: {
                            'fillColor': c,
                            'color': 'black',
                            'weight': 2,
                            'fillOpacity': 0.3
                        },
                        tooltip=f"Kodepos: {row['kodepos']} ({row['nama_zona']})"
                    ).add_to(m)
                
                st_folium(m, width="100%", height=600)
            else:
                st.info("Data zona belum tersedia untuk kantor ini.")

    # --- MENU 2: HISTORY ANTARAN ---
    elif menu == "📦 History Antaran Per Petugas":
        st.header("History Antaran & Jalur Petugas")
        
        if engine:
            with engine.connect() as conn:
                df_petugas = pd.read_sql(text("SELECT id_petugas, nama_petugas FROM petugas_antaran"), conn)
            
            # Baris Filter
            c1, c2 = st.columns(2)
            with c1:
                p_pilih = st.selectbox("Pilih Petugas:", df_petugas['nama_petugas'].tolist() if not df_petugas.empty else ["Data Kosong"])
            with c2:
                t_pilih = st.date_input("Pilih Tanggal Antaran", datetime.now())

            # Query Data berdasarkan filter waktu_kejadian
            query_hist = text("""
                SELECT t.connote, t.penerima, t.status_antaran, t.waktu_kejadian,
                       ST_Y(t.geom) as lat, ST_X(t.geom) as lon
                FROM titikan_antaran t
                JOIN petugas_antaran p ON t.id_petugas = p.id_petugas
                WHERE p.nama_petugas = :n AND DATE(t.waktu_kejadian) = :d
                ORDER BY t.waktu_kejadian ASC
            """)

            with engine.connect() as conn:
                df_hist = pd.read_sql(query_hist, conn, params={"n": p_pilih, "d": t_pilih})

            if not df_hist.empty:
                st.success(f"Ditemukan {len(df_hist)} kiriman untuk {p_pilih}")
                
                # Layout Peta & Tabel
                col_map, col_tab = st.columns([2, 1])
                
                with col_map:
                    m_hist = folium.Map(location=[df_hist['lat'].mean(), df_hist['lon'].mean()], zoom_start=14)
                    
                    points = []
                    for _, row in df_hist.iterrows():
                        coord = [row['lat'], row['lon']]
                        points.append(coord)
                        
                        # Marker Warna
                        icon_c = 'green' if row['status_antaran'] == 'DELIVERED' else 'orange'
                        folium.Marker(
                            coord,
                            popup=f"Resi: {row['connote']}<br>Waktu: {row['waktu_kejadian']}",
                            tooltip=f"{row['connote']} - {row['status_antaran']}",
                            icon=folium.Icon(color=icon_c, icon='bicycle', prefix='fa')
                        ).add_to(m_hist)
                    
                    # Hubungkan titik menjadi jalur rute
                    if len(points) > 1:
                        folium.PolyLine(points, color="blue", weight=3, opacity=0.7).add_to(m_hist)
                    
                    st_folium(m_hist, width="100%", height=500)
                
                with col_tab:
                    st.write("📋 **Detail Urutan Antaran**")
                    df_display = df_hist[['waktu_kejadian', 'connote', 'status_antaran']]
                    st.dataframe(df_display, use_container_width=True, height=450)
            else:
                st.warning(f"Tidak ada aktivitas antaran untuk {p_pilih} pada tanggal tersebut.")

# FOOTER
st.markdown("---")
st.caption(f"SIG-DOM v1.0 | PT Pos Indonesia | {datetime.now().year}")
