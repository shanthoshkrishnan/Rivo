"""
RIVO Backend — Baseline Benchmark Model
========================================
Robust hierarchical statistical baseline:
  H3 Cell + BHK -> Locality + BHK -> Citywide BHK -> Global Median

Calculates empirical MAE, RMSE, MedAE, and percentile intervals (p25, p50, p75).
ML models MUST demonstrate material improvement over this baseline to be promoted.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.schemas.ml import RentPredictionRequest, RentPredictionResponse
from app.services.ml.dataset import RentalDatasetRecord


class RentBaselineModel:
    """
    Hierarchical empirical baseline model for Chennai residential rents.
    """

    def __init__(self, model_version: str = "baseline_v1") -> None:
        self.model_version = model_version
        self.cell_bhk_medians: Dict[Tuple[str, int], Dict[str, float]] = {}
        self.locality_bhk_medians: Dict[Tuple[str, int], Dict[str, float]] = {}
        self.city_bhk_medians: Dict[int, Dict[str, float]] = {}
        self.citywide_median: float = 15000.0
        self.price_per_sqft_median: float = 18.0
        self.global_p25_ratio: float = 0.85
        self.global_p75_ratio: float = 1.18
        self.is_fitted: bool = False
        self.training_record_count: int = 0
        self.metrics: Dict[str, float] = {}

    def fit(self, records: List[RentalDatasetRecord]) -> Dict[str, Any]:
        """Fit empirical medians and quantiles from real training observations."""
        if not records:
            self.is_fitted = False
            return {"status": "NO_DATA", "record_count": 0}

        self.training_record_count = len(records)
        rents = [r.rent for r in records]
        sqft_prices = [r.rent / r.area_sqft for r in records if r.area_sqft > 0]

        self.citywide_median = float(np.median(rents))
        self.price_per_sqft_median = float(np.median(sqft_prices)) if sqft_prices else 18.0

        p25 = float(np.percentile(rents, 25))
        p75 = float(np.percentile(rents, 75))
        if self.citywide_median > 0:
            self.global_p25_ratio = p25 / self.citywide_median
            self.global_p75_ratio = p75 / self.citywide_median

        # Group by Citywide BHK
        bhk_groups: Dict[int, List[float]] = {}
        for r in records:
            bhk_groups.setdefault(r.bhk, []).append(r.rent)

        self.city_bhk_medians = {}
        for bhk, g_rents in bhk_groups.items():
            self.city_bhk_medians[bhk] = {
                "median": float(np.median(g_rents)),
                "p25": float(np.percentile(g_rents, 25)),
                "p75": float(np.percentile(g_rents, 75)),
                "count": len(g_rents),
            }

        # Group by Locality + BHK
        loc_bhk_groups: Dict[Tuple[str, int], List[float]] = {}
        for r in records:
            key = (r.locality.lower().strip(), r.bhk)
            loc_bhk_groups.setdefault(key, []).append(r.rent)

        self.locality_bhk_medians = {}
        for key, g_rents in loc_bhk_groups.items():
            self.locality_bhk_medians[key] = {
                "median": float(np.median(g_rents)),
                "p25": float(np.percentile(g_rents, 25)),
                "p75": float(np.percentile(g_rents, 75)),
                "count": len(g_rents),
            }

        # Group by H3 Cell + BHK
        cell_bhk_groups: Dict[Tuple[str, int], List[float]] = {}
        for r in records:
            if r.h3_index and r.h3_index != "unknown":
                key = (r.h3_index, r.bhk)
                cell_bhk_groups.setdefault(key, []).append(r.rent)

        self.cell_bhk_medians = {}
        for key, g_rents in cell_bhk_groups.items():
            self.cell_bhk_medians[key] = {
                "median": float(np.median(g_rents)),
                "p25": float(np.percentile(g_rents, 25)),
                "p75": float(np.percentile(g_rents, 75)),
                "count": len(g_rents),
            }

        self.is_fitted = True
        return {
            "status": "FITTED",
            "training_record_count": self.training_record_count,
            "citywide_median": self.citywide_median,
            "bhk_classes": list(self.city_bhk_medians.keys()),
            "localities": len({k[0] for k in self.locality_bhk_medians.keys()}),
            "h3_cells": len({k[0] for k in self.cell_bhk_medians.keys()}),
        }

    def evaluate(self, validation_records: List[RentalDatasetRecord]) -> Dict[str, float]:
        """Calculates MAE, RMSE, and MedAE against a validation set."""
        if not self.is_fitted or not validation_records:
            return {"mae": 0.0, "rmse": 0.0, "medae": 0.0, "sample_size": 0}

        y_true: List[float] = []
        y_pred: List[float] = []

        for r in validation_records:
            pred = self.predict(
                RentPredictionRequest(
                    bhk=r.bhk,
                    area_sqft=r.area_sqft,
                    locality=r.locality,
                    latitude=r.latitude,
                    longitude=r.longitude,
                    h3_index=r.h3_index,
                )
            )
            if pred.rent_p50 is not None:
                y_true.append(r.rent)
                y_pred.append(pred.rent_p50)

        if not y_true:
            return {"mae": 0.0, "rmse": 0.0, "medae": 0.0, "sample_size": 0}

        errors = np.abs(np.array(y_true) - np.array(y_pred))
        sq_errors = (np.array(y_true) - np.array(y_pred)) ** 2

        metrics = {
            "mae": float(np.mean(errors)),
            "rmse": float(np.sqrt(np.mean(sq_errors))),
            "medae": float(np.median(errors)),
            "sample_size": len(y_true),
        }
        self.metrics = metrics
        return metrics

    def predict(self, req: RentPredictionRequest) -> RentPredictionResponse:
        """
        Hierarchical fallback prediction:
          Cell+BHK -> Locality+BHK -> Citywide BHK -> Global Median
        """
        if not self.is_fitted:
            return RentPredictionResponse(
                model_name="baseline_hierarchical",
                model_version=self.model_version,
                confidence="INSUFFICIENT_DATA",
                method="unfitted",
                insufficient_data=True,
                explanation="Model has not been trained on sufficient empirical observations.",
            )

        bhk = req.bhk
        locality = (req.locality or "").lower().strip()
        h3_idx = req.h3_index

        # Tier 1: Cell + BHK
        if h3_idx and (h3_idx, bhk) in self.cell_bhk_medians:
            stats = self.cell_bhk_medians[(h3_idx, bhk)]
            count = stats["count"]
            conf = "HIGH" if count >= 4 else "MEDIUM"
            return RentPredictionResponse(
                rent_p25=round(stats["p25"], 0),
                rent_p50=round(stats["median"], 0),
                rent_p75=round(stats["p75"], 0),
                price_per_sqft_median=round(self.price_per_sqft_median, 1),
                model_name="baseline_hierarchical",
                model_version=self.model_version,
                confidence=conf,
                method="h3_cell_empirical_median",
                data_freshness="MODELLED",
                insufficient_data=False,
                explanation=f"Estimated from {count} real observations in hex cell {h3_idx[:8]} for {bhk} BHK.",
            )

        # Tier 2: Locality + BHK
        if locality and (locality, bhk) in self.locality_bhk_medians:
            stats = self.locality_bhk_medians[(locality, bhk)]
            count = stats["count"]
            conf = "MEDIUM" if count >= 3 else "LOW"
            return RentPredictionResponse(
                rent_p25=round(stats["p25"], 0),
                rent_p50=round(stats["median"], 0),
                rent_p75=round(stats["p75"], 0),
                price_per_sqft_median=round(self.price_per_sqft_median, 1),
                model_name="baseline_hierarchical",
                model_version=self.model_version,
                confidence=conf,
                method="locality_bhk_empirical_median",
                data_freshness="MODELLED",
                insufficient_data=False,
                explanation=f"Estimated from {count} real observations in {locality.title()} for {bhk} BHK.",
            )

        # Tier 3: Citywide BHK
        if bhk in self.city_bhk_medians:
            stats = self.city_bhk_medians[bhk]
            return RentPredictionResponse(
                rent_p25=round(stats["p25"], 0),
                rent_p50=round(stats["median"], 0),
                rent_p75=round(stats["p75"], 0),
                price_per_sqft_median=round(self.price_per_sqft_median, 1),
                model_name="baseline_hierarchical",
                model_version=self.model_version,
                confidence="LOW",
                method="citywide_bhk_fallback",
                data_freshness="MODELLED",
                insufficient_data=False,
                explanation=f"Estimated from city-wide {bhk} BHK empirical median across Chennai.",
            )

        # Tier 4: Global Fallback
        p50 = self.citywide_median
        return RentPredictionResponse(
            rent_p25=round(p50 * self.global_p25_ratio, 0),
            rent_p50=round(p50, 0),
            rent_p75=round(p50 * self.global_p75_ratio, 0),
            price_per_sqft_median=round(self.price_per_sqft_median, 1),
            model_name="baseline_hierarchical",
            model_version=self.model_version,
            confidence="LOW",
            method="citywide_global_fallback",
            data_freshness="MODELLED",
            insufficient_data=False,
            explanation="Estimated from overall Chennai city-wide rental baseline.",
        )
