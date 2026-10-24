/**
 * RFC 8785 (JCS) and the `package` domain (type byte 0x09).
 *
 * JCS is the one bytes rule an alloy signs and a continuum package is named by:
 * members sorted by UTF-16 code units, numbers as ECMAScript renders them,
 * minimal string escapes, no whitespace. A package's ContentId is
 * `sha256:<64 hex>` of its manifest's JCS bytes. Rust, Python and the browser
 * verifier implement the same rules over test-vectors/jcs.json.
 */

/** `sha256:<64 lowercase hex>` */
export type ContentId = string;

export const CONTENT_ID_PATTERN = /^sha256:[0-9a-f]{64}$/;

/** The provenance part's media type inside a continuum package. */
export const PROVENANCE_MEDIA = 'application/vnd.forge-alloy+json';

/** The chain produced a continuum package, named by its ContentId. */
export interface PackStage {
  type: 'pack';
  kind: string;
  schema: number;
  contentId: ContentId;
  inputs?: ContentId[];
  notes?: string;
}

/** A schema migration turned package `from` into package `contentId`. */
export interface MigrateStage {
  type: 'migrate';
  kind: string;
  fromSchema: number;
  toSchema: number;
  from: ContentId;
  contentId: ContentId;
  notes?: string;
}

export interface PackageHead {
  kind: string;
  schema: number;
  contentId: ContentId;
}

/** The RFC 8785 text of a JSON value (encode as UTF-8 for the bytes). */
export function canonicalize(value: unknown): string {
  if (value === null || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error(`${value} has no JSON form`);
    return JSON.stringify(value); // ECMAScript Number::toString, -0 -> "0"
  }
  if (typeof value === 'string') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonicalize).join(',') + ']';
  if (typeof value === 'object') {
    const o = value as Record<string, unknown>;
    // Array.prototype.sort compares UTF-16 code units: exactly the RFC order.
    const keys = Object.keys(o).filter((k) => o[k] !== undefined).sort();
    return '{' + keys.map((k) => JSON.stringify(k) + ':' + canonicalize(o[k])).join(',') + '}';
  }
  throw new Error(`${typeof value} is not a JSON value`);
}

/** sha256 of the value's JCS bytes, as a ContentId. */
export async function contentIdOf(value: unknown): Promise<ContentId> {
  const bytes = new TextEncoder().encode(canonicalize(value));
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
  return 'sha256:' + Array.from(digest, (b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Walk the pack / migrate stages; return where the package chain ends (null
 * when there are none). Every migrate must continue the id, kind and schema
 * before it; a later pack starts a new package (its inputs carry the lineage).
 */
export function packageChain(stages: ReadonlyArray<{ type: string }>): PackageHead | null {
  let head: PackageHead | null = null;
  for (let i = 0; i < stages.length; i++) {
    const s = stages[i];
    if (s.type === 'pack') {
      const p = s as PackStage;
      if (!CONTENT_ID_PATTERN.test(p.contentId)) throw new Error(`stage[${i}] contentId ${p.contentId} is malformed`);
      head = { kind: p.kind, schema: p.schema, contentId: p.contentId };
    } else if (s.type === 'migrate') {
      const m = s as MigrateStage;
      if (!CONTENT_ID_PATTERN.test(m.contentId)) throw new Error(`stage[${i}] contentId ${m.contentId} is malformed`);
      if (head === null) throw new Error(`stage[${i}] migrates before any pack stage`);
      if (m.from !== head.contentId) throw new Error(`stage[${i}] migrates ${m.from}, but the chain is at ${head.contentId}`);
      if (m.kind !== head.kind || m.fromSchema !== head.schema || m.toSchema <= m.fromSchema) {
        throw new Error(`stage[${i}]: ${m.kind} ${m.fromSchema}->${m.toSchema} does not continue ${head.kind} schema ${head.schema}`);
      }
      head = { kind: head.kind, schema: m.toSchema, contentId: m.contentId };
    }
  }
  return head;
}

/** Verify a manifest (any serialization) against the chain; returns its ContentId. */
export async function verifyPackage(stages: ReadonlyArray<{ type: string }>, manifestJson: string): Promise<ContentId> {
  const head = packageChain(stages);
  if (head === null) throw new Error('the alloy has no pack stage');
  const manifest = JSON.parse(manifestJson) as { kind?: unknown; schema?: unknown };
  const actual = await contentIdOf(manifest);
  if (actual !== head.contentId) throw new Error(`manifest is ${actual}, the chain ends at ${head.contentId}`);
  if (manifest.kind !== head.kind || manifest.schema !== head.schema) {
    throw new Error(`manifest is ${String(manifest.kind)} schema ${String(manifest.schema)}, the chain ends at ${head.kind} schema ${head.schema}`);
  }
  return actual;
}
