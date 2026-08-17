
import argparse
import hashlib
import io
import json
import posixpath
import re
import tarfile
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
ASSET_DIR = ROOT / "assets" / "icons" / "community"

INPUT = DATA / "community-enriched.json"
OUTPUT = DATA / "community-assets.json"

MAX_WORKERS = 8
MAX_RETRIES = 4
MAX_TARBALL_SIZE = 25 * 1024 * 1024
MAX_SOURCE_SIZE = 2 * 1024 * 1024
MAX_ICON_SIZE = 2 * 1024 * 1024

ALLOWED_ICON_EXTENSIONS = {
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
}

STRING_RE = re.compile(
    r"""(['"`])((?:\\.|(?!\1).)*?)\1""",
    re.DOTALL,
)

ASSET_WRITE_LOCK = threading.Lock()


def fetch(url, accept=None):
    headers = {"User-Agent": "n8n-atlas/1.0"}

    if accept:
        headers["Accept"] = accept

    request = urllib.request.Request(url, headers=headers)
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content_length = response.headers.get("Content-Length")

                if content_length and int(content_length) > MAX_TARBALL_SIZE:
                    raise ValueError("Remote file is too large")

                data = response.read(MAX_TARBALL_SIZE + 1)

                if len(data) > MAX_TARBALL_SIZE:
                    raise ValueError("Downloaded file is too large")

                return data

        except Exception as exc:
            last_error = exc

            if attempt == MAX_RETRIES - 1:
                break

            time.sleep(2 ** attempt)

    raise last_error


def fetch_json(url):
    return json.loads(fetch(url, accept="application/json"))


def extract_balanced(source, start, opening="{", closing="}"):
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False

    i = start

    while i < len(source):
        char = source[i]
        next_char = source[i + 1] if i + 1 < len(source) else ""

        if line_comment:
            if char == "\n":
                line_comment = False
            i += 1
            continue

        if block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                i += 2
                continue
            i += 1
            continue

        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None

            i += 1
            continue

        if char == "/" and next_char == "/":
            line_comment = True
            i += 2
            continue

        if char == "/" and next_char == "*":
            block_comment = True
            i += 2
            continue

        if char in ("'", '"', "`"):
            quote = char
            i += 1
            continue

        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1

            if depth == 0:
                return source[start:i + 1]

        i += 1

    return None


def find_description_object(source):
    patterns = [
        r"\bthis\.description\s*=\s*\{",
        r"\bdescription\s*=\s*\{",
        r"\bdescription\s*:\s*\{",
    ]

    for pattern in patterns:
        match = re.search(pattern, source)

        if not match:
            continue

        start = source.find("{", match.start())

        if start != -1:
            block = extract_balanced(source, start)

            if block:
                return block

    return None


def find_named_object(source, name):
    match = re.search(
        rf"""(?:\b{re.escape(name)}\b|['"]{re.escape(name)}['"])\s*:\s*\{{""",
        source,
    )

    if not match:
        return None

    start = source.find("{", match.start())

    if start == -1:
        return None

    return extract_balanced(source, start)


def parse_js_strings(text):
    values = []

    for match in STRING_RE.finditer(text):
        value = (
            match.group(2)
            .replace("\\'", "'")
            .replace('\\"', '"')
            .replace("\\`", "`")
            .replace("\\n", " ")
            .replace("\\r", " ")
            .replace("\\t", " ")
            .strip()
        )

        if value:
            values.append(value)

    return values


def extract_icon_spec(source):
    description = find_description_object(source)

    if not description:
        return {}

    direct = re.search(
        r"""\bicon\s*:\s*(['"`])(file:[^'"`]+)\1""",
        description,
        re.DOTALL,
    )

    if direct:
        return {"light": direct.group(2)[5:].strip()}

    object_match = re.search(r"\bicon\s*:\s*\{", description)

    if not object_match:
        return {}

    start = description.find("{", object_match.start())
    block = extract_balanced(description, start)

    if not block:
        return {}

    result = {}

    for theme in ("light", "dark"):
        match = re.search(
            rf"""\b{theme}\s*:\s*(['"`])(file:[^'"`]+)\1""",
            block,
            re.DOTALL,
        )

        if match:
            result[theme] = match.group(2)[5:].strip()

    if not result:
        values = re.findall(
            r"""(['"`])file:([^'"`]+)\1""",
            block,
            re.DOTALL,
        )

        if values:
            result["light"] = values[0][1].strip()

    return result


