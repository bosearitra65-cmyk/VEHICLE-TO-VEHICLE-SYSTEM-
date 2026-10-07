from pathlib import Path

root = Path("app")
files = sorted(root.rglob("*.py"))

terms = [
    "fault_injection",
    "fault scenario",
    "fault_scenario",
    "fault_controller",
    "experiment",
    "observation",
    "ground_truth",
    "metric",
    "evidence",
    "run_id",
    "baseline",
    "candidate",
    "seed",
    "fingerprint",
]

print("=" * 70)
print("STAGE 10 - STEP 4.1")
print("EXISTING FAULT / RESEARCH IMPLEMENTATION AUDIT")
print("=" * 70)
print(f"PYTHON_FILES={len(files)}")

for term in terms:
    matches = []

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if term.lower() in text.lower():
            matches.append(path)

    print()
    print(f"[{term}]")
    print(f"FILES_MATCHED={len(matches)}")

    for path in matches[:20]:
        print(f"  {path}")

print()
print("=" * 70)
print("AUDIT COMPLETE")
print("APPLICATION_CODE_MODIFIED=NO")
print("=" * 70)
