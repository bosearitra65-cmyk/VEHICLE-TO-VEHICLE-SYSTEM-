from pathlib import Path

p = Path("stage10_step5_1_verify.py")
s = p.read_text(encoding="utf-8")

old = '''    assert result.score == 0.75
    assert result.state == "DEGRADED"
'''

new = '''    assert abs(result.score - 0.75) < 1e-9
    assert result.state == "DEGRADED"
'''

if old not in s:
    raise SystemExit(
        "DEGRADED_ASSERT_BLOCK_NOT_FOUND=STOP"
    )

s = s.replace(old, new)

old = '''    assert result.score == 0.5
    assert result.state == "SUSPECT"
'''

new = '''    assert abs(result.score - 0.5) < 1e-9
    assert result.state == "SUSPECT"
'''

if old not in s:
    raise SystemExit(
        "SUSPECT_ASSERT_BLOCK_NOT_FOUND=STOP"
    )

s = s.replace(old, new)

old = '''    assert result.score == 0.1
    assert result.state == "UNTRUSTED"
'''

new = '''    assert abs(result.score - 0.1) < 1e-9
    assert result.state == "UNTRUSTED"
'''

if old not in s:
    raise SystemExit(
        "UNTRUSTED_ASSERT_BLOCK_NOT_FOUND=STOP"
    )

s = s.replace(old, new)

old = '''    assert result.score == 0.0
    assert result.state == "UNTRUSTED"
'''

new = '''    assert abs(result.score - 0.0) < 1e-9
    assert result.state == "UNTRUSTED"
'''

if old not in s:
    raise SystemExit(
        "WEIGHTED_ASSERT_BLOCK_NOT_FOUND=STOP"
    )

s = s.replace(old, new)

p.write_text(s, encoding="utf-8")

print("FLOATING_POINT_TEST_FIX=APPLIED")
print("CANDIDATE_IMPLEMENTATION_MODIFIED=NO")
print("PRODUCTION_STATE_MODIFIED=NO")
