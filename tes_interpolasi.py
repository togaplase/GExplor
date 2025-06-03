import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from scipy.interpolate import griddata, RectBivariateSpline
st.title("Interpolasi Manual Cubic - Free Air Anomaly")
from scipy.interpolate import CloughTocher2DInterpolator

def cubic_manual_interpolation(points, values, grid_x, grid_y):
    # Buat interpolator cubic-like
    interpolator = CloughTocher2DInterpolator(points, values)

    # Flatten grid untuk diinterpolasi
    grid_x_flat = grid_x.flatten()
    grid_y_flat = grid_y.flatten()
    grid_coords = np.vstack((grid_x_flat, grid_y_flat)).T

    # Interpolasi
    grid_z_flat = interpolator(grid_coords)

    # Reshape kembali ke grid 2D
    grid_z = grid_z_flat.reshape(grid_x.shape)
    return grid_z

# Upload file Excel/CSV
uploaded_file = st.file_uploader("Upload file data gravitasi (Excel/CSV)", type=["xlsx", "csv"])
if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success("File berhasil dimuat!")
    st.dataframe(df.head())

    # # Pastikan kolom yang dibutuhkan tersedia
    # required_cols = ["Longitude", "Latitude", "G Obs", "GReduksi Gravitasi", "G FA"]
    # if all(col in df.columns for col in required_cols):
    #
    #     # Hitung Free Air Anomaly
    #     df['G Free Air Anomaly'] = (df['G Obs'] - df['GReduksi Gravitasi'] + df['G FA']).round(3)
    #
    #     # Input resolusi grid dari sidebar
    #     grid_resolution = st.sidebar.slider("Grid Resolution", 100, 1500, 500, step=100)
    #
    #     # Buat grid untuk interpolasi
    #     grid_x, grid_y = np.meshgrid(
    #         np.linspace(df["Longitude"].min(), df["Longitude"].max(), grid_resolution),
    #         np.linspace(df["Latitude"].min(), df["Latitude"].max(), grid_resolution)
    #     )
    #
    #     # Data input untuk interpolasi
    #     points = df[["Longitude", "Latitude"]].values
    #     values = df["G Free Air Anomaly"].values
    #
    #     grid_z = cubic_manual_interpolation(points, values, grid_x, grid_y)
    #
    #
    #     # Visualisasi dengan Matplotlib
    #     fig, ax = plt.subplots(figsize=(10, 6))
    #     contour = ax.contourf(grid_x, grid_y, grid_z, levels=20, cmap="RdBu_r")
    #     plt.colorbar(contour, ax=ax, label="Free Air Anomaly (mGal)")
    #     ax.set_title("Interpolasi Cubic - Peta Free Air Anomaly")
    #     ax.set_xlabel("Longitude")
    #     ax.set_ylabel("Latitude")
    #
    #     # Tambahkan titik pengukuran
    #     ax.scatter(df["Longitude"], df["Latitude"], color='black', s=10, label="Measurement Points")
    #     ax.legend()
    #
    #     st.pyplot(fig)
    #
    # else:
    #     st.warning("Pastikan kolom: Longitude, Latitude, G Obs, GReduksi Gravitasi, dan G FA tersedia.")
    # Sidebar dan logika utama
    if st.sidebar.checkbox("Free Air Anomaly Map"):
        x_column, y_column, z_column = "Longitude", "Latitude", "G Obs"

        if all(col in df.columns for col in [x_column, y_column, z_column, 'GReduksi Gravitasi', 'G FA']):
            df['G Free Air Anomaly'] = (df[z_column] - df['GReduksi Gravitasi'] + df['G FA']).round(3)
            df_filtered = df.copy()

            # Pilihan interpolasi dan grid
            interp_method = st.sidebar.selectbox("Interpolation Method", ["cubic (manual grid)", "linear", "nearest"],
                                                 index=0)
            grid_resolution = st.sidebar.slider("Grid Resolution", 100, 1500, 500, step=100)

            # Buat grid
            x_grid = np.linspace(df_filtered['Longitude'].min(), df_filtered['Longitude'].max(), grid_resolution)
            y_grid = np.linspace(df_filtered['Latitude'].min(), df_filtered['Latitude'].max(), grid_resolution)
            grid_x, grid_y = np.meshgrid(x_grid, y_grid)

            # Ambil titik dan nilai
            points = df_filtered[["Longitude", "Latitude"]].values
            values = df_filtered["G Free Air Anomaly"].values

            # Interpolasi manual cubic via RectBivariateSpline
            if interp_method == "cubic (manual grid)":
                # 1. Interpolasi awal ke grid agar bisa pakai spline
                z_grid = griddata(points, values, (grid_x, grid_y), method='cubic')

                # 2. Isi NaN dengan nearest
                z_grid_filled = np.where(np.isnan(z_grid),
                                         griddata(points, values, (grid_x, grid_y), method='nearest'),
                                         z_grid)

                # 3. Buat spline interpolator
                spline = RectBivariateSpline(y_grid, x_grid, z_grid_filled)

                # 4. Interpolasi ulang ke grid resolusi tinggi (opsional)
                z_interp = spline(y_grid, x_grid)

            else:
                z_interp = griddata(points, values, (grid_x, grid_y), method=interp_method)

            # Colormap
            colormap = st.sidebar.selectbox("Select Colormap", options=["RdBu_r", "rainbow", "bwr", "jet", "hsv"],
                                            index=0)

            # Plot hasil
            fig, ax = plt.subplots(figsize=(10, 6))
            cs = ax.contourf(grid_x, grid_y, z_interp, cmap=colormap, levels=20)
            fig.colorbar(cs, ax=ax, label="Free Air Anomaly (mGal)")

            # Titik pengukuran
            if st.sidebar.checkbox("Show Measurement Points", value=True):
                ax.scatter(df_filtered['Longitude'], df_filtered['Latitude'], color='black', s=10,
                           label="Measurement Points")
                ax.legend()

            st.pyplot(fig)

        else:
            st.warning("Kolom yang dibutuhkan untuk perhitungan FAA tidak tersedia.")
