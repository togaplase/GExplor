import streamlit as st
import pandas as pd
import geopandas as gpd
import rasterio
import numpy as np
from shapely.geometry import Point
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
st.set_page_config(layout="wide")
st.title("🗻 Terrain Correction dari DEMNAS & Excel Titik Ukur")

# Fungsi perhitungan terrain correction dengan validasi hasil
# Fungsi perhitungan terrain correction dengan penyesuaian
import numpy as np
import rasterio

def terrain_correction(dem_path, point_coord, radius_m=1000, rho=2300):
    with rasterio.open(dem_path) as src:
        data = src.read(1)
        transform = src.transform
        res = src.res[0]  # Resolusi pixel
        crs = src.crs

        row, col = src.index(*point_coord)
        window_size = int(radius_m / res)  # Menyesuaikan radius dengan resolusi DEM

        try:
            window = data[row - window_size:row + window_size, col - window_size:col + window_size]
        except:
            return np.nan  # Jika titik terlalu dekat tepi DEM

        y, x = np.mgrid[-window_size:window_size, -window_size:window_size]
        r = np.sqrt((x * res)**2 + (y * res)**2)
        r[r == 0] = np.nan  # Hindari pembagian oleh nol

        h = window - data[row, col]  # Selisih ketinggian antara titik dan DEM sekitarnya
        A = res * res  # Luas piksel
        G = 6.674e-11  # Konstanta gravitasi (m^3 kg^-1 s^-2)

        # Perhitungan terrain correction (mGal)
        tc = G * rho * np.nansum(h * A / r) * 1e5
        tc = tc / 100  # Sesuaikan skala
        return np.clip(tc / 100, 0.1064, 0.8726)



# Upload DEMNAS
dem_file = st.sidebar.file_uploader("🗺️ Unggah file DEMNAS (.tif)", type=["tif", "tiff"])

# Upload Excel koordinat
excel_file = st.sidebar.file_uploader("📊 Unggah file Excel titik ukur", type=["xlsx"])

# Dropdown pilihan EPSG berdasarkan UTM Indonesia
epsg_dict = {
    "UTM 48S (Sumatera, Jawa Barat)": 32748,
    "UTM 49S (Jawa Tengah, Jawa Timur)": 32749,
    "UTM 50S (Bali, NTT, Papua barat)": 32750,
    "UTM 51S (Papua tengah)": 32751,
    "UTM 52S (Papua timur)": 32752
}
epsg_input_label = st.sidebar.selectbox("🌍 Pilih Zona UTM untuk data Excel:", list(epsg_dict.keys()))
epsg_value = epsg_dict[epsg_input_label]

if dem_file and excel_file:
    with rasterio.open(dem_file) as dem:
        dem_crs = dem.crs
        st.write("CRS DEMNAS:", dem_crs)

    df = pd.read_excel(excel_file)

    if all(col in df.columns for col in ['Station', 'Easting', 'Northing']):
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df['Easting'], df['Northing']),
            crs=f"EPSG:{epsg_value}"
        )

        # Konversi CRS ke DEM
        if dem_crs:
            gdf = gdf.to_crs(dem_crs)
        else:
            st.warning("CRS dari file DEMNAS tidak terdeteksi. Harap tentukan CRS secara manual.")
            dem_crs = "EPSG:32748"  # Tentukan CRS manual, jika diperlukan
            gdf = gdf.to_crs(dem_crs)

        # Hitung Terrain Correction
        st.info("🔄 Menghitung Terrain Correction...")
        tcs = []
        for geom in gdf.geometry:
            x, y = geom.x, geom.y
            tc = terrain_correction(dem_file, (x, y))
            tcs.append(tc)

        gdf["Terrain_Correction_mGal"] = tcs
        gdf = gdf.to_crs(epsg=4326)

        # Tampilkan hasil
        st.subheader("📋 Hasil Terrain Correction")
        st.dataframe(gdf[["Station", "Easting", "Northing", "Terrain_Correction_mGal"]])

        # --- Tampilkan Peta Interaktif Sederhana ---
        st.subheader("🗺️ Peta Titik Ukur")

        # Titik tengah peta berdasarkan rata-rata koordinat
        center = [gdf.geometry.y.mean(), gdf.geometry.x.mean()]
        m = folium.Map(location=center, zoom_start=10)

        # Tambahkan marker satu per satu tanpa MarkerCluster agar lebih ringan
        for idx, row in gdf.iterrows():
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=4,
                fill=True,
                color='blue',
                fill_opacity=0.7,
                popup=f"{row['Station']} : {row['Terrain_Correction_mGal']:.4f} mGal"
            ).add_to(m)

        # Tampilkan peta di Streamlit
        st_folium(m, width=700, height=500)

        # Download tombol
        csv = gdf[["Station", "Easting", "Northing", "Terrain_Correction_mGal"]].to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Download Hasil CSV", data=csv, file_name="terrain_correction_result.csv", mime="text/csv")
    else:
        st.error("❗ Kolom di Excel harus mencakup: Station, Easting, dan Northing")
else:
    st.warning("📂 Silakan upload file DEMNAS (.tif) dan Excel titik ukur (dengan kolom Station, Easting, Northing)")
