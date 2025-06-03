import streamlit as st
import pandas as pd
import numpy as np
from pyproj import Proj, transform
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import geopandas as gpd
import requests
import rasterio
from rasterio.plot import show
from scipy.interpolate import CubicSpline
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
import plotly.express as px
# Fungsi untuk konversi UTM ke Longitude dan Latitude
def utm_to_latlon(easting, northing, zone, datum, hemisphere):
    proj_utm = Proj(proj='utm', zone=zone, datum=datum, south=hemisphere.lower() == 'south')
    proj_latlon = Proj(proj='latlong', datum=datum)
    longitude, latitude = transform(proj_utm, proj_latlon, easting, northing)
    return longitude, latitude


# Fungsi untuk menghilangkan outlier menggunakan IQR
def remove_outliers(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

st.sidebar.image("D:\PycharmProjects\pythonProject\SEG\streamlit-mark-color.png", width=150)

# Header di sidebar
st.sidebar.header('GExplor')
st.sidebar.markdown("*Comprehensive Gravity Exploration with Data Processing and Interactive Mapping*")

# File uploader untuk beberapa file Excel
uploaded_files = st.sidebar.file_uploader("Upload your Excel files", type=["xlsx", "xls"], accept_multiple_files=True)

# Memeriksa apakah ada file yang diunggah
if uploaded_files:
    st.sidebar.subheader("Select a file to view")
    file_options = [file.name for file in uploaded_files]
    selected_file = st.sidebar.selectbox("Choose a file:", file_options)
    selected_file_obj = next((file for file in uploaded_files if file.name == selected_file), None)

    # Pengaturan proyeksi di bawah file uploader
    st.sidebar.markdown("---")
    if st.sidebar.checkbox("Show Projection Settings"):
        st.sidebar.subheader("Projection Settings")
        zone = st.sidebar.number_input("UTM Zone (1-60):", min_value=1, max_value=60, value=48, step=1)
        datum = st.sidebar.selectbox("Datum:", ["WGS84", "NAD83", "NAD27"])
        hemisphere = st.sidebar.selectbox("Hemisphere:", ["north", "south"])
    else:
        zone = 48
        datum = "WGS84"
        hemisphere = "south"

    if selected_file_obj:
        try:
            # Membaca file Excel
            df = pd.read_excel(selected_file_obj)

            # Tambahkan kolom Grav Read Tide sebelum Drift
            if 'Gaverage' in df.columns and 'Tide Correction Average' in df.columns:
                df.insert(
                    df.columns.get_loc('Drift'),
                    'Grav Read Tide',
                    (df['Gaverage'] + df['Tide Correction Average']).round(3)
                )

            # Tambahkan kolom Grav Obs setelah Drift
            if 'Gaverage' in df.columns and 'Drift' in df.columns:
                df.insert(
                    df.columns.get_loc('Drift') + 1,
                    'Grav Obs',
                    (df['Gaverage'] + df['Drift']).round(3)
                )

            # Tambahkan kolom Delta G
            if 'Grav Obs' in df.columns:
                grav_obs_abs_first = abs(df['Grav Obs'].iloc[0])
                df['Delta G'] = (df['Grav Obs'] - grav_obs_abs_first).round(3)

            # Tambahkan kolom G Obs
            if 'Delta G' in df.columns:
                gabsolut = 977863.579
                df['G Obs'] = (gabsolut + df['Delta G']).round(3)

                # Konversi UTM ke Latitude dan Longitude
                if 'EASTING (m)' in df.columns and 'NORTHING (m)' in df.columns:
                    df[['Longitude', 'Latitude']] = df.apply(
                        lambda row: pd.Series(
                            utm_to_latlon(row['EASTING (m)'], row['NORTHING (m)'], zone, datum, hemisphere)),
                        axis=1
                    )

                    # Konversi Latitude ke Radians
                    df['Latitude (radians)'] = np.radians(df['Latitude'])

                    # Perhitungan GReduksi Gravitasi
                    df['GReduksi Gravitasi'] = 978031.8 * (
                            1
                            + 0.005304 * np.sin(df['Latitude (radians)']) ** 2
                            + 0.0000059 * np.sin(2 * df['Latitude (radians)']) ** 2
                    ).round(3)

                # Perhitungan G FA
                if 'ELEVATION (m)' in df.columns:
                    df['G FA'] = (0.3085672 * df['ELEVATION (m)']).round(3)
                else:
                    st.warning("Kolom 'ELEVATION (m)' tidak ditemukan.")

            # Tampilkan kolom BS hanya jika Bouguer Anomaly dipilih
            if st.sidebar.checkbox("Show Paransis Method Regression") :
                if 'ELEVATION (m)' in df.columns and 'G Obs' in df.columns and 'GReduksi Gravitasi' in df.columns and 'G FA' in df.columns:
                    # Perhitungan x dan y
                    # Perhitungan x dan y
                    df['x'] = 0.04185 * df['ELEVATION (m)']  # Elevasi yang dikalikan konstanta
                    df['y'] = df['G Obs']  # Tidak ada pengurangan, hanya mengambil kolom G Obs

                    # Hilangkan outlier dari y
                    df_no_outliers = remove_outliers(df, 'y')

                    # Regresi linier
                    x = df_no_outliers['x'].values.reshape(-1, 1)
                    y = df_no_outliers['y'].values.reshape(-1, 1)
                    model = LinearRegression()
                    model.fit(x, y)
                    y_pred = model.predict(x)

                    # Plot scatter plot dan garis regresi
                    plt.figure(figsize=(10, 6))
                    plt.scatter(df_no_outliers['x'], df_no_outliers['y'], color='blue',
                                label='Data Points (No Outliers)')
                    plt.plot(df_no_outliers['x'], y_pred, color='red', label='Linear Regression')
                    plt.xlabel('0.04185 * ELEVATION (m)')
                    plt.ylabel('G Obs')
                    plt.title('Paransis Method with Linear Regression (No Outliers)')
                    plt.legend()
                    plt.grid(True)
                    st.pyplot(plt)

                    # Tampilkan persamaan regresi
                    st.write(f"Linear Regression Equation: y = {model.coef_[0][0]:.4f}x + {model.intercept_[0]:.4f}")

                else:
                    st.warning("Kolom 'ELEVATION (m)', 'G Obs', 'GReduksi Gravitasi', atau 'G FA' tidak ditemukan.")
                K = st.sidebar.number_input("Enter constant (K) for BS calculation:", min_value=0.01, max_value=10.0,
                                            value=1.00, step=0.01)

                # Tambahkan kolom BS jika kolom ELEVATION (m) ada
                if 'ELEVATION (m)' in df.columns:
                    df['BS'] = (0.04193 * df['ELEVATION (m)'] * K).round(2)
                else:
                    st.warning("Kolom 'ELEVATION (m)' tidak ditemukan. Tidak bisa menghitung BS.")

            # Tampilkan tabel dengan semua kolom
            st.write(f"Displaying data from: **{selected_file}**")
            st.dataframe(df)

        except Exception as e:
            st.error(f"Error reading the file: {e}")
    # Tampilkan kolom BS hanya jika Bouguer Anomaly dipilih
    if st.sidebar.checkbox("Simple Bouguer Anaomaly Map"):
        st.sidebar.subheader("Select Columns for Map")
        coordinate_system = "Lat/Lon"  # Set to Lat/Lon directly
        x_column = "Longitude"
        y_column = "Latitude"

        z_column = "G Obs"  # Or create new column as you suggested: [G Obs - GReduksi Gravitasi + G FA - BS]

        if 'Longitude' in df.columns and 'Latitude' in df.columns and z_column in df.columns:
            # Calculate Bouguer Anomaly
            df['Bouguer Anomaly'] = (df[z_column] - df['GReduksi Gravitasi'] + df['G FA'] - df['BS']).round(3)

            # Sidebar sliders for min and max anomaly values
            anomaly_min = st.sidebar.slider("Min Anomaly Value", min_value=float(df['Bouguer Anomaly'].min()),
                                            max_value=float(df['Bouguer Anomaly'].max()),
                                            value=float(df['Bouguer Anomaly'].quantile(0.05)))
            anomaly_max = st.sidebar.slider("Max Anomaly Value", min_value=float(df['Bouguer Anomaly'].min()),
                                            max_value=float(df['Bouguer Anomaly'].max()),
                                            value=float(df['Bouguer Anomaly'].quantile(0.95)))

            # Filter data within selected range
            df_filtered = df[(df['Bouguer Anomaly'] >= anomaly_min) & (df['Bouguer Anomaly'] <= anomaly_max)]

            # Pilihan metode interpolasi
            interp_method = st.sidebar.selectbox(
                "Select Interpolation Method",
                options=["cubic", "linear", "nearest"],
                index=0  # default 'cubic'
            )

            # Pilih ukuran grid (interaktif)
            grid_resolution = st.sidebar.slider("Grid Resolution", min_value=100, max_value=1500, value=500, step=100)

            # Siapkan grid untuk interpolasi
            grid_x, grid_y = np.meshgrid(
                np.linspace(df_filtered['Longitude'].min(), df_filtered['Longitude'].max(), grid_resolution),
                np.linspace(df_filtered['Latitude'].min(), df_filtered['Latitude'].max(), grid_resolution)
            )

            # Interpolasi nilai
            points = df_filtered[['Longitude', 'Latitude']].values
            values = df_filtered['Bouguer Anomaly'].values
            grid_z = griddata(points, values, (grid_x, grid_y), method=interp_method)

            # Optional: smooth interpolasi
            apply_smoothing = st.sidebar.checkbox("Apply Gaussian Smoothing", value=False)
            if apply_smoothing:
                sigma = st.sidebar.slider("Smoothing Level (Sigma)", 0.5, 5.0, 1.0)
                grid_z = gaussian_filter(grid_z, sigma=sigma)

            # Pilih colormap
            colormap = st.sidebar.selectbox("Select Colormap", options=["bwr", "jet", "hsv"], index=0)

            # Plotting
            fig, ax = plt.subplots(figsize=(10, 6))
            cs = ax.contourf(grid_x, grid_y, grid_z, cmap=colormap, levels=20,
                             vmin=anomaly_min, vmax=anomaly_max)

            cbar = fig.colorbar(cs, ax=ax, label="Bouguer Anomaly (mGal)")

            # Checkbox untuk titik ukur
            show_points = st.sidebar.checkbox("Show Measurement Points", value=True)
            if show_points:
                ax.scatter(df_filtered['Longitude'], df_filtered['Latitude'], color='black', s=10,
                           label="Measurement Points")
                ax.legend(loc='upper right')

            st.pyplot(fig)
            #

            #
            # # Prepare data for interpolation
            # points = df_filtered[[x_column, y_column]].values  # Coordinates (Longitude, Latitude)
            # values = df_filtered['Bouguer Anomaly'].values  # Bouguer Anomaly values
            #
            # # Create grid for interpolation
            # grid_x, grid_y = np.meshgrid(np.linspace(df_filtered[x_column].min(), df_filtered[x_column].max(), 1000),
            #                              np.linspace(df_filtered[y_column].min(), df_filtered[y_column].max(), 1000))
            #
            # # Interpolate using griddata
            # grid_z = griddata(points, values, (grid_x, grid_y), method=interp_method)
            #
            # # Pilihan colormap
            # colormap = st.sidebar.selectbox(
            #     "Select Colormap",
            #     options=["bwr", "jet", "hsv"],
            #     index=0  # default "bwr"
            # )
            # # Plot Bouguer Anomaly with Interpolation
            # fig, ax = plt.subplots(figsize=(10, 6))
            # # cs = ax.contourf(grid_x, grid_y, grid_z, cmap='bwr', levels=20,
            # #                  vmin=anomaly_min, vmax=anomaly_max)
            # cs = ax.contourf(grid_x, grid_y, grid_z, cmap=colormap, levels=10,
            #                  vmin=anomaly_min, vmax=anomaly_max)
            #
            # cbar = fig.colorbar(cs, ax=ax, label="Bouguer Anomaly (mGal)")
            #
            # # Checkbox to show measurement points
            # show_points = st.sidebar.checkbox("Show Measurement Points", value=True)
            # if show_points:
            #     ax.scatter(df_filtered[x_column], df_filtered[y_column], color='black', s=10,
            #                label="Measurement Points")
            #     ax.legend(loc='upper right')

            # # Title and labels
            # ax.set_title("Interpolated Bouguer Anomaly Map")
            # ax.set_xlabel("Longitude")
            # ax.set_ylabel("Latitude")
            # st.pyplot(fig)


        else:
            st.warning(f"Columns {x_column} or {y_column} or {z_column} are missing.")



else:
    st.write("Please upload Excel files to begin.")

