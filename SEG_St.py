import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from pyproj import Proj, transform
from sklearn.linear_model import LinearRegression
from streamlit_option_menu import option_menu
from pyproj import Transformer
import io
import rasterio
import geopandas as gpd
from shapely.geometry import Point
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
# Interpolasi manual (pada bagian Map)
from scipy.interpolate import LinearNDInterpolator, CloughTocher2DInterpolator, NearestNDInterpolator
# Import fungsi imshow_hs dari graphics.py
# from graphics import imshow_hs
from scipy.interpolate import interp2d
from mpl_toolkits.mplot3d import Axes3D
from scipy.optimize import minimize
from typing import Literal
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors, cm, contour
from matplotlib.colors import LightSource
# ===============================
# Fungsi-fungsi tambahan
# ===============================
def utm_to_latlon(easting, northing, zone, datum, hemisphere):
    utm_crs = f"+proj=utm +zone={zone} +datum={datum} {'+south' if hemisphere.lower() == 'south' else ''}"
    transformer = Transformer.from_crs(utm_crs, f"+proj=latlong +datum={datum}", always_xy=True)
    longitude, latitude = transformer.transform(easting, northing)
    return longitude, latitude

def remove_outliers(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]


from scipy.interpolate import griddata

def interpolate_manual(method, grid_x, grid_y, points, values):
    return griddata(points, values, (grid_x, grid_y), method=method)

def save_gxf(grid_z, x_coords, y_coords, filename="output.gxf", no_data=-99999):
    dx = x_coords[1] - x_coords[0]
    dy = y_coords[1] - y_coords[0]
    nx = len(x_coords)
    ny = len(y_coords)
    xmin = x_coords.min()
    ymin = y_coords.min()

    # Ganti NaN atau inf dengan no_data
    grid_z = np.nan_to_num(grid_z, nan=no_data, posinf=no_data, neginf=no_data)

    with open(filename, "w") as f:
        f.write(f"DX {dx:.2f}\n")
        f.write(f"DY {dy:.2f}\n")
        f.write(f"NX {nx}\n")
        f.write(f"NY {ny}\n")
        f.write(f"XMIN {xmin:.2f}\n")
        f.write(f"YMIN {ymin:.2f}\n")
        f.write(f"NO_DATA {no_data}\n")
        f.write("HEADER_END\n")

        for row in grid_z:
            f.write(" ".join([f"{val:.2f}" for val in row]) + "\n")

    return filename

def add_hillshade(data, ax, cmap='viridis', hs=True, azdeg=315, altdeg=45,
                  alpha=0.7, contours=24, show_contours=True):
    dy, dx = np.gradient(data)
    slope = np.arctan(np.sqrt(dx**2 + dy**2))
    aspect = np.arctan2(dy, dx)

    zenith_rad = np.radians(90 - altdeg)
    azimuth_rad = np.radians(360 - azdeg + 90)
    shaded = np.sin(zenith_rad) * np.sin(slope) + np.cos(zenith_rad) * np.cos(slope) * np.cos(azimuth_rad - aspect)
    shaded = (shaded - shaded.min()) / (shaded.max() - shaded.min())

    # Set extent sesuai dengan data grid_x dan grid_y
    extent = [
        np.min(grid_x), np.max(grid_x),
        np.min(grid_y), np.max(grid_y)
    ]

    if hs:
        ax.imshow(shaded, cmap='gray', alpha=0.5, origin='lower', extent=extent)
    
    im = ax.imshow(data, cmap=cmap, alpha=alpha, origin='lower', interpolation='bilinear', extent=extent)
    
    if show_contours and contours:
        cs = ax.contour(data, levels=contours, colors='black', linewidths=0.5, alpha=0.8, extent=extent)
        ax.clabel(cs, inline=True, fontsize=8, fmt="%.1f")
    
    return im
                      
# ===============================
# Sidebar dan Menu Navigasi
# ===============================


