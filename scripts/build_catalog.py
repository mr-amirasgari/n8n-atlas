import json
import re
from pathlib import Path


ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

OFFICIAL_INPUT = DATA / "nodes.json"
COMMUNITY_INPUT = DATA / "community-enriched.json"
COMMUNITY_SEARCH_INPUT = DATA / "community-nodes.json"
ASSETS_INPUT = DATA / "community-assets.json"

OUTPUT = DATA / "catalog.json"


# --------------------------------------------------
# Curated featured integrations
# فقط official n8n-nodes-base
# --------------------------------------------------

FEATURED = [
    ("openai", "OpenAI"),
    ("telegram", "Telegram"),
    ("github", "GitHub"),
    ("postgres", "PostgreSQL"),
    ("slack", "Slack"),
    ("discord", "Discord"),
    ("googlesheets", "Google Sheets"),
    ("gmail", "Gmail"),
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalize_name(value):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        (value or "").lower()
    )


def get_node_kind(display_name, node_path=""):
    text = (
        f"{display_name or ''} "
        f"{node_path or ''}"
    ).lower()

    if "trigger" in text:
        return "trigger"

    return "action"


def get_featured_info(
    display_name,
    package_name,
    source
):
    # Featured را فقط از official nodes-base می‌گیریم
    if source != "official":
        return None

    if package_name != "n8n-nodes-base":
        return None

    normalized = normalize_name(
        display_name
    )

    for rank, (
        expected_name,
        pretty_name
    ) in enumerate(FEATURED):

        if normalized == expected_name:
            return {
                "rank": rank,
                "label": pretty_name,
            }

    return None


