"""Pure helpers for the conceptual Mini Research Lab."""


def glacier_surface_melt_pressure(
    air_temperature_c: float,
    cold_baseline_c: float = -5.0,
) -> float:
    """Return a monotonic conceptual surface-melt pressure.

    The control covers a cold Antarctic range.  Warming from the lower bound
    must increase, never decrease, the surface-loss contribution.
    """

    return max(0.0, float(air_temperature_c) - float(cold_baseline_c)) * 0.4
