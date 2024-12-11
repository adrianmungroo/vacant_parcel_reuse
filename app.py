import streamlit as st
import geopandas as gpd
import pickle
import folium
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Vacant Parcel Reuse",  
    page_icon="🏘️",                   
    layout="wide"                     
)

st.title("Vacant Parcel Reuse Ranking")

st.write("""
    This app analyzes Fulton County parcels and ranks their reuse desirability based on a user-defined metric. 
""")
st.divider()


with open('result.pkl', 'rb') as f: # loading the data
    data = pickle.load(f)

# Convert the loaded data into a GeoDataFrame
data = gpd.GeoDataFrame(data, geometry='geometry')

# Getting rid of some ridiculous values that skewed the result
data = data[data['land_value_ratio'] < 50] # getting rid of some ridiculous values that skewed the result

# Define columns that represent different metrics
metrics = ['r_reuse', 'c_reuse', 'i_reuse', 'land_value_ratio', 'walkability', 'drivability', 'shape_factor']

# ---------------------------------------------------------------------
# User input: Choice of target reuse category
# ---------------------------------------------------------------------
st.write("##### Select the target reuse category by clicking one of the radio buttons below")
reuse_choice = st.radio(
    '',
    ['Residential', 'Commercial', 'Industrial'],
    horizontal=True
)

st.divider()

# ---------------------------------------------------------------------
# User input: Assign weights to each chosen metric
# ---------------------------------------------------------------------

# Based on the chosen category, exclude irrelevant columns
if reuse_choice == 'Residential':
    excluded_metrics = ['c_reuse', 'i_reuse']
elif reuse_choice == 'Commercial':
    excluded_metrics = ['r_reuse', 'i_reuse']
elif reuse_choice == 'Industrial':
    excluded_metrics = ['r_reuse', 'c_reuse']
else:
    excluded_metrics = []

# Filter the columns to be weighted by the user
filtered_metrics = [m for m in metrics if m not in excluded_metrics]

st.subheader("Design your custom desirability metric below!")
st.write("Adjust the weights of each of the following attributes. A positive weight means that the desirability increases with the attribute. A negative weight means that if the attribute increases, the desirability decreases.")

metric_cols = st.columns(len(filtered_metrics))
weights = {}
for metric, col in zip(filtered_metrics, metric_cols):
    if metric == "land_value_ratio": 
        value = 0.01
    else: 
        value = 1.0
    weights[metric] = col.slider(
        f"{metric}",
        min_value=-5.0,
        max_value=5.0,
        value=value,
        step=0.01
    )

st.divider()

# User defined area bounds below
st.subheader("Select bounds on the parcel areas below")
c1,c2 = st.columns(2)
with c1:
    min_area = st.slider("Minimum Area", min_value=0, max_value=10000, value=0)
with c2:
    max_area = st.slider("Maximum Area", min_value=10000, max_value=1000000, value=1000000)
data = data[(data.geometry.area < max_area) & (data.geometry.area > min_area)]

st.divider()

# ---------------------------------------------------------------------
# Compute weighted sum for each parcel
# ---------------------------------------------------------------------
data['weighted_sum'] = 0
for metric in filtered_metrics:
    data['weighted_sum'] += data[metric] * weights[metric]

# ---------------------------------------------------------------------
# Display top 10 parcels based on weighted sum
# ---------------------------------------------------------------------
top_10 = (data
          .nlargest(10, 'weighted_sum')
          [['ParcelID'] + filtered_metrics + ['weighted_sum', 'geometry']]
          .to_crs(epsg=4326))

st.subheader("See the most reusable parcels according to your metric below!")
st.write("The table shows the top 10 most desirable parcels, sorted from most desirable (top) to least (bottom).")
col1, col2, col3 = st.columns([2, 4, 1])
with col2:
    with st.container():
        st.dataframe(top_10.drop(columns='geometry'), height=300)


st.divider()

# ---------------------------------------------------------------------
# User input: Select a parcel to visualize
# ---------------------------------------------------------------------
st.subheader("Map Visualization")
st.write("Please select one of the top 10 parcels from the above table to plot on a map to investigate its location!")
c1, c2 = st.columns([1,3])
with c1:
    selected_parcel = st.selectbox("Select a parcel to view on the map:", top_10['ParcelID'])
    basemap = st.selectbox("Select basemap", ['Normal','Satellite'])
selected_geom = top_10.loc[top_10['ParcelID'] == selected_parcel, 'geometry'].iloc[0]
centroid = selected_geom.centroid

# plot the parcel

if basemap == "Satellite":
    tiles = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
    attr = 'Tiles © Google'
else:
    tiles = "OpenStreetMap"
    attr = ""

m = folium.Map(location=[centroid.y, centroid.x], zoom_start=18, tiles=tiles, attr=attr)
folium.GeoJson(
    selected_geom.__geo_interface__,
    name="Selected Parcel",
    style_function=lambda x: {
        "color": "blue",
        "fillColor": "blue",
        "fillOpacity": 0.5
    }
).add_to(m)
with c2:
    st_folium(m, width=1750, height=600)
