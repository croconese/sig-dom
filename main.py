import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import folium
from streamlit_folium import st_folium
from datetime import datetime
import random

# --- CONFIG & ENGINE ---
st.set_page_config(page_title="SIG-DOM POS", layout="wide", page_icon="🚚")

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
    try:
        random.seed(int(kodepos)) 
    except:
        random.seed(hash(str(kodepos)))
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
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>SIG-DOM Dashboard</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>PT Pos Indonesia (Persero)</p>", unsafe_allow_html=True)
        
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
    st.sidebar.title("SIG-DOM")
    st.sidebar.markdown(f"**📍 {user['nama']}**")
    st.sidebar.markdown("---")
    
    menu = st.sidebar.selectbox("Pilih Menu:", ["🗺️ Peta Wilayah Antaran", "📦 Data Riwayat Antaran"])
    
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.rerun()

    if menu == "🗺️ Peta Wilayah Antaran":
        st.header("Visualisasi Spasial Wilayah Antaran")
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text("SELECT kodepos, kecamatan, kelurahan, ST_AsGeoJSON(geom)::json as geo FROM zona_antaran"), conn)
            if not df.empty:
                m = folium.Map(location=[-6.9147, 107.6098], zoom_start=12)
                for _, row in df.iterrows():
                    color = get_bright_color(row['kodepos'])
                    folium.GeoJson(row['geo'], style_function=lambda x, color=color: {'fillColor': color, 'color': 'white', 'weight': 2, 'fillOpacity': 0.7}, tooltip=folium.Tooltip(f"Kodepos : {row['kodepos']} <br>Kecamatan : {row['kecamatan']} <br> Kelurahan : {row['kelurahan']}")).add_to(m)
                st_folium(m, width="100%", height=600)
        except Exception as e:
            st.error(f"Gagal memuat peta: {e}")

    elif menu == "📦 Data Riwayat Antaran":
        st.header("Data Riwayat Antaran")
        try:
            with engine.connect() as conn:
                query_petugas = text("SELECT DISTINCT p.id_petugas, p.nama_petugas FROM petugas_antaran p JOIN titikan_antaran t ON p.id_petugas = t.id_petugas WHERE p.id_kantor = :id_kantor")
                res_petugas = conn.execute(query_petugas, {"id_kantor": user['id']}).fetchall()
                dict_petugas = {f"{p[0]} - {p[1]}": p[0] for p in res_petugas}

                if dict_petugas:
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        selected_label = st.selectbox("Pilih Petugas Antar:", list(dict_petugas.keys()))
                        selected_id = dict_petugas[selected_label]
                    with col_f2:
                        selected_date = st.date_input("Pilih Tanggal Kiriman:", datetime.now())

                    query_titik = text("""
                        SELECT connote, produk, status_antaran, penerima, alamat_penerima, waktu_kejadian, keterangan,
                               ST_X(geom) as longitude, ST_Y(geom) as latitude
                        FROM titikan_antaran 
                        WHERE id_petugas = :petugas AND id_kantor = :id_kantor AND DATE(waktu_kejadian) = :tgl
                    """)
                    df_titik = pd.read_sql(query_titik, conn, params={"petugas": selected_id, "id_kantor": user['id'], "tgl": selected_date})

                    if not df_titik.empty:
                        # Peta
                        m_antaran = folium.Map(location=[df_titik['latitude'].mean(), df_titik['longitude'].mean()], zoom_start=14)
                        for _, row in df_titik.iterrows():
                            status_up = str(row['status_antaran']).upper()
                            color_icon = "green" if status_up == "DELIVERED" else "red" if "FAILED" in status_up else "orange"
                            folium.Marker([row['latitude'], row['longitude']], tooltip=f"{row['connote']}", icon=folium.Icon(color=color_icon, icon='bicycle', prefix='fa')).add_to(m_antaran)
                        st_folium(m_antaran, width="100%", height=500, key=f"map_{selected_id}_{selected_date}")

                        # --- RESUME ---
                        st.markdown("---")
                        st.subheader(f"📊 Resume & Rincian - {selected_date.strftime('%d/%m/%Y')}")
                        
                        total_ant = len(df_titik)
                        success_count = len(df_titik[df_titik['status_antaran'].str.upper() == "DELIVERED"])
                        failed_count = len(df_titik[df_titik['status_antaran'].str.upper().str.contains("FAILED", na=False)])
                        
                        # Kalkulasi Persentase Global
                        p_success = (success_count / total_ant * 100) if total_ant > 0 else 0
                        p_failed = (failed_count / total_ant * 100) if total_ant > 0 else 0

                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total Antaran", total_ant)
                        m2.metric("Berhasil (DELIVERED)", f"{success_count} ({p_success:.1f}%)")
                        m3.metric("Gagal (FAILED)", f"{failed_count} ({p_failed:.1f}%)")

                        # Tabel Resume per Produk dengan Persentase
                        st.markdown("##### Resume per Produk")
                        df_res = df_titik.copy()
                        df_res['Berhasil'] = df_res['status_antaran'].apply(lambda x: 1 if str(x).upper() == "DELIVERED" else 0)
                        df_res['Gagal'] = df_res['status_antaran'].apply(lambda x: 1 if "FAILED" in str(x).upper() else 0)
                        
                        resume_tab = df_res.groupby('produk').agg({
                            'Berhasil': 'sum', 
                            'Gagal': 'sum', 
                            'connote': 'count'
                        }).reset_index()
                        
                        resume_tab.columns = ['Produk', 'Berhasil', 'Gagal', 'Jumlah']
                        
                        # Tambahkan kolom Prosentase di Tabel
                        resume_tab['% Sukses'] = (resume_tab['Berhasil'] / resume_tab['Jumlah'] * 100).map('{:.1f}%'.format)
                        resume_tab['% Gagal'] = (resume_tab['Gagal'] / resume_tab['Jumlah'] * 100).map('{:.1f}%'.format)
                        
                        # Susun ulang kolom agar lebih rapi
                        resume_tab = resume_tab[['Produk', 'Berhasil', '% Sukses', 'Gagal', '% Gagal', 'Jumlah']]
                        st.dataframe(resume_tab, use_container_width=True, hide_index=True)

                        st.markdown("##### Rincian Data")
                        st.dataframe(df_titik[['connote', 'produk', 'penerima', 'status_antaran', 'waktu_kejadian', 'alamat_penerima']], use_container_width=True, hide_index=True)
                    else:
                        st.warning(f"Tidak ada data antaran untuk petugas {selected_label} pada tanggal {selected_date}")
                else:
                    st.info("Petugas tidak ditemukan.")
        except Exception as e:
            st.error(f"Error Database: {e}")

if not st.session_state.logged_in:
    login_ui()
else:
    main_app()
