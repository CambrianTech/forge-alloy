//! The `package` domain (type byte 0x09): an alloy whose output is a continuum package.
//!
//! A package is named by its ContentId, `sha256:<64 hex>` of its manifest's RFC 8785 bytes.
//! The manifest names every part by digest, so the id commits to every byte at any depth and
//! an alloy that ends in it vouches for the whole tree. Two stages:
//!
//! - `pack`: the chain produced the package `contentId` (kind + schema), made from `inputs`;
//! - `migrate`: a schema migration turned package `from` into package `contentId`. The
//!   original chain still verifies its own link; the migration is a new signed link.
//!
//! [`package_chain`] walks those stages (each `migrate` must continue the id before it);
//! [`verify_package`] checks a manifest's bytes against where the chain ends.

use std::fmt;

use serde::{Deserialize, Deserializer, Serialize, Serializer};
use serde_json::Value;
use sha2::{Digest, Sha256};

#[cfg(feature = "typescript")]
use ts_rs::TS;

use crate::jcs::{canonicalize, CanonicalError};
use crate::AlloyStage;

const PREFIX: &str = "sha256:";

/// A continuum package's id: the sha256 of its manifest's RFC 8785 bytes.
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct ContentId([u8; 32]);

impl ContentId {
    /// The id of these bytes (already canonical: a stored manifest).
    pub fn of(bytes: &[u8]) -> Self {
        Self(Sha256::digest(bytes).into())
    }

    /// The id of a manifest value: sha256 of its RFC 8785 bytes.
    pub fn of_manifest(manifest: &Value) -> Result<Self, CanonicalError> {
        Ok(Self::of(&canonicalize(manifest)?))
    }

    /// Parse `sha256:<64 lowercase hex>`.
    pub fn parse(s: &str) -> Result<Self, PackageError> {
        let bad = || PackageError::BadContentId(s.to_owned());
        let hex = s.strip_prefix(PREFIX).ok_or_else(bad)?;
        if hex.len() != 64 {
            return Err(bad());
        }
        let mut out = [0u8; 32];
        for (i, pair) in hex.as_bytes().chunks(2).enumerate() {
            let nibble = |c: u8| match c {
                b'0'..=b'9' => Some(c - b'0'),
                b'a'..=b'f' => Some(c - b'a' + 10),
                _ => None,
            };
            out[i] = (nibble(pair[0]).ok_or_else(bad)? << 4) | nibble(pair[1]).ok_or_else(bad)?;
        }
        Ok(Self(out))
    }
}

impl fmt::Display for ContentId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(PREFIX)?;
        self.0.iter().try_for_each(|b| write!(f, "{b:02x}"))
    }
}

impl fmt::Debug for ContentId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Display::fmt(self, f)
    }
}

impl Serialize for ContentId {
    fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.collect_str(self)
    }
}

impl<'de> Deserialize<'de> for ContentId {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        let s = String::deserialize(d)?;
        Self::parse(&s).map_err(serde::de::Error::custom)
    }
}

/// The chain produced a continuum package.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct PackStage {
    /// The manifest's kind (e.g. `genome.gene`, `persona`, `kv.page`).
    pub kind: String,
    /// The kind's schema number the manifest was written at.
    pub schema: u32,
    /// The package produced: sha256 of its manifest's RFC 8785 bytes.
    #[cfg_attr(feature = "typescript", ts(type = "string"))]
    pub content_id: ContentId,
    /// Packages it was made from (its lineage), by id.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    #[cfg_attr(feature = "typescript", ts(type = "string[]"))]
    pub inputs: Vec<ContentId>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub notes: Option<String>,
}

/// A schema migration turned one package into another.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "typescript", derive(TS), ts(export))]
#[serde(rename_all = "camelCase")]
pub struct MigrateStage {
    pub kind: String,
    pub from_schema: u32,
    pub to_schema: u32,
    /// The package before the migration.
    #[cfg_attr(feature = "typescript", ts(type = "string"))]
    pub from: ContentId,
    /// The package after it.
    #[cfg_attr(feature = "typescript", ts(type = "string"))]
    pub content_id: ContentId,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub notes: Option<String>,
}

/// Where a package chain ends: the package the alloy vouches for.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PackageHead {
    pub kind: String,
    pub schema: u32,
    pub content_id: ContentId,
}

