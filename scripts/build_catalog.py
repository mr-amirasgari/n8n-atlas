import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

with open(DATA / "nodes.json", encoding="utf-8") as f:
    official = json.load(f)

with open(DATA / "community-nodes.json", encoding="utf-8") as f:
    community = json.load(f)

catalog = []

# Official
for item in official:
    catalog.append({
        "id": f"official:{item['package']}:{item['name']}",
        "name": item["name"],
        "source": "official",
        "package": item["package"],
        "description": None,
        "version": None,
        "links": {},
    })

# Community
seen = set()

for item in community:
    name = item.get("name")

    if not name or name in seen:
        continue

    seen.add(name)

    catalog.append({
        "id": f"community:{name}",
        "name": name,
        "source": "community",
        "package": name,
        "description": item.get("description"),
        "version": item.get("version"),
        "links": item.get("links", {}),
    })

catalog.sort(key=lambda x: x["name"].lower())

output = DATA / "catalog.json"

with open(output, "w", encoding="utf-8") as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)

print(f"Official: {len(official)}")
print(f"Community unique: {len(seen)}")
print(f"Total catalog: {len(catalog)}")
print(f"Saved to: {output}")