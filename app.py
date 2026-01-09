import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import folium
import streamlit as st
from streamlit_folium import st_folium
import os


def add_aqi_bands(ax, pollutant):
    if pollutant == "pm2_5":
        bands = [(0,30), (30,60), (60,90), (90,300)]
    elif pollutant == "pm10":
        bands = [(0,50), (50,100), (100,250), (250,600)]
    elif pollutant == "nitrogen_dioxide":
        bands = [(0,40), (40,80), (80,180), (180,400)]
    else:
        return

    colors = ["green", "yellow", "orange", "red"]

    for (low, high), color in zip(bands, colors):
        ax.axhspan(low, high, color=color, alpha=0.2)


st.set_page_config(page_title="Air Quality Dashboard", layout="wide")
st.title("🌫️ Live Air Quality Time Series Dashboard")
if st.button("🔄 Refresh data"):
    st.rerun()


# Load data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "air_quality.db")

conn = sqlite3.connect(DB_PATH)

# Time handling
df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], utc=True)
df["datetime_ist"] = df["datetime_utc"].dt.tz_convert("Asia/Kolkata")

now_ist = pd.Timestamp.now(tz="Asia/Kolkata")
df = df[df["datetime_ist"] <= now_ist]

cities = ["Delhi", "Mumbai", "Bengaluru", "Kolkata"]
pollutants = ["pm2_5", "pm10", "nitrogen_dioxide"]

def get_aqi_color(pollutant, value):
    if pollutant == "pm2_5":
        if value <= 30: return "green"
        elif value <= 60: return "yellow"
        elif value <= 90: return "orange"
        else: return "red"

    if pollutant == "pm10":
        if value <= 50: return "green"
        elif value <= 100: return "yellow"
        elif value <= 250: return "orange"
        else: return "red"

    if pollutant == "nitrogen_dioxide":
        if value <= 40: return "green"
        elif value <= 80: return "yellow"
        elif value <= 180: return "orange"
        else: return "red"

    return "gray"

# Dashboard
for city in cities:
    st.subheader(city)
    cols = st.columns(3)

    for i, pollutant in enumerate(pollutants):
        with cols[i]:

            subset = (
                 df[(df["city"] == city) & (df["pollutant"] == pollutant)]
                 .sort_values("datetime_ist")
                 .drop_duplicates(subset="datetime_ist", keep="last")
            )

            if subset.empty:
                st.write("No data")
                continue

            fig, ax = plt.subplots(figsize=(4, 3))

            # AQI bands
            add_aqi_bands(ax, pollutant)

            # Time series
            ax.plot(
                subset["datetime_ist"],
                subset["value"],
                linewidth=1.5,
                color="black"
            )

            ax.set_title(pollutant.upper())
            ax.set_ylabel("µg/m³")
            ax.set_xlabel("Date & Time (IST)")

            ax.xaxis.set_major_formatter(
                mdates.DateFormatter("%d %b %H:%M")
            )
            plt.xticks(rotation=45)

            st.pyplot(fig)

st.sidebar.header("📍 City Selection")

selected_cities = st.sidebar.multiselect(
    "Select cities",
    options=sorted(df["city"].unique()),
    default=["Delhi", "Mumbai", "Bengaluru", "Kolkata"]
)
if not selected_cities:
    st.warning("Please select at least one city")
    st.stop()

latest_df = (
    df[
        df["city"].isin(selected_cities)
    ]
    .dropna(subset=["latitude", "longitude"])
    .sort_values("datetime_ist")
    .groupby(["city", "pollutant"], as_index=False)
    .tail(1)
)

with st.expander("🔍 View latest data points"):
    st.dataframe(latest_df)

st.subheader("🗺️ Latest Air Quality Map (Fast Load View)")

m = folium.Map(
    location=[22.5, 80.9],
    zoom_start=5,
    tiles="CartoDB Positron",
    attr="© OpenStreetMap © CARTO"
)

latest_city = (
    latest_df
    .sort_values("value", ascending=False)
    .groupby("city", as_index=False)
    .head(1)
)

for _, row in latest_city.iterrows():
    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=10,
        color="black",
        fill=True,
        fill_color=get_aqi_color(row["pollutant"], row["value"]),
        fill_opacity=0.8,
        tooltip=f"""
        <b>{row['city']}</b><br>
        Pollutant: {row['pollutant']}<br>
        Value: {row['value']} µg/m³<br>
        Time: {row['datetime_ist']}
        """
    ).add_to(m)

# Auto-zoom to data
m.fit_bounds(latest_city[["latitude", "longitude"]].values.tolist())

legend_html = """
<div style="
position: fixed;
bottom: 50px;
left: 50px;
width: 150px;
height: 160px;
background-color: white;
border:2px solid grey;
z-index:9999;
font-size:16px;
padding: 12px;
">
<b>AQI Categories</b><br>
<span style="color:green;">●</span> Good<br>
<span style="color:yellow;">●</span> Moderate<br>
<span style="color:orange;">●</span> Poor<br>
<span style="color:red;">●</span> Very Poor<br>
</div>
"""

m.get_root().html.add_child(folium.Element(legend_html))

st_folium(m, width=900, height=600)


