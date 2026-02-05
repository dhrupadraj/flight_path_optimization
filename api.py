from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
from datetime import datetime
import logging

from model.predrnn_inference import PredRNNInference
from Astarinference import astar_search
from visualisation.map import generate_latlon_grid, generate_synthetic_wind_field
from data.grib_loader import denormalize_wind, _load_grib
from data.grib_loader import get_wind_history_for_region
from data.grib_loader import get_wind_field_for_display

app = FastAPI()
logger = logging.getLogger(__name__)

# 1. Initialize Model once on startup
logger.info("Loading PredRNN model...")
predrnn = PredRNNInference(
    checkpoint_path="checkpoints/predrnn_best.pt",
    out_steps=6
)
logger.info("PredRNN model loaded successfully")

# 2. Pre-load GRIB file on startup to avoid first-request delay
@app.on_event("startup")
def startup_event():
    """Pre-load GRIB file synchronously on startup to cache data."""
    logger.info("Pre-loading GRIB file...")
    try:
        _load_grib()  # Cache the GRIB data
        logger.info("GRIB file pre-loaded successfully")
    except Exception as e:
        logger.warning(f"Could not pre-load GRIB file: {e}. Will load on first request.")

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
@app.get("/health-check")
def health_check():
    return {"status": "ok"}
def get_grib_bounds():
    """
    Get the geographic bounds of the GRIB file to check coverage.
    Returns the latitude and longitude ranges available in the GRIB data.
    """
    try:
        wind, grib_lat, grib_lon, grib_times = _load_grib()
        return {
            "status": "success",
            "bounds": {
                "lat_min": float(grib_lat.min()),
                "lat_max": float(grib_lat.max()),
                "lon_min": float(grib_lon.min()),
                "lon_max": float(grib_lon.max())
            },
            "time_range": {
                "start": str(grib_times[0]) if len(grib_times) > 0 else None,
                "end": str(grib_times[-1]) if len(grib_times) > 0 else None,
                "num_timesteps": int(len(grib_times))
            }
        }
    except Exception as e:
        logger.error(f"Error getting GRIB bounds: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading GRIB file: {str(e)}")

