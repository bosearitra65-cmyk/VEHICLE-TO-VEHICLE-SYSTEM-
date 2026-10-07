
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any


@dataclass(frozen=True)
class EvidenceIntegrity:
    algorithm: str
    digest: str


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    experiment_id: str
    run_id: str | None
    evidence_type: str
    source_references: tuple[str, ...]
    payload: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    version: str
    integrity: EvidenceIntegrity
    finalized: bool = False


class EvidenceManager:
    """
    Research evidence preservation layer.

    Evidence preserves experiment/run provenance, source references,
    metadata, calculation/version context and integrity information.

    Finalized evidence is immutable. Corrections create new evidence
    records rather than silently replacing historical evidence.

    This layer does not modify authoritative vehicle state, operational
    database state, realtime state, alerts, or operational events.
    """

    RESEARCH_ONLY = True
    OPERATIONAL_ACTION = "NO_OPERATIONAL_ACTION"
    HASH_ALGORITHM = "SHA256"

    def __init__(self) -> None:
        self._records: dict[str, EvidenceRecord] = {}

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    @classmethod
    def _digest(
        cls,
        *,
        evidence_id: str,
        experiment_id: str,
        run_id: str | None,
        evidence_type: str,
        source_references: tuple[str, ...],
        payload: dict[str, Any],
        metadata: dict[str, Any],
        version: str,
    ) -> str:
        canonical=cls._canonical(
            {
                "evidence_id": evidence_id,
                "experiment_id": experiment_id,
                "run_id": run_id,
                "evidence_type": evidence_type,
                "source_references": source_references,
                "payload": payload,
                "metadata": metadata,
                "version": version,
            }
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def create(
        self,
        *,
        evidence_id: str,
        experiment_id: str,
        run_id: str | None,
        evidence_type: str,
        source_references: list[str] | tuple[str, ...],
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        version: str = "EVIDENCE-v1",
    ) -> EvidenceRecord:
        if evidence_id in self._records:
            raise ValueError("EVIDENCE_ID_ALREADY_EXISTS")

        refs=tuple(source_references)
        payload_copy=json.loads(self._canonical(payload))
        metadata_copy=json.loads(self._canonical(metadata or {}))

        digest=self._digest(
            evidence_id=evidence_id,
            experiment_id=experiment_id,
            run_id=run_id,
            evidence_type=evidence_type,
            source_references=refs,
            payload=payload_copy,
            metadata=metadata_copy,
            version=version,
        )

        record=EvidenceRecord(
            evidence_id=evidence_id,
            experiment_id=experiment_id,
            run_id=run_id,
            evidence_type=evidence_type,
            source_references=refs,
            payload=payload_copy,
            metadata=metadata_copy,
            created_at=datetime.now(timezone.utc),
            version=version,
            integrity=EvidenceIntegrity(
                algorithm=self.HASH_ALGORITHM,
                digest=digest,
            ),
            finalized=False,
        )

        self._records[evidence_id]=record
        return record

    def get(self, evidence_id: str) -> EvidenceRecord:
        if evidence_id not in self._records:
            raise KeyError("EVIDENCE_NOT_FOUND")
        return self._records[evidence_id]

    def finalize(self, evidence_id: str) -> EvidenceRecord:
        record=self.get(evidence_id)

        if record.finalized:
            raise ValueError("EVIDENCE_ALREADY_FINALIZED")

        finalized=EvidenceRecord(
            evidence_id=record.evidence_id,
            experiment_id=record.experiment_id,
            run_id=record.run_id,
            evidence_type=record.evidence_type,
            source_references=record.source_references,
            payload=record.payload,
            metadata=record.metadata,
            created_at=record.created_at,
            version=record.version,
            integrity=record.integrity,
            finalized=True,
        )

        self._records[evidence_id]=finalized
        return finalized

    def verify_integrity(self, evidence_id: str) -> bool:
        record=self.get(evidence_id)

        expected=self._digest(
            evidence_id=record.evidence_id,
            experiment_id=record.experiment_id,
            run_id=record.run_id,
            evidence_type=record.evidence_type,
            source_references=record.source_references,
            payload=record.payload,
            metadata=record.metadata,
            version=record.version,
        )

        return (
            record.integrity.algorithm == self.HASH_ALGORITHM
            and expected == record.integrity.digest
        )

    def verify_provenance(
        self,
        evidence_id: str,
        *,
        experiment_id: str,
        run_id: str | None,
        source_references: list[str] | tuple[str, ...],
    ) -> bool:
        record=self.get(evidence_id)

        return (
            record.experiment_id == experiment_id
            and record.run_id == run_id
            and record.source_references == tuple(source_references)
            and self.verify_integrity(evidence_id)
        )

    def replace(self, evidence_id: str, **_: Any) -> EvidenceRecord:
        record=self.get(evidence_id)

        if record.finalized:
            raise ValueError("FINALIZED_EVIDENCE_IMMUTABLE")

        raise ValueError("EVIDENCE_REPLACEMENT_NOT_SUPPORTED")

    def correction(
        self,
        *,
        new_evidence_id: str,
        original_evidence_id: str,
        correction_payload: dict[str, Any],
        created_by: str,
    ) -> EvidenceRecord:
        original=self.get(original_evidence_id)

        payload={
            "corrects_evidence_id": original.evidence_id,
            "correction": correction_payload,
        }

        metadata={
            "created_by": created_by,
            "correction_of": original.evidence_id,
            "original_integrity_digest": original.integrity.digest,
        }

        return self.create(
            evidence_id=new_evidence_id,
            experiment_id=original.experiment_id,
            run_id=original.run_id,
            evidence_type="CORRECTION",
            source_references=(original.evidence_id,),
            payload=payload,
            metadata=metadata,
            version="EVIDENCE-CORRECTION-v1",
        )
