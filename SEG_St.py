import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from pyproj import Proj, transform
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
from streamlit_option_menu import option_menu



# ===============================
# FUNGSI UTILITAS
# ===============================

def utm_to_latlon(easting, northing, zone, datum, hemisphere):
    proj_utm = Proj(proj='utm', zone=zone, datum=datum, south=hemisphere.lower() == 'south')
    proj_latlon = Proj(proj='latlong', datum=datum)
    longitude, latitude = transform(proj_utm, proj_latlon, easting, northing)
    return longitude, latitude


def remove_outliers(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

# ===============================
# SIDEBAR
# ===============================

st.sidebar.image("D:/PycharmProjects/pythonProject/SEG/streamlit-mark-color.png", width=150)
st.sidebar.header('GExplor')
st.sidebar.markdown("*Comprehensive Gravity Exploration with Data Processing and Interactive Mapping*")

uploaded_files = st.sidebar.file_uploader("Upload your Excel files", type=["xlsx", "xls"], accept_multiple_files=True)
# ===============================
# NAVIGATION MENU
# ===============================
with st.sidebar:
    selected = option_menu("Main Menu", ["Data Upload", "Regression", "FAA Map", "BA Map", "Settings"],
                           icons=['cloud-upload', 'graph-up', 'map', 'map-fill', 'gear'],
                           menu_icon="cast", default_index=0)

st.title("GExplor - Gravity Data Analysis")

# Optional: Tambahan horizontal menu di main page
menu_style = option_menu(None, ["Upload", "Regression", "FAA", "Bouguer", "Settings"],
                         icons=['cloud-upload', 'graph-up', 'map', 'map-fill', 'gear'],
                         orientation="horizontal")
if selected == "Data Upload":
    # Taruh semua bagian upload file dan preprocessing di sini
    uploaded_files = st.sidebar.file_uploader(...)
    ...
elif selected == "Regression":
    # Bagian regresi Paransis
    ...
elif selected == "FAA Map":
    # Bagian peta Free Air Anomaly
    ...
elif selected == "BA Map":
    # Bagian peta Bouguer Anomaly
    ...
elif selected == "Settings":
    # Tampilkan pengaturan UTM/datum dan lainnya
    ...

# Projection Settings
st.sidebar.markdown("---")
if st.sidebar.checkbox("Show Projection Settings"):
    zone = st.sidebar.number_input("UTM Zone (1-60):", min_value=1, max_value=60, value=48, step=1)
    datum = st.sidebar.selectbox("Datum:", ["WGS84", "NAD83", "NAD27"])
    hemisphere = st.sidebar.selectbox("Hemisphere:", ["north", "south"])
else:
    zone = 48
    datum = "WGS84"
    hemisphere = "south"

# ===============================
# FILE HANDLING & PREPROCESSING
# ===============================

if uploaded_files:
    file_options = [file.name for file in uploaded_files]
    selected_file = st.sidebar.selectbox("Choose a file:", file_options)
    selected_file_obj = next((file for file in uploaded_files if file.name == selected_file), None)

    try:
        df = pd.read_excel(selected_file_obj)

        if 'Gaverage' in df.columns and 'Tide Correction Average' in df.columns:
            df.insert(df.columns.get_loc('Drift'), 'Grav Read Tide', (df['Gaverage'] + df['Tide Correction Average']).round(3))

        if 'Gaverage' in df.columns and 'Drift' in df.columns:
            df.insert(df.columns.get_loc('Drift') + 1, 'Grav Obs', (df['Gaverage'] + df['Drift']).round(3))

        if 'Grav Obs' in df.columns:
            df['Delta G'] = (df['Grav Obs'] - abs(df['Grav Obs'].iloc[0])).round(3)

        if 'Delta G' in df.columns:
            df['G Obs'] = (977863.579 + df['Delta G']).round(3)

        if 'EASTING (m)' in df.columns and 'NORTHING (m)' in df.columns:
            df[['Longitude', 'Latitude']] = df.apply(lambda row: pd.Series(utm_to_latlon(row['EASTING (m)'], row['NORTHING (m)'], zone, datum, hemisphere)), axis=1)
            df['Latitude (radians)'] = np.radians(df['Latitude'])
            df['GReduksi Gravitasi'] = 978031.8 * (1 + 0.005304 * np.sin(df['Latitude (radians)']) ** 2 + 0.0000059 * np.sin(2 * df['Latitude (radians)']) ** 2).round(3)

        if 'ELEVATION (m)' in df.columns:
            df['G FA'] = (0.3085672 * df['ELEVATION (m)']).round(3)

        # ===============================
        # REGRESI PARANSIS
        # ===============================

        if st.sidebar.checkbox("Show Paransis Method Regression"):
            if all(col in df.columns for col in ['ELEVATION (m)', 'G Obs', 'GReduksi Gravitasi', 'G FA']):
                df['x'] = 0.04185 * df['ELEVATION (m)']
                df['y'] = df['G Obs']
                df_no_outliers = remove_outliers(df, 'y')

                model = LinearRegression()
                model.fit(df_no_outliers['x'].values.reshape(-1, 1), df_no_outliers['y'].values.reshape(-1, 1))
                y_pred = model.predict(df_no_outliers['x'].values.reshape(-1, 1))

                plt.figure(figsize=(10, 6))
                plt.scatter(df_no_outliers['x'], df_no_outliers['y'], color='blue', label='Data Points')
                plt.plot(df_no_outliers['x'], y_pred, color='red', label='Regression')
                plt.xlabel('0.04185 * Elevation (m)')
                plt.ylabel('G Obs')
                plt.title('Paransis Method Regression')
                plt.grid(True)
                plt.legend()
                st.pyplot(plt)

                st.write(f"Regression: y = {model.coef_[0][0]:.4f}x + {model.intercept_[0]:.4f}")

            K = st.sidebar.number_input("Enter constant (K) for BS calculation:", min_value=0.01, max_value=10.0, value=1.00, step=0.01)
            if 'ELEVATION (m)' in df.columns:
                df['BS'] = (0.04193 * df['ELEVATION (m)'] * K).round(2)

        # ===============================
        # PEMETAAN BOUGUER
        # ===============================

        if st.sidebar.checkbox("Free Air Anomaly Map"):
            x_column, y_column, z_column = "Longitude", "Latitude", "G Obs"

            if all(col in df.columns for col in [x_column, y_column, z_column, 'GReduksi Gravitasi', 'G FA']):
                # Hitung Free Air Anomaly
                df['G Free Air Anomaly'] = (df[z_column] - df['GReduksi Gravitasi'] + df['G FA']).round(3)

                # Langsung gunakan seluruh data (tanpa filter min/max)
                df_filtered = df.copy()

                # Pilihan metode interpolasi
                interp_method = st.sidebar.selectbox("Interpolation Method", ["cubic", "linear", "nearest"], index=0)
                grid_resolution = st.sidebar.slider("Grid Resolution", 100, 1500, 500, step=100)

                # Buat grid interpolasi
                grid_x, grid_y = np.meshgrid(
                    np.linspace(df_filtered['Longitude'].min(), df_filtered['Longitude'].max(), grid_resolution),
                    np.linspace(df_filtered['Latitude'].min(), df_filtered['Latitude'].max(), grid_resolution)
                )

                # Ambil titik dan nilai
                points = df_filtered[["Longitude", "Latitude"]].values
                values = df_filtered["G Free Air Anomaly"].values
                grid_z = griddata(points, values, (grid_x, grid_y), method=interp_method)

                # Pilihan colormap
                colormap = st.sidebar.selectbox("Select Colormap", options=["RdBu_r","rainbow","bwr", "jet", "hsv"], index=0)

                # Tampilkan peta kontur
                fig, ax = plt.subplots(figsize=(10, 6))
                cs = ax.contourf(grid_x, grid_y, grid_z, cmap=colormap, levels=20)
                fig.colorbar(cs, ax=ax, label="Free Air Anomaly (mGal)")

                # Titik pengukuran
                if st.sidebar.checkbox("Show Measurement Points", value=True):
                    ax.scatter(df_filtered['Longitude'], df_filtered['Latitude'], color='black', s=10,
                               label="Measurement Points")
                    ax.legend()

                st.pyplot(fig)

            else:
                st.warning("Kolom yang dibutuhkan untuk perhitungan FAA tidak tersedia.")

        if st.sidebar.checkbox("Simple Bouguer Anomaly Map"):
            x_column, y_column, z_column = "Longitude", "Latitude", "G Obs"

            if all(col in df.columns for col in [x_column, y_column, z_column, 'GReduksi Gravitasi', 'G FA', 'BS']):
                df['Bouguer Anomaly'] = (df[z_column] - df['GReduksi Gravitasi'] + df['G FA'] - df['BS']).round(3)

                # Langsung gunakan seluruh data (tanpa filter min/max)
                df_filtered = df.copy()

                interp_method = st.sidebar.selectbox("Interpolation Method", ["cubic", "linear", "nearest"], index=0)
                grid_resolution = st.sidebar.slider("Grid Resolution", 100, 1500, 500, step=100)

                grid_x, grid_y = np.meshgrid(
                    np.linspace(df_filtered['Longitude'].min(), df_filtered['Longitude'].max(), grid_resolution),
                    np.linspace(df_filtered['Latitude'].min(), df_filtered['Latitude'].max(), grid_resolution)
                )

                points = df_filtered[["Longitude", "Latitude"]].values
                values = df_filtered["Bouguer Anomaly"].values
                grid_z = griddata(points, values, (grid_x, grid_y), method=interp_method)

                colormap = st.sidebar.selectbox("Select Colormap", options=["RdBu_r","rainbow", "bwr", "jet", "hsv"], index=0)

                fig, ax = plt.subplots(figsize=(10, 6))
                cs = ax.contourf(grid_x, grid_y, grid_z, cmap=colormap, levels=20)
                fig.colorbar(cs, ax=ax, label="Bouguer Anomaly (mGal)")

                if st.sidebar.checkbox("Show Measurement Points", value=True):
                    ax.scatter(df_filtered['Longitude'], df_filtered['Latitude'], color='black', s=10, label="Measurement Points")
                    ax.legend()

                st.pyplot(fig)
            else:
                st.warning("Required columns for Bouguer Anomaly calculation are missing.")

        # ===============================
        # TAMPILKAN TABEL DATA
        # ===============================

        st.write(f"Displaying data from: **{selected_file}**")
        st.dataframe(df)

    except Exception as e:
        st.error(f"Error reading the file: {e}")
else:
    st.write("Please upload Excel files to begin.")
