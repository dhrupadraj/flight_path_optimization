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

    # Add directional arrows along the route
    num_arrows = 5
    arrow_indices = np.linspace(0, len(lats)-1, num_arrows, dtype=int)
    
    for i in range(len(arrow_indices)-1):
        idx = arrow_indices[i]
        lat1, lon1 = lats[idx], lons[idx]
        lat2, lon2 = lats[arrow_indices[i+1]], lons[arrow_indices[i+1]]
        
        # Add arrow annotation
        fig.add_annotation(
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
            arrowcolor="darkblue",
            opacity=0.6
        )

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

    # Departure (Green)
    fig.add_trace(go.Scattergeo(
        lat=[lats[0]],
        lon=[lons[0]],
        mode="markers+text",
        marker=dict(size=18, color="green", symbol="star"),
        text=f"<b>{dep_name}</b><br>Departure",
        textposition="top center",
        hovertext=f"<b>Departure Airport: {dep_name}</b><br>Lat: {lats[0]:.2f}<br>Lon: {lons[0]:.2f}",
        hoverinfo="text",
        name=f"Departure ({dep_name})"
    ))

    # Arrival (Red)
    fig.add_trace(go.Scattergeo(
        lat=[lats[-1]],
        lon=[lons[-1]],
        mode="markers+text",
        marker=dict(size=18, color="red", symbol="star"),
        text=f"<b>{arr_name}</b><br>Arrival",
        textposition="top center",
        hovertext=f"<b>Arrival Airport: {arr_name}</b><br>Lat: {lats[-1]:.2f}<br>Lon: {lons[-1]:.2f}",
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

def add_direct_route(fig, direct_coords):
    fig.add_trace(go.Scattergeo(
        lat=[p[0] for p in direct_coords],
        lon=[p[1] for p in direct_coords],
        mode="lines",
        line=dict(width=2, dash="dash", color="green"),
        name="Direct Route"
    ))
