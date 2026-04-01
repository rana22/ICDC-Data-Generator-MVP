from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml, os

from dotenv import dotenv_values, load_dotenv

load_dotenv()
print("SKIP_FIELDS =", os.getenv("SKIP_FIELDS"))

@dataclass(frozen=True)
class PropertySchema:
    name: str
    description: str = ""
    type: str | None = None
    enum: list[str] = field(default_factory=list)
    required: bool | str | None = None
    tags: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        parts = [self.name.replace("_", " ")]
        if self.description:
            parts.append(self.description)
        if self.enum:
            # parts.append(" ".join(self.enum[:20]))
            parts.append(" ".join(str(v) for v in self.enum[:20]))
        return "\n".join(parts)


@dataclass(frozen=True)
class NodeSchema:
    name: str
    description: str = ""
    properties: dict[str, PropertySchema] = field(default_factory=dict)
    exclude_like: list[str] = field(default_factory=list)

    def property_names(self) -> list[str]:
        return list(self.properties.keys())

    def property_texts(self) -> dict[str, str]:
        return {name: prop.text for name, prop in self.properties.items()}


def load_node_schema(path: str | Path, nodes) -> NodeSchema:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    node_name = raw.get("node", "sample")
    description = raw.get("description", "")
    exclude_like = raw.get("exclude_like", []) or []

    properties: dict[str, PropertySchema] = {}
    for prop_name, spec in (raw.get("properties", {}) or {}).items():
        properties[prop_name] = PropertySchema(
            name=prop_name,
            description=spec.get("description", "") or "",
            type=spec.get("type"),
            enum=list(spec.get("enum", []) or []),
            required=spec.get("required"),
            tags=dict(spec.get("tags", {}) or {}),
        )

    return NodeSchema(
        name=node_name,
        description=description,
        properties=properties,
        exclude_like=[str(x) for x in exclude_like],
    )

def load_nodes_schema(nodes: list[str]) -> list[NodeSchema]:
    schemas: list[NodeSchema] = []
    base_path = Path(os.environ["ICDC_SCHEMA_OUTPUT_DIR"])

    for node in nodes:
        rp_node = f"{node}".replace(" ", "_")
        path = base_path / f"{rp_node}_node.yaml"

        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        node_name = raw.get("node", "sample")
        description = raw.get("description", "")
        exclude_like = raw.get("exclude_like", []) or []

        properties: dict[str, PropertySchema] = {}
        for prop_name, spec in (raw.get("properties", {}) or {}).items():
            properties[prop_name] = PropertySchema(
                name=prop_name,
                description=spec.get("description", "") or "",
                type=spec.get("type"),
                enum=list(spec.get("enum", []) or []),
                required=spec.get("required"),
                tags=dict(spec.get("tags", {}) or {}),
            )

        schemas.append(NodeSchema(
            name=node_name,
            description=description,
            properties=properties,
            exclude_like=[str(x) for x in exclude_like],
        ))
    return schemas