def build_catalog():

    official = load_json(
        OFFICIAL_INPUT
    )

    community = load_json(
        COMMUNITY_INPUT
    )

    community_search = load_json(
        COMMUNITY_SEARCH_INPUT
    )

    assets = load_json(
        ASSETS_INPUT
    )


    # --------------------------------------------------
    # Popularity index
    # --------------------------------------------------

    popularity_index = {}

    for package in community_search:

        name = package.get("name")

        if not name:
            continue

        popularity_index[name] = {
            "npmScore":
                package.get(
                    "npmScore"
                ),

            "npmPopularity":
                package.get(
                    "npmPopularity"
                ),

            "npmQuality":
                package.get(
                    "npmQuality"
                ),

            "npmMaintenance":
                package.get(
                    "npmMaintenance"
                ),
        }


    # --------------------------------------------------
    # Asset index
    # --------------------------------------------------

    asset_index = {}

    for item in assets:

        key = (
            item.get("package"),
            item.get("version"),
            item.get("nodePath"),
        )

        asset_index[key] = item


    catalog = []


    # ==================================================
    # OFFICIAL
    # ==================================================

    for item in official:

        name = item.get("name")

        if not name:
            continue

        package = item.get(
            "package",
            "n8n-nodes-base"
        )

        node_path = item.get(
            "path"
        )

        featured_info = (
            get_featured_info(
                name,
                package,
                "official"
            )
        )

        display_name = name

        # برای Featured اسم برند را تمیز نمایش بده
        if featured_info:
            display_name = (
                featured_info["label"]
            )

        catalog.append({

            "id": (
                f"official:"
                f"{package}:"
                f"{name}"
            ),

            "name": name,

            "displayName":
                display_name,

            "source":
                "official",

            "official":
                True,

            "verified":
                True,

            "featured":
                featured_info
                is not None,

            "featuredRank":
                (
                    featured_info["rank"]
                    if featured_info
                    else None
                ),

            "nodeKind":
                get_node_kind(
                    name,
                    node_path
                ),

            "package":
                package,

            "nodePath":
                node_path,

            "description":
                "Official n8n integration.",

            "version":
                None,

            "publisher":
                "n8n",

            "icon":
                None,

            "iconLight":
                None,

            "iconDark":
                None,

            "categories": [
                "Official"
            ],

            "subcategories":
                {},

            "links":
                {},

            "npmScore":
                None,

            "npmPopularity":
                None,

            "npmQuality":
                None,

            "npmMaintenance":
                None,

            "metadataStatus":
                "official",
        })


    # ==================================================
    # COMMUNITY
    # ==================================================

    verified_packages = 0
    skipped_packages = 0

    for package in community:

        package_name = package.get(
            "name"
        )

        version = package.get(
            "version"
        )

        if not package_name:
            continue

        if (
            package.get(
                "metadataStatus"
            ) != "ok"
        ):
            skipped_packages += 1
            continue

        package_nodes = (
            package.get("nodes")
            or []
        )

        if not package_nodes:
            skipped_packages += 1
            continue

        verified_packages += 1


        popularity = (
            popularity_index.get(
                package_name,
                {}
            )
        )


        links = dict(
            package.get("links")
            or {}
        )


        repository = (
            package.get(
                "repository"
            )
        )

        homepage = (
            package.get(
                "homepage"
            )
        )


        if repository:
            links[
                "repository"
            ] = repository

        if homepage:
            links[
                "homepage"
            ] = homepage


        links["npm"] = (
            "https://www.npmjs.com/package/"
            f"{package_name}"
        )


        for index, node in enumerate(
            package_nodes
        ):

            display_name = (
                node.get(
                    "displayName"
                )
            )

            if not display_name:
                continue

            node_path = (
                node.get(
                    "path"
                )
            )


            asset = asset_index.get(
                (
                    package_name,
                    version,
                    node_path,
                ),
                {}
            )


            icon_data = (
                asset.get("icon")
                or {}
            )


            icon_light = (
                icon_data.get(
                    "light"
                )
            )

            icon_dark = (
                icon_data.get(
                    "dark"
                )
            )

            icon = (
                icon_light
                or icon_dark
            )


            categories = (
                asset.get(
                    "categories"
                )
                or []
            )

            subcategories = (
                asset.get(
                    "subcategories"
                )
                or {}
            )


            catalog.append({

                "id": (
                    f"community:"
                    f"{package_name}:"
                    f"{node_path or index}"
                ),

                "name":
                    display_name,

                "displayName":
                    display_name,

                "source":
                    "community",

                "official":
                    False,

                "verified":
                    True,

                # Community هرگز Featured دستی نیست
                "featured":
                    False,

                "featuredRank":
                    None,

                "nodeKind":
                    get_node_kind(
                        display_name,
                        node_path
                    ),

                "package":
                    package_name,

                "nodePath":
                    node_path,

                "description": (
                    package.get(
                        "description"
                    )
                    or
                    "Community integration for n8n."
                ),

                "version":
                    version,

                "publisher":
                    package.get(
                        "publisher"
                    ),

                "license":
                    package.get(
                        "license"
                    ),

                "deprecated":
                    package.get(
                        "deprecated"
                    ),

                "icon":
                    icon,

                "iconLight":
                    icon_light,

                "iconDark":
                    icon_dark,

                "categories":
                    categories,

                "subcategories":
                    subcategories,

                "links":
                    links,

                "npmScore":
                    popularity.get(
                        "npmScore"
                    ),

                "npmPopularity":
                    popularity.get(
                        "npmPopularity"
                    ),

                "npmQuality":
                    popularity.get(
                        "npmQuality"
                    ),

                "npmMaintenance":
                    popularity.get(
                        "npmMaintenance"
                    ),

                "metadataStatus":
                    "verified",
            })


    # --------------------------------------------------
    # Sort main catalog
    # --------------------------------------------------

    catalog.sort(
        key=lambda item: (
            item.get(
                "displayName"
            )
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
        if item["source"]
        == "official"
    )

    community_count = sum(
        1
        for item in catalog
        if item["source"]
        == "community"
    )

    featured_nodes = [
        item
        for item in catalog
        if item.get(
            "featured"
        )
    ]

    popular_count = sum(
        1
        for item in catalog
        if item.get(
            "npmPopularity"
        ) is not None
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
        f"Community nodes: "
        f"{community_count}"
    )

    print(
        f"Featured nodes: "
        f"{len(featured_nodes)}"
    )

    print(
        "Featured:"
    )

    for item in sorted(
        featured_nodes,
        key=lambda x:
            x.get(
                "featuredRank",
                999
            )
    ):
        print(
            f"  - "
            f"{item['displayName']}"
        )

    print(
        f"Nodes with popularity: "
        f"{popular_count}"
    )

    print(
        f"Verified community packages: "
        f"{verified_packages}"
    )

    print(
        f"Skipped packages: "
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

    return catalog


if __name__ == "__main__":
    build_catalog()