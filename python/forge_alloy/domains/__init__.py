"""forge_alloy.domains — registered vocabularies for the universal core.

Each domain extension is a registered vocabulary for one universe of
data transformation pipelines. Adding a new domain (photo-provenance,
ticketing, delivery, compute-receipt, ...) is exactly one new file in
this package + one import line below. The universal forge_alloy.types
core never changes when a new domain ships.

Architectural rule: NEVER add domain-specific stage types or root
extension fields to forge_alloy/types.py. The dependency direction is
strict: extensions → core, never core → extensions. The bd4349d
checkpoint commit on the domain-extensibility-refactor branch was the
wrong-layered first attempt (ML fields bolted into the universal core);
this package is the correct layer.

Currently registered:
    llm-forge          ML model forging (the morning's qwen3-coder-30b-a3b
                       artifact and the rest of the continuum-ai/* catalog
                       all declare this domain implicitly)
    photo-provenance   stub — camera enclave → edits → publish chain
    ticketing          stub — venue tickets, FedEx delivery, concerts

Stubs exist as witnesses that the registry handles non-ML domains. When
real photo-provenance or ticketing artifacts ship, the stubs get filled
in with concrete Pydantic schemas.
"""

from .base import DomainExtension
from .registry import DomainRegistry

# Module-level singleton — the canonical registry the universal core
# composes its discriminated stage union from at validation time.
_REGISTRY = DomainRegistry()


def register_domain(ext_class: type[DomainExtension]) -> type[DomainExtension]:
    """Register a DomainExtension subclass with the singleton."""
    return _REGISTRY.register(ext_class)


def resolve_domain(domain_id: str) -> DomainExtension:
    """Look up and instantiate the domain extension for an id string.

    Used by the universal core when validating an alloy whose domains[]
    field declares this id. Raises KeyError with a clear message naming
    what IS registered if the id isn't known — loud failure pointing
    at the missing extension file.
    """
    return _REGISTRY.resolve(domain_id)


def registered_domains() -> list[str]:
    """All registered domain id strings, sorted."""
    return _REGISTRY.domains()


# Importing each concrete extension module triggers the register() call
# below. Order doesn't matter; the registry is keyed by id, not by import
# order. NEW domain = new module + new import line + new register() call.
from . import llm_forge          # noqa: E402,F401
from . import photo_provenance   # noqa: E402,F401
from . import ticketing          # noqa: E402,F401

_REGISTRY.register(llm_forge.LlmForgeDomain)
_REGISTRY.register(photo_provenance.PhotoProvenanceDomain)
_REGISTRY.register(ticketing.TicketingDomain)


__all__ = [
    "DomainExtension",
    "DomainRegistry",
    "register_domain",
    "resolve_domain",
    "registered_domains",
]
