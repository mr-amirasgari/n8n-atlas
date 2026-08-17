import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

SEARCH_TERM = "keywords:n8n-community-node-package"
PAGE_SIZE = 250
MAX_RETRIES = 6

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT = DATA_DIR / "community-nodes.json"
PROGRESS = DATA_DIR / "community-progress.json"

DATA_DIR.mkdir(exist_ok=True)

# Resume
all_packages = []

if OUTPUT.exists():
    try:
        with open(OUTPUT, "r", encoding="utf-8") as f:
            all_packages = json.load(f)
    except:
        all_packages = []

offset = len(all_packages)

print("Searching npm registry...")
print(f"Starting from: {offset}")

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
                f"Connection error. "
                f"Retry {attempt + 1}/{MAX_RETRIES} "
                f"in {wait}s..."
            )

            print(e)
            time.sleep(wait)

    if data is None:
        print("Failed after retries.")
        print("Progress has been saved.")
        break

    objects = data.get("objects", [])

    if not objects:
        break

    for item in objects:
        package = item.get("package", {})

        all_packages.append({
            "name": package.get("name"),
            "description": package.get("description"),
            "version": package.get("version"),
            "date": package.get("date"),
            "keywords": package.get("keywords", []),
            "publisher": (
                package.get("publisher") or {}
            ).get("username"),
            "links": package.get("links", {}),
            "type": "community",
            "official": False,
        })

    offset += len(objects)

    # ذخیره بعد از هر صفحه
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(
            all_packages,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"Collected: {len(all_packages)}")

    total = data.get("total", 0)

    if offset >= total:
        break

    time.sleep(0.5)

print()
print(f"Done: {len(all_packages)} community packages collected")
print(f"Saved to: {OUTPUT}")