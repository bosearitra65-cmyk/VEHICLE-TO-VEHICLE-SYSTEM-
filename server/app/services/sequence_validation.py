from enum import Enum


class SequenceStatus(str, Enum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    OUT_OF_ORDER = "out_of_order"
    GAP = "gap"


class SequenceValidationResult:
    def __init__(
        self,
        status: SequenceStatus,
        expected_sequence: int | None = None,
        gap_start: int | None = None,
        gap_end: int | None = None,
    ):
        self.status = status
        self.expected_sequence = expected_sequence
        self.gap_start = gap_start
        self.gap_end = gap_end


def validate_sequence(
    incoming_sequence: int,
    last_sequence: int | None,
) -> SequenceValidationResult:
    if last_sequence is None:
        return SequenceValidationResult(
            status=SequenceStatus.ACCEPTED,
        )

    if incoming_sequence == last_sequence:
        return SequenceValidationResult(
            status=SequenceStatus.DUPLICATE,
            expected_sequence=last_sequence + 1,
        )

    if incoming_sequence < last_sequence:
        return SequenceValidationResult(
            status=SequenceStatus.OUT_OF_ORDER,
            expected_sequence=last_sequence + 1,
        )

    if incoming_sequence == last_sequence + 1:
        return SequenceValidationResult(
            status=SequenceStatus.ACCEPTED,
            expected_sequence=last_sequence + 1,
        )

    return SequenceValidationResult(
        status=SequenceStatus.GAP,
        expected_sequence=last_sequence + 1,
        gap_start=last_sequence + 1,
        gap_end=incoming_sequence - 1,
    )
