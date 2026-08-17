import argparse
import io
import json
import re
import tarfile
import time
import urllib.parse
import urllib.request

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

INPUT = DATA / "community-nodes.json"
OUTPUT = DATA / "community-enriched.json"

MAX_WORKERS = 8
MAX_RETRIES = 4

MAX_TARBALL_SIZE = 25 * 1024 * 1024
MAX_FILE_SIZE = 2 * 1024 * 1024


DISPLAY_NAME_RE = re.compile(
    r"""displayName\s*:\s*(['"`])((?:\\.|(?!\1).)*?)\1""",
    re.DOTALL,
)


def fetch(url, accept=None):
    headers = {
        "User-Agent": "n8n-atlas/1.0"
    }

    if accept:
        headers["Accept"] = accept

    request = urllib.request.Request(
        url,
        headers=headers
    )

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:

                content_length = response.headers.get(
                    "Content-Length"
                )

                if content_length:
                    if int(content_length) > MAX_TARBALL_SIZE:
                        raise ValueError(
                            "Remote file is too large"
                        )

                data = response.read(
                    MAX_TARBALL_SIZE + 1
                )

                if len(data) > MAX_TARBALL_SIZE:
                    raise ValueError(
                        "Downloaded file is too large"
                    )

                return data

        except Exception as e:
            last_error = e

            if attempt == MAX_RETRIES - 1:
                break

            wait = 2 ** attempt

            time.sleep(wait)

    raise last_error


def fetch_json(url):
    raw = fetch(
        url,
        accept="application/json"
    )

    return json.loads(raw)


