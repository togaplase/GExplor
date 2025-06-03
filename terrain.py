import streamlit as st
import pandas as pd
import numpy as np
from pyproj import Proj, Transformer
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import geopandas as gpd
import requests
import rasterio
from rasterio.plot import show


# Fungsi untuk konversi UTM ke Longitude dan Latitude
def utm_to_latlon(easting, northing, zone, datum, hemisphere):
    proj_utm = Proj(proj='utm', zone=zone, datum=datum, south=hemisphere.lower() == 'south')
    proj_latlon = Proj(proj='latlong', datum=datum)
    transformer = Transformer.from_proj(proj_utm, proj_latlon)
    longitude, latitude = transformer.transform(easting, northing)
    return longitude, latitude


# Fungsi untuk menghilangkan outlier menggunakan IQR
def remove_outliers(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]


# Fungsi untuk mengunduh data DEMNAS dari API
def download_dem(lon_min, lat_min, lon_max, lat_max):
    base_url = "https://demnas.big.go.id/api/download"  # Perbarui endpoint sesuai dokumentasi API resmi
    params = {
        "bbox": f"{lon_min},{lat_min},{lon_max},{lat_max}",
        "format": "GeoTIFF"
    }
    try:
        response = requests.get(base_url, params=params, timeout=60)
        response.raise_for_status()
        with open("demnas.tif", "wb") as f:
            f.write(response.content)
        return "demnas.tif"
    except requests.exceptions.RequestException as e:
        st.error(f"Error downloading DEMNAS data: {e}")
        return None


# Fungsi untuk menghitung koreksi terrain gravity
def terrain_correction(dem_path, density=2670):
    with rasterio.open(dem_path) as src:
        elevation = src.read(1)  # Ambil data elevasi
        resolution = src.res  # Resolusi piksel (dx, dy)

        # Rumus koreksi terrain sederhana
        G = 6.67430e-11  # Gravitasi universal
        correction = (2 * np.pi * G * density * elevation) * (resolution[0] * resolution[1])
        return correction


# Header di sidebar
st.sidebar.header('Settings')

# File uploader untuk beberapa file Excel
uploaded_files = st.sidebar.file_uploader("Upload your Excel files", type=["xlsx", "xls"], accept_multiple_files=True)

if uploaded_files:
    st.sidebar.subheader("Select a file to view")
    file_options = [file.name for file in uploaded_files]
    selected_file = st.sidebar.selectbox("Choose a file:", file_options)
    selected_file_obj = next((file for file in uploaded_files if file.name == selected_file), None)

    st.sidebar.markdown("---")
    zone = st.sidebar.number_input("UTM Zone (1-60):", min_value=1, max_value=60, value=48, step=1)
    datum = st.sidebar.selectbox("Datum:", ["WGS84", "NAD83", "NAD27"])
    hemisphere = st.sidebar.selectbox("Hemisphere:", ["north", "south"])

    if selected_file_obj:
        try:
            df = pd.read_excel(selected_file_obj)

            if 'EASTING (m)' in df.columns and 'NORTHING (m)' in df.columns:
                df[['Longitude', 'Latitude']] = df.apply(
                    lambda row: pd.Series(
                        utm_to_latlon(row['EASTING (m)'], row['NORTHING (m)'], zone, datum, hemisphere)),
                    axis=1
                )

                lon_min, lat_min = df['Longitude'].min(), df['Latitude'].min()
                lon_max, lat_max = df['Longitude'].max(), df['Latitude'].max()

                dem_path = download_dem(lon_min, lat_min, lon_max, lat_max)

                if dem_path:
                    correction = terrain_correction(dem_path)
                    st.write("Terrain Correction Calculated Successfully")
                    st.write(correction)

            st.dataframe(df)
        except Exception as e:
            st.error(f"Error processing the file: {e}")
else:
    st.write("Please upload Excel files to begin.")
