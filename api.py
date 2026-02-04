from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
from datetime import datetime

from model.predrnn_inference import PredRNNInference
from Astarinference import astar_search
from visualisation.map import generate_latlon_grid, generate_synthetic_wind_field
from data.grib_loader import denormalize_wind

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
    departure_time: str
    flight_date: str

def get_nearest_index(target_lat, target_lon, lat_grid, lon_grid):
    """Finds the (i, j) grid index closest to the given lat/lon."""
    # lat_grid and lon_grid are 1D arrays from generate_latlon_grid
    i = np.abs(lat_grid - target_lat).argmin()
    j = np.abs(lon_grid - target_lon).argmin()
    return (int(i), int(j))
@app.get("/")
def read_root():
    return {"message": "Fast api is running"}


@app.post("/wind-field")
def wind_field(req: RouteRequest):
    """
    Return ERA5 (data.grib) wind field for the route region for map display.
    Used by the app to show wind heatmap and vectors from real data.
    Falls back to synthetic wind if GRIB is unavailable or region outside domain.
    """
    try:
        lat_min = min(req.dep_lat, req.arr_lat) - 2.0
        lat_max = max(req.dep_lat, req.arr_lat) + 2.0
        lon_min = min(req.dep_lon, req.arr_lon) - 2.0
        lon_max = max(req.dep_lon, req.arr_lon) + 2.0
        grid_size = 28

        try:
            from data.grib_loader import get_wind_field_for_display
            u, v, lat_mesh, lon_mesh = get_wind_field_for_display(
                lat_min, lat_max, lon_min, lon_max, grid_size=grid_size
            )
            source = "era5"
        except Exception:
            u, v, _, lat_mesh, lon_mesh = generate_synthetic_wind_field(
                lat_min, lat_max, lon_min, lon_max, grid_size=grid_size
            )
            source = "synthetic"

        return {
            "source": source,
            "lat_grid": lat_mesh[:, 0].tolist(),
            "lon_grid": lon_mesh[0, :].tolist(),
            "wind_u": u.tolist(),
            "wind_v": v.tolist(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/optimize-route")
def optimize_route(req: RouteRequest):
    try:
        # Streamlit time_input usually sends HH:MM:SS, but be tolerant of HH:MM too.
        dt_str = f"{req.flight_date} {req.departure_time}"
        try:
            target_datetime = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            target_datetime = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        
        # =====================================================
        # 1. Generate spatial grid between departure & arrival
        # =====================================================
        lat_grid, lon_grid = generate_latlon_grid(
            req.dep_lat, req.dep_lon,
            req.arr_lat, req.arr_lon,
            size=64  # must match PredRNN training resolution
        )

        # =====================================================
        # 2. Convert airports → grid indices (A* works in index space)
        # =====================================================
        start_idx = get_nearest_index(req.dep_lat, req.dep_lon, lat_grid, lon_grid)
        goal_idx = get_nearest_index(req.arr_lat, req.arr_lon, lat_grid, lon_grid)

        # =====================================================
        # 3. Build PredRNN inference input
        # =====================================================
        """
        PredRNN expects:
        [B, Tin, C, H, W]
        C = 2 (u, v wind)
        """

        Tin = 12  # must match training (INPUT_STEPS)
        H = len(lat_grid)
        W = len(lon_grid)
        lat_min = float(min(lat_grid[0], lat_grid[-1]))
        lat_max = float(max(lat_grid[0], lat_grid[-1]))
        lon_min = float(min(lon_grid[0], lon_grid[-1]))
        lon_max = float(max(lon_grid[0], lon_grid[-1]))

        # 3. Load wind from GRIB (real data) or fall back to synthetic
        try:
            from data.grib_loader import get_wind_history_for_region
            wind_history = get_wind_history_for_region(
                lat_min, lat_max, lon_min, lon_max,
                target_h=H, target_w=W, num_timesteps=Tin, target_datetime=target_datetime
            )
        except Exception:
            u_syn, v_syn, _, _, _ = generate_synthetic_wind_field(
                lat_min, lat_max, lon_min, lon_max, grid_size=H
            )
            wind_raw = np.stack(
                [np.stack([u_syn, v_syn], axis=0)] * Tin, axis=0
            ).astype(np.float32)
            mean = np.load("data/processed/mean.npy")
            std = np.load("data/processed/std.npy")
            wind_history = (wind_raw - mean) / (std + 1e-6)

        # =====================================================
        # 4. Run PredRNN inference (model expects normalized input)
        # =====================================================
        wind_pred_norm = predrnn.predict(wind_history)
        wind_pred = denormalize_wind(wind_pred_norm)

        # Use first predicted timestep for routing; convert m/s → km/h
        wind_u = wind_pred[0, 0] * 3.6  # (H, W)
        wind_v = wind_pred[0, 1] * 3.6  # (H, W)

        # =====================================================
        # 5. Run A* with PredRNN-predicted wind
        # =====================================================
        path = astar_search(
            start_idx=start_idx,
            goal_idx=goal_idx,
            lat_grid=lat_grid,
            lon_grid=lon_grid,
            wind_u=wind_u,
            wind_v=wind_v,
            v_air=250.0  # cruise speed km/h
        )

        if not path:
            raise HTTPException(status_code=404, detail="No optimized path found")

        # =====================================================
        # 6. Send response to UI
        # =====================================================
        return {
            "status": "success",
            "optimized_route": [
                {"lat": float(lat), "lon": float(lon)} for lat, lon in path
            ],
            "direct_route": [
                {"lat": req.dep_lat, "lon": req.dep_lon},
                {"lat": req.arr_lat, "lon": req.arr_lon}
            ],
            "num_waypoints": len(path)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
