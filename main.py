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
                
                # --- UPDATE BAGIAN KETERANGAN WARNA ---
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
                # 1. Ambil daftar pengantar (id_petugas)
                query_pengantar = text("SELECT DISTINCT id_petugas FROM titikan_antaran WHERE id_kantor = :id_kantor")
                list_pengantar = conn.execute(query_pengantar, {"id_kantor": user['id']}).fetchall()
                list_pengantar = [p[0] for p in list_pengantar if p[0] is not None]

                if list_pengantar:
                    selected_pengantar = st.selectbox("Pilih ID Petugas:", list_pengantar)

                    # 2. Query dengan nama kolom yang disesuaikan (barcode/no_resi)
                    # Saya tambahkan alias 'connote' agar kode di bawahnya tetap konsisten
                    query_titik = text("""
                        SELECT 
                            connote,
                            produk,
                            jenis_kiriman,
                            status_antaran, 
                            is_cod,
                            nominal_cod,
                            berat_kg,
                            penerima,
                            alamat_penerima,
                            telp_penerima,
                            kodepos_penerima,
                            keterangan,
                            waktu_kejadian, 
                            ST_X(geom) as longitude, 
                            ST_Y(geom) as latitude
                        FROM titikan_antaran 
                        WHERE id_petugas = :petugas AND id_kantor = :id_kantor
                        ORDER BY waktu_kejadian DESC
                    """)
                    
                    df_titik = pd.read_sql(query_titik, conn, params={
                        "petugas": selected_pengantar, 
                        "id_kantor": user['id']
                    })

                    if not df_titik.empty:
                        col_map, col_data = st.columns([2, 1])

                        with col_map:
                            st.subheader(f"Peta Sebaran: {selected_pengantar}")
                            avg_lat = df_titik['latitude'].mean()
                            avg_lon = df_titik['longitude'].mean()
                            
                            m_antaran = folium.Map(location=[avg_lat, avg_lon], zoom_start=14)

                            for _, row in df_titik.iterrows():
                                # Logika warna: Hijau untuk sukses/delivered
                                status_str = str(row['status_antaran']).upper()
                                color_icon = "green" if "SELESAI" in status_str or "DELIVERED" in status_str else "orange"
                                
                                folium.Marker(
                                    location=[row['latitude'], row['longitude']],
                                    popup=f"<b>Connote : </b> {row['connote']}<br> <b> Penerima : </b>  {row['penerima']} <br> <b> Produk : </b>  {row['produk']}  <br> <b> Jenis : </b>  {row['jenis_kiriman']}  <br> <b> Berat : </b>  {row['berat_kg']}",
                                    tooltip=f"{row['connote']}",
                                    icon=folium.Icon(color=color_icon, icon='bicycle', prefix='fa')
                                ).add_to(m_antaran)
                            
                            st_folium(m_antaran, width="100%", height=500, key="map_riwayat_new")

                        with col_data:
                            st.subheader("Data Kiriman")
                            st.metric("Total Kiriman", len(df_titik))
                            # Menampilkan tabel ringkas
                            st.dataframe(
                                df_titik[['connote', 'status_antaran', 'waktu_kejadian']], 
                                use_container_width=True,
                                hide_index=True
                            )
                    else:
                        st.warning(f"Belum ada koordinat untuk petugas {selected_pengantar}")
                else:
                    st.info("Tidak ada data petugas untuk kantor ini.")

        except Exception as e:
            # Jika masih error kolom, tampilkan daftar kolom yang ada agar kita bisa perbaiki
            st.error(f"Terjadi kesalahan struktur tabel.")
            if "column" in str(e):
                st.info("Tips: Pastikan nama kolom di tabel 'titikan_antaran' adalah 'barcode', jika bukan silakan ganti di kode.")
            st.expander("Lihat Detail Error").write(e)

# --- JALANKAN APLIKASI ---
if not st.session_state.logged_in:
    login_ui()
else:
    main_app()
