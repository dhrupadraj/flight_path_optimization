import streamlit as st
import plotly.graph_objects as go
import numpy as np
from geopy.distance import geodesic
import requests
from visualisation.map import plot_route_map, generate_direct_route, create_wind_heatmap_and_vectors

# Airport coordinates (lat, lon) for major Indian airports
AIRPORT_COORDINATES = {
    "DEL": (28.5563, 77.1010),      # Delhi
    "BOM": (19.0895, 72.8656),      # Mumbai
    "BLR": (13.1939, 77.7064),      # Bengaluru
    "HYD": (17.3850, 78.4867),      # Hyderabad
    "MAA": (12.9920, 80.1608),      # Chennai
    "CCU": (22.6542, 88.4467),      # Kolkata
    "COK": (10.1926, 76.2719),      # Kochi
    "TRV": (8.4825, 76.9208),       # Thiruvananthapuram
    "CNN": (11.8875, 75.3670),      # Kannur
    "CJB": (11.0146, 76.7302),      # Coimbatore
    "IXM": (9.8388, 78.0855),       # Madurai
    "TRZ": (11.0025, 78.7999),      # Tiruchirappalli
    "IXE": (12.9352, 74.8311),      # Mangaluru
    "VGA": (16.5278, 80.7900),      # Vijayawada
    "VTZ": (17.9101, 83.2289),      # Visakhapatnam
    "TIR": (13.1939, 79.8250),      # Tirupati
    "AMD": (23.0725, 72.6347),      # Ahmedabad
    "PNQ": (18.5824, 73.9197),      # Pune
    "GOI": (15.3809, 73.8310),      # Goa Dabolim
    "GOX": (15.7942, 73.7618),      # Goa Mopa
    "BDQ": (22.3252, 73.4680),      # Vadodara
    "STV": (21.0812, 72.7911),      # Surat
    "RAJ": (22.3039, 70.7821),      # Rajkot
    "JAI": (26.8124, 75.8027),      # Jaipur
    "IXC": (30.6735, 76.7905),      # Chandigarh
    "ATQ": (31.7160, 74.8021),      # Amritsar
    "LKO": (26.7609, 80.8910),      # Lucknow
    "VNS": (25.4009, 82.8537),      # Varanasi
    "DED": (30.1928, 78.5615),      # Dehradun
    "IXJ": (32.6347, 74.5497),      # Jammu
    "SXR": (34.1526, 75.7619),      # Srinagar
    "GAU": (26.1439, 91.7505),      # Guwahati
    "IXB": (27.0844, 88.4867),      # Bagdogra
    "IMF": (24.7541, 94.9037),      # Imphal
    "IXA": (23.8841, 92.7176),      # Agartala
    "DIB": (27.8047, 94.9056),      # Dibrugarh
    "IXS": (24.8170, 92.9781),      # Silchar
    "NAG": (21.0912, 79.0409),      # Nagpur
    "BHO": (23.2831, 77.4192),      # Bhopal
    "IDR": (22.7196, 75.8044),      # Indore
    "RPR": (21.2537, 81.6660),      # Raipur
    "IXZ": (11.6425, 92.7281),      # Port Blair
}

# Function to get airport code from label
def get_airport_code(label):
    return label.split("(")[-1].rstrip(")")

# Function to calculate distance between waypoints
def calculate_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers

# Function to create sample waypoints between two airports
def generate_waypoints(start_coords, end_coords, num_waypoints=5):
    """Generate intermediate waypoints between start and end"""
    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    
    waypoints = []
    
    # Add start point
    waypoints.append({
        "lat": start_lat,
        "lon": start_lon,
        "name": "Start",
        "distance_from_prev": 0.0
    })
    
    # Generate intermediate waypoints
    for i in range(1, num_waypoints + 1):
        t = i / (num_waypoints + 1)
        lat = start_lat + t * (end_lat - start_lat)
        lon = start_lon + t * (end_lon - start_lon)
        
        prev_lat = start_lat if i == 1 else waypoints[-1]["lat"]
        prev_lon = start_lon if i == 1 else waypoints[-1]["lon"]
        distance = calculate_distance(prev_lat, prev_lon, lat, lon)
        
        waypoints.append({
            "lat": lat,
            "lon": lon,
            "name": f"Waypoint {i}",
            "distance_from_prev": distance
        })
    
    # Add end point
    distance_to_end = calculate_distance(waypoints[-1]["lat"], waypoints[-1]["lon"], end_lat, end_lon)
    waypoints.append({
        "lat": end_lat,
        "lon": end_lon,
        "name": "End",
        "distance_from_prev": distance_to_end
    })
    
    return waypoints


