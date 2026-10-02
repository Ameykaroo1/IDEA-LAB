import urllib.request
import json

url = "http://localhost:8000/api/datasets?element=K&limit=5"
res = urllib.request.urlopen(url)
data = json.loads(res.read().decode())

print("Total Potassium Materials in Catalog:", data.get("total_records"))
print(f"Showing page {data.get('page')} of {data.get('total_pages')}:")
for m in data.get("materials", []):
    print(f"  [{m['dataset_source']}] {m['material_id']}: {m['formula']} (Ehull: {m['energy_above_hull']} eV, BandGap: {m['band_gap']} eV, SpaceGroup: {m['space_group']})")

# Test search query
url_search = "http://localhost:8000/api/datasets?query=LiCoO2"
res_search = urllib.request.urlopen(url_search)
data_search = json.loads(res_search.read().decode())
print(f"\nSearch for LiCoO2 returned {data_search.get('total_records')} records:")
for m in data_search.get("materials", [])[:3]:
    print(f"  [{m['dataset_source']}] {m['material_id']}: {m['formula']}")
