"""TDD spec for the forge_alloy domain-extension package layout.

Roadmap step 5 from sentinel-ai/docs/PLUGIN-SPRINT.md and the schema-side
proposal in continuum/docs/architecture/FORGE-ALLOY-DOMAIN-EXTENSIBILITY.md:
move every ML-specific stage type and root extension out of the universal
forge_alloy.types core and into a forge_alloy.domains.llm_forge extension.
The universal core stays domain-agnostic (suitable for photo provenance,
ticketing, delivery, compute receipts — any data transformation pipeline,
not just ML model forging).

Written test-first per TDD/TDValidation discipline. The contract this
test asserts IS the spec the refactor must satisfy. The bd4349d
checkpoint commit on this branch is the wrong-layered first attempt
(ML fields bolted into the universal core); the wip preservation branch
wip/types-additive-checkpoint-bd4349d holds it for the never-lose-work rule.

This test runs offline against the existing forge_alloy package — no
network, no model loading, no external services.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python"))


# ── domains/ package exists ─────────────────────────────────────────────────


def test_domains_package_is_importable():
    """forge_alloy.domains MUST be a package (directory with __init__.py).

    The mechanism for registering and resolving domain extensions lives
    here. Each ML / non-ML use case gets its own module under this
    package and registers via the package-level registry.
    """
    pkg = importlib.import_module("forge_alloy.domains")
    assert pkg is not None
    assert hasattr(pkg, "__path__"), "forge_alloy.domains must be a package, not a module"


def test_domain_registry_is_importable():
    """The DomainRegistry singleton + its helpers MUST be importable."""
    from forge_alloy.domains import (
        DomainRegistry,
        register_domain,
        resolve_domain,
        registered_domains,
    )
    assert DomainRegistry is not None
    assert callable(register_domain)
    assert callable(resolve_domain)
    assert callable(registered_domains)


def test_domain_extension_base_class_exists():
    """The DomainExtension ABC defines the contract every registered
    domain must satisfy. At minimum it carries an `id` (the string the
    alloy's domains[] field carries) and a method to enumerate the
    stage types this domain owns."""
    from forge_alloy.domains.base import DomainExtension
    assert hasattr(DomainExtension, "id")
    assert hasattr(DomainExtension, "stage_types")


# ── llm_forge domain extension ──────────────────────────────────────────────


def test_llm_forge_domain_module_is_importable():
    """forge_alloy.domains.llm_forge MUST be importable. This module owns
    every ML-specific stage type and root extension (the things that used
    to be bolted into types.py via the bd4349d checkpoint)."""
    mod = importlib.import_module("forge_alloy.domains.llm_forge")
    assert mod is not None


def test_llm_forge_is_registered():
    """The llm-forge domain MUST be registered against the singleton on
    package import. resolve_domain('llm-forge') returns the extension."""
    from forge_alloy.domains import resolve_domain
    ext = resolve_domain("llm-forge")
    assert ext is not None
    assert ext.id == "llm-forge"


def test_llm_forge_owns_the_ml_stage_types():
    """Every ML stage type MUST be owned by the llm_forge domain extension.
    These are the stage types the morning's flagship qwen3-coder-30b-a3b
    alloy uses + the stage types the rest of the published catalog uses."""
    from forge_alloy.domains import resolve_domain
    ext = resolve_domain("llm-forge")
    owned = set(ext.stage_types().keys())
    # The morning's MoE flagship uses these stage types
    expected = {
        "prune",
        "train",
        "lora",
        "expert-prune",
        "expert-activation-profile",
        "compensation-lora",
        "context-extend",
        "modality",
        "quant",
        "eval",
        "publish",
        "package",
        "deploy",
        "deliver",
        "source-config",
    }
    missing = expected - owned
    assert not missing, (
        f"llm-forge domain extension is missing stage types: {sorted(missing)}. "
        f"Owned: {sorted(owned)}"
    )


def test_llm_forge_exposes_priormetricbaseline():
    """The §4.1.3.4 falsifiability anchor structure (PriorMetricBaseline)
    is an ML-specific concept and MUST live in the llm_forge domain
    extension, NOT in the universal core."""
    from forge_alloy.domains.llm_forge import PriorMetricBaseline
    assert PriorMetricBaseline is not None


def test_llm_forge_exposes_calibration_corpus_ref():
    """Calibration corpus reference is the §4.1.3.4.1 discipline gate
    structure. ML-specific. Must live in the llm_forge extension."""
    from forge_alloy.domains.llm_forge import CalibrationCorpusRef
    assert CalibrationCorpusRef is not None


def test_llm_forge_exposes_expert_prune_stage():
    """Expert pruning is the §4.1.3.4 mechanism. Must live in llm_forge."""
    from forge_alloy.domains.llm_forge import ExpertPruneStage
    assert ExpertPruneStage is not None


# ── Stub domain extensions to prove the mechanism is non-ML ─────────────────


def test_photo_provenance_stub_is_importable():
    """forge_alloy.domains.photo_provenance MUST be importable as a stub
    that proves the registry mechanism handles non-ML domains. The actual
    schema is empty for now — the point is that adding a non-ML domain
    is one new file, no edits to the universal core."""
    mod = importlib.import_module("forge_alloy.domains.photo_provenance")
    assert mod is not None


def test_photo_provenance_is_registered():
    from forge_alloy.domains import resolve_domain
    ext = resolve_domain("photo-provenance")
    assert ext is not None
    assert ext.id == "photo-provenance"


def test_ticketing_stub_is_importable():
    """Same proof for the ticketing domain — non-ML, registered, separate
    file. Adding a new domain is never a core edit."""
    mod = importlib.import_module("forge_alloy.domains.ticketing")
    assert mod is not None


def test_ticketing_is_registered():
    from forge_alloy.domains import resolve_domain
    ext = resolve_domain("ticketing")
    assert ext is not None
    assert ext.id == "ticketing"


def test_registered_domains_lists_all_three():
    """The singleton MUST know about all three domains after package import:
    llm-forge (the real one), photo-provenance + ticketing (the stubs).
    Adding a new domain is one new file plus one import in
    forge_alloy/domains/__init__.py."""
    from forge_alloy.domains import registered_domains
    domains = set(registered_domains())
    expected = {"llm-forge", "photo-provenance", "ticketing"}
    missing = expected - domains
    assert not missing, (
        f"registered_domains() missing: {sorted(missing)}. "
        f"Got: {sorted(domains)}"
    )


# ── Registry behavior contract ──────────────────────────────────────────────


def test_resolve_unknown_domain_raises_clearly():
    """Unknown domain id MUST raise with a message naming what IS
    registered. Loud failure, no silent default to llm-forge."""
    from forge_alloy.domains import resolve_domain
    with pytest.raises((KeyError, ValueError)) as exc_info:
        resolve_domain("not-a-real-domain")
    msg = str(exc_info.value)
    assert "not-a-real-domain" in msg
    assert "llm-forge" in msg, "error must list registered domains"


def test_register_different_class_against_same_id_raises():
    """Re-registering a DIFFERENT extension class against an existing id
    MUST raise. Silent shadowing is the f-word pattern — one domain
    extension shadowing another would silently change the schema for
    every alloy that declares that domain."""
    from forge_alloy.domains import DomainRegistry
    from forge_alloy.domains.base import DomainExtension

    class FirstExt(DomainExtension):
        id = "shared-id"
        def stage_types(self):
            return {}
        def root_extensions(self):
            return {}

    class SecondExt(DomainExtension):
        id = "shared-id"
        def stage_types(self):
            return {}
        def root_extensions(self):
            return {}

    reg = DomainRegistry()
    reg.register(FirstExt)
    reg.register(FirstExt)  # idempotent same class
    with pytest.raises(ValueError) as exc_info:
        reg.register(SecondExt)
    assert "shared-id" in str(exc_info.value)


# ── Universal core hygiene ──────────────────────────────────────────────────


def test_universal_core_does_not_import_llm_forge():
    """forge_alloy.types (the universal core) MUST NOT import anything
    from the llm_forge domain extension. The dependency direction is
    extensions → core, never core → extensions. Otherwise the universal
    core becomes ML-locked again, defeating the purpose of the domain
    package.

    This test parses types.py source and checks for any import of
    forge_alloy.domains.* — would catch a refactor that accidentally
    introduces a back-import.
    """
    types_src = (REPO_ROOT / "python" / "forge_alloy" / "types.py").read_text()
    forbidden_imports = [
        "from forge_alloy.domains",
        "from .domains",
        "import forge_alloy.domains",
    ]
    for forbidden in forbidden_imports:
        assert forbidden not in types_src, (
            f"forge_alloy/types.py contains forbidden import {forbidden!r}. "
            f"The universal core must not depend on any domain extension; "
            f"the dependency direction is extensions → core, never core → extensions."
        )