def generate_waypoints_from_route(route_coords, num_waypoints=5):
    """Generate waypoints evenly spaced along an existing route (e.g. optimized path)."""
    if not route_coords or len(route_coords) < 2:
        start = route_coords[0] if route_coords else (0.0, 0.0)
        end = route_coords[-1] if len(route_coords) > 1 else start
        return generate_waypoints(start, end, num_waypoints=num_waypoints)
    n = len(route_coords)
    # Indices for start, num_waypoints intermediate, and end (total num_waypoints+2 points)
    indices = [0] + [int((i + 1) * (n - 1) / (num_waypoints + 1)) for i in range(num_waypoints)] + [n - 1]
    indices = sorted(set(indices))  # avoid duplicates if n is small
    waypoints = []
    for i, idx in enumerate(indices):
        lat, lon = route_coords[idx][0], route_coords[idx][1]
        if i == 0:
            waypoints.append({"lat": lat, "lon": lon, "name": "Start", "distance_from_prev": 0.0})
        else:
            prev = waypoints[-1]
            dist = calculate_distance(prev["lat"], prev["lon"], lat, lon)
            name = "End" if i == len(indices) - 1 else f"Waypoint {i}"
            waypoints.append({"lat": lat, "lon": lon, "name": name, "distance_from_prev": dist})
    return waypoints


# -----------------------------
# Sidebar: Flight Configuration
# -----------------------------
st.sidebar.title("✈️ Flight Route Optimization")

# Airport selection
st.sidebar.subheader("Airports")
INDIAN_AIRPORTS = {
    "Indira Gandhi Intl – Delhi (DEL)": "DEL",
    "Chhatrapati Shivaji Intl – Mumbai (BOM)": "BOM",
    "Kempegowda Intl – Bengaluru (BLR)": "BLR",
    "Rajiv Gandhi Intl – Hyderabad (HYD)": "HYD",
    "Chennai Intl – Chennai (MAA)": "MAA",
    "Netaji Subhas Chandra Bose Intl – Kolkata (CCU)": "CCU",

    # South India
    "Cochin Intl – Kochi (COK)": "COK",
    "Trivandrum Intl – Thiruvananthapuram (TRV)": "TRV",
    "Kannur Intl – Kannur (CNN)": "CNN",
    "Coimbatore Intl – Coimbatore (CJB)": "CJB",
    "Madurai Intl – Madurai (IXM)": "IXM",
    "Tiruchirappalli Intl – Tiruchirappalli (TRZ)": "TRZ",
    "Mangaluru Intl – Mangaluru (IXE)": "IXE",
    "Vijayawada Intl – Vijayawada (VGA)": "VGA",
    "Visakhapatnam Intl – Visakhapatnam (VTZ)": "VTZ",
    "Tirupati Intl – Tirupati (TIR)": "TIR",

    # West India
    "Sardar Vallabhbhai Patel Intl – Ahmedabad (AMD)": "AMD",
    "Pune Intl – Pune (PNQ)": "PNQ",
    "Goa Intl – Dabolim (GOI)": "GOI",
    "Manohar Intl – Mopa, Goa (GOX)": "GOX",
    "Vadodara Intl – Vadodara (BDQ)": "BDQ",
    "Surat Intl – Surat (STV)": "STV",
    "Rajkot Intl – Rajkot (RAJ)": "RAJ",

    # North India
    "Jaipur Intl – Jaipur (JAI)": "JAI",
    "Chandigarh Intl – Chandigarh (IXC)": "IXC",
    "Amritsar Intl – Amritsar (ATQ)": "ATQ",
    "Lucknow Intl – Lucknow (LKO)": "LKO",
    "Varanasi Intl – Varanasi (VNS)": "VNS",
    "Dehradun – Jolly Grant (DED)": "DED",
    "Jammu – Satwari (IXJ)": "IXJ",
    "Srinagar Intl – Srinagar (SXR)": "SXR",

    # East & North-East India
    "Lokpriya Gopinath Bordoloi Intl – Guwahati (GAU)": "GAU",
    "Bagdogra Intl – Bagdogra (IXB)": "IXB",
    "Imphal Intl – Imphal (IMF)": "IMF",
    "Agartala Intl – Agartala (IXA)": "IXA",
    "Dibrugarh – Mohanbari (DIB)": "DIB",
    "Silchar – Kumbhirgram (IXS)": "IXS",

    # Central India
    "Dr. Babasaheb Ambedkar Intl – Nagpur (NAG)": "NAG",
    "Bhopal – Raja Bhoj (BHO)": "BHO",
    "Indore – Devi Ahilyabai Holkar (IDR)": "IDR",
    "Raipur – Swami Vivekananda (RPR)": "RPR",

    # Islands
    "Veer Savarkar Intl – Port Blair (IXZ)": "IXZ"
}

