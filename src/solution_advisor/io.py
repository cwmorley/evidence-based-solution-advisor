"""File loading and minimal input validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AdvisorDataError(ValueError):
    """Raised when advisor input data is missing or malformed."""


def load_json(path: str | Path) -> Any:
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise AdvisorDataError(f"File not found: {source}") from exc
    except json.JSONDecodeError as exc:
        raise AdvisorDataError(
            f"Invalid JSON in {source} at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def dump_json(data: Any, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def get_path(data: dict[str, Any], dotted_path: str, default: Any = None) -> Any:
    value: Any = data
    for segment in dotted_path.split("."):
        if not isinstance(value, dict) or segment not in value:
            return default
        value = value[segment]
    return value


def load_knowledge_store(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    products_dir = base / "products"
    services_dir = base / "services"
    competitive_dir = base / "competitive-observations"
    rules_dir = base / "rules"

    if not products_dir.is_dir():
        raise AdvisorDataError(f"Missing products directory: {products_dir}")

    products = [load_json(path) for path in sorted(products_dir.glob("*.json"))]
    services = [load_json(path) for path in sorted(services_dir.glob("*.json"))]
    competitive_observations = (
        [load_json(path) for path in sorted(competitive_dir.glob("*.json"))]
        if competitive_dir.is_dir()
        else []
    )
    constraints = load_json(rules_dir / "constraints.json")
    scoring = load_json(rules_dir / "scoring-profile.json")
    questions = load_json(rules_dir / "question-catalog.json")

    for product in products:
        _validate_product(product)
    _validate_unique_ids(products, "product")
    _validate_unique_ids(services, "service")

    return {
        "products": products,
        "services": services,
        "competitive_observations": competitive_observations,
        "constraints": constraints,
        "scoring": scoring,
        "questions": questions,
    }


def validate_intake(intake: dict[str, Any]) -> None:
    for path in ("intake_id", "vertical", "requirements"):
        if path not in intake:
            raise AdvisorDataError(f"Intake is missing required field: {path}")
    if not isinstance(intake["requirements"], dict):
        raise AdvisorDataError("Intake requirements must be an object")


def _validate_product(product: dict[str, Any]) -> None:
    required = (
        "product_id",
        "synthetic",
        "vertical",
        "identity",
        "commercial",
        "specifications",
        "evidence",
    )
    for field in required:
        if field not in product:
            raise AdvisorDataError(
                f"Product {product.get('product_id', '<unknown>')} is missing: {field}"
            )
    identity = product["identity"]
    for field in ("make", "model", "model_number"):
        if not identity.get(field):
            raise AdvisorDataError(
                f"Product {product['product_id']} identity is missing: {field}"
            )


def _validate_unique_ids(records: list[dict[str, Any]], label: str) -> None:
    key = f"{label}_id"
    identifiers = [record.get(key) for record in records]
    duplicates = sorted({item for item in identifiers if identifiers.count(item) > 1})
    if duplicates:
        raise AdvisorDataError(f"Duplicate {label} IDs: {', '.join(duplicates)}")