def extract_icon_candidates(source):
    spec = extract_icon_spec(source)
    result = []

    for theme in ("light", "dark"):
        value = spec.get(theme)

        if value and value not in result:
            result.append(value)

    return result


def extract_codex_from_source(source):
    description = find_description_object(source)

    if not description:
        return {
            "categories": [],
            "subcategories": {},
        }

    codex = find_named_object(description, "codex")

    if not codex:
        return {
            "categories": [],
            "subcategories": {},
        }

    categories = []
    category_match = re.search(
        r"\bcategories\s*:\s*\[([^\]]*)\]",
        codex,
        re.DOTALL,
    )

    if category_match:
        categories = parse_js_strings(category_match.group(1))

    subcategories = {}
    sub_block = find_named_object(codex, "subcategories")

    if sub_block:
        pair_re = re.compile(
            r"""(?:(['"])(.*?)\1|([A-Za-z_$][\w$]*))\s*:\s*\[([^\]]*)\]""",
            re.DOTALL,
        )

        for match in pair_re.finditer(sub_block):
            key = match.group(2) or match.group(3)
            values = parse_js_strings(match.group(4))

            if key and values:
                subcategories[key] = values

    return {
        "categories": categories,
        "subcategories": subcategories,
    }


def sanitize_svg(data):
    root = ET.fromstring(data)

    blocked_tags = {
        "script",
        "foreignObject",
        "iframe",
        "object",
        "embed",
    }

    def local_name(value):
        return value.rsplit("}", 1)[-1]

    def clean_element(element):
        for child in list(element):
            if local_name(child.tag) in blocked_tags:
                element.remove(child)
                continue

            clean_element(child)

        for attr in list(element.attrib):
            attr_name = local_name(attr).lower()
            value = element.attrib.get(attr, "")
            lower_value = value.strip().lower()

            if attr_name.startswith("on"):
                del element.attrib[attr]
                continue

            if "javascript:" in lower_value:
                del element.attrib[attr]
                continue

            if attr_name in {"href", "src"}:
                allowed = (
                    lower_value.startswith("#")
                    or lower_value.startswith("data:image/png")
                    or lower_value.startswith("data:image/jpeg")
                    or lower_value.startswith("data:image/webp")
                    or lower_value.startswith("data:image/gif")
                )

                if lower_value and not allowed:
                    del element.attrib[attr]
                    continue

            if attr_name == "style":
                if "javascript:" in lower_value or "url(http" in lower_value:
                    del element.attrib[attr]

        if local_name(element.tag) == "style":
            text = (element.text or "").lower()

            if "@import" in text or "javascript:" in text or "url(http" in text:
                element.text = ""

    clean_element(root)

    return ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=False,
    )


def normalize_tar_path(node_path, icon_path):
    node_path = node_path.replace("\\", "/")
    icon_path = icon_path.replace("\\", "/")

    directory = posixpath.dirname(node_path)
    combined = posixpath.normpath(
        posixpath.join(directory, icon_path)
    )

    if (
        combined.startswith("../")
        or combined == ".."
        or combined.startswith("/")
    ):
        return None

    return f"package/{combined}"


def read_member_bytes(tar, name, max_size):
    try:
        member = tar.getmember(name)
    except KeyError:
        return None

    if not member.isfile() or member.size > max_size:
        return None

    handle = tar.extractfile(member)

    if handle is None:
        return None

    return handle.read()


def read_member_text(tar, name):
    raw = read_member_bytes(tar, name, MAX_SOURCE_SIZE)

    if raw is None:
        return None

    return raw.decode("utf-8", errors="replace")


def codex_path_for_node(node_path):
    normalized = node_path.replace("\\", "/")

    for suffix in (
        ".node.js",
        ".node.ts",
        ".node.mjs",
        ".node.cjs",
    ):
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)] + ".node.json"

    return None