airport_labels = list(INDIAN_AIRPORTS.keys())

# Departure (searchable by default)
departure_label = st.sidebar.selectbox(
    "Departure Airport",
    airport_labels,
    help="Search and select departure airport"
)

# Filter arrival airports to prevent same selection
arrival_options = [a for a in airport_labels if a != departure_label]

arrival_label = st.sidebar.selectbox(
    "Arrival Airport",
    arrival_options,
    help="Arrival airport must be different from departure"
)

# Flight timings
st.sidebar.subheader("Flight Timings")


departure_time = st.sidebar.time_input(
    "Departure Time (UTC)"
)

date = st.sidebar.date_input(
    "Flight Date"
)

# Optimization settings
st.sidebar.subheader("Optimization Settings")

optimize_for = st.sidebar.radio(
    "Optimize For",
    options=[
        "Minimum Time",
        "Fuel Efficiency",
        "Balanced (Time + Fuel)"
    ]
)

wind_weight = st.sidebar.slider(
    "Wind Influence Weight",
    min_value=0.0,
    max_value=1.0,
    value=0.7,
    step=0.05,
    help="Higher value prioritizes tailwinds"
)

# Wind visualization toggle
show_wind_field = st.sidebar.checkbox(
    "Show Wind Field & Vectors",
    value=True,
    help="Display wind speed heatmap and vector field"
)

# Wind grid resolution
wind_grid_size = st.sidebar.slider(
    "Wind Grid Resolution",
    min_value=10,
    max_value=40,
    value=20,
    step=5,
    help="Higher = more detailed wind field"
)

# -----------------------------
# Sidebar: Actions
# -----------------------------
st.sidebar.subheader("Actions")

show_straight_route = st.sidebar.button(
    "Show Original Route"
)

show_optimized_route = st.sidebar.button(
    "Show Optimized Route"
)

st.sidebar.markdown("---")

# Get airport codes and coordinates
dep_code = get_airport_code(departure_label)
arr_code = get_airport_code(arrival_label)
dep_coords = AIRPORT_COORDINATES.get(dep_code)
arr_coords = AIRPORT_COORDINATES.get(arr_code)

# Calculate distance
distance = calculate_distance(dep_coords[0], dep_coords[1], arr_coords[0], arr_coords[1])

# Main content area
st.title("✈️ Flight Route Optimization System")

