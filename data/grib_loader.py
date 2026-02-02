"""
Load wind data from GRIB file for PredRNN inference.
Uses same preprocessing as training: 500 hPa u/v, normalization with mean/std.
"""
import os
import numpy as np

GRIB_PATH = os.path.join(os.path.dirname(__file__), "data.grib")
MEAN_PATH = os.path.join(os.path.dirname(__file__), "processed", "mean.npy")
STD_PATH = os.path.join(os.path.dirname(__file__), "processed", "std.npy")
LEVEL = 500  # hPa
INPUT_STEPS = 12  # match training

_cached_wind = None
_cached_mean = None
_cached_std = None


def _load_grib():
    """Load GRIB and return wind (T, 2, H, W), lat, lon. Cached."""
    global _cached_wind
    if _cached_wind is not None:
        return _cached_wind

    import xarray as xr

    try:
        ds = xr.open_dataset(
            GRIB_PATH,
            engine="cfgrib",
            backend_kwargs={
                "filter_by_keys": {"typeOfLevel": "isobaricInhPa", "level": LEVEL},
            },
        )
    except Exception:
        ds = xr.open_dataset(
            GRIB_PATH,
            engine="cfgrib",
            backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa"}},
        )
    u = ds["u"].values  # (T, lat, lon)
    v = ds["v"].values
    lat_coord = ds.coords.get("latitude", ds.coords.get("lat", None))
    lon_coord = ds.coords.get("longitude", ds.coords.get("lon", None))
    lat = np.asarray(lat_coord.values)
    lon = np.asarray(lon_coord.values)
    ds.close()

    u = np.asarray(u, dtype=np.float32)
    v = np.asarray(v, dtype=np.float32)
    if lat[0] > lat[-1]:
        u = u[:, ::-1, :]
        v = v[:, ::-1, :]
        lat = lat[::-1]
    wind = np.stack([u, v], axis=1)  # (T, 2, H, W)
    _cached_wind = (wind, lat, lon)
    return _cached_wind


def _load_mean_std():
    """Load mean and std. Cached."""
    global _cached_mean, _cached_std
    if _cached_mean is None:
        _cached_mean = np.load(MEAN_PATH)
        _cached_std = np.load(STD_PATH)
    return _cached_mean, _cached_std


def _resample_to_grid(data, src_lat, src_lon, dst_lat, dst_lon):
    """Resample 2D or 3D data from src grid to dst grid via linear interpolation."""
    from scipy.interpolate import RegularGridInterpolator

    if data.ndim == 2:
        data = data[np.newaxis, ...]
        squeeze = True
    else:
        squeeze = False

    n_t, *spatial = data.shape
    dst_h, dst_w = len(dst_lat), len(dst_lon)
    dst_lon_2d, dst_lat_2d = np.meshgrid(dst_lon, dst_lat)

    out = np.zeros((n_t, dst_h, dst_w), dtype=np.float32)
    for t in range(n_t):
        interp = RegularGridInterpolator(
            (src_lat, src_lon),
            data[t],
            method="linear",
            bounds_error=False,
            fill_value=np.nan,
        )
        pts = np.column_stack([dst_lat_2d.ravel(), dst_lon_2d.ravel()])
        out[t] = interp(pts).reshape(dst_h, dst_w)
        if np.any(np.isnan(out[t])):
            out[t] = np.nan_to_num(out[t], nan=0.0)

    if squeeze:
        out = out[0]
    return out


def get_wind_history_for_region(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    target_h: int,
    target_w: int,
    num_timesteps: int = INPUT_STEPS,
) -> np.ndarray:
    """
    Extract wind history from GRIB for the given region, resampled to (target_h, target_w).
    Returns (Tin, 2, H, W) normalized for PredRNN.
    Uses the last num_timesteps from the GRIB file.
    """
    wind, grib_lat, grib_lon = _load_grib()
    mean, std = _load_mean_std()

    # Bounds check
    grib_lat_min, grib_lat_max = float(grib_lat.min()), float(grib_lat.max())
    grib_lon_min, grib_lon_max = float(grib_lon.min()), float(grib_lon.max())
    if lat_min < grib_lat_min or lat_max > grib_lat_max or lon_min < grib_lon_min or lon_max > grib_lon_max:
        raise ValueError(
            f"Route region [{lat_min},{lat_max}] x [{lon_min},{lon_max}] "
            f"outside GRIB domain [{grib_lat_min},{grib_lat_max}] x [{grib_lon_min},{grib_lon_max}]"
        )

    # Target grid
    dst_lat = np.linspace(lat_min, lat_max, target_h)
    dst_lon = np.linspace(lon_min, lon_max, target_w)

    # Take last num_timesteps
    n_total = wind.shape[0]
    start = max(0, n_total - num_timesteps)
    wind_slice = wind[start : start + num_timesteps]  # (Tin, 2, H, W)

    # Resample each timestep and channel
    resampled = np.zeros((num_timesteps, 2, target_h, target_w), dtype=np.float32)
    for t in range(num_timesteps):
        for c in range(2):
            resampled[t, c] = _resample_to_grid(
                wind_slice[t, c], grib_lat, grib_lon, dst_lat, dst_lon
            )

    # Normalize (same as training)
    norm = (resampled - mean) / (std + 1e-6)
    return norm.astype(np.float32)


def denormalize_wind(wind_norm: np.ndarray) -> np.ndarray:
    """Convert normalized wind back to m/s."""
    mean, std = _load_mean_std()
    return wind_norm * std + mean


def get_wind_field_for_display(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    grid_size: int = 28,
) -> tuple:
    """
    Get ERA5 (GRIB) wind field for map display: raw u, v in m/s on a regular grid.
    Returns (u, v, lat_mesh, lon_mesh) for the given region. Raises if outside GRIB domain.
    """
    wind, grib_lat, grib_lon = _load_grib()
    grib_lat_min, grib_lat_max = float(grib_lat.min()), float(grib_lat.max())
    grib_lon_min, grib_lon_max = float(grib_lon.min()), float(grib_lon.max())
    if lat_min < grib_lat_min or lat_max > grib_lat_max or lon_min < grib_lon_min or lon_max > grib_lon_max:
        raise ValueError(
            f"Region outside GRIB domain [{grib_lat_min},{grib_lat_max}] x [{grib_lon_min},{grib_lon_max}]"
        )
    dst_lat = np.linspace(lat_min, lat_max, grid_size)
    dst_lon = np.linspace(lon_min, lon_max, grid_size)
    # Last timestep (most recent) for display
    u_src = wind[-1, 0]  # (H, W)
    v_src = wind[-1, 1]
    u = _resample_to_grid(u_src, grib_lat, grib_lon, dst_lat, dst_lon)
    v = _resample_to_grid(v_src, grib_lat, grib_lon, dst_lat, dst_lon)
    lon_mesh, lat_mesh = np.meshgrid(dst_lon, dst_lat)
    return u.astype(np.float32), v.astype(np.float32), lat_mesh, lon_mesh
