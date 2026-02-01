from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np

from model.predrnn_inference import PredRNNInference
from Astarinference import astar_search
from visualisation.map import generate_latlon_grid, generate_synthetic_wind_field

app = FastAPI()

# 1. Initialize Model once on startup
predrnn = PredRNNInference(
    checkpoint_path="checkpoints/predrnn_best.pt",
    out_steps=6
)

class RouteRequest(BaseModel):
    dep_lat: float
    dep_lon: float
    arr_lat: float
    arr_lon: float

def get_nearest_index(target_lat, target_lon, lat_grid, lon_grid):
    """Finds the (i, j) grid index closest to the given lat/lon."""
    # lat_grid and lon_grid are 1D arrays from generate_latlon_grid
    i = np.abs(lat_grid - target_lat).argmin()
    j = np.abs(lon_grid - target_lon).argmin()
    return (int(i), int(j))
@app.get("/")
def read_root():
    return {"message": "Fast api is running"}
    
@app.post("/optimize-route")
def optimize_route(req: RouteRequest):
    try:
        # 1. Generate the search space grid
        lat_grid, lon_grid = generate_latlon_grid(
            req.dep_lat, req.dep_lon, req.arr_lat, req.arr_lon
        )

        # 2. Map coordinates to Grid Indices (Crucial Step!)
        start_idx = get_nearest_index(req.dep_lat, req.dep_lon, lat_grid, lon_grid)
        goal_idx = get_nearest_index(req.arr_lat, req.arr_lon, lat_grid, lon_grid)

        # 3. Wind field for A* (same grid as route)
        H, W = len(lat_grid), len(lon_grid)
        lat_min = float(min(lat_grid[0], lat_grid[-1]))
        lat_max = float(max(lat_grid[0], lat_grid[-1]))
        lon_min = float(min(lon_grid[0], lon_grid[-1]))
        lon_max = float(max(lon_grid[0], lon_grid[-1]))
        # Use synthetic wind matching the map visualization so A* can optimize (avoids zero-wind straight line)
        wind_u, wind_v, _, _, _ = generate_synthetic_wind_field(
            lat_min, lat_max, lon_min, lon_max, grid_size=H
        )
        # A* expects wind in same units as v_air (km/h) for ground_speed; synthetic wind is m/s
        wind_u_kmh = wind_u * 3.6
        wind_v_kmh = wind_v * 3.6

        # 4. Execute A* Search with wind-aware cost (minimizes time = distance/ground_speed)
        path = astar_search(
            start_idx=start_idx,
            goal_idx=goal_idx,
            lat_grid=lat_grid,
            lon_grid=lon_grid,
            wind_u=wind_u_kmh,
            wind_v=wind_v_kmh,
            v_air=250.0,  # Cruise speed in km/h
        )

        if not path:
            raise HTTPException(status_code=404, detail="No optimized path found.")

        # 5. Format response
        return {
            "status": "success",
            "optimized_route": [{"lat": float(p[0]), "lon": float(p[1])} for p in path],
            "direct_route": [
                {"lat": req.dep_lat, "lon": req.dep_lon},
                {"lat": req.arr_lat, "lon": req.arr_lon}
            ],
            "num_waypoints": len(path)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))