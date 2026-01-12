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
    "#00BFFF", "#FF00FF", "#7B68EE", "#FFA07A", "#00FA9A"
]

def get_bright_color(kodepos):
    try: random.seed(int(kodepos)) 
    except: random.seed(hash(str(kodepos)))
    return random.choice(VIBRANT_PALETTE)

# --- SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_info' not in st.session_state: st.session_state.user_info = None

# --- FUNGSI LOGIN ---
def login_ui():
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>SIG-DOM Dashboard</h1>", unsafe_allow_html=True)
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
                        else: st.error("Username atau Password salah!")
                except Exception as e: st.error(f"Error Database: {e}")

# --- MENU UTAMA ---
def main_app():
    user = st.session_state.user_info
    st.sidebar.title("SIG-DOM")
    st.sidebar.markdown(f"**📍 {user['nama']}**")
    st.sidebar.markdown("---")
    
    menu = st.sidebar.selectbox("Pilih Menu:", ["🗺️ Peta Wilayah Antaran", "📦 Data Riwayat Antaran"])
    
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    # --- MENU: PETA WILAYAH ---
    if menu == "🗺️ Peta Wilayah Antaran":
        st.header("Visualisasi Spasial Wilayah Antaran")
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text("""
                    SELECT kodepos, kecamatan, kelurahan, 
                           ST_AsGeoJSON(geom)::json as geo,
                           (ST_Area(geom::geography) / 1000000) as luas_km2
                    FROM zona_antaran
                """), conn)
            
            if not df.empty:
                m = folium.Map(location=[-6.9147, 107.6098], zoom_start=12)
                for _, row in df.iterrows():
                    color = get_bright_color(row['kodepos'])
                    
                    # --- TOOLTIP WILAYAH (HOVER) ---
                    tooltip_html = f"""
                    <div style="font-family: Arial; font-size: 12px;">
                        <b style="color: #003366;">{row['kelurahan']}</b><br>
                        Kodepos: {row['kodepos']}
                    </div>
                    """
                    
                    # --- POPUP WILAYAH (CLICK) ---
                    popup_html = f"""
                    <div style="width: 220px; font-family: sans-serif;">
                        <div style="background-color: #003366; color: white; padding: 6px; border-radius: 5px 5px 0 0; text-align: center; font-weight: bold; font-size: 13px;">
                            DATA WILAYAH
                        </div>
                        <div style="padding: 10px; border: 1px solid #ddd; background-color: #fcfcfc;">
                            <table style="width: 100%; font-size: 11px; border-collapse: collapse;">
                                <tr><td style="padding: 2px;"><b>Kodepos</b></td><td>: {row['kodepos']}</td></tr>
                                <tr><td style="padding: 2px;"><b>Kecamatan</b></td><td>: {row['kecamatan']}</td></tr>
                                <tr><td style="padding: 2px;"><b>Kelurahan</b></td><td>: {row['kelurahan']}</td></tr>
                                <tr><td style="padding: 2px;"><b>Luas Area</b></td><td style="color: #d9534f; font-weight: bold;">: {row['luas_km2']:.2f} km²</td></tr>
                            </table>
                        </div>
                    </div>
                    """
                    
                    folium.GeoJson(
                        row['geo'],
                        style_function=lambda x, color=color: {
                            'fillColor': color, 'color': 'white', 'weight': 1.5, 'fillOpacity': 0.6
                        },
                        tooltip=folium.Tooltip(tooltip_html),
                        popup=folium.Popup(popup_html, max_width=250)
                    ).add_to(m)
                
                st_folium(m, width="100%", height=600)
                
                st.markdown("### 📋 Keterangan Wilayah & Luas Area")
                cols = st.columns(5)
                for idx, row in df.iterrows():
                    with cols[idx % 5]:
                        warna = get_bright_color(row['kodepos'])
                        st.markdown(f"""
                            <div style="background-color:{warna}; padding:10px; border-radius:5px; text-align:center; color:white; font-weight:bold; text-shadow: 1px 1px 2px black;">
                                {row['kodepos']}
                            </div>
                            <div style="text-align:center; font-size:12px; margin-top:5px;">
                                <b>{row['kelurahan']}</b><br>{row['luas_km2']:.2f} km²
                            </div>
                            <br>
                        """, unsafe_allow_html=True)
        except Exception as e: st.error(f"Error: {e}")

    # --- MENU: DATA RIWAYAT ---
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
                        SELECT connote, produk, status_antaran, penerima, alamat_penerima, waktu_kejadian,
                               ST_X(geom) as longitude, ST_Y(geom) as latitude
                        FROM titikan_antaran 
                        WHERE id_petugas = :petugas AND id_kantor = :id_kantor AND DATE(waktu_kejadian) = :tgl
                        ORDER BY waktu_kejadian ASC
                    """)
                    df_titik = pd.read_sql(query_titik, conn, params={"petugas": selected_id, "id_kantor": user['id'], "tgl": selected_date})

                    if not df_titik.empty:
                        df_titik['waktu_kejadian'] = pd.to_datetime(df_titik['waktu_kejadian'])
                        df_titik['jeda'] = df_titik['waktu_kejadian'].diff().dt.total_seconds() / 60
                        df_titik['jeda'] = df_titik['jeda'].fillna(0)

                        m_antaran = folium.Map(location=[df_titik['latitude'].mean(), df_titik['longitude'].mean()], zoom_start=14)
                        for _, row in df_titik.iterrows():
                            status_up = str(row['status_antaran']).upper()
                            color_icon = "green" if status_up == "DELIVERED" else "red" if "FAILED" in status_up else "orange"
                            badge_color = "#28a745" if status_up == "DELIVERED" else "#dc3545"

                            t_html = f"<div style='font-family: Arial;'><b>{row['connote']}</b><br>👤 {row['penerima']}</div>"
                            p_html = f"""
                            <div style="width: 240px; font-family: sans-serif;">
                                <div style="background-color: #003366; color: white; padding: 7px; border-radius: 5px 5px 0 0; font-weight: bold; text-align: center; font-size: 12px;">RINCIAN ANTARAN</div>
                                <div style="padding: 10px; border: 1px solid #ddd; background-color: #f9f9f9;">
                                    <table style="width: 100%; font-size: 11px; border-collapse: collapse;">
                                        <tr><td><b>Connote</b></td><td>: {row['connote']}</td></tr>
                                        <tr><td><b>Penerima</b></td><td>: {row['penerima']}</td></tr>
                                        <tr><td><b>Waktu</b></td><td>: {row['waktu_kejadian'].strftime('%H:%M:%S')}</td></tr>
                                        <tr><td><b>Jeda</b></td><td>: {int(row['jeda'])} Menit</td></tr>
                                    </table>
                                    <div style="margin-top: 8px; text-align: center;">
                                        <span style="background-color: {badge_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px;">{status_up}</span>
                                    </div>
                                </div>
                            </div>
                            """
                            folium.Marker(
                                [row['latitude'], row['longitude']],
                                tooltip=folium.Tooltip(t_html),
                                popup=folium.Popup(p_html, max_width=300),
                                icon=folium.Icon(color=color_icon, icon='bicycle', prefix='fa')
                            ).add_to(m_antaran)
                        st_folium(m_antaran, width="100%", height=450, key=f"map_{selected_id}_{selected_date}")

                        # --- RESUME AREA ---
                        st.markdown("---")
                        c1, c2, c3, c4 = st.columns(4)
                        durasi_total = (df_titik['waktu_kejadian'].max() - df_titik['waktu_kejadian'].min()).total_seconds() / 60
                        c1.metric("Mulai", df_titik['waktu_kejadian'].min().strftime('%H:%M'))
                        c2.metric("Selesai", df_titik['waktu_kejadian'].max().strftime('%H:%M'))
                        c3.metric("Durasi Operasi", f"{int(durasi_total//60)}j {int(durasi_total%60)}m")
                        c4.metric("Avg Speed/Titik", f"{(durasi_total/len(df_titik)):.1f} Menit")

                        st.markdown("---")
                        total_k = len(df_titik)
                        berhasil_k = len(df_titik[df_titik['status_antaran'].str.upper() == "DELIVERED"])
                        gagal_k = total_k - berhasil_k
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total Kiriman", total_k)
                        m2.metric("Berhasil (DELIVERED)", berhasil_k, f"{(berhasil_k/total_k*100):.1f}%")
                        m3.metric("Gagal (FAILED)", gagal_k, f"-{(gagal_k/total_k*100):.1f}%", delta_color="inverse")
                    else: st.warning("Data tidak ditemukan.")
        except Exception as e: st.error(f"Error: {e}")

if not st.session_state.logged_in: login_ui()
else: main_app()
