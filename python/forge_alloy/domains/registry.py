"""DomainRegistry — domain id string → DomainExtension class lookup.

Mirror of scripts/adapters/registry.py and scripts/eval_runners/registry.py
in sentinel-ai. Same shape: strict exact-match dispatch on the id string,
idempotent registration of the same class, raise on a different class
against an existing id (silent shadowing is the f-word pattern), clear
KeyError listing what IS registered when an unknown id is requested.
"""

from __future__ import annotations

from .base import DomainExtension


class DomainRegistry:
    """id → DomainExtension class lookup."""

    def __init__(self) -> None:
        self._domains: dict[str, type[DomainExtension]] = {}

    def register(self, ext_class: type[DomainExtension]) -> type[DomainExtension]:
        """Register a DomainExtension subclass under its `id` class attribute.

        Idempotent for the same class. Raises ValueError if a DIFFERENT
        class is registered against an existing id (silent override would
        let one extension shadow another and is exactly the kind of
        unfindable-bug surface the no-fallback rule prohibits).
        """
        domain_id = getattr(ext_class, "id", "")
        if not domain_id:
            raise ValueError(
                f"{ext_class.__name__} has no .id class attribute — set it "
                f"to the domain id string this extension answers to."
            )
        existing = self._domains.get(domain_id)
        if existing is not None and existing is not ext_class:
            raise ValueError(
                f"domain id {domain_id!r} is already registered to "
                f"{existing.__name__}; cannot also register {ext_class.__name__}. "
                f"If this is a vocabulary upgrade, register under a NEW id "
                f"so old alloys still resolve to the original extension for "
                f"reproducibility."
            )
        self._domains[domain_id] = ext_class
        return ext_class

    def resolve(self, domain_id: str) -> DomainExtension:
        """Look up the extension for a domain id and instantiate it."""
        ext_class = self._domains.get(domain_id)
        if ext_class is None:
            registered = sorted(self._domains.keys())
            raise KeyError(
                f"no DomainExtension registered for id={domain_id!r}. "
                f"Registered domains: {registered}. To add a new domain, "
                f"create forge_alloy/domains/<id>.py with a DomainExtension "
                f"subclass that sets id = '{domain_id}', then import it "
                f"from forge_alloy/domains/__init__.py."
            )
        return ext_class()

    def domains(self) -> list[str]:
        """All registered domain id strings, sorted."""
        return sorted(self._domains.keys())
