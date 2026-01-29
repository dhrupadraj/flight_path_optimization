import plotly.graph_objects as go
from geopy.distance import geodesic
import numpy as np

def plot_route_map(route_coords, waypoints, dep_name, arr_name):
    lats = [p[0] for p in route_coords]
    lons = [p[1] for p in route_coords]

    wp_lats = [wp["lat"] for wp in waypoints]
    wp_lons = [wp["lon"] for wp in waypoints]
    wp_text = [
        f"<b>{wp['name']}</b><br>Lat: {wp['lat']:.2f}<br>Lon: {wp['lon']:.2f}<br>Distance: {wp['distance_from_prev']:.1f} km"
        for wp in waypoints
    ]

    fig = go.Figure()

    # Optimized Route Line with gradient colors
    fig.add_trace(go.Scattergeo(
        lat=lats,
        lon=lons,
        mode="lines",
        line=dict(width=4, color="blue"),
        name="Flight Route",
        hoverinfo="skip"
    ))

    # Straight-line interpolation between departure and arrival
    straight_lats = np.linspace(lats[0], lats[-1], 50)
    straight_lons = np.linspace(lons[0], lons[-1], 50)
    fig.add_trace(go.Scattergeo(
        lat=straight_lats,
        lon=straight_lons,
        mode="lines",
        line=dict(width=2, color="rgba(100, 200, 100, 0.5)", dash="dash"),
        name="Straight Line",
        hoverinfo="skip"
    ))

    # Waypoints
    fig.add_trace(go.Scattergeo(
        lat=wp_lats,
        lon=wp_lons,
        mode="markers+text",
        marker=dict(size=8, color="orange", symbol="diamond"),
        text=[wp["name"] for wp in waypoints],
        textposition="top center",
        textfont=dict(size=10),
        hovertext=wp_text,
        hoverinfo="text",
        name="Waypoints"
    ))

    # Departure (Green) with coordinates displayed
    fig.add_trace(go.Scattergeo(
        lat=[lats[0]],
        lon=[lons[0]],
        mode="markers+text",
        marker=dict(size=18, color="green", symbol="star"),
        text=f"<b>{dep_name}</b><br>({lats[0]:.4f}°, {lons[0]:.4f}°)",
        textposition="top center",
        textfont=dict(size=11, color="darkgreen"),
        hovertext=f"<b>Departure: {dep_name}</b><br>Lat: {lats[0]:.4f}<br>Lon: {lons[0]:.4f}",
        hoverinfo="text",
        name=f"Departure ({dep_name})"
    ))

    # Arrival (Red) with coordinates displayed
    fig.add_trace(go.Scattergeo(
        lat=[lats[-1]],
        lon=[lons[-1]],
        mode="markers+text",
        marker=dict(size=18, color="red", symbol="star"),
        text=f"<b>{arr_name}</b><br>({lats[-1]:.4f}°, {lons[-1]:.4f}°)",
        textposition="bottom center",
        textfont=dict(size=11, color="darkred"),
        hovertext=f"<b>Arrival: {arr_name}</b><br>Lat: {lats[-1]:.4f}<br>Lon: {lons[-1]:.4f}",
        hoverinfo="text",
        name=f"Arrival ({arr_name})"
    ))

    # Calculate map center and scope
    center_lat = np.mean(lats)
    center_lon = np.mean(lons)
    
    fig.update_layout(
        title=dict(
            text=f"✈️ Flight Route: {dep_name} → {arr_name}",
            font=dict(size=20)
        ),
        geo=dict(
            scope="asia",
            projection_type="mercator",
            showland=True,
            landcolor="rgb(243, 243, 243)",
            showocean=True,
            oceancolor="rgb(230, 245, 255)",
            showcountries=True,
            countrycolor="rgb(200, 200, 200)",
            coastcolor="rgb(100, 100, 100)",
            center=dict(lat=center_lat, lon=center_lon),
            projection_scale=4
        ),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.8)"),
        hovermode="closest"
    )

    return fig


def generate_direct_route(start, end, num_points=100):
    """
    start, end: (lat, lon)
    """
    lats = np.linspace(start[0], end[0], num_points)
    lons = np.linspace(start[1], end[1], num_points)
    return list(zip(lats, lons))