/// Why a package chain or manifest does not verify.
#[derive(Debug, Clone, PartialEq)]
pub enum PackageError {
    BadContentId(String),
    /// A `migrate` with no package before it.
    MigrateBeforePack { stage: usize },
    /// A `migrate` whose `from` is not the id the chain reached.
    Discontinuous { stage: usize, expected: ContentId, found: ContentId },
    /// A `migrate` of a different kind, or from a schema the chain is not at, or not forward.
    SchemaStep { stage: usize, detail: String },
    /// The alloy has no `pack` stage.
    NoPackage,
    Canonical(CanonicalError),
    ManifestNotJson(String),
    /// The manifest hashes to another id than the chain ends at.
    IdMismatch { expected: ContentId, actual: ContentId },
    /// The manifest's own kind/schema disagree with the chain's last stage.
    ManifestShape { detail: String },
}

impl fmt::Display for PackageError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::BadContentId(s) => write!(f, "{s:?} is not sha256:<64 lowercase hex>"),
            Self::MigrateBeforePack { stage } => {
                write!(f, "stage[{stage}] migrates before any pack stage")
            }
            Self::Discontinuous { stage, expected, found } => write!(
                f,
                "stage[{stage}] migrates {found}, but the chain is at {expected}"
            ),
            Self::SchemaStep { stage, detail } => write!(f, "stage[{stage}]: {detail}"),
            Self::NoPackage => f.write_str("the alloy has no pack stage"),
            Self::Canonical(e) => write!(f, "manifest has no RFC 8785 form: {e}"),
            Self::ManifestNotJson(e) => write!(f, "manifest is not JSON: {e}"),
            Self::IdMismatch { expected, actual } => {
                write!(f, "manifest is {actual}, the chain ends at {expected}")
            }
            Self::ManifestShape { detail } => write!(f, "manifest disagrees with the chain: {detail}"),
        }
    }
}

impl std::error::Error for PackageError {}

/// Walk the `pack` / `migrate` stages in order; return where the package chain ends (None
/// when the alloy has no package stages). A later `pack` starts a new package (its `inputs`
/// carry the lineage); every `migrate` continues the id, kind and schema before it.
pub fn package_chain(stages: &[AlloyStage]) -> Result<Option<PackageHead>, PackageError> {
    let mut head: Option<PackageHead> = None;
    for (stage, s) in stages.iter().enumerate() {
        match s {
            AlloyStage::Pack(p) => {
                head = Some(PackageHead {
                    kind: p.kind.clone(),
                    schema: p.schema,
                    content_id: p.content_id,
                })
            }
            AlloyStage::Migrate(m) => {
                let h = head.as_mut().ok_or(PackageError::MigrateBeforePack { stage })?;
                if m.from != h.content_id {
                    return Err(PackageError::Discontinuous {
                        stage,
                        expected: h.content_id,
                        found: m.from,
                    });
                }
                if m.kind != h.kind || m.from_schema != h.schema || m.to_schema <= m.from_schema {
                    return Err(PackageError::SchemaStep {
                        stage,
                        detail: format!(
                            "{} {}->{} does not continue {} schema {}",
                            m.kind, m.from_schema, m.to_schema, h.kind, h.schema
                        ),
                    });
                }
                h.schema = m.to_schema;
                h.content_id = m.content_id;
            }
            _ => {}
        }
    }
    Ok(head)
}

