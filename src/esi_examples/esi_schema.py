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


def fetch_esi_schema(url: str | None = None) -> dict[str, Any]:
    """Fetch the ESI schema from the specified URL.

    Args:
        url (str | None): The URL to fetch the ESI schema from. Defaults to ESI_SCHEMA_URL.

    Returns:
        dict[str, Any]: The parsed JSON schema as a dictionary.
    """
    if url is None:
        url = ESI_SCHEMA_URL
    with httpx2.Client() as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    # argparse cli to script.
    # Features:
    # - Option to specify a custom schema URL (default to ESI_SCHEMA_URL)
    # - Option to specify an output file to save the resolved schema (default to stdout)
    # - default non colorized output, can be used with a pipe. Flag to use rich for colorized output (only if output is stdout)
    # - option to output raw schema, or resolved schema when using plain or rich output to stdout
    # - option to save both version to file, by accepting a output directory. Will use a default file name.
    parser = argparse.ArgumentParser(description="Fetch and resolve the ESI schema.")
    parser.add_argument(
        "--schema-url",
        type=str,
        default=ESI_SCHEMA_URL,
        help="The URL to fetch the ESI schema from (default: %(default)s)",
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
    schema = fetch_esi_schema(args.schema_url)
    resolved_schema = resolve_schema(schema)
    import json
    from yaml import safe_dump

    if args.output_dir:
        output_dir_path = Path(args.output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        raw_path = output_dir_path / (
            "esi_schema_raw.yaml" if args.yaml else "esi_schema_raw.json"
        )
        resolved_path = output_dir_path / (
            "esi_schema_resolved.yaml" if args.yaml else "esi_schema_resolved.json"
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
        print(f"Saved raw schema to {raw_path}")
        print(f"Saved resolved schema to {resolved_path}")
    else:
        output_data = schema if args.raw else resolved_schema

        if args.color:
            from rich.console import Console

            console = Console()
            console.print(f"[bold green]ESI Schema from {args.schema_url}[/bold green]")
            output_format = "YAML" if args.yaml else "JSON"
            console.print(
                f"[bold blue]Outputting {'raw' if args.raw else 'resolved'} schema in {output_format} format[/bold blue]"
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
