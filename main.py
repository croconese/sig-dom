import streamlit as st
import pandas as pd
import psycopg2
import folium
from streamlit_folium import folium_static
import os
import json
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

# 2. Fungsi Koneksi Database
from sqlalchemy import create_engine

def get_connection():
    try:
        # Menambahkan connect_args untuk memaksa IPv4 jika memungkinkan
        engine = create_engine(os.getenv("DB_URL"))
        return engine.connect()
    except Exception as e:
        st.error(f"Gagal koneksi: {e}")
        return None
        

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="SIG-DOM PT POS INDONESIA",
    page_icon="🚚",
    layout="wide"
)

# 3. Header Dashboard
st.title("🚚 Delivery Operation Management (SIG-DOM)")
st.subheader("Monitoring Antaran DC Asia Afrika - Bandung")
st.markdown("---")

conn = get_connection()

if conn:
    # --- SIDEBAR FILTER ---
    st.sidebar.header("Filter Operasional")
    
    # Ambil daftar petugas untuk filter
    petugas_list = pd.read_sql("SELECT DISTINCT nama_petugas FROM petugas_antaran", conn)['nama_petugas'].tolist()
    selected_petugas = st.sidebar.multiselect("Pilih Petugas:", petugas_list)
    
    # Filter Status
    status_list = ["DELIVERED", "ON PROCESS", "REDELIVER"]
    selected_status = st.sidebar.multiselect("Status Antaran:", status_list, default=["DELIVERED", "ON PROCESS"])

    # --- QUERY DATA ---
    # Query Poligon Zona
    query_zona = """
        SELECT kodepos, nama_zona, ST_AsGeoJSON(geom)::json as geojson 
        FROM zona_antaran
    """
    df_zona = pd.read_sql(query_zona, conn)

    # Query Titik Antaran (dengan Filter)
    query_titik = """
        SELECT t.connote, t.penerima, t.status_antaran, t.alamat_penerima,
               p.nama_petugas, ST_Y(t.geom) as lat, ST_X(t.geom) as lon
        FROM titikan_antaran t
        LEFT JOIN petugas_antaran p ON t.id_petugas = p.id_petugas
        WHERE 1=1
    """
    
    if selected_petugas:
        query_titik += f" AND p.nama_petugas IN {tuple(selected_petugas) if len(selected_petugas) > 1 else '('+chr(39)+selected_petugas[0]+chr(39)+')'}"
    if selected_status:
        query_titik += f" AND t.status_antaran IN {tuple(selected_status) if len(selected_status) > 1 else '('+chr(39)+selected_status[0]+chr(39)+')'}"

    df_titik = pd.read_sql(query_titik, conn)

    # --- LAYOUT DASHBOARD ---
    col_map, col_stats = st.columns([3, 1])

    with col_map:
        st.markdown("#### Peta Sebaran Antaran")
        # Inisialisasi Peta Bandung
        m = folium.Map(location=[-6.9147, 107.6098], zoom_start=13, tiles="cartodbpositron")

        # Layer 1: Poligon Zona Antaran (Kodepos)
        for _, row in df_zona.iterrows():
            folium.GeoJson(
                row['geojson'],
                style_function=lambda x: {
                    'fillColor': '#ffcc00',
                    'color': '#ff6600',
                    'weight': 1.5,
                    'fillOpacity': 0.1
                },
                tooltip=f"Kodepos: {row['kodepos']} ({row['nama_zona']})"
            ).add_to(m)

        # Layer 2: Titik Antaran (Markers)
        for _, row in df_titik.iterrows():
            # Warna marker berdasarkan status
            color = "green" if row['status_antaran'] == "DELIVERED" else "orange"
            
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=folium.Popup(f"""
                    <b>Resi:</b> {row['connote']}<br>
                    <b>Penerima:</b> {row['penerima']}<br>
                    <b>Status:</b> {row['status_antaran']}<br>
                    <b>Kurir:</b> {row['nama_petugas']}
                """, max_width=300),
                tooltip=f"{row['penerima']} ({row['status_antaran']})",
                icon=folium.Icon(color=color, icon="info-sign")
            ).add_to(m)

        # Tampilkan Peta
        folium_static(m, width=950, height=600)

    with col_stats:
        st.markdown("#### Statistik")
        st.metric("Total Kiriman", len(df_titik))
        
        # Grafik Status
        if not df_titik.empty:
            status_counts = df_titik['status_antaran'].value_counts()
            st.bar_chart(status_counts)
            
            st.markdown("---")
            st.markdown("#### Detail Kiriman")
            st.dataframe(df_titik[['connote', 'penerima', 'status_antaran']], height=300)
        else:
            st.warning("Tidak ada data untuk filter ini.")

    conn.close()
else:
    st.error("Hubungkan database Supabase Anda melalui file .env")

# Footer
st.markdown("---")
st.caption("Aplikasi SIG-DOM PT Pos Indonesia © 2024 - Powered by Supabase & Streamlit")