/// Verify a package manifest (any JSON serialization of it) against the alloy's chain: its
/// RFC 8785 sha256 is where the chain ends, and its own `kind` / `schema` agree.
pub fn verify_package(stages: &[AlloyStage], manifest: &[u8]) -> Result<ContentId, PackageError> {
    let head = package_chain(stages)?.ok_or(PackageError::NoPackage)?;
    let value: Value =
        serde_json::from_slice(manifest).map_err(|e| PackageError::ManifestNotJson(e.to_string()))?;
    let actual = ContentId::of_manifest(&value).map_err(PackageError::Canonical)?;
    if actual != head.content_id {
        return Err(PackageError::IdMismatch { expected: head.content_id, actual });
    }
    let (kind, schema) = (value["kind"].as_str(), value["schema"].as_u64());
    if kind != Some(head.kind.as_str()) || schema != Some(u64::from(head.schema)) {
        return Err(PackageError::ManifestShape {
            detail: format!(
                "manifest is {kind:?} schema {schema:?}, the chain ends at {} schema {}",
                head.kind, head.schema
            ),
        });
    }
    Ok(actual)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    const VECTORS: &str = include_str!("../../test-vectors/jcs.json");
    const TINY_V1: &str = r#"{"fields":{"count":7,"label":"old"},"format":1,"kind":"test.tiny","parts":{},"requires":{"model":{"model":"sha256:1111111111111111111111111111111111111111111111111111111111111111"}},"schema":1}"#;

    fn id(byte: u8) -> ContentId {
        ContentId([byte; 32])
    }

    fn stages(v: Value) -> Vec<AlloyStage> {
        serde_json::from_value(v).unwrap()
    }

    // what this catches: the ContentId rule differing from continuum-pack's: every shared
    // contentIds vector (one is continuum-pack's recorded TINY_V1 manifest, one the same value
    // reordered) hashes to the pinned id here too.
    #[test]
    fn shared_content_id_vectors() {
        let v: Value = serde_json::from_str(VECTORS).unwrap();
        for t in v["contentIds"].as_array().unwrap() {
            let m: Value = serde_json::from_str(t["input"].as_str().unwrap()).unwrap();
            let got = ContentId::of_manifest(&m).unwrap();
            assert_eq!(got.to_string(), t["contentId"].as_str().unwrap(), "{}", t["name"]);
            assert_eq!(ContentId::parse(t["contentId"].as_str().unwrap()).unwrap(), got);
        }
    }

    // what this catches: a malformed id (wrong prefix, uppercase, short) accepted as a name.
    #[test]
    fn content_id_parse_is_strict() {
        for bad in ["sha1:00", "sha256:AB", &format!("sha256:{}", "A".repeat(64)), &"0".repeat(71)] {
            assert!(ContentId::parse(bad).is_err(), "{bad}");
        }
    }

    // what this catches: a pack -> migrate chain that verifies end to end against the real
    // manifest bytes, and each way it must refuse: a migrate that does not continue the id,
    // a schema step backwards, a migrate before any pack, a manifest of another id.
    #[test]
    fn pack_then_migrate_chain_verifies_and_refuses_breaks() {
        let tiny = ContentId::of(TINY_V1.as_bytes());
        let alloy = stages(json!([
            {"type": "pack", "kind": "test.tiny", "schema": 1, "contentId": tiny.to_string(),
             "inputs": [id(3).to_string()]},
        ]));
        assert_eq!(verify_package(&alloy, TINY_V1.as_bytes()).unwrap(), tiny);
        // any serialization of the same manifest value verifies (the id is over JCS bytes).
        let spaced = serde_json::to_vec_pretty(&serde_json::from_str::<Value>(TINY_V1).unwrap()).unwrap();
        assert_eq!(verify_package(&alloy, &spaced).unwrap(), tiny);

        let migrated = stages(json!([
            {"type": "pack", "kind": "test.tiny", "schema": 1, "contentId": tiny.to_string()},
            {"type": "migrate", "kind": "test.tiny", "fromSchema": 1, "toSchema": 2,
             "from": tiny.to_string(), "contentId": id(9).to_string()},
        ]));
        let head = package_chain(&migrated).unwrap().unwrap();
        assert_eq!((head.schema, head.content_id), (2, id(9)));
        assert!(matches!(
            verify_package(&migrated, TINY_V1.as_bytes()),
            Err(PackageError::IdMismatch { .. })
        ));

        let broken = stages(json!([
            {"type": "pack", "kind": "test.tiny", "schema": 1, "contentId": tiny.to_string()},
            {"type": "migrate", "kind": "test.tiny", "fromSchema": 1, "toSchema": 2,
             "from": id(7).to_string(), "contentId": id(9).to_string()},
        ]));
        assert!(matches!(package_chain(&broken), Err(PackageError::Discontinuous { stage: 1, .. })));

        let backwards = stages(json!([
            {"type": "pack", "kind": "test.tiny", "schema": 2, "contentId": tiny.to_string()},
            {"type": "migrate", "kind": "test.tiny", "fromSchema": 2, "toSchema": 1,
             "from": tiny.to_string(), "contentId": id(9).to_string()},
        ]));
        assert!(matches!(package_chain(&backwards), Err(PackageError::SchemaStep { .. })));

        let orphan = stages(json!([
            {"type": "migrate", "kind": "test.tiny", "fromSchema": 1, "toSchema": 2,
             "from": tiny.to_string(), "contentId": id(9).to_string()},
        ]));
        assert!(matches!(package_chain(&orphan), Err(PackageError::MigrateBeforePack { stage: 0 })));

        let wrong_kind = stages(json!([
            {"type": "pack", "kind": "persona", "schema": 1, "contentId": tiny.to_string()},
        ]));
        assert!(matches!(
            verify_package(&wrong_kind, TINY_V1.as_bytes()),
            Err(PackageError::ManifestShape { .. })
        ));
    }
}