def read_codex(tar, node_path, source):
    codex_path = codex_path_for_node(node_path)

    if codex_path:
        raw = read_member_text(
            tar,
            f"package/{codex_path.lstrip('./')}",
        )

        if raw:
            try:
                data = json.loads(raw)

                categories = data.get("categories") or []
                subcategories = data.get("subcategories") or {}

                if isinstance(categories, list) and isinstance(subcategories, dict):
                    return {
                        "categories": [
                            item
                            for item in categories
                            if isinstance(item, str)
                        ],
                        "subcategories": {
                            key: [
                                item
                                for item in value
                                if isinstance(item, str)
                            ]
                            for key, value in subcategories.items()
                            if isinstance(key, str)
                            and isinstance(value, list)
                        },
                    }
            except json.JSONDecodeError:
                pass

    return extract_codex_from_source(source or "")


def save_icon_asset(raw, source_path):
    extension = Path(source_path).suffix.lower()

    if extension not in ALLOWED_ICON_EXTENSIONS:
        return None

    if len(raw) > MAX_ICON_SIZE:
        return None

    if extension == ".svg":
        try:
            raw = sanitize_svg(raw)
        except ET.ParseError:
            return None

    digest = hashlib.sha256(raw).hexdigest()[:24]
    output = ASSET_DIR / f"{digest}{extension}"

    with ASSET_WRITE_LOCK:
        ASSET_DIR.mkdir(parents=True, exist_ok=True)

        if not output.exists():
            temp = output.with_suffix(output.suffix + ".tmp")
            temp.write_bytes(raw)
            temp.replace(output)

    return output.relative_to(ROOT).as_posix()


def extract_node_assets(tar, package_name, version, node):
    node_path = node.get("path")
    display_name = node.get("displayName")

    result = {
        "package": package_name,
        "version": version,
        "nodePath": node_path,
        "displayName": display_name,
        "icon": {},
        "categories": [],
        "subcategories": {},
        "assetStatus": "no-assets",
    }

    if not node_path:
        result["assetStatus"] = "missing-node-path"
        return result

    normalized_node_path = node_path.replace("\\", "/").lstrip("./")
    source = read_member_text(
        tar,
        f"package/{normalized_node_path}",
    )

    if not source:
        result["assetStatus"] = "missing-node-source"
        return result

    codex = read_codex(tar, normalized_node_path, source)
    result["categories"] = codex.get("categories", [])
    result["subcategories"] = codex.get("subcategories", {})

    icon_spec = extract_icon_spec(source)

    for theme, relative_icon in icon_spec.items():
        tar_path = normalize_tar_path(
            normalized_node_path,
            relative_icon,
        )

        if not tar_path:
            continue

        raw = read_member_bytes(
            tar,
            tar_path,
            MAX_ICON_SIZE,
        )

        if raw is None:
            continue

        saved = save_icon_asset(
            raw,
            relative_icon,
        )

        if saved:
            result["icon"][theme] = saved

    if result["icon"] or result["categories"] or result["subcategories"]:
        result["assetStatus"] = "ok"

    return result


def get_package_metadata(name, version):
    encoded_name = urllib.parse.quote(
        name,
        safe="@",
    )

    return fetch_json(
        f"https://registry.npmjs.org/{encoded_name}/{version}"
    )


def process_package(package):
    name = package.get("name")
    version = package.get("version")
    nodes = package.get("nodes") or []

    if not name or not version:
        return []

    metadata = get_package_metadata(name, version)
    tarball_url = (metadata.get("dist") or {}).get("tarball")

    if not tarball_url:
        return [
            {
                "package": name,
                "version": version,
                "nodePath": node.get("path"),
                "displayName": node.get("displayName"),
                "icon": {},
                "categories": [],
                "subcategories": {},
                "assetStatus": "missing-tarball",
            }
            for node in nodes
            if node.get("displayName")
        ]

    blob = fetch(tarball_url)

    with tarfile.open(
        fileobj=io.BytesIO(blob),
        mode="r:gz",
    ) as tar:
        return [
            extract_node_assets(
                tar,
                name,
                version,
                node,
            )
            for node in nodes
            if node.get("displayName")
        ]


