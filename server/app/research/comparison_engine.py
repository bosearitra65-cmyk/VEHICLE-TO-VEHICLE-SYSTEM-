
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import median
from typing import Any


@dataclass(frozen=True)
class MetricObservation:
    run_id: str
    metric_name: str
    value: float
    unit: str
    source_references: tuple[str, ...] = ()
    calculation_version: str = "METRIC-v1"


@dataclass(frozen=True)
class RunMetricSummary:
    run_id: str
    mechanism_type: str
    mechanism_version: str
    valid: bool
    metrics: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class MetricDifference:
    metric_name: str
    unit: str
    baseline_value: float
    candidate_value: float
    difference: float
    calculation_version: str


@dataclass(frozen=True)
class ComparisonResult:
    comparison_id: str
    experiment_id: str
    baseline_run_ids: tuple[str, ...]
    candidate_run_ids: tuple[str, ...]
    comparison_configuration: dict[str, Any]
    calculated_metrics: dict[str, dict[str, Any]]
    differences: tuple[MetricDifference, ...]
    generated_at: datetime
    calculation_version: str = "COMPARISON-v1"


class ComparisonEngine:
    """
    Research-only factual comparison engine.

    It calculates measurements and differences between valid baseline and
    candidate runs. It deliberately does not produce a winner, verdict,
    operational action, alert, event, realtime publication, or DB mutation.
    """

    RESEARCH_ONLY = True
    OPERATIONAL_ACTION = "NO_OPERATIONAL_ACTION"

    def compare(
        self,
        *,
        comparison_id: str,
        experiment_id: str,
        baseline_runs: list[RunMetricSummary],
        candidate_runs: list[RunMetricSummary],
        comparison_configuration: dict[str, Any] | None = None,
    ) -> ComparisonResult:
        if not baseline_runs:
            raise ValueError("BASELINE_RUNS_REQUIRED")
        if not candidate_runs:
            raise ValueError("CANDIDATE_RUNS_REQUIRED")

        all_runs=baseline_runs+candidate_runs

        for run in all_runs:
            if not run.valid:
                raise ValueError(f"INVALID_RUN:{run.run_id}")

        baseline_metrics=self._aggregate(baseline_runs)
        candidate_metrics=self._aggregate(candidate_runs)

        common=set(baseline_metrics).intersection(candidate_metrics)
        if not common:
            raise ValueError("NO_COMPARABLE_METRICS")

        differences=[]
        calculated={}

        for name in sorted(common):
            b=baseline_metrics[name]
            c=candidate_metrics[name]

            if b["unit"] != c["unit"]:
                raise ValueError(f"METRIC_UNIT_MISMATCH:{name}")

            difference=c["value"]-b["value"]

            calculated[name]={
                "baseline": b["value"],
                "candidate": c["value"],
                "unit": b["unit"],
                "baseline_sample_count": b["sample_count"],
                "candidate_sample_count": c["sample_count"],
            }

            differences.append(
                MetricDifference(
                    metric_name=name,
                    unit=b["unit"],
                    baseline_value=b["value"],
                    candidate_value=c["value"],
                    difference=difference,
                    calculation_version="COMPARISON-v1",
                )
            )

        return ComparisonResult(
            comparison_id=comparison_id,
            experiment_id=experiment_id,
            baseline_run_ids=tuple(r.run_id for r in baseline_runs),
            candidate_run_ids=tuple(r.run_id for r in candidate_runs),
            comparison_configuration=dict(comparison_configuration or {}),
            calculated_metrics=calculated,
            differences=tuple(differences),
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _aggregate(
        runs: list[RunMetricSummary],
    ) -> dict[str, dict[str, Any]]:
        grouped: dict[str, list[tuple[float,str]]] = {}

        for run in runs:
            for name, metric in run.metrics.items():
                value=float(metric["value"])
                unit=str(metric["unit"])
                grouped.setdefault(name,[]).append((value,unit))

        result={}

        for name, samples in grouped.items():
            units={unit for _,unit in samples}
            if len(units)!=1:
                raise ValueError(f"METRIC_UNIT_MISMATCH:{name}")

            values=[value for value,_ in samples]

            result[name]={
                "value":float(median(values)),
                "unit":next(iter(units)),
                "sample_count":len(values),
            }

        return result
