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
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        selected_label = st.selectbox("Pilih Petugas Antar:", list(dict_petugas.keys()))
                        selected_id = dict_petugas[selected_label]
                    with col_f2:
                        selected_date = st.date_input("Pilih Tanggal Kiriman:", datetime.now())

                    # 2. Query Data Riwayat
                    query_titik = text("""
                        SELECT 
                            connote, produk, jenis_kiriman, status_antaran, 
                            penerima, alamat_penerima, waktu_kejadian, keterangan,
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
                        st.subheader(f"Peta Sebaran: {selected_label} ({selected_date.strftime('%d %b %Y')})")
                        avg_lat = df_titik['latitude'].mean()
                        avg_lon = df_titik['longitude'].mean()
                        m_antaran = folium.Map(location=[avg_lat, avg_lon], zoom_start=14)

                        for _, row in df_titik.iterrows():
                            status_str = str(row['status_antaran']).upper()
                            
                            # LOGIKA WARNA TAG LOKASI
                            if "FAILED" in status_str:
                                color_icon = "red"
                            elif status_str == "DELIVERED":
                                color_icon = "green"
                            else:
                                color_icon = "orange"
                            
                            tooltip_html = f"""
                            <div style="font-family: sans-serif; font-size: 12px; width: 250px;">
                                <h4 style="margin:0 0 5px 0; color:#003366;">{row['connote']}</h4>
                                <b>Penerima:</b> {row['penerima']}<br>
                                <b>Status:</b> <span style="color:{color_icon};">{row['status_antaran']}</span><br>
                                <b>Waktu:</b> {row['waktu_kejadian']}
                            </div>
                            """
                            folium.Marker(
                                location=[row['latitude'], row['longitude']],
                                popup=folium.Popup(tooltip_html, max_width=300),
                                icon=folium.Icon(color=color_icon, icon='bicycle', prefix='fa')
                            ).add_to(m_antaran)
                        
                        st_folium(m_antaran, width="100%", height=500, key=f"map_{selected_id}_{selected_date}")
                        st.markdown("---")

                        # --- BAGIAN RESUME & RINCIAN ---
                        st.subheader(f"📊 Resume & Rincian - {selected_date.strftime('%d/%m/%Y')}")
                        
                        # Hitung metrik (Hanya DELIVERED untuk Berhasil)
                        delivered_mask = df_titik['status_antaran'].str.upper() == "DELIVERED"
                        failed_mask = df_titik['status_antaran'].str.upper().str.contains("FAILED", na=False)
                        
                        success_count = len(df_titik[delivered_mask])
                        failed_count = len(df_titik[failed_mask])
                        
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total Antaran", len(df_titik))
                        m2.metric("Berhasil (DELIVERED)", success_count)
                        m3.metric("Gagal (FAILED)", failed_count)

                        # --- LOGIKA RESUME PER PRODUK (TABLE PIVOT) ---
                        st.markdown("##### Resume per Produk")
                        
                        # Membuat kolom kategori untuk pivot
                        df_res = df_titik.copy()
                        df_res['Berhasil'] = df_res['status_antaran'].apply(lambda x: 1 if str(x).upper() == "DELIVERED" else 0)
                        df_res['Gagal'] = df_res['status_antaran'].apply(lambda x: 1 if "FAILED" in str(x).upper() else 0)
                        
                        # Grouping sesuai permintaan: Produk | Berhasil | Gagal | Jumlah
                        resume_tab = df_res.groupby('produk').agg({
                            'Berhasil': 'sum',
                            'Gagal': 'sum',
                            'connote': 'count'
                        }).reset_index()
                        
                        resume_tab.columns = ['Produk', 'Berhasil', 'Gagal', 'Jumlah']
                        st.dataframe(resume_tab, use_container_width=True, hide_index=True)

                        st.markdown("##### Rincian Data")
                        st.dataframe(
                            df_titik[['connote', 'produk', 'penerima', 'status_antaran', 'waktu_kejadian', 'alamat_penerima', 'keterangan']], 
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.warning(f"Tidak ada data titikan untuk petugas {selected_label} pada tanggal {selected_date}")
                else:
                    st.info("Tidak ada data petugas pengantar yang tercatat di kantor ini.")
        except Exception as e:
            st.error(f"Kesalahan Database: {e}")
