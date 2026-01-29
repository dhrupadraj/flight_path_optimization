import streamlit as st
import plotly.graph_objects as go
import numpy as np
from geopy.distance import geodesic
from visualisation.map import plot_route_map, generate_direct_route, add_direct_route

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

# Flight parameters
st.sidebar.subheader("Flight Parameters")

cruise_altitude = st.sidebar.selectbox(
    "Cruise Altitude (ft)",
    options=[30000, 32000, 34000, 36000, 38000],
    index=2
)

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
    # Display flight information in better layout
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("From", dep_code)
    with col2:
        st.metric("To", arr_code)
    with col3:
        st.metric("Distance", f"{distance:.0f} km")
    with col4:
        st.metric("Altitude", f"{cruise_altitude} ft")
    
    st.markdown("---")
    
    # Create default interactive map
    st.subheader("📍 Interactive Route Map")
    
    # Default map showing both departure and arrival
    fig_default = go.Figure()
    
    # Determine which route to show
    if show_optimized_route:
        # Show optimized route with waypoints
        num_points = 200
        optimized_coords = generate_direct_route(dep_coords, arr_coords, num_points=num_points)
        waypoints = generate_waypoints(dep_coords, arr_coords, num_waypoints=5)
        
        fig_default = plot_route_map(
            route_coords=optimized_coords,
            waypoints=waypoints,
            dep_name=dep_code,
            arr_name=arr_code
        )
    elif show_straight_route:
        # Show direct route
        direct_coords = generate_direct_route(dep_coords, arr_coords, num_points=100)
        
        fig_default.add_trace(go.Scattergeo(
            lat=[p[0] for p in direct_coords],
            lon=[p[1] for p in direct_coords],
            mode="lines",
            line=dict(width=3, color="green", dash="dash"),
            name="Direct Route",
            hoverinfo="skip"
        ))
        
        # Add directional arrows
        num_arrows = 3
        arrow_indices = np.linspace(0, len(direct_coords)-1, num_arrows, dtype=int)
        
        for i in range(len(arrow_indices)-1):
            idx = arrow_indices[i]
            lat1, lon1 = direct_coords[idx][0], direct_coords[idx][1]
            lat2, lon2 = direct_coords[arrow_indices[i+1]][0], direct_coords[arrow_indices[i+1]][1]
            
            fig_default.add_annotation(
                x=lon1,
                y=lat1,
                ax=lon2,
                ay=lat2,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=2,
                arrowwidth=2,
                arrowcolor="darkgreen",
                opacity=0.6
            )
        
        # Add markers
        fig_default.add_trace(go.Scattergeo(
            lat=[dep_coords[0], arr_coords[0]],
            lon=[dep_coords[1], arr_coords[1]],
            mode="markers+text",
            marker=dict(size=16, color=["green", "red"], symbol="star"),
            text=[f"<b>{dep_code}</b><br>Start", f"<b>{arr_code}</b><br>End"],
            textposition=["top center", "bottom center"],
            name="Airports",
            hovertext=[f"<b>Departure: {dep_code}</b><br>Lat: {dep_coords[0]:.2f}<br>Lon: {dep_coords[1]:.2f}",
                      f"<b>Arrival: {arr_code}</b><br>Lat: {arr_coords[0]:.2f}<br>Lon: {arr_coords[1]:.2f}"],
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
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.8)"),
            hovermode="closest"
        )
    else:
        # Default: show just departure and arrival points with arrow
        
        # Add arrow from departure to arrival
        fig_default.add_annotation(
            x=dep_coords[1],
            y=dep_coords[0],
            ax=arr_coords[1],
            ay=arr_coords[0],
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=2,
            arrowsize=3,
            arrowwidth=2,
            arrowcolor="blue",
            opacity=0.5
        )
        
        fig_default.add_trace(go.Scattergeo(
            lat=[dep_coords[0], arr_coords[0]],
            lon=[dep_coords[1], arr_coords[1]],
            mode="markers+text",
            marker=dict(size=18, color=["green", "red"], symbol="star"),
            text=[f"<b>{dep_code}</b><br>Departure", f"<b>{arr_code}</b><br>Arrival"],
            textposition=["top center", "bottom center"],
            name="Airports",
            hovertext=[f"<b>Departure: {dep_code}</b><br>Lat: {dep_coords[0]:.2f}<br>Lon: {dep_coords[1]:.2f}",
                      f"<b>Arrival: {arr_code}</b><br>Lat: {arr_coords[0]:.2f}<br>Lon: {arr_coords[1]:.2f}"],
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
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.8)"),
            hovermode="closest"
        )
    
    # Display the map
    st.plotly_chart(fig_default, use_container_width=True)
    
    st.markdown("---")
    
    # Show direct route
    if show_straight_route:
        st.subheader("📍 Direct Route (Straight Line)")
        direct_coords = generate_direct_route(dep_coords, arr_coords, num_points=100)
        
        fig_direct = go.Figure()
        
        # Direct route line
        fig_direct.add_trace(go.Scattergeo(
            lat=[p[0] for p in direct_coords],
            lon=[p[1] for p in direct_coords],
            mode="lines",
            line=dict(width=2, color="green", dash="dash"),
            name="Direct Route",
            hoverinfo="skip"
        ))
        
        # Start and end markers
        fig_direct.add_trace(go.Scattergeo(
            lat=[dep_coords[0], arr_coords[0]],
            lon=[dep_coords[1], arr_coords[1]],
            mode="markers+text",
            marker=dict(size=16, color=["green", "red"], symbol="star"),
            text=[f"<b>{dep_code}</b><br>Start", f"<b>{arr_code}</b><br>End"],
            textposition=["top center", "bottom center"],
            name="Airports",
            hovertext=[f"<b>Departure: {dep_code}</b><br>Lat: {dep_coords[0]:.2f}<br>Lon: {dep_coords[1]:.2f}",
                      f"<b>Arrival: {arr_code}</b><br>Lat: {arr_coords[0]:.2f}<br>Lon: {arr_coords[1]:.2f}"],
            hoverinfo="text"
        ))
        
        center_lat = (dep_coords[0] + arr_coords[0]) / 2
        center_lon = (dep_coords[1] + arr_coords[1]) / 2
        
        fig_direct.update_layout(
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
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.8)"),
            hovermode="closest"
        )
        st.plotly_chart(fig_direct, use_container_width=True)
        
        # Show distance
        st.info(f"✈️ Direct distance: **{distance:.2f} km**")
    
    # Show optimized route
    if show_optimized_route:
        st.subheader("🛤️ Optimized Route with Waypoints")
        st.write(f"Route from **{dep_code}** to **{arr_code}** with {len(waypoints)-2} waypoints")
        
        # Generate optimized route (interpolated path with waypoints)
        num_points = 200
        optimized_coords = generate_direct_route(dep_coords, arr_coords, num_points=num_points)
        
        # Generate waypoints for display
        waypoints = generate_waypoints(dep_coords, arr_coords, num_waypoints=5)
        
        # Create the optimized route map
        fig_opt = plot_route_map(
            route_coords=optimized_coords,
            waypoints=waypoints,
            dep_name=dep_code,
            arr_name=arr_code
        )
        
        st.plotly_chart(fig_opt, use_container_width=True)
        
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