@app.get("/grib-bounds")
def get_grib_bounds():
    """
    Get the geographic bounds of the GRIB file to check coverage.
    Returns the latitude and longitude ranges available in the GRIB data.
    """
    try:
        wind, grib_lat, grib_lon, grib_times = _load_grib()
        return {
            "status": "success",
            "bounds": {
                "lat_min": float(grib_lat.min()),
                "lat_max": float(grib_lat.max()),
                "lon_min": float(grib_lon.min()),
                "lon_max": float(grib_lon.max())
            },
            "time_range": {
                "start": str(grib_times[0]) if len(grib_times) > 0 else None,
                "end": str(grib_times[-1]) if len(grib_times) > 0 else None,
                "num_timesteps": int(len(grib_times))
            }
        }
    except Exception as e:
        logger.error(f"Error getting GRIB bounds: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading GRIB file: {str(e)}")


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
    """
    Optimize flight route using PredRNN wind prediction and A* pathfinding.
    This endpoint may take 30-90 seconds depending on route length and GRIB processing.
    """
    try:
        logger.info(f"Starting route optimization: {req.dep_lat},{req.dep_lon} -> {req.arr_lat},{req.arr_lon}")
        # Streamlit time_input usually sends HH:MM:SS, but be tolerant of HH:MM too.
        dt_str = f"{req.flight_date} {req.departure_time}"
        try:
            target_datetime = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            target_datetime = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        
        # =====================================================
        # 1. Generate spatial grid between departure & arrival
        # =====================================================
        logger.info("Step 1/5: Generating spatial grid...")
        lat_grid, lon_grid = generate_latlon_grid(
            req.dep_lat, req.dep_lon,
            req.arr_lat, req.arr_lon,
            size=64  # must match PredRNN training resolution
        )

        # =====================================================
        # 2. Convert airports → grid indices (A* works in index space)
        # =====================================================
        logger.info("Step 2/5: Converting airports to grid indices...")
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
        # Calculate bounds correctly (lat_grid and lon_grid are 1D arrays from np.linspace)
        lat_min = float(min(lat_grid.min(), lat_grid.max()))
        lat_max = float(max(lat_grid.min(), lat_grid.max()))
        lon_min = float(min(lon_grid.min(), lon_grid.max()))
        lon_max = float(max(lon_grid.min(), lon_grid.max()))

        # 3. Load wind from GRIB (real data) or fall back to synthetic
        logger.info(f"Step 3/5: Loading wind data from GRIB for region: lat[{lat_min:.2f}, {lat_max:.2f}], lon[{lon_min:.2f}, {lon_max:.2f}]...")
        data_source = "synthetic"  # Track data source
        try:
            wind_history = get_wind_history_for_region(
                lat_min, lat_max, lon_min, lon_max,
                target_h=H, target_w=W, num_timesteps=Tin, target_datetime=target_datetime
            )
            data_source = "era5_grib"
            logger.info("✓ Wind data loaded from GRIB successfully (using REAL ERA5 data)")
        except ValueError as e:
            # Geographic bounds error - route outside GRIB coverage
            logger.warning(f"⚠ Route outside GRIB domain: {e}")
            logger.warning("⚠ Falling back to SYNTHETIC wind data (model predictions may be less accurate)")
            u_syn, v_syn, _, _, _ = generate_synthetic_wind_field(
                lat_min, lat_max, lon_min, lon_max, grid_size=H
            )
            wind_raw = np.stack(
                [np.stack([u_syn, v_syn], axis=0)] * Tin, axis=0
            ).astype(np.float32)
            mean = np.load("data/processed/mean.npy")
            std = np.load("data/processed/std.npy")
            wind_history = (wind_raw - mean) / (std + 1e-6)
        except Exception as e:
            # Other errors (file not found, parsing errors, etc.)
            logger.error(f"✗ GRIB load error: {e}")
            logger.warning("⚠ Falling back to SYNTHETIC wind data")
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
        logger.info("Step 4/5: Running PredRNN inference...")
        wind_pred_norm = predrnn.predict(wind_history)
        wind_pred = denormalize_wind(wind_pred_norm)

        # Use first predicted timestep for routing; convert m/s → km/h
        wind_u = wind_pred[0, 0] * 3.6  # (H, W)
        wind_v = wind_pred[0, 1] * 3.6  # (H, W)
        logger.info("PredRNN inference completed")

        # =====================================================
        # 5. Run A* with PredRNN-predicted wind
        # =====================================================
        logger.info("Step 5/5: Running A* pathfinding...")
        path = astar_search(
            start_idx=start_idx,
            goal_idx=goal_idx,
            lat_grid=lat_grid,
            lon_grid=lon_grid,
            wind_u=wind_u,
            wind_v=wind_v,
            v_air=250.0  # cruise speed km/h
        )
        logger.info(f"Route optimization completed. Path length: {len(path)} waypoints")

        if not path:
            raise HTTPException(status_code=404, detail="No optimized path found")

        # =====================================================
        # 6. Send response to UI
        # =====================================================
        return {
            "status": "success",
            "data_source": data_source,  # "era5_grib" or "synthetic"
            "optimized_route": [
                {"lat": float(lat), "lon": float(lon)} for lat, lon in path
            ],
            "direct_route": [
                {"lat": req.dep_lat, "lon": req.dep_lon},
                {"lat": req.arr_lat, "lon": req.arr_lon}
            ],
            "num_waypoints": len(path),
            "region_bounds": {
                "lat_min": lat_min,
                "lat_max": lat_max,
                "lon_min": lon_min,
                "lon_max": lon_max
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
