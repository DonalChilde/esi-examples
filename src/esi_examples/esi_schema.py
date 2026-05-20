# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "httpx2>=2.0.0",
#     "pyyaml>=6.0.3",
#     "rich>=15.0.0",
# ]
#
# [tool.uv]
# exclude-newer = "7 days"
# ///
import argparse
from typing import Any
import httpx2
from pathlib import Path
from datetime import datetime, UTC


ESI_SCHEMA_URL = "https://esi.evetech.net/meta/openapi.json"
"""The URL to download the ESI schema from."""


def _resolve_internal_refs(parent: dict[str, Any], child: Any) -> Any:
    """Recursively resolve internal JSON references ($ref) in a child object.

    Using the provided parent object as the reference root.

    Args:
        parent (dict[str, Any]): The full parent JSON object.
        child (Any): The child subsection to resolve.

    Returns:
        Any: The child object with all internal references resolved.

    Example:
        >>> parent = {
        ...     "components": {
        ...         "schemas": {"A": {"type": "object"}, "B": {"$ref": "#/components/schemas/A"}}
        ...     }
        ... }
        >>> child = parent["components"]["schemas"]["B"]
        >>> _resolve_internal_refs(parent, child)
        {'type': 'object'}
    """

    def _resolve(obj):
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_path = obj["$ref"]
                if not ref_path.startswith("#/"):
                    raise ValueError(f"Only internal refs supported, got: {ref_path}")
                # Split and traverse the parent object
                parts = ref_path.lstrip("#/").split("/")
                ref_obj = parent
                for part in parts:
                    ref_obj = ref_obj[part]
                # Recursively resolve the referenced object
                return _resolve(ref_obj)
            else:
                # Recursively resolve all dict values
                return {k: _resolve(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_resolve(item) for item in obj]
        else:
            return obj

    return _resolve(child)


def resolve_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Resolve all internal JSON references ($ref) in the provided schema.

    Args:
        schema (dict[str, Any]): The original JSON schema with potential $ref references.
    Returns:
        dict[str, Any]: The schema with all internal references resolved.
    """
    return _resolve_internal_refs(schema, schema)


def verify_compatibility_date(date_str: str | None) -> str:
    """Verify the provided compatibility date string is in the correct format (YYYY-MM-DD).

    Args:
        date_str (str|None): The compatibility date string to verify.
    Returns:
        str: The verified compatibility date string, or the current date in UTC if None was provided.
    Raises:
        ValueError: If the provided date string is not in the correct format.
    """
    if date_str is not None:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            raise ValueError(
                f"Invalid compatibility date format: {date_str}. Expected format: YYYY-MM-DD"
            )
    else:
        return datetime.now(UTC).strftime("%Y-%m-%d")


def fetch_esi_schema(
    url: str | None = None, compatibility_date: str | None = None
) -> dict[str, Any]:
    """Fetch the ESI schema from the specified URL.

    Args:
        url (str | None): The URL to fetch the ESI schema from. Defaults to ESI_SCHEMA_URL.
        compatibility_date (str | None): The compatibility date for the ESI schema. Defaults to current date UTC. If provided, will attempt to fetch the schema from the ESI schema archive for that date (format: YYYY-MM-DD).

    Returns:
        dict[str, Any]: The parsed JSON schema as a dictionary.
    """
    compatibility_date = verify_compatibility_date(compatibility_date)
    if url is None:
        url = ESI_SCHEMA_URL
    with httpx2.Client() as client:
        response = client.get(url, params={"compatibility_date": compatibility_date})
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and resolve the ESI schema.")
    parser.add_argument(
        "--schema-url",
        type=str,
        default=ESI_SCHEMA_URL,
        help="The URL to fetch the ESI schema from (default: %(default)s)",
    )
    parser.add_argument(
        "--compatibility-date",
        type=str,
        default=None,
        help="The compatibility date for the ESI schema. Defaults to current date UTC. If provided, will attempt to fetch the schema from the ESI schema archive for that date (format: YYYY-MM-DD).",
    )
    parser.add_argument(
        "--color",
        action="store_true",
        help="Use rich for colorized output (only if output is stdout)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output the raw schema instead of the resolved schema when using plain or rich output to stdout",
    )
    parser.add_argument(
        "--yaml",
        action="store_true",
        help="Output the schemas in YAML format instead of JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="The directory to save both raw and resolved schemas to (default: None). Outputs to file instead of stdout with default file names.",
    )
    args = parser.parse_args()
    requested_compatibility_date = verify_compatibility_date(args.compatibility_date)
    schema = fetch_esi_schema(args.schema_url, requested_compatibility_date)
    fetch_timestamp = str(datetime.now(UTC).timestamp())
    reported_compatibility_date = schema.get("info", {}).get("version", "unknown")
    resolved_schema = resolve_schema(schema)
    import json
    from yaml import safe_dump

    if args.output_dir:
        print(
            f"Requested latest ESI schema with compatibility date: {requested_compatibility_date}"
        )
        print(
            f"Received ESI schema with reported compatibility date: {reported_compatibility_date}"
        )
        output_dir_path = Path(args.output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        raw_path = output_dir_path / (
            f"esi_schema_raw-{reported_compatibility_date}-{fetch_timestamp}.yaml"
            if args.yaml
            else f"esi_schema_raw-{reported_compatibility_date}-{fetch_timestamp}.json"
        )
        resolved_path = output_dir_path / (
            f"esi_schema_resolved-{reported_compatibility_date}-{fetch_timestamp}.yaml"
            if args.yaml
            else f"esi_schema_resolved-{reported_compatibility_date}-{fetch_timestamp}.json"
        )
        with open(raw_path, "w") as f:
            if args.yaml:
                safe_dump(schema, f)
            else:
                json.dump(schema, f, indent=2)
        with open(resolved_path, "w") as f:
            if args.yaml:
                safe_dump(resolved_schema, f)
            else:
                json.dump(resolved_schema, f, indent=2)
        print(f"Saved raw schema to {raw_path.resolve()}")
        print(f"Saved resolved schema to {resolved_path.resolve()}")
    else:
        output_data = schema if args.raw else resolved_schema

        if args.color:
            from rich.console import Console

            console = Console()
            console.print(f"[bold green]ESI Schema from {args.schema_url} for requested Compatibility Date: {requested_compatibility_date}[/bold green]")
            output_format = "YAML" if args.yaml else "JSON"
            console.print(
                f"[bold blue]Outputting {'raw' if args.raw else 'resolved'} schema in {output_format} format with received Compatibility Date: {reported_compatibility_date}[/bold blue]"
            )
            if args.yaml:
                from rich.syntax import Syntax

                output_str = safe_dump(output_data)
                console.print(Syntax(output_str, "yaml"))
                parser.exit(0)
            from rich.json import JSON

            console.print(JSON.from_data(output_data))
            parser.exit(0)
        else:
            if args.yaml:
                print(safe_dump(output_data))
            else:
                print(json.dumps(output_data, indent=2))
