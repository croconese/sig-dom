# sig-dom
SIG - Delivery Operation Monitoring

# Anggota 
 - Adi Nugroho - 714252026
 - Ari Hadiyono - 714252012
 - Aulia Rahman - 714252027
 - Syarif Mahfud - 714252025
 - Tri Windyartono - 714252003

# Latar Belakang
PT. Pos Indonesia (PosIND) mengelola jaringan logistik dan kurir terbesar di Indonesia, menjangkau seluruh pelosok negeri.
1. TANTANGAN
  - Efisiensi rute dan pembagian beban kerja kurir (Pengantar) yang merata
  - Kesulitan memonitor posisi dan progres antaran secara real-time
  - Analisis kinerja pengantaran (misalnya, area mana yang sering gagal) masih bersifat manual atau berbasis tabel, bukan spasial (peta)
2. MASALAH
Tanpa visualisasi spasial, manajemen di Delivery Center (DC) atau Kantor Cabang/Kantor Cabang Utama (KC/KCU) kesulitan mengambil keputusan cepat untuk optimalisasi rute, penanganan kegagalan, dan evaluasi kinerja area antaran.

# Tujuan
  - Merancang dan membangun Geodatabase (basis data spasial) untuk operasi antaran PT. Pos Indonesia.
  - Mengembangkan dashboard WebGIS interaktif untuk memvisualisasikan data operasional antaran.
  - Menyediakan tools analisis spasial sederhana untuk evaluasi kinerja pengantaran.

# Manfaat
  - Transparansi Operasional: Manajemen dapat melihat (secara visual) di mana setiap petugas berada dan area mana yang menjadi tanggung jawabnya.
  - Optimalisasi Beban Kerja: Memastikan pembagian zona antaran adil dan efisien berdasarkan data historis.
  - Akuntabilitas Kinerja: Memudahkan evaluasi kinerja kurir berdasarkan data spasial (rute, waktu, status keberhasilan).
  - Pengambilan Keputusan : Mengidentifikasi hotspot (area) kegagalan antaran untuk perbaikan layanan.

# Ruang Lingkup & Fitur Utama
 1. MANAJEMEN ZONA ANTARAN dengan Visualisasi data poligon yang merepresentasikan wilayah kerja (zona antaran) yang biasanya mereferensikan satu atau lebih wilayah kodepos karena setiap poligon zona akan termapping dengan petugas antaran dan kode kantor
 2. PELACAKAN RUTE ANTARAN HARIAN dengan Visualisasi data titik (points) yang direkam dari handheld petugas saat melakukan pembaruan/update status (misalnya: "Delivered", "Failed", "On Process") karena jika titik-titik ini diurutkan berdasarkan waktu, akan membentuk rute perjalanan harian petugas antaran.
 3. VISUALISASI ATRIBUT KIRIMAN dengan Menampilkan data non-spasial (atribut) yang melekat pada setiap titik antaran dimana saat pengguna mengklik sebuah titik antaran di peta, akan muncul pop-up berisi informasi kiriman.
 4. ANALISIS KINERJA ANTARAN yang akan menampilkan dashboard untuk melakukan kalkulasi/perhitungan sederhana serta mengukur kinerja proses antaran.

# Tools Pengembangan
  - Backend : Node.js
  - Backend Framework: Express.js 
  - Database Driver:  PostgreSQL
  - Frontend : React
  - Map : Leaflet