if dep_coords and arr_coords:
    # Fetch ERA5 (data.grib) wind field for map when wind overlay is enabled
    wind_data = None
    if show_wind_field:
        try:
            wind_resp = requests.post(
                "http://127.0.0.1:8000/wind-field",
                json={
                    "dep_lat": dep_coords[0],
                    "dep_lon": dep_coords[1],
                    "arr_lat": arr_coords[0],
                    "arr_lon": arr_coords[1],
                    "departure_time": str(departure_time),
                    "flight_date":str(date)
                },
                timeout=250,
            )
            wind_resp.raise_for_status()
            wind_data = wind_resp.json()
        except Exception:
            wind_data = None  # fall back to synthetic in create_wind_heatmap_and_vectors

    # Display flight information in better layout
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("From", dep_code)
    with col2:
        st.metric("To", arr_code)
    with col3:
        st.metric("Distance", f"{distance:.0f} km")
    
    
    st.markdown("---")
    
    # Create default interactive map
    st.subheader("📍 Interactive Route Map")
    
    # Default map showing both departure and arrival
    fig_default = go.Figure()
    
    # Determine which route to show
    if show_optimized_route:
        # Call FastAPI to compute optimized route using model + A* (expecting local server at 127.0.0.1:8000)
        api_url = "http://127.0.0.1:8000/optimize-route"
        payload = {
            "dep_lat": dep_coords[0],
            "dep_lon": dep_coords[1],
            "arr_lat": arr_coords[0],
            "arr_lon": arr_coords[1],
            "departure_time": str(departure_time),
            "flight_date":str(date)
        }

        with st.spinner("Computing optimized route using model and A*... (This may take 30-90 seconds)"):
            try:
                resp = requests.post(api_url, json=payload, timeout=180)  # Increased to 180 seconds
                resp.raise_for_status()
                data = resp.json()
                # API returns optimized_route as [{"lat": x, "lon": y}, ...]; convert to [(lat, lon), ...]
                route_points = data.get("optimized_route", [])
                optimized_coords = [(p["lat"], p["lon"]) for p in route_points] if route_points else []
            except Exception as e:
                st.error(f"Failed to fetch optimized route: {e}")
                optimized_coords = generate_direct_route(dep_coords, arr_coords, num_points=200)

        # If API returned an empty route, fall back to straight interpolation
        if not optimized_coords:
            optimized_coords = generate_direct_route(dep_coords, arr_coords, num_points=200)

        waypoints = generate_waypoints_from_route(optimized_coords, num_waypoints=5)

        fig_default = plot_route_map(
            route_coords=optimized_coords,
            waypoints=waypoints,
            dep_name=dep_code,
            arr_name=arr_code
        )

        # Add wind field if enabled (ERA5 from API or synthetic fallback)
        if show_wind_field:
            create_wind_heatmap_and_vectors(
                fig_default, dep_coords, arr_coords,
                grid_size=wind_grid_size, wind_data=wind_data
            )
    elif show_straight_route:
        # Show direct route with straight-line interpolation
        direct_coords = generate_direct_route(dep_coords, arr_coords, num_points=100)
        
        fig_default.add_trace(go.Scattergeo(
            lat=[p[0] for p in direct_coords],
            lon=[p[1] for p in direct_coords],
            mode="lines",
            line=dict(width=3, color="green", dash="dash"),
            name="Direct Route",
            hoverinfo="skip"
        ))
        
        # Add airport markers with coordinates displayed
        fig_default.add_trace(go.Scattergeo(
            lat=[dep_coords[0], arr_coords[0]],
            lon=[dep_coords[1], arr_coords[1]],
            mode="markers+text",
            marker=dict(size=16, color=["green", "red"], symbol="star"),
            text=[f"<b>{dep_code}</b><br>({dep_coords[0]:.4f}°, {dep_coords[1]:.4f}°)",
                  f"<b>{arr_code}</b><br>({arr_coords[0]:.4f}°, {arr_coords[1]:.4f}°)"],
            textposition=["top center", "bottom center"],
            textfont=dict(size=11, color="black"),
            name="Airports",
            hovertext=[f"<b>Departure: {dep_code}</b><br>Lat: {dep_coords[0]:.4f}<br>Lon: {dep_coords[1]:.4f}",
                      f"<b>Arrival: {arr_code}</b><br>Lat: {arr_coords[0]:.4f}<br>Lon: {arr_coords[1]:.4f}"],
            hoverinfo="text"
        ))
        
        center_lat = (dep_coords[0] + arr_coords[0]) / 2
        center_lon = (dep_coords[1] + arr_coords[1]) / 2
        
        fig_default.update_layout(
            title=f"✈️ Direct Route: {dep_code} → {arr_code}",
            geo=dict(
                scope="asia",
                projection_type="mercator",
                showland=True,
                landcolor="rgb(243, 243, 243)",
                showocean=True,
                oceancolor="rgb(230, 245, 255)",
                showcountries=True,
                countrycolor="rgb(200, 200, 200)",
                center=dict(lat=center_lat, lon=center_lon),
                projection_scale=4
            ),
            height=600,
            margin=dict(l=0, r=0, t=50, b=0),
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.8)", font=dict(color="black")),
            hovermode="closest"
        )
        
        # Add wind field if enabled (ERA5 from API or synthetic fallback)
        if show_wind_field:
            create_wind_heatmap_and_vectors(
                fig_default, dep_coords, arr_coords,
                grid_size=wind_grid_size, wind_data=wind_data
            )
    else:
        # Default: show departure and arrival with straight-line interpolation
        
        # Add straight-line between airports
        direct_coords = generate_direct_route(dep_coords, arr_coords, num_points=50)
        fig_default.add_trace(go.Scattergeo(
            lat=[p[0] for p in direct_coords],
            lon=[p[1] for p in direct_coords],
            mode="lines",
            line=dict(width=2, color="rgba(100, 100, 200, 0.4)", dash="dash"),
            name="Direct Path",
            hoverinfo="skip"
        ))
        
        # Add airport markers with coordinates displayed
        fig_default.add_trace(go.Scattergeo(
            lat=[dep_coords[0], arr_coords[0]],
            lon=[dep_coords[1], arr_coords[1]],
            mode="markers+text",
            marker=dict(size=18, color=["green", "red"], symbol="star"),
            text=[f"<b>{dep_code}</b><br>({dep_coords[0]:.4f}°, {dep_coords[1]:.4f}°)",
                f"<b>{arr_code}</b><br>({arr_coords[0]:.4f}°, {arr_coords[1]:.4f}°)"],
            textposition=["top center", "bottom center"],
            textfont=dict(size=12, color=["Black", "Black"]),
            name="Airports",
            hovertext=[f"<b>Departure: {dep_code}</b><br>Lat: {dep_coords[0]:.4f}<br>Lon: {dep_coords[1]:.4f}",
                    f"<b>Arrival: {arr_code}</b><br>Lat: {arr_coords[0]:.4f}<br>Lon: {arr_coords[1]:.4f}"],
            hoverinfo="text"
        ))
        
        center_lat = (dep_coords[0] + arr_coords[0]) / 2
        center_lon = (dep_coords[1] + arr_coords[1]) / 2
        
        fig_default.update_layout(
            title=f"✈️ Route: {dep_code} → {arr_code}",
            geo=dict(
                scope="asia",
                projection_type="mercator",
                showland=True,
                landcolor="rgb(243, 243, 243)",
                showocean=True,
                oceancolor="rgb(230, 245, 255)",
                showcountries=True,
                countrycolor="rgb(200, 200, 200)",
                center=dict(lat=center_lat, lon=center_lon),
                projection_scale=4
            ),
            height=600,
            margin=dict(l=0, r=0, t=50, b=0),
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.8)", font=dict(color="black")),
            hovermode="closest"
        )
        
        # Add wind field if enabled (ERA5 from API or synthetic fallback)
        if show_wind_field:
            create_wind_heatmap_and_vectors(
                fig_default, dep_coords, arr_coords,
                grid_size=wind_grid_size, wind_data=wind_data
            )
    
    # Display the map
    st.plotly_chart(fig_default, use_container_width=True, key="route_map_main")
    
        # Show distance
    st.info(f"✈️ Direct distance: **{distance:.2f} km**")
    
    # Show optimized route details (reuse optimized_coords from API already plotted above)
    if show_optimized_route:
        st.subheader("🛤️ Optimized Route with Waypoints")
        num_waypoints_display = max(0, len(optimized_coords) - 2)  # exclude dep/arr
        st.write(f"Route from **{dep_code}** to **{arr_code}** with {num_waypoints_display} waypoints")

        # Waypoints on the optimized route (same as main map)
        waypoints = generate_waypoints_from_route(optimized_coords, num_waypoints=5)
        
        # Create the optimized route map
        fig_opt = plot_route_map(
            route_coords=optimized_coords,
            waypoints=waypoints,
            dep_name=dep_code,
            arr_name=arr_code
        )
        
        # Add wind field if enabled (ERA5 from API or synthetic fallback)
        if show_wind_field:
            create_wind_heatmap_and_vectors(
                fig_opt, dep_coords, arr_coords,
                grid_size=wind_grid_size, wind_data=wind_data
            )
        
        st.plotly_chart(fig_opt, use_container_width=True, key="route_map_optimized_details")
        
        # Display waypoint details
        st.subheader("📍 Waypoint Details")
        
        waypoint_df_data = []
        total_distance = 0
        for i, wp in enumerate(waypoints):
            total_distance += wp["distance_from_prev"]
            waypoint_df_data.append({
                "Waypoint": wp["name"],
                "Latitude": f"{wp['lat']:.4f}",
                "Longitude": f"{wp['lon']:.4f}",
                "Distance from Previous": f"{wp['distance_from_prev']:.2f} km",
                "Cumulative Distance": f"{total_distance:.2f} km"
            })
        
        st.dataframe(waypoint_df_data, use_container_width=True)
        
        # Flight stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Distance", f"{total_distance:.2f} km")
        with col2:
            # Estimate flight time (average speed ~500 knots)
            flight_time = (total_distance / 926) * 60  # 926 km/h = 500 knots
            st.metric("Est. Flight Time", f"{flight_time:.1f} min")
        with col3:
            st.metric("Optimization Goal", optimize_for)
        with col4:
            st.metric("Wind Weight", f"{wind_weight:.2f}")
else:
    st.error("❌ Could not find coordinates for selected airports. Please try different airports.")
