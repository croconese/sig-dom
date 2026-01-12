import streamlit as st
import pandas as pd
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
    
    # SIDEBAR NAVIGASI
    st.sidebar.title("SIG-DOM")
    st.sidebar.markdown(f"**📍 {user['nama']}**")
    st.sidebar.markdown("---")
    
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
                        tooltip=folium.Tooltip(f"Kodepos : {row['kodepos']} <br>Kecamatan : {row['kecamatan']} <br> Kelurahan : {row['kelurahan']} <br> ")
                    ).add_to(m)

                st_folium(m, width="100%", height=600)
                
                st.markdown("### 📋 Keterangan Warna")
                cols = st.columns(5)
                for idx, row in df.iterrows():
                    with cols[idx % 5]:
                        warna = get_bright_color(row['kodepos'])
                        st.markdown(f"""
                            <div style="background-color:{warna}; padding:10px; border-radius:5px; 
                            text-align:center; color:white; font-weight:bold; text-shadow: 1px 1px 2px black; min-height: 50px; display: flex; align-items: center; justify-content: center;">
                                {row['kodepos']}
                            </div>
                            <div style="text-align:center; font-size:12px; margin-top:5px;">
                                <b>{row['kelurahan']}</b><br>
                                <span style="color: gray;">{row['kecamatan']}</span>
                            </div>
                            <br>
                        """, unsafe_allow_html=True)
            else:
                st.info("Belum ada data geometri di database.")
        except Exception as e:
            st.error(f"Gagal memuat peta: {e}")

    elif menu == "📦 Data Riwayat Antaran":
        st.header("Data Riwayat Antaran")
        
        try:
            with engine.connect() as conn:
                # 1. Ambil daftar pengantar (ID + Nama)
                query_petugas = text("""
                    SELECT DISTINCT p.id_petugas, p.nama_petugas 
                    FROM petugas_antaran p
                    JOIN titikan_antaran t ON p.id_petugas = t.id_petugas
                    WHERE p.id_kantor = :id_kantor
                """)
                res_petugas = conn.execute(query_petugas, {"id_kantor": user['id']}).fetchall()
                dict_petugas = {f"{p[0]} - {p[1]}": p[0] for p in res_petugas}

                if dict_petugas:
                    # --- BAGIAN FILTER (Petugas & Tanggal) ---
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        selected_label = st.selectbox("Pilih Petugas Antar:", list(dict_petugas.keys()))
                        selected_id = dict_petugas[selected_label]
                    with col_f2:
                        # Filter Tanggal (Default: Hari Ini)
                        selected_date = st.date_input("Pilih Tanggal Kiriman:", datetime.now())

                    # 2. Query Data Riwayat dengan Filter Tanggal
                    # Kita gunakan DATE(waktu_kejadian) untuk membandingkan hanya tanggalnya saja
                    query_titik = text("""
                        SELECT 
                            connote, produk, jenis_kiriman, status_antaran, 
                            is_cod, nominal_cod, berat_kg, penerima, 
                            alamat_penerima, telp_penerima, kodepos_penerima, 
                            keterangan, waktu_kejadian, 
                            ST_X(geom) as longitude, 
                            ST_Y(geom) as latitude
                        FROM titikan_antaran 
                        WHERE id_petugas = :petugas 
                        AND id_kantor = :id_kantor
                        AND DATE(waktu_kejadian) = :tgl
                        ORDER BY waktu_kejadian DESC
                    """)
                    
                    df_titik = pd.read_sql(query_titik, conn, params={
                        "petugas": selected_id, 
                        "id_kantor": user['id'],
                        "tgl": selected_date
                    })

                    if not df_titik.empty:
                        # Peta Full Width
                        st.subheader(f"Peta Sebaran: {selected_label} ({selected_date.strftime('%d %b %Y')})")
                        avg_lat = df_titik['latitude'].mean()
                        avg_lon = df_titik['longitude'].mean()
                        m_antaran = folium.Map(location=[avg_lat, avg_lon], zoom_start=14)

                        for _, row in df_titik.iterrows():
                            status_str = str(row['status_antaran']).upper()
                            color_icon = "green" if "SELESAI" in status_str or "DELIVERED" in status_str else "orange"
                            
                            tooltip_html = f"""
                            <div style="font-family: sans-serif; font-size: 12px; width: 250px;">
                                <h4 style="margin:0 0 5px 0; color:#003366;">{row['connote']}</h4>
                                <b>Penerima:</b> {row['penerima']}<br>
                                <b>Alamat:</b> {row['alamat_penerima']}<br>
                                <b>Produk:</b> {row['produk']} ({row['jenis_kiriman']})<br>
                                <b>Status:</b> <span style="color:{'green' if color_icon=='green' else 'red'};">{row['status_antaran']}</span><br>
                                <b>Waktu:</b> {row['waktu_kejadian']}<br>
                                <b>Keterangan:</b> {row['keterangan'] or '-'}
                            </div>
                            """
                            
                            folium.Marker(
                                location=[row['latitude'], row['longitude']],
                                popup=folium.Popup(tooltip_html, max_width=300),
                                tooltip=f"{row['connote']} - {row['penerima']}",
                                icon=folium.Icon(color=color_icon, icon='bicycle', prefix='fa')
                            ).add_to(m_antaran)
                        
                        st_folium(m_antaran, width="100%", height=500, key=f"map_{selected_id}_{selected_date}")

                        st.markdown("---")

                        # --- BAGIAN RESUME & RINCIAN ---
                        st.subheader(f"📊 Resume & Rincian - {selected_date.strftime('%d/%m/%Y')}")
                        
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total Antaran", len(df_titik))
                        success_count = len(df_titik[df_titik['status_antaran'].str.contains('Selesai|Delivered', case=False, na=False)])
                        m2.metric("Berhasil (Selesai)", success_count)
                        m3.metric("Gagal / Proses", len(df_titik) - success_count)

                        st.markdown("##### Resume per Produk")
                        resume_produk = df_titik.groupby(['produk', 'status_antaran']).size().reset_index(name='Jumlah')
                        st.dataframe(resume_produk, use_container_width=True, hide_index=True)

                        st.markdown("##### Rincian Data")
                        st.dataframe(
                            df_titik[['connote', 'produk', 'penerima', 'status_antaran', 'waktu_kejadian', 'alamat_penerima', 'keterangan']], 
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.warning(f"Tidak ada data titikan untuk petugas {selected_label} pada tanggal {selected_date}")
                else:
                    st.info("Tidak ada data petugas pengantar yang tercatat memiliki titikan di kantor ini.")

        except Exception as e:
            st.error(f"Kesalahan Database: {e}")

# --- JALANKAN APLIKASI ---
if not st.session_state.logged_in:
    login_ui()
else:
    main_app()
