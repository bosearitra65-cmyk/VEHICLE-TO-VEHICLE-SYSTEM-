
import pytest

from app.research.comparison_engine import (
    ComparisonEngine,
    RunMetricSummary,
)
from app.research.evidence_manager import EvidenceManager


def run(run_id, mechanism, valid=True, detection=10.0, recovery=20.0):
    return RunMetricSummary(
        run_id=run_id,
        mechanism_type=mechanism,
        mechanism_version=f"{mechanism}-v1",
        valid=valid,
        metrics={
            "detection_latency":{
                "value":detection,
                "unit":"seconds",
            },
            "recovery_time":{
                "value":recovery,
                "unit":"seconds",
            },
        },
    )


def test_comparison_requires_both_sides():
    engine=ComparisonEngine()

    with pytest.raises(ValueError):
        engine.compare(
            comparison_id="C1",
            experiment_id="EXP1",
            baseline_runs=[],
            candidate_runs=[run("C1","CANDIDATE")],
        )

    with pytest.raises(ValueError):
        engine.compare(
            comparison_id="C2",
            experiment_id="EXP1",
            baseline_runs=[run("B1","BASELINE")],
            candidate_runs=[],
        )


def test_valid_baseline_candidate_comparison():
    engine=ComparisonEngine()

    result=engine.compare(
        comparison_id="CMP1",
        experiment_id="EXP1",
        baseline_runs=[
            run("B1","BASELINE",detection=10,recovery=20),
            run("B2","BASELINE",detection=12,recovery=22),
        ],
        candidate_runs=[
            run("C1","CANDIDATE",detection=7,recovery=18),
            run("C2","CANDIDATE",detection=9,recovery=16),
        ],
        comparison_configuration={"aggregation":"median"},
    )

    assert result.baseline_run_ids==("B1","B2")
    assert result.candidate_run_ids==("C1","C2")
    assert result.calculated_metrics["detection_latency"]["baseline"]==11.0
    assert result.calculated_metrics["detection_latency"]["candidate"]==8.0
    assert result.differences[0].calculation_version=="COMPARISON-v1"


def test_invalid_run_cannot_be_compared():
    engine=ComparisonEngine()

    with pytest.raises(ValueError):
        engine.compare(
            comparison_id="CMP2",
            experiment_id="EXP1",
            baseline_runs=[run("B1","BASELINE",valid=False)],
            candidate_runs=[run("C1","CANDIDATE")],
        )


def test_metric_unit_mismatch_is_rejected():
    engine=ComparisonEngine()

    baseline=run("B1","BASELINE")
    candidate=run("C1","CANDIDATE")
    candidate.metrics["detection_latency"]["unit"]="milliseconds"

    with pytest.raises(ValueError):
        engine.compare(
            comparison_id="CMP3",
            experiment_id="EXP1",
            baseline_runs=[baseline],
            candidate_runs=[candidate],
        )


def test_no_winner_or_verdict_is_created():
    engine=ComparisonEngine()

    result=engine.compare(
        comparison_id="CMP4",
        experiment_id="EXP1",
        baseline_runs=[run("B1","BASELINE",detection=100)],
        candidate_runs=[run("C1","CANDIDATE",detection=1)],
    )

    assert not hasattr(result,"winner")
    assert not hasattr(result,"verdict")
    assert engine.RESEARCH_ONLY is True
    assert engine.OPERATIONAL_ACTION=="NO_OPERATIONAL_ACTION"


def test_evidence_has_first_class_metadata_and_integrity():
    manager=EvidenceManager()

    record=manager.create(
        evidence_id="E1",
        experiment_id="EXP1",
        run_id="C1",
        evidence_type="COMPARISON",
        source_references=["RUN-C1","METRIC-1"],
        payload={"detection_latency":8.0},
        metadata={
            "calculation_version":"COMPARISON-v1",
            "aggregation":"median",
            "created_by":"researcher-1",
        },
    )

    assert record.metadata["calculation_version"]=="COMPARISON-v1"
    assert record.integrity.algorithm=="SHA256"
    assert len(record.integrity.digest)==64
    assert manager.verify_integrity("E1") is True


def test_evidence_provenance_is_explicitly_verified():
    manager=EvidenceManager()

    manager.create(
        evidence_id="E2",
        experiment_id="EXP1",
        run_id="B1",
        evidence_type="METRIC",
        source_references=["OBS-1","METRIC-1"],
        payload={"value":10},
        metadata={"metric_name":"detection_latency"},
    )

    assert manager.verify_provenance(
        "E2",
        experiment_id="EXP1",
        run_id="B1",
        source_references=["OBS-1","METRIC-1"],
    ) is True

    assert manager.verify_provenance(
        "E2",
        experiment_id="EXP1",
        run_id="C1",
        source_references=["OBS-1","METRIC-1"],
    ) is False


def test_evidence_finalization_preserves_integrity_and_metadata():
    manager=EvidenceManager()

    record=manager.create(
        evidence_id="E3",
        experiment_id="EXP1",
        run_id="C1",
        evidence_type="COMPARISON",
        source_references=["CMP1"],
        payload={"difference":-3},
        metadata={"calculation_version":"COMPARISON-v1"},
    )

    digest_before=record.integrity.digest
    finalized=manager.finalize("E3")

    assert finalized.finalized is True
    assert finalized.integrity.digest==digest_before
    assert finalized.metadata["calculation_version"]=="COMPARISON-v1"
    assert manager.verify_integrity("E3") is True


def test_finalized_evidence_cannot_be_replaced():
    manager=EvidenceManager()

    manager.create(
        evidence_id="E4",
        experiment_id="EXP1",
        run_id="B1",
        evidence_type="RAW_OBSERVATION",
        source_references=["OBS-1"],
        payload={"sequence":100},
    )
    manager.finalize("E4")

    with pytest.raises(ValueError):
        manager.replace("E4",payload={"sequence":999})


def test_correction_creates_new_evidence_with_lineage():
    manager=EvidenceManager()

    manager.create(
        evidence_id="E5",
        experiment_id="EXP1",
        run_id="B1",
        evidence_type="METRIC",
        source_references=["OBS-1"],
        payload={"value":10},
        metadata={"calculation_version":"METRIC-v1"},
    )
    original=manager.finalize("E5")

    correction=manager.correction(
        new_evidence_id="E5-C1",
        original_evidence_id="E5",
        correction_payload={"value":11,"reason":"recalculation"},
        created_by="researcher-1",
    )

    assert correction.evidence_type=="CORRECTION"
    assert correction.source_references==("E5",)
    assert correction.metadata["correction_of"]=="E5"
    assert correction.metadata["original_integrity_digest"]==original.integrity.digest
    assert manager.get("E5").finalized is True
    assert manager.verify_integrity("E5") is True
    assert manager.verify_integrity("E5-C1") is True


def test_research_only_evidence_boundary():
    assert EvidenceManager.RESEARCH_ONLY is True
    assert EvidenceManager.OPERATIONAL_ACTION=="NO_OPERATIONAL_ACTION"