def clean_js_string(value):
    value = (
        value
        .replace("\\'", "'")
        .replace('\\"', '"')
        .replace("\\n", " ")
        .replace("\\r", " ")
        .replace("\\t", " ")
        .replace("\\`", "`")
        .strip()
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value


def is_valid_display_name(value):
    if not value:
        return False

    if len(value) > 80:
        return False

    if "${" in value:
        return False

    if "\n" in value:
        return False

    if value.count(" ") > 12:
        return False

    suspicious = [
        "response format",
        "make sure to",
        "you must",
        "prompt in your",
        "select latest models",
        "description",
    ]

    lower_value = value.lower()

    for text in suspicious:
        if text in lower_value:
            return False

    return True


def find_description_object(source):
    patterns = [
        r"\bthis\.description\s*=\s*\{",
        r"\bdescription\s*=\s*\{",
        r"\bdescription\s*:\s*\{",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            source
        )

        if not match:
            continue

        brace_position = source.find(
            "{",
            match.start()
        )

        if brace_position == -1:
            continue

        block = extract_balanced_object(
            source,
            brace_position
        )

        if block:
            return block

    return None


def extract_balanced_object(source, start):
    depth = 0

    quote = None
    escaped = False

    line_comment = False
    block_comment = False

    i = start

    while i < len(source):
        char = source[i]

        next_char = (
            source[i + 1]
            if i + 1 < len(source)
            else ""
        )

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

        if char == "{":
            depth += 1

        elif char == "}":
            depth -= 1

            if depth == 0:
                return source[start:i + 1]

        i += 1

    return None


def extract_display_name(source):
    description = find_description_object(
        source
    )

    if not description:
        return None

    match = DISPLAY_NAME_RE.search(
        description
    )

    if not match:
        return None

    value = clean_js_string(
        match.group(2)
    )

    if not is_valid_display_name(value):
        return None

    return value


def safe_tar_member(name):
    normalized = name.replace(
        "\\",
        "/"
    )

    if normalized.startswith("/"):
        return False

    parts = normalized.split("/")

    if ".." in parts:
        return False

    return True


def read_member(tar, name):
    if not safe_tar_member(name):
        return None

    try:
        member = tar.getmember(name)

    except KeyError:
        return None

    if not member.isfile():
        return None

    if member.size > MAX_FILE_SIZE:
        return None

    file = tar.extractfile(member)

    if file is None:
        return None

    raw = file.read()

    return raw.decode(
        "utf-8",
        errors="replace"
    )


def analyze_tarball(blob):
    result = {
        "nodes": [],
        "displayNames": [],
        "metadataStatus": "unknown",
    }

    try:
        tar = tarfile.open(
            fileobj=io.BytesIO(blob),
            mode="r:gz"
        )

    except Exception:
        result["metadataStatus"] = "invalid-tarball"
        return result

    with tar:

        package_text = read_member(
            tar,
            "package/package.json"
        )

        if not package_text:
            result["metadataStatus"] = (
                "missing-package-json"
            )

            return result

        try:
            package_json = json.loads(
                package_text
            )

        except json.JSONDecodeError:
            result["metadataStatus"] = (
                "invalid-package-json"
            )

            return result

        n8n_config = package_json.get(
            "n8n",
            {}
        )

        node_paths = n8n_config.get(
            "nodes",
            []
        )

        if not isinstance(node_paths, list):
            result["metadataStatus"] = (
                "invalid-n8n-nodes"
            )

            return result

        if not node_paths:
            result["metadataStatus"] = (
                "no-n8n-nodes"
            )

            return result

        for node_path in node_paths:

            if not isinstance(
                node_path,
                str
            ):
                continue

            clean_path = (
                node_path
                .replace("\\", "/")
                .lstrip("./")
            )

            tar_path = (
                f"package/{clean_path}"
            )

            source = read_member(
                tar,
                tar_path
            )

            display_name = None

            if source:
                display_name = (
                    extract_display_name(
                        source
                    )
                )

            node_info = {
                "path": node_path,
                "displayName": display_name,
                "verified": bool(
                    display_name
                ),
            }

            result["nodes"].append(
                node_info
            )

            if (
                display_name
                and display_name
                not in result["displayNames"]
            ):
                result[
                    "displayNames"
                ].append(
                    display_name
                )

        if result["displayNames"]:
            result["metadataStatus"] = "ok"

        else:
            result["metadataStatus"] = (
                "no-display-name"
            )

    return result


def get_package_metadata(
    name,
    version
):
    encoded_name = urllib.parse.quote(
        name,
        safe="@"
    )

    url = (
        "https://registry.npmjs.org/"
        f"{encoded_name}/{version}"
    )

    return fetch_json(url)


def enrich(package):
    name = package.get("name")
    version = package.get("version")

    record = dict(package)

    if not name or not version:
        record["metadataStatus"] = (
            "invalid-package"
        )

        return record

    try:
        metadata = get_package_metadata(
            name,
            version
        )

        dist = metadata.get(
            "dist",
            {}
        )

        tarball_url = dist.get(
            "tarball"
        )

        if not tarball_url:
            record["metadataStatus"] = (
                "missing-tarball"
            )

            return record

        blob = fetch(
            tarball_url
        )

        analysis = analyze_tarball(
            blob
        )

        record.update(
            analysis
        )

        repository = metadata.get(
            "repository"
        )

        if isinstance(
            repository,
            dict
        ):
            repository = repository.get(
                "url"
            )

        record[
            "repository"
        ] = repository

        record[
            "homepage"
        ] = metadata.get(
            "homepage"
        )

        record[
            "license"
        ] = metadata.get(
            "license"
        )

        record[
            "deprecated"
        ] = metadata.get(
            "deprecated"
        )

        return record

    except Exception as e:
        record["metadataStatus"] = "error"

        record["metadataError"] = (
            f"{type(e).__name__}: {e}"
        )

        return record


def save_results(results):
    temp_output = OUTPUT.with_suffix(
        ".tmp"
    )

    sorted_results = sorted(
        results,
        key=lambda x:
        (
            x.get("name")
            or ""
        ).lower()
    )

    with open(
        temp_output,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            sorted_results,
            f,
            ensure_ascii=False,
            indent=2
        )

    temp_output.replace(
        OUTPUT
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extract real n8n display names "
            "from community npm packages."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS
    )

    parser.add_argument(
        "--fresh",
        action="store_true"
    )

    args = parser.parse_args()

    if not INPUT.exists():
        print(
            f"Missing input file: {INPUT}"
        )

        return

    with open(
        INPUT,
        encoding="utf-8"
    ) as f:
        packages = json.load(f)

    if args.limit:
        packages = packages[
            :args.limit
        ]

    existing = {}

    if (
        OUTPUT.exists()
        and not args.fresh
        and not args.limit
    ):
        try:
            with open(
                OUTPUT,
                encoding="utf-8"
            ) as f:
                previous = json.load(f)

            existing = {
                (
                    item.get("name"),
                    item.get("version"),
                ): item
                for item in previous
            }

        except Exception:
            existing = {}

    results = []
    pending = []

    for package in packages:

        key = (
            package.get("name"),
            package.get("version"),
        )

        if key in existing:
            results.append(
                existing[key]
            )

        else:
            pending.append(
                package
            )

    print()
    print(
        f"Total packages: {len(packages)}"
    )

    print(
        f"Cached: {len(results)}"
    )

    print(
        f"Pending: {len(pending)}"
    )

    print(
        f"Workers: {args.workers}"
    )

    print()

    with ThreadPoolExecutor(
        max_workers=args.workers
    ) as executor:

        futures = {
            executor.submit(
                enrich,
                package
            ): package
            for package in pending
        }

        completed = len(results)

        for future in as_completed(
            futures
        ):
            try:
                result = future.result()

            except Exception as e:
                package = futures[
                    future
                ]

                result = dict(
                    package
                )

                result[
                    "metadataStatus"
                ] = "error"

                result[
                    "metadataError"
                ] = str(e)

            results.append(
                result
            )

            completed += 1

            name = result.get(
                "name"
            )

            names = result.get(
                "displayNames",
                []
            )

            status = result.get(
                "metadataStatus"
            )

            if names:
                output_text = ", ".join(
                    names
                )

            else:
                output_text = status

            print(
                f"[{completed}/{len(packages)}] "
                f"{name} -> "
                f"{output_text}"
            )

            if (
                not args.limit
                and completed % 25 == 0
            ):
                save_results(
                    results
                )

    save_results(
        results
    )

    verified_packages = sum(
        1
        for item in results
        if item.get(
            "metadataStatus"
        ) == "ok"
    )

    verified_nodes = sum(
        len(
            item.get(
                "displayNames",
                []
            )
        )
        for item in results
    )

    failed = sum(
        1
        for item in results
        if item.get(
            "metadataStatus"
        ) == "error"
    )

    print()
    print("=" * 50)
    print("DONE")
    print("=" * 50)

    print(
        f"Packages: {len(results)}"
    )

    print(
        f"Verified packages: "
        f"{verified_packages}"
    )

    print(
        f"Verified nodes: "
        f"{verified_nodes}"
    )

    print(
        f"Errors: {failed}"
    )

    print(
        f"Saved to: {OUTPUT}"
    )


if __name__ == "__main__":
    main()