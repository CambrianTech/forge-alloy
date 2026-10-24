"""The `package` domain: pack / migrate stages name a continuum package by its
ContentId, and the chain verifies against the manifest itself."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "python"))

from forge_alloy.domains import registered_domains, resolve_domain  # noqa: E402
from forge_alloy.domains.package import PackageChainError, package_chain, verify_package  # noqa: E402
from forge_alloy.types import ForgeAlloy, MigrateStage, PackStage  # noqa: E402

VECTORS = json.loads((REPO_ROOT / "test-vectors" / "jcs.json").read_text(encoding="utf-8"))
TINY_V1 = VECTORS["contentIds"][0]["input"]
TINY_ID = VECTORS["contentIds"][0]["contentId"]
OTHER = "sha256:" + "9" * 64


def alloy(*stages):
    return {
        "name": "gene-test", "version": "1.0.0", "cycles": 1,
        "source": {"baseModel": "Qwen/Qwen3.5-4B", "architecture": "qwen3_5"},
        "stages": list(stages),
        "outputs": {"produces": [{"type": "package", "contentId": TINY_ID}]},
    }


PACK = {"type": "pack", "kind": "test.tiny", "schema": 1, "contentId": TINY_ID, "inputs": [OTHER]}


# what this catches: the domain not registered, or its stage vocabulary missing.
def test_package_domain_is_registered_with_pack_and_migrate():
    assert "package" in registered_domains()
    assert set(resolve_domain("package").stage_types()) == {"pack", "migrate"}


# what this catches: pack / migrate not in the stage union, or their wire names
# (schema, from, contentId) not round-tripping.
def test_stages_parse_and_round_trip():
    raw = alloy(PACK, {"type": "migrate", "kind": "test.tiny", "fromSchema": 1,
                       "toSchema": 2, "from": TINY_ID, "contentId": OTHER})
    a = ForgeAlloy.model_validate(raw)
    assert isinstance(a.stages[0], PackStage) and isinstance(a.stages[1], MigrateStage)
    out = a.model_dump(by_alias=True, exclude_unset=True)
    assert out["stages"] == raw["stages"]
    assert out["outputs"]["produces"][0]["contentId"] == TINY_ID


# what this catches: a malformed id accepted as a package name.
@pytest.mark.parametrize("bad", ["sha256:AB", "sha1:" + "0" * 64, "sha256:" + "A" * 64])
def test_bad_content_id_is_rejected(bad):
    with pytest.raises(Exception):
        ForgeAlloy.model_validate(alloy({**PACK, "contentId": bad}))


# what this catches: a chain that verifies against the real manifest (any
# serialization), and each break it must refuse.
def test_chain_verifies_and_refuses_breaks():
    assert verify_package(alloy(PACK), TINY_V1) == TINY_ID
    assert verify_package(alloy(PACK), json.dumps(json.loads(TINY_V1), indent=2)) == TINY_ID

    migrated = ForgeAlloy.model_validate(alloy(PACK, {
        "type": "migrate", "kind": "test.tiny", "fromSchema": 1, "toSchema": 2,
        "from": TINY_ID, "contentId": OTHER}))
    head = package_chain(migrated.stages)
    assert (head.schema, head.content_id) == (2, OTHER)
    with pytest.raises(PackageChainError, match="chain ends at"):
        verify_package(migrated, TINY_V1)

    for broken in (
        [PACK, {"type": "migrate", "kind": "test.tiny", "fromSchema": 1, "toSchema": 2,
                "from": OTHER, "contentId": OTHER}],                       # discontinuous
        [PACK, {"type": "migrate", "kind": "test.tiny", "fromSchema": 1, "toSchema": 1,
                "from": TINY_ID, "contentId": OTHER}],                     # not forward
        [{"type": "migrate", "kind": "test.tiny", "fromSchema": 1, "toSchema": 2,
          "from": TINY_ID, "contentId": OTHER}],                           # before pack
    ):
        with pytest.raises(PackageChainError):
            package_chain(ForgeAlloy.model_validate(alloy(*broken)).stages)

    with pytest.raises(PackageChainError, match="disagrees|schema"):
        verify_package(alloy({**PACK, "kind": "persona"}), TINY_V1)
