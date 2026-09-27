"""
RIVO Backend — Spatial Rent Surface & H3 Hexagon Smoothing
===========================================================
Generates and queries the spatial rent surface across Chennai:
  - Aggregated at H3 resolution (Resolution 8 ~ 0.7 km² / Resolution 9 ~ 0.1 km²)
  - Multi-tier spatial fallback:
      Target H3 Cell -> Neighboring Cells (k-ring 1) -> Locality -> Citywide Baseline
  - Enforces reduced confidence for every fallback step
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np

import h3

from app.schemas.ml import RentCellOut
from app.services.ml.dataset import RentalDatasetRecord


class RentSurfaceService:
    """
    Manages spatial H3 rent surface with hierarchical smoothing.
    """

    def __init__(self, resolution: int = 8) -> None:
        self.resolution = resolution
        self.cells: Dict[str, Dict[str, Any]] = {}
        self.locality_cells: Dict[str, List[str]] = {}

    def build_surface(self, records: List[RentalDatasetRecord]) -> Dict[str, RentCellOut]:
        """
        Aggregates empirical records into H3 rent cells.
        """
        self.cells.clear()
        self.locality_cells.clear()

        # Group records by H3 cell
        cell_records: Dict[str, List[RentalDatasetRecord]] = {}
        for r in records:
            if not r.h3_index or r.h3_index == "unknown":
                continue
            cell_records.setdefault(r.h3_index, []).append(r)

        result: Dict[str, RentCellOut] = {}

        for h3_idx, g_recs in cell_records.items():
            rents = [r.rent for r in g_recs]
            sqft_prices = [r.rent / r.area_sqft for r in g_recs if r.area_sqft > 0]
            unique_props = len({r.listing_id for r in g_recs})
            sources = len({r.source for r in g_recs})
            latest_obs = max(r.observed_at for r in g_recs)
            loc = g_recs[0].locality

            p25 = float(np.percentile(rents, 25))
            p50 = float(np.median(rents))
            p75 = float(np.percentile(rents, 75))
            sqft_med = float(np.median(sqft_prices)) if sqft_prices else 18.0

            conf = "HIGH" if (len(rents) >= 4 and sources >= 2) else ("MEDIUM" if len(rents) >= 2 else "LOW")

            cell_out = RentCellOut(
                h3_index=h3_idx,
                resolution=self.resolution,
                locality=loc,
                rent_p25=round(p25, 0),
                rent_p50=round(p50, 0),
                rent_p75=round(p75, 0),
                price_per_sqft_median=round(sqft_med, 1),
                observation_count=len(rents),
                unique_properties=unique_props,
                source_count=sources,
                latest_observation=latest_obs,
                confidence=conf,
                model_version="empirical_h3_surface",
            )
            self.cells[h3_idx] = cell_out.model_dump()
            self.locality_cells.setdefault(loc.lower().strip(), []).append(h3_idx)
            result[h3_idx] = cell_out

        return result

    def get_cell_estimate(
        self,
        h3_index: str,
        locality: Optional[str] = None,
    ) -> RentCellOut:
        """
        Retrieves rent surface metrics with hierarchical spatial fallback:
          Cell -> k-ring 1 neighbors -> Locality -> INSUFFICIENT_DATA
        """
        # 1. Direct cell match
        if h3_index in self.cells:
            return RentCellOut(**self.cells[h3_index])

        # 2. Spatial Smoothing: Check k-ring 1 neighboring cells
        try:
            # Handle h3 version differences (grid_disk in v4, k_ring in v3)
            if hasattr(h3, "grid_disk"):
                neighbors = list(h3.grid_disk(h3_index, 1))
            else:
                neighbors = list(h3.k_ring(h3_index, 1))
        except Exception:
            neighbors = []

        neighbor_cells = [self.cells[n] for n in neighbors if n in self.cells and n != h3_index]
        if neighbor_cells:
            # Aggregate neighbor cells
            p50_vals = [c["rent_p50"] for c in neighbor_cells if c.get("rent_p50")]
            p25_vals = [c["rent_p25"] for c in neighbor_cells if c.get("rent_p25")]
            p75_vals = [c["rent_p75"] for c in neighbor_cells if c.get("rent_p75")]
            if p50_vals:
                return RentCellOut(
                    h3_index=h3_index,
                    resolution=self.resolution,
                    locality=locality or neighbor_cells[0].get("locality"),
                    rent_p25=round(float(np.mean(p25_vals)), 0) if p25_vals else None,
                    rent_p50=round(float(np.mean(p50_vals)), 0),
                    rent_p75=round(float(np.mean(p75_vals)), 0) if p75_vals else None,
                    confidence="LOW",  # Reduced confidence due to smoothing fallback
                    model_version="h3_neighbor_smoothed",
                    observation_count=sum(c.get("observation_count", 0) for c in neighbor_cells),
                )

        # 3. Locality Fallback
        if locality:
            loc_key = locality.lower().strip()
            loc_cell_ids = self.locality_cells.get(loc_key, [])
            if loc_cell_ids:
                loc_data = [self.cells[cid] for cid in loc_cell_ids if cid in self.cells]
                p50s = [c["rent_p50"] for c in loc_data if c.get("rent_p50")]
                if p50s:
                    return RentCellOut(
                        h3_index=h3_index,
                        resolution=self.resolution,
                        locality=locality,
                        rent_p50=round(float(np.median(p50s)), 0),
                        confidence="LOW",
                        model_version="locality_fallback",
                        observation_count=len(p50s),
                    )

        # 4. Insufficient Evidence
        return RentCellOut(
            h3_index=h3_index,
            resolution=self.resolution,
            locality=locality,
            confidence="INSUFFICIENT_DATA",
            model_version="none",
            observation_count=0,
        )


rent_surface_service = RentSurfaceService()
