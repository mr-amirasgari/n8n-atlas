import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

SEARCH_TERM = "keywords:n8n-community-node-package"
PAGE_SIZE = 250
MAX_RETRIES = 6

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

RAW_OUTPUT = DATA / "community-nodes-raw.json"
UNIQUE_OUTPUT = DATA / "community-nodes.json"

DATA.mkdir(exist_ok=True)

all_packages = []
offset = 0

print("Collecting community packages from npm...")

while True:
    params = urllib.parse.urlencode({
        "text": SEARCH_TERM,
        "size": PAGE_SIZE,
        "from": offset,
    })

    url = f"https://registry.npmjs.org/-/v1/search?{params}"

    data = None

    for attempt in range(MAX_RETRIES):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "n8n-atlas/1.0"
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:
                data = json.load(response)

            break

        except Exception as e:
            wait = 2 ** attempt

            print(
                f"Retry {attempt + 1}/"
                f"{MAX_RETRIES} in {wait}s..."
            )

            print(e)

            time.sleep(wait)

    if data is None:
        print(
            "Stopped after repeated connection errors."
        )
        break

    objects = data.get("objects", [])

    if not objects:
        break

    for item in objects:
        package = item.get("package", {})

        score = item.get("score") or {}
        detail = score.get("detail") or {}

        all_packages.append({
            "name": package.get("name"),
            "description": package.get("description"),
            "version": package.get("version"),
            "date": package.get("date"),
            "keywords": package.get(
                "keywords",
                []
            ),

            "publisher": (
                package.get("publisher")
                or {}
            ).get("username"),

            "links": package.get(
                "links",
                {}
            ),

            "npmScore": score.get("final"),

            "npmPopularity": detail.get(
                "popularity"
            ),

            "npmQuality": detail.get(
                "quality"
            ),

            "npmMaintenance": detail.get(
                "maintenance"
            ),

            "type": "community",
            "official": False,
        })

    offset += len(objects)

    print(
        f"Raw: {len(all_packages)}"
    )

    with open(
        RAW_OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            all_packages,
            f,
            ensure_ascii=False,
            indent=2
        )

    total = data.get(
        "total",
        0
    )

    if offset >= total:
        break

    time.sleep(0.5)


# ----------------------------------------
# Deduplicate packages
# ----------------------------------------

unique = {}

for package in all_packages:
    name = package.get("name")

    if not name:
        continue

    current = unique.get(name)

    if current is None:
        unique[name] = package
        continue

    current_date = (
        current.get("date") or ""
    )

    new_date = (
        package.get("date") or ""
    )

    if new_date > current_date:
        unique[name] = package


unique_packages = sorted(
    unique.values(),
    key=lambda x:
        (x.get("name") or "").lower()
)


with open(
    UNIQUE_OUTPUT,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        unique_packages,
        f,
        ensure_ascii=False,
        indent=2
    )


with_popularity = sum(
    1
    for item in unique_packages
    if item.get("npmPopularity")
    is not None
)


print()
print("=" * 50)
print("COMMUNITY COLLECTION DONE")
print("=" * 50)

print(
    f"Raw records: "
    f"{len(all_packages)}"
)

print(
    f"Unique packages: "
    f"{len(unique_packages)}"
)

print(
    f"Packages with popularity: "
    f"{with_popularity}"
)

print(
    f"Raw saved: "
    f"{RAW_OUTPUT}"
)

print(
    f"Unique saved: "
    f"{UNIQUE_OUTPUT}"
)