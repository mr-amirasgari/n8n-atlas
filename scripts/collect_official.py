import json
import urllib.request
from pathlib import Path

PACKAGES = {
    "n8n-nodes-base":
        "https://raw.githubusercontent.com/n8n-io/n8n/master/packages/nodes-base/package.json",

    "@n8n/nodes-langchain":
        "https://raw.githubusercontent.com/n8n-io/n8n/master/packages/@n8n/nodes-langchain/package.json",
}


def fetch_json(url):
    with urllib.request.urlopen(url) as response:
        return json.load(response)


all_nodes = []

for package_name, url in PACKAGES.items():
    print(f"Fetching {package_name}...")

    package = fetch_json(url)

    for path in package.get("n8n", {}).get("nodes", []):
        filename = Path(path).name

        name = (
            filename
            .replace(".node.js", "")
            .replace(".js", "")
        )

        all_nodes.append({
            "name": name,
            "package": package_name,
            "path": path,
            "type": "trigger" if "Trigger" in name else "node",
            "official": True
        })


all_nodes.sort(key=lambda x: x["name"].lower())

output = Path(__file__).parent.parent / "data" / "nodes.json"
output.parent.mkdir(exist_ok=True)

with open(output, "w", encoding="utf-8") as f:
    json.dump(all_nodes, f, ensure_ascii=False, indent=2)

print()
print(f"Done: {len(all_nodes)} official nodes collected")
print(f"Saved to: {output}")