with st.sidebar:
    st.image("GExplore.png")
    # Garis pemisah (divider)
    st.markdown("""<hr style="border:1px solid #ccc">""", unsafe_allow_html=True)
    st.sidebar.title("About")
    st.sidebar.markdown("""
        The processing and mapping of gravity exploration data have traditionally depended on spreadsheet tools 
    and specialized software. This has made gravity method processing a tedious task, as users are often forced 
    to choose between manually processing data or using complex software focused more on modeling and filtering data.
    \n
    **Gexplor** provides the perfect solution, simplifying the process and offering a user-friendly approach to 
    efficiently handle and map gravity exploration data.
    """)

    st.write("LinkedIn: [togaplase](https://www.linkedin.com/in/togaplase/)", unsafe_allow_html=True)
    st.markdown(
        '<a href="https://www.linkedin.com/in/togaplase/" target="_blank"><div class="linkedin-logo"></div></a>',
        unsafe_allow_html=True)



# Menampilkan menu navigasi dengan ikon
selected2 = option_menu(
    None,  # Tidak ada judul untuk menu
    ["Home", "Upload", "Graphics", "Map",'DEM', 'Reg-Res', 'Inversion'],  # Opsi menu
    icons=["house", "cloud-upload", "search", "map", 'layers', 'sliders',  'download' ],  # Ikon yang sesuai
    menu_icon="cast",  # Ikon menu utama
    default_index=0,  # Menu yang dipilih secara default
    orientation="horizontal"  # Menu horizontal
)


# ===============================
# Home
# ===============================
if selected2 == "Home":
    st.title("GExplor")
    st.markdown("### Comprehensive Gravity Exploration with Data Processing and Interactive Mapping")
    st.markdown("Before we start processing the Gravity data, we need to prepare our Excel data which consists of:")
    st.image("Screenshot 2025-06-03 103715.png")
    st.markdown("Once that's done, we can start with the file upload as shown in the image below.")
    st.image("file_upload.png")

    # Menampilkan logo email dan LinkedIn
    st.markdown("""
        <style>
            .email-logo, .linkedin-logo {
                display: inline-block;
                width: 30px;
                height: 30px;
                background-size: cover;
                vertical-align: middle;
            }
            .email-logo {
                background-image: url('https://upload.wikimedia.org/wikipedia/commons/a/a7/Email_Icon.png');
            }
            .linkedin-logo {
                background-image: url('https://upload.wikimedia.org/wikipedia/commons/0/01/LinkedIn_Logo_2023.svg');
            }
        </style>
    """, unsafe_allow_html=True)

    # Menampilkan informasi pengarang dengan logo email dan LinkedIn
    st.write("Author: togaplase8668@gmail.com", unsafe_allow_html=True)
    st.markdown('<div class="email-logo"></div>', unsafe_allow_html=True)





# ===============================
# Upload dan Proses Data
# ===============================
elif selected2 == "Upload":
    st.title("Upload Your Gravity Data")
    uploaded_files = st.file_uploader("Upload one or more Excel files", type=['xlsx'], accept_multiple_files=True)

    if uploaded_files:
        file_options = [file.name for file in uploaded_files]
        selected_file = st.sidebar.selectbox("Choose a file:", file_options)
        selected_file_obj = next((file for file in uploaded_files if file.name == selected_file), None)

        try:
            df = pd.read_excel(selected_file_obj)

            # =====================================
            # Konstanta Koordinat
            # =====================================
            # zone = 48
            # datum = 'WGS84'
            # hemisphere = 'south'
            if st.sidebar.checkbox("Show Projection Settings"):
                st.sidebar.subheader("Projection Settings")
                zone = st.sidebar.number_input("UTM Zone (1-60):", min_value=1, max_value=60, value=48, step=1)
                datum = st.sidebar.selectbox("Datum:", ["WGS84", "NAD83", "NAD27"])
                hemisphere = st.sidebar.selectbox("Hemisphere:", ["north", "south"])
            else:
                zone = 48
                datum = "WGS84"
                hemisphere = "south"

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

            # Simpan ke session state agar bisa dipanggil di tab Graphics
            st.session_state.df = df

            st.write(f"Displaying data from: **{selected_file}**")
            st.dataframe(df)

        except Exception as e:
            st.error(f"Error reading the file: {e}")
    else:
        st.info("Please upload Excel files to begin.")
    # Simpan DataFrame ke session_state agar bisa digunakan di tab lain
    # st.session_state.df = df



