import urllib.request
import json
import time

API_BASE = "http://localhost:8000/api"

print("==================================================")
print("CRYSTAL-X FULL SYSTEM VERIFICATION")
print("==================================================")

# 1. Check datasets status
print("\n--- 1. Testing /api/datasets/status ---")
res = urllib.request.urlopen(f"{API_BASE}/datasets/status")
status = json.loads(res.read().decode())
print(f"Status: OK")
print(f"MP-20 Records: {status['mp20']['count']} (Train: {status['mp20']['train_count']}, Val: {status['mp20']['val_count']}, Test: {status['mp20']['test_count']})")
print(f"JARVIS-DFT Records: {status['jarvis']['count']}")
print(f"Total Reference Structures: {status['total_reference_structures']}")
assert status['mp20']['count'] == 45229, f"Expected 45229, got {status['mp20']['count']}"
assert status['jarvis']['count'] == 93902, f"Expected 93902, got {status['jarvis']['count']}"
assert status['total_reference_structures'] == 139131, f"Expected 139131, got {status['total_reference_structures']}"

# 2. Check reference catalog search
print("\n--- 2. Testing /api/datasets?element=K ---")
res = urllib.request.urlopen(f"{API_BASE}/datasets?element=K&limit=3")
catalog_res = json.loads(res.read().decode())
print(f"Total Potassium Reference Crystals Found: {catalog_res['total_records']}")
for m in catalog_res['materials']:
    print(f"  - [{m['dataset_source']}] {m['material_id']}: {m['formula']} (Ehull: {m['energy_above_hull']} eV, Stable: {m['is_stable']})")
assert catalog_res['total_records'] > 5000, f"Expected >5000 K materials, got {catalog_res['total_records']}"

# 3. Test End-to-End Discovery Pipeline
print("\n--- 3. Testing /api/discover with K-Fe Battery Material Prompt ---")
prompt_text = "Find crystalline energy-storage cathode material containing K and Fe with band gap between 1.0 and 2.5 eV, energy above hull below 0.05 eV/atom. Exclude Pb, Cd, Hg, and As."

# Parse prompt
req_data = json.dumps({"text": prompt_text}).encode("utf-8")
parse_req = urllib.request.Request(f"{API_BASE}/requirements/parse", data=req_data, headers={"Content-Type": "application/json"})
parse_res = json.loads(urllib.request.urlopen(parse_req).read().decode())
print(f"Parsed Requirements:")
print(f"  Required Elements: {parse_res['requirements']['required_elements']}")
print(f"  Excluded Elements: {parse_res['requirements']['excluded_elements']}")
print(f"  Target Energy Above Hull: {parse_res['requirements'].get('target_energy_above_hull', 'None')}")

# Run discovery
disc_data = json.dumps({
    "requirements": parse_res['requirements'],
    "generator_mode": "DEMO_GENERATOR",
    "configured_model": "LOCAL_DEMO"
}).encode("utf-8")
disc_req = urllib.request.Request(f"{API_BASE}/discover", data=disc_data, headers={"Content-Type": "application/json"})
t0 = time.time()
disc_res = json.loads(urllib.request.urlopen(disc_req).read().decode())
dur = time.time() - t0

candidates = disc_res.get("candidates", [])
print(f"\nDiscovery completed in {dur:.2f}s! Returned {len(candidates)} candidates.")

for idx, c in enumerate(candidates[:3], 1):
    nov = c.get("novelty", {})
    screen = c.get("screening", {})
    val = c.get("validation", {})
    print(f"\nCandidate #{idx}: {c['formula']} (ID: {c['candidate_id']})")
    print(f"  Generator Mode: {c.get('generator_mode')} ({c.get('generation_source')})")
    print(f"  Valid Structure: {val.get('is_valid')} (SpaceGroup: {c.get('space_group')})")
    print(f"  Screening: {screen.get('overall_status')} (Passed: {screen.get('passed')})")
    print(f"  Novelty Comparison across 139,131 records:")
    print(f"    Verdict: {nov.get('result')}")
    print(f"    Label: {nov.get('verdict_label')}")
    print(f"    Structures Compared: {nov.get('structures_compared')}")
    print(f"    Matched Ref ID: {nov.get('matched_reference_id')}")

print("\n==================================================")
print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
print("==================================================")
