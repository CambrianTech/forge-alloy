"""DomainExtension ABC — the contract every forge-alloy domain extension satisfies.

A domain extension is a registered vocabulary for one universe of data
transformation pipelines:

    llm-forge          ML model forging (prune, train, expert-prune, quant, eval, ...)
    photo-provenance   Camera enclave → edits → publish chain (capture, edit, publish)
    ticketing          Venue ticket batches (issued, transferred, scanned)
    delivery           Package waypoints (picked-up, in-transit, delivered)
    compute-receipt    Grid job receipts (job-submitted, completed, attested)

The universal forge-alloy core knows nothing about any specific domain.
It enforces the Merkle chain-of-custody walk and the integrity attestation
surface. The vocabulary for "what stages exist" comes from the registered
domain extensions, not from the core.

Each extension owns:
    - id:                a string the alloy's domains[] field carries
    - stage_types():     dict of stage type name → Pydantic model class
                         (the schemas the alloy's stages[] entries validate against)
    - root_extensions(): dict of root field name → Pydantic model class
                         (additional fields this domain adds at the alloy root)

Concrete extensions live in sibling files: llm_forge.py, photo_provenance.py,
ticketing.py, etc. Each registers itself with the singleton in __init__.py
on package import.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DomainExtension(ABC):
    """Abstract base for one domain's vocabulary."""

    # Subclass MUST set this — the string the alloy's domains[] field carries.
    # Examples: 'llm-forge', 'photo-provenance', 'ticketing', 'delivery'.
    id: str = ""

    @abstractmethod
    def stage_types(self) -> dict[str, type]:
        """Return the stage type registry for this domain.

        Maps stage type strings (the alloy's stages[].type field) to
        Pydantic model classes that validate the stage's params. The
        universal core's discriminated stage union is composed from
        the union of every registered domain's stage_types().
        """
        ...

    @abstractmethod
    def root_extensions(self) -> dict[str, type]:
        """Return the root-extension field registry for this domain.

        Maps root field names (e.g. 'priorMetricBaselines',
        'calibrationCorpora') to Pydantic model classes. These fields
        are additions to the alloy root that this domain owns; the
        universal core ignores them.
        """
        ...

    def __repr__(self) -> str:
        return f"<{type(self).__name__} id={self.id!r}>"