# ===============================
# Graphics
# ===============================
elif selected2 == "Graphics":
    st.title("Paransis Regression Visualization")

    if 'df' not in st.session_state:
        st.warning("Please upload and process data in the Upload tab first.")
        st.stop()

    df = st.session_state.df.copy()  # Gunakan salinan agar tidak konflik langsung di visualisasi

    required_cols = ['ELEVATION (m)', 'G Obs']
    if not all(col in df.columns for col in required_cols):
        st.error("Required columns for Paransis Regression not found.")
        st.stop()

    # Hitung regresi Paransis
    df['x'] = 0.04185 * df['ELEVATION (m)']
    df['y'] = df['G Obs']
    df_no_outliers = remove_outliers(df, 'y')

    model = LinearRegression()
    model.fit(df_no_outliers['x'].values.reshape(-1, 1), df_no_outliers['y'].values.reshape(-1, 1))
    y_pred = model.predict(df_no_outliers['x'].values.reshape(-1, 1))

    # Plot
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

    # Input konstanta K dari sidebar
    K = st.sidebar.number_input("Enter constant (K) for BS calculation:", min_value=0.01, max_value=10.0,
                                value=1.00, step=0.01)

    if 'ELEVATION (m)' in df.columns:
        df['BS'] = (0.04193 * df['ELEVATION (m)'] * K).round(2)
        st.session_state.df['BS'] = df['BS']  # Simpan ke session_state agar update antar tab
    else:
        st.warning("Kolom 'ELEVATION (m)' tidak ditemukan. Tidak bisa menghitung BS.")

    # Tampilkan hasil
    st.dataframe(df)


