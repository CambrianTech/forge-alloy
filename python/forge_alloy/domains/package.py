"""package — an alloy whose output is a continuum package (type byte 0x09).

A continuum package (genes, KV pages, personas, projects: everything a mind
owns) is named by its ContentId, ``sha256:<64 hex>`` of its manifest's
RFC 8785 (JCS) bytes. The manifest names every part by digest, so the id
commits to every byte at any depth, and an alloy whose chain ends in it
vouches for the whole tree. Packages carry their alloy as their provenance
part (media type ``application/vnd.forge-alloy+json``).

Stages:
    pack     the chain produced package ``contentId`` (kind, schema), made
             from ``inputs`` (its lineage, by id)
    migrate  a schema migration turned package ``from`` into ``contentId``;
             the original chain still verifies its own link

``package_chain`` walks those stages; ``verify_package`` checks a manifest
against where the chain ends. Rust (``forge_alloy::package``), TypeScript
(``content-id.ts``) and the browser verifier implement the same rules over
the same shared vectors (``test-vectors/jcs.json``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Union

from ..jcs import content_id
from ..types import CONTENT_ID_PATTERN, ForgeAlloy, MigrateStage, PackStage
from .base import DomainExtension

#: The provenance part's media type inside a continuum package.
PROVENANCE_MEDIA = "application/vnd.forge-alloy+json"

#: The README's domain classification byte for this domain.
TYPE_BYTE = 0x09


class PackageChainError(ValueError):
    """A package chain or manifest that does not verify."""


@dataclass(frozen=True)
class PackageHead:
    """Where a package chain ends: the package the alloy vouches for."""
    kind: str
    schema: int
    content_id: str


def package_chain(stages: Iterable[Any]) -> Optional[PackageHead]:
    """Walk the pack / migrate stages in order and return where the chain ends
    (None when there are none). A later ``pack`` starts a new package (its
    ``inputs`` carry the lineage); every ``migrate`` must continue the id, kind
    and schema before it."""
    head: Optional[PackageHead] = None
    for i, stage in enumerate(stages):
        if isinstance(stage, PackStage):
            head = PackageHead(stage.kind, stage.kind_schema, stage.content_id)
        elif isinstance(stage, MigrateStage):
            if head is None:
                raise PackageChainError(f"stage[{i}] migrates before any pack stage")
            if stage.from_id != head.content_id:
                raise PackageChainError(
                    f"stage[{i}] migrates {stage.from_id}, but the chain is at {head.content_id}")
            if (stage.kind != head.kind or stage.from_schema != head.schema
                    or stage.to_schema <= stage.from_schema):
                raise PackageChainError(
                    f"stage[{i}]: {stage.kind} {stage.from_schema}->{stage.to_schema} "
                    f"does not continue {head.kind} schema {head.schema}")
            head = PackageHead(head.kind, stage.to_schema, stage.content_id)
    return head


def verify_package(alloy: Union[ForgeAlloy, dict], manifest: Union[bytes, str, dict]) -> str:
    """Verify a package manifest (any JSON serialization of it) against the
    alloy's chain: its RFC 8785 sha256 is where the chain ends, and its own
    kind / schema agree. Returns the ContentId."""
    if isinstance(alloy, dict):
        alloy = ForgeAlloy.model_validate(alloy)
    head = package_chain(alloy.stages)
    if head is None:
        raise PackageChainError("the alloy has no pack stage")
    value = manifest if isinstance(manifest, dict) else json.loads(manifest)
    actual = content_id(value)
    if actual != head.content_id:
        raise PackageChainError(f"manifest is {actual}, the chain ends at {head.content_id}")
    if value.get("kind") != head.kind or value.get("schema") != head.schema:
        raise PackageChainError(
            f"manifest is {value.get('kind')!r} schema {value.get('schema')!r}, "
            f"the chain ends at {head.kind!r} schema {head.schema}")
    return actual


class PackageDomain(DomainExtension):
    """The package domain extension. Registered against id 'package'."""

    id = "package"

    def stage_types(self) -> dict[str, type]:
        return {"pack": PackStage, "migrate": MigrateStage}

    def root_extensions(self) -> dict[str, type]:
        return {}


__all__ = [
    "CONTENT_ID_PATTERN",
    "PROVENANCE_MEDIA",
    "TYPE_BYTE",
    "PackageDomain",
    "PackageChainError",
    "PackageHead",
    "PackStage",
    "MigrateStage",
    "package_chain",
    "verify_package",
]
