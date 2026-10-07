from pathlib import Path

p = Path("stage10_step5_1_verify.py")
s = p.read_text(encoding="utf-8")

old = '''def test_degraded():
    evidence = dict(NORMAL)
    evidence["communication"] = 0.0

    result = evaluate_reliability(evidence)

    assert result.state == "DEGRADED"

    print("DEGRADED_STATE=PASS")
'''

new = '''def test_degraded():
    evidence = {
        "temporal": 0.5,
        "spatial": 0.5,
        "motion": 0.5,
        "route": 1.0,
        "communication": 1.0,
        "convoy": 1.0,
    }

    result = evaluate_reliability(evidence)

    assert result.score == 0.75
    assert result.state == "DEGRADED"

    print("DEGRADED_STATE=PASS")
'''

if old not in s:
    raise SystemExit(
        "EXPECTED_TEST_BLOCK_NOT_FOUND=STOP"
    )

p.write_text(
    s.replace(old, new),
    encoding="utf-8",
)

print("TEST_CORRECTION=APPLIED")
print("EVALUATOR_CODE_MODIFIED=NO")
print("PRODUCTION_STATE_MODIFIED=NO")