# ===============================
# Map Visualization
# ===============================
elif selected2 == "Map":
    st.title("Gravity Anomaly Map")

    if 'df' not in st.session_state:
        st.warning("Please upload and process data in the Upload tab first.")
        st.stop()

    df = st.session_state.df.copy()

    # ===============================
    # PEMETAAN BOUGUER
    # ===============================
    
    if st.sidebar.checkbox("Free Air Anomaly Map"):
        x_column, y_column, z_column = "Longitude", "Latitude", "G Obs"

        if all(col in df.columns for col in [x_column, y_column, z_column, 'GReduksi Gravitasi', 'G FA']):
            # Hitung Free Air Anomaly
            df['G Free Air Anomaly'] = (df[z_column] - df['GReduksi Gravitasi'] + df['G FA']).round(3)

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

            # Interpolasi manual menggunakan griddata
            grid_z = interpolate_manual(interp_method, grid_x, grid_y, points, values)


            # Tabs untuk memisahkan visualisasi
            tab1, tab2 = st.tabs(["Standard Visualization", "UNDER-CONSTRUCTION"])

            with tab1:
                st.subheader("Free Air Anomaly Map (Oasis Montaj Style)")
            
                # Sidebar Controls
                st.sidebar.header("Visual Options")
                cmap_options = ['RdBu_r', 'viridis', 'plasma', 'jet', 'coolwarm']
                selected_cmap = st.sidebar.selectbox("Pilih Colormap", options=cmap_options, index=0)
                enable_hillshade = st.sidebar.checkbox("Gunakan Hillshade", value=True)
                contour_levels = st.sidebar.slider("Jumlah Garis Kontur", 5, 50, 20, step=1)
                show_contours = st.sidebar.checkbox("Tampilkan Garis Kontur", value=True)
                alpha_value = st.sidebar.slider("Transparansi Warna", 0.0, 1.0, 0.7, step=0.05)
                show_points = st.sidebar.checkbox("Tampilkan Titik Pengukuran", value=True)
            
                fig, ax = plt.subplots(figsize=(12, 8))
                im = add_hillshade(grid_z, ax=ax, cmap=selected_cmap, hs=enable_hillshade,
                                   alpha=alpha_value, contours=contour_levels, show_contours=show_contours)
            
                # Colorbar
                cbar = fig.colorbar(im, ax=ax, label="Free Air Anomaly (mGal)")
            
                # Titik pengukuran
                if show_points:
                    ax.scatter(df_filtered['Longitude'], df_filtered['Latitude'], color='white', edgecolor='black',
                               s=10, label="Measurement Points")
                    ax.legend()
            
                ax.set_title("Free Air Anomaly Map (Style Oasis Montaj)")
                ax.set_xlabel("Longitude")
                ax.set_ylabel("Latitude")
                ax.axis('image')  # Agar aspek rasio sesuai
                plt.tight_layout()
                st.pyplot(fig)
            
                # Tombol Download Gambar
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
                st.download_button(
                    label="🖼️ Download Peta sebagai PNG",
                    data=buf.getvalue(),
                    file_name="faa_oasis_style_map.png",
                    mime="image/png"
                )
            


    if st.sidebar.checkbox("Simple Bouguer Anomaly Map"):
    x_column, y_column, z_column = "Longitude", "Latitude", "G Obs"

    if all(col in df.columns for col in [x_column, y_column, 'GReduksi Gravitasi', 'G FA', 'BS']):
        # Hitung Simple Bouguer Anomaly
        df['Bouguer Anomaly'] = (df[z_column] - df['GReduksi Gravitasi'] + df['G FA'] - df['BS']).round(3)

        df_filtered = df.copy()

        # Pilihan metode interpolasi
        interp_method = st.sidebar.selectbox("Interpolation Method (Bouguer)", ["cubic", "linear", "nearest"], index=0)
        grid_resolution = st.sidebar.slider("Grid Resolution (Bouguer)", 100, 1500, 500, step=100)

        # Buat grid interpolasi
        grid_x, grid_y = np.meshgrid(
            np.linspace(df_filtered['Longitude'].min(), df_filtered['Longitude'].max(), grid_resolution),
            np.linspace(df_filtered['Latitude'].min(), df_filtered['Latitude'].max(), grid_resolution)
        )

        # Ambil titik dan nilai
        points = df_filtered[["Longitude", "Latitude"]].values
        values = df_filtered["Bouguer Anomaly"].values

        # Interpolasi manual menggunakan griddata
        grid_z = interpolate_manual(interp_method, grid_x, grid_y, points, values)

        # Tabs untuk memisahkan visualisasi
        tab1, tab2 = st.tabs(["Standard Visualization", "UNDER-CONSTRUCTION"])

        with tab1:
            st.subheader("Simple Bouguer Anomaly Map (Oasis Montaj Style)")

            # Sidebar Controls
            st.sidebar.header("Visual Options (Bouguer)")
            cmap_options = ['RdBu_r', 'viridis', 'plasma', 'jet', 'coolwarm']
            selected_cmap = st.sidebar.selectbox("Pilih Colormap (Bouguer)", options=cmap_options, index=0)
            enable_hillshade = st.sidebar.checkbox("Gunakan Hillshade (Bouguer)", value=True)
            contour_levels = st.sidebar.slider("Jumlah Garis Kontur (Bouguer)", 5, 50, 20, step=1)
            show_contours = st.sidebar.checkbox("Tampilkan Garis Kontur (Bouguer)", value=True)
            alpha_value = st.sidebar.slider("Transparansi Warna (Bouguer)", 0.0, 1.0, 0.7, step=0.05)
            show_points = st.sidebar.checkbox("Tampilkan Titik Pengukuran (Bouguer)", value=True)

            fig, ax = plt.subplots(figsize=(12, 8))

            # Dummy imshow untuk mendapatkan extent
            im = ax.imshow(grid_z, cmap='viridis', alpha=0)
            plt.close(fig)  # Tutup agar tidak double plot

            # Tambahkan peta dengan hillshade dan kontur
            fig, ax = plt.subplots(figsize=(12, 8))
            im = add_hillshade(grid_z, ax=ax, cmap=selected_cmap, hs=enable_hillshade,
                               alpha=alpha_value, contours=contour_levels, show_contours=show_contours)

            # Colorbar
            cbar = fig.colorbar(im, ax=ax, label="Bouguer Anomaly (mGal)")

            # Titik pengukuran
            if show_points:
                ax.scatter(df_filtered['Longitude'], df_filtered['Latitude'], color='white', edgecolor='black',
                           s=10, label="Measurement Points")
                ax.legend()

            ax.set_title("Simple Bouguer Anomaly Map (Style Oasis Montaj)")
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.axis('image')  # Agar aspek rasio sesuai
            plt.tight_layout()
            st.pyplot(fig)

            # Tombol Download Gambar
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
            st.download_button(
                label="🖼️ Download Peta sebagai PNG",
                data=buf.getvalue(),
                file_name="bouguer_oasis_style_map.png",
                mime="image/png"
            )
    
        else:
            st.error("Required columns for Bouguer Anomaly calculation not found in your data.")
