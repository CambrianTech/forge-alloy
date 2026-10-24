// RFC 8785 + the package domain against the shared vectors (test-vectors/jcs.json), for both
// TypeScript implementations: src/content-id.ts and the browser verifier's inline block
// (verify/index.html, between JCS-BEGIN and JCS-END), so the page cannot drift from the SDK.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { canonicalize, contentIdOf, packageChain, verifyPackage } from '../src/content-id.ts';

const root = new URL('../../', import.meta.url);
const vectors = JSON.parse(readFileSync(new URL('test-vectors/jcs.json', root), 'utf8'));

type Impl = { name: string; canonicalize: (v: unknown) => string; packageChain: (s: any[]) => any };

function browserImpl(): Impl {
  const html = readFileSync(new URL('verify/index.html', root), 'utf8');
  const block = html.slice(html.indexOf('// JCS-BEGIN'), html.indexOf('// JCS-END'));
  assert.ok(block.length > 100, 'verify/index.html carries the JCS block');
  const api = new Function(block + '\nreturn { jcsCanonicalize, packageChain };')();
  return { name: 'browser verifier', canonicalize: api.jcsCanonicalize, packageChain: api.packageChain };
}

const impls: Impl[] = [{ name: 'content-id.ts', canonicalize, packageChain }, browserImpl()];

function double(bitsHex: string): number {
  const view = new DataView(new ArrayBuffer(8));
  view.setBigUint64(0, BigInt('0x' + bitsHex));
  return view.getFloat64(0);
}

for (const impl of impls) {
  // what this catches: drift from ECMAScript number rendering on RFC 8785 Appendix B.
  test(`${impl.name}: number vectors`, () => {
    for (const v of vectors.numbers) assert.equal(impl.canonicalize(double(v.bits)), v.expected, v.bits);
  });

  // what this catches: member order, escapes and whitespace drifting from Rust and Python.
  test(`${impl.name}: document vectors`, () => {
    for (const v of vectors.documents) assert.equal(impl.canonicalize(JSON.parse(v.input)), v.expected, v.name);
  });

  // what this catches: a migrate that does not continue the chain accepted by either verifier.
  test(`${impl.name}: package chain continuity`, () => {
    const a = 'sha256:' + 'a'.repeat(64), b = 'sha256:' + 'b'.repeat(64);
    const pack = { type: 'pack', kind: 'genome.gene', schema: 1, contentId: a };
    const mig = { type: 'migrate', kind: 'genome.gene', fromSchema: 1, toSchema: 2, from: a, contentId: b };
    assert.deepEqual(impl.packageChain([pack, mig]), { kind: 'genome.gene', schema: 2, contentId: b });
    assert.equal(impl.packageChain([{ type: 'prune' }]), null);
    assert.throws(() => impl.packageChain([pack, { ...mig, from: b }]), /chain is at/);
    assert.throws(() => impl.packageChain([mig]), /before any pack/);
    assert.throws(() => impl.packageChain([pack, { ...mig, toSchema: 1 }]), /does not continue/);
  });
}

// what this catches: a ContentId differing from continuum-pack's and from Rust/Python's.
test('content-id.ts: content id vectors', async () => {
  for (const v of vectors.contentIds) assert.equal(await contentIdOf(JSON.parse(v.input)), v.contentId, v.name);
});

// what this catches: a manifest verified against the wrong id, or a matching id accepted
// for a manifest of another kind.
test('content-id.ts: verifyPackage', async () => {
  const tiny = vectors.contentIds[0];
  const stages = [{ type: 'pack', kind: 'test.tiny', schema: 1, contentId: tiny.contentId }];
  assert.equal(await verifyPackage(stages, JSON.stringify(JSON.parse(tiny.input), null, 2)), tiny.contentId);
  await assert.rejects(verifyPackage([{ ...stages[0], kind: 'persona' }], tiny.input), /schema/);
  await assert.rejects(
    verifyPackage([{ ...stages[0], contentId: 'sha256:' + '0'.repeat(64) }], tiny.input),
    /chain ends at/,
  );
});
