import json
from pathlib import Path


ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

OFFICIAL_INPUT = DATA / "nodes.json"
COMMUNITY_INPUT = DATA / "community-enriched.json"
OUTPUT = DATA / "catalog.json"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


official = load_json(OFFICIAL_INPUT)
community = load_json(COMMUNITY_INPUT)

catalog = []


# --------------------------------------------------
# Official nodes
# --------------------------------------------------

for item in official:
    name = item.get("name")

    if not name:
        continue

    package = item.get(
        "package",
        "n8n-nodes-base"
    )

    catalog.append({
        "id": (
            f"official:"
            f"{package}:"
            f"{name}"
        ),

        "name": name,
        "displayName": name,

        "source": "official",
        "official": True,
        "verified": True,

        "package": package,

        "nodePath": item.get("path"),

        "description": (
            "Official n8n integration."
        ),

        "version": None,

        "publisher": "n8n",

        "links": {},

        "metadataStatus": "official",
    })


# --------------------------------------------------
# Community nodes
# --------------------------------------------------

community_node_count = 0
verified_package_count = 0
skipped_packages = 0


for package in community:

    package_name = package.get("name")

    if not package_name:
        continue

    display_names = package.get(
        "displayNames",
        []
    )

    nodes = package.get(
        "nodes",
        []
    )

    # فقط پکیج‌هایی که اسم واقعی استخراج شده
    if (
        package.get("metadataStatus") != "ok"
        or not display_names
    ):
        skipped_packages += 1
        continue

    verified_package_count += 1

    package_links = dict(
        package.get("links") or {}
    )

    # لینک‌های enrichment
    repository = package.get(
        "repository"
    )

    homepage = package.get(
        "homepage"
    )

    if repository:
        package_links[
            "repository"
        ] = repository

    if homepage:
        package_links[
            "homepage"
        ] = homepage

    # لینک npm همیشه موجود باشد
    package_links[
        "npm"
    ] = (
        "https://www.npmjs.com/package/"
        f"{package_name}"
    )

    for index, node in enumerate(nodes):

        display_name = node.get(
            "displayName"
        )

        # Nodeهایی که اسم واقعی ندارند
        # در سایت نمایش داده نمی‌شوند
        if not display_name:
            continue

        node_path = node.get(
            "path"
        )

        node_id = (
            f"community:"
            f"{package_name}:"
            f"{node_path or index}"
        )

        catalog.append({
            "id": node_id,

            "name": display_name,
            "displayName": display_name,

            "source": "community",
            "official": False,
            "verified": True,

            "package": package_name,

            "nodePath": node_path,

            "description": (
                package.get("description")
                or "Community integration for n8n."
            ),

            "version": package.get(
                "version"
            ),

            "publisher": package.get(
                "publisher"
            ),

            "license": package.get(
                "license"
            ),

            "deprecated": package.get(
                "deprecated"
            ),

            "links": package_links,

            "metadataStatus": "verified",
        })

        community_node_count += 1


# --------------------------------------------------
# Sort
# --------------------------------------------------

catalog.sort(
    key=lambda item: (
        item.get("displayName")
        or ""
    ).lower()
)


# --------------------------------------------------
# Save
# --------------------------------------------------

with open(
    OUTPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        catalog,
        f,
        ensure_ascii=False,
        indent=2
    )


# --------------------------------------------------
# Stats
# --------------------------------------------------

official_count = sum(
    1
    for item in catalog
    if item["source"] == "official"
)

community_count = sum(
    1
    for item in catalog
    if item["source"] == "community"
)


print()
print("=" * 50)
print("CATALOG BUILT")
print("=" * 50)

print(
    f"Official nodes: "
    f"{official_count}"
)

print(
    f"Verified community packages: "
    f"{verified_package_count}"
)

print(
    f"Community nodes: "
    f"{community_count}"
)

print(
    f"Skipped community packages: "
    f"{skipped_packages}"
)

print(
    f"Total catalog: "
    f"{len(catalog)}"
)

print(
    f"Saved to: "
    f"{OUTPUT}"
)