def save_results(results):
    DATA.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".tmp")

    ordered = sorted(
        results,
        key=lambda item: (
            (item.get("package") or "").lower(),
            (item.get("displayName") or "").lower(),
            item.get("nodePath") or "",
        ),
    )

    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(
            ordered,
            handle,
            ensure_ascii=False,
            indent=2,
        )

    temp.replace(OUTPUT)


def main():
    parser = argparse.ArgumentParser(
        description="Extract safe local icons and categories from n8n community nodes."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N packages.",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS,
    )

    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore cached community-assets.json.",
    )

    args = parser.parse_args()

    if not INPUT.exists():
        raise SystemExit(f"Missing input: {INPUT}")

    with open(INPUT, encoding="utf-8") as handle:
        packages = json.load(handle)

    packages = [
        package
        for package in packages
        if package.get("metadataStatus") == "ok"
        and package.get("nodes")
    ]

    if args.limit:
        packages = packages[: args.limit]

    cached = {}

    if OUTPUT.exists() and not args.fresh and not args.limit:
        try:
            with open(OUTPUT, encoding="utf-8") as handle:
                previous = json.load(handle)

            cached = {
                (
                    item.get("package"),
                    item.get("version"),
                    item.get("nodePath"),
                ): item
                for item in previous
            }
        except Exception:
            cached = {}

    pending_packages = []
    results = []
    cached_nodes = 0

    for package in packages:
        package_nodes = [
            node
            for node in package.get("nodes", [])
            if node.get("displayName")
        ]

        all_cached = bool(package_nodes)

        for node in package_nodes:
            key = (
                package.get("name"),
                package.get("version"),
                node.get("path"),
            )

            if key in cached:
                results.append(cached[key])
                cached_nodes += 1
            else:
                all_cached = False

        if not all_cached:
            pending_packages.append(package)

    print(f"Packages: {len(packages)}")
    print(f"Cached nodes: {cached_nodes}")
    print(f"Pending packages: {len(pending_packages)}")
    print(f"Workers: {args.workers}")
    print()

    completed_packages = 0

    with ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:
        futures = {
            executor.submit(process_package, package): package
            for package in pending_packages
        }

        for future in as_completed(futures):
            package = futures[future]

            try:
                package_results = future.result()
            except Exception as exc:
                package_results = [
                    {
                        "package": package.get("name"),
                        "version": package.get("version"),
                        "nodePath": node.get("path"),
                        "displayName": node.get("displayName"),
                        "icon": {},
                        "categories": [],
                        "subcategories": {},
                        "assetStatus": "error",
                        "assetError": f"{type(exc).__name__}: {exc}",
                    }
                    for node in package.get("nodes", [])
                    if node.get("displayName")
                ]

            results.extend(package_results)
            completed_packages += 1

            ok = sum(
                1
                for item in package_results
                if item.get("assetStatus") == "ok"
            )

            icons = sum(
                1
                for item in package_results
                if item.get("icon")
            )

            print(
                f"[{completed_packages}/{len(pending_packages)}] "
                f"{package.get('name')} -> "
                f"{ok} metadata, {icons} icons"
            )

            if not args.limit and completed_packages % 25 == 0:
                save_results(results)

    save_results(results)

    icon_nodes = sum(1 for item in results if item.get("icon"))
    categorized_nodes = sum(
        1 for item in results
        if item.get("categories")
    )
    errors = sum(
        1 for item in results
        if item.get("assetStatus") == "error"
    )

    print()
    print("=" * 50)
    print("ASSET EXTRACTION DONE")
    print("=" * 50)
    print(f"Nodes: {len(results)}")
    print(f"Nodes with icons: {icon_nodes}")
    print(f"Categorized nodes: {categorized_nodes}")
    print(f"Errors: {errors}")
    print(f"Saved: {OUTPUT}")
    print(f"Icons: {ASSET_DIR}")


if __name__ == "__main__":
    main()
