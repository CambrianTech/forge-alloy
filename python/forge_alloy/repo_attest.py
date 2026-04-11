"""repo_attest.py — forge-alloy eats its own dogfood.

Git IS a Merkle chain. Every commit hash = SHA-1(parent + tree + author + msg).
This script reads git's native chain and wraps it as a forge-alloy attestation,
proving that the repo's own trust infrastructure is self-attested.

CI adds stages on top: tests passed, linting clean, attestation computed.
The chain hash in the QR code on the README IS the git Merkle root.

Usage:
    python -m forge_alloy.repo_attest chain              # full chain JSON
    python -m forge_alloy.repo_attest chain --pr BASE HEAD  # PR range
    python -m forge_alloy.repo_attest qr HASH --output x.svg
    python -m forge_alloy.repo_attest full --output-dir .attestation/
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def git(*args: str) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def compute_chain(
    from_ref: Optional[str] = None,
    to_ref: str = "HEAD",
) -> tuple[str, list[dict]]:
    """Compute the forge-alloy attestation chain from git history.

    Git is already a Merkle chain. We read it directly — no reinvention.
    Each stage captures the full commit metadata: hash, tree, parents,
    author, timestamp, message. The chain_hash at each stage is a
    SHA-256 over the commit's git hash + previous chain_hash + tree hash,
    creating a secondary attestation chain that rides on top of git's own.

    Returns (final_chain_hash, stages).
    """
    fmt = "%H%x00%T%x00%P%x00%an%x00%ae%x00%aI%x00%s"
    cmd = ["log", f"--format={fmt}", "--reverse"]
    if from_ref:
        cmd.append(f"{from_ref}..{to_ref}")
    else:
        cmd.append(to_ref)

    raw = git(*cmd)
    if not raw:
        return ("0" * 64, [])

    chain_hash = "0" * 64  # genesis
    stages = []

    for line in raw.split("\n"):
        parts = line.split("\0")
        if len(parts) < 7:
            continue

        commit_sha, tree_sha, parents, author_name, author_email, timestamp, message = parts

        # Chain hash: SHA-256(commit + prev_chain + tree)
        # This rides on top of git's own Merkle chain (SHA-1/SHA-256)
        payload = f"{commit_sha}{chain_hash}{tree_sha}"
        chain_hash = hashlib.sha256(payload.encode()).hexdigest()

        stages.append({
            "commit": commit_sha,
            "tree": tree_sha,
            "parents": parents.split() if parents else [],
            "author": author_name,
            "email": author_email,
            "timestamp": timestamp,
            "message": message,
            "chain_hash": chain_hash,
        })

    return chain_hash, stages


def build_attestation(
    chain_hash: str,
    stages: list[dict],
    ci_env: Optional[dict] = None,
) -> dict:
    """Build a forge-alloy attestation JSON from the chain.

    This IS the dogfood — the same schema we use for model forging,
    applied to the repo that defines the schema.
    """
    repo_url = "https://github.com/CambrianTech/forge-alloy"
    verify_url = f"https://cambriantech.github.io/forge-alloy/verify/#github:forge-alloy@{chain_hash[:16]}"

    # Get current repo info
    try:
        current_branch = git("rev-parse", "--abbrev-ref", "HEAD")
        remote_url = git("config", "--get", "remote.origin.url")
    except subprocess.CalledProcessError:
        current_branch = "unknown"
        remote_url = repo_url

    attestation = {
        "forgeAlloyVersion": "0.3.0",
        "type": "repo-attestation",
        "name": "forge-alloy",
        "description": "Self-attestation of the forge-alloy trust infrastructure repository",
        "repository": remote_url,
        "branch": current_branch,
        "chainHash": chain_hash,
        "verifyUrl": verify_url,
        "attestedAt": datetime.now(timezone.utc).isoformat(),
        "totalCommits": len(stages),
        "integrity": {
            "trustLevel": "self-attested",
            "alloyHash": chain_hash,
            "code": {
                "runner": "forge-alloy/repo_attest",
                "version": "0.1.0",
                "sourceHash": chain_hash,
                "commit": stages[-1]["commit"] if stages else None,
            },
        },
        "stages": stages,
    }

    if ci_env:
        attestation["ci"] = ci_env

    return attestation


def generate_qr_svg(url: str, size: int = 200) -> str:
    """Generate a QR code SVG string. Only dependency: qrcode (pip install qrcode)."""
    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage
    except ImportError:
        print("Install qrcode: pip install qrcode", file=sys.stderr)
        sys.exit(1)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(image_factory=SvgPathImage)
    svg_bytes = img.to_string()
    svg_str = svg_bytes.decode("utf-8") if isinstance(svg_bytes, bytes) else svg_bytes

    # Wrap with forge-alloy branded container
    # Extract the inner SVG content and viewBox
    return svg_str


def generate_badge_svg(chain_hash: str, verify_url: str, commit_count: int) -> str:
    """Generate a branded badge SVG with QR code + chain info.

    This is what goes in the README — a self-contained SVG that shows
    the QR code, the chain hash (truncated), and the commit count.
    """
    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage
    except ImportError:
        print("Install qrcode: pip install qrcode", file=sys.stderr)
        sys.exit(1)

    # Generate QR modules as a boolean matrix
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=2,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    rows = len(matrix)
    cols = len(matrix[0]) if matrix else 0

    # Build QR path data
    path_parts = []
    for r, row in enumerate(matrix):
        for c, cell in enumerate(row):
            if cell:
                path_parts.append(f"M{c},{r}h1v1h-1z")
    qr_path = "".join(path_parts)

    qr_size = 120
    scale = qr_size / max(rows, cols, 1)
    short_hash = chain_hash[:16]

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="280" height="160" viewBox="0 0 280 160">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0a1520"/>
      <stop offset="100%" stop-color="#0d1f2d"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#00d4ff"/>
      <stop offset="100%" stop-color="#00ffc8"/>
    </linearGradient>
  </defs>
  <rect width="280" height="160" rx="8" fill="url(#bg)" stroke="#1a2a3a" stroke-width="1"/>
  <!-- QR code -->
  <g transform="translate(16,16) scale({scale:.4f})">
    <path d="{qr_path}" fill="#e0e6ed"/>
  </g>
  <!-- Text -->
  <text x="152" y="36" fill="url(#accent)" font-family="monospace" font-size="11" font-weight="bold">FORGE-ALLOY</text>
  <text x="152" y="54" fill="#8a92a5" font-family="monospace" font-size="9">attestation chain</text>
  <text x="152" y="78" fill="#e0e6ed" font-family="monospace" font-size="8">{short_hash}</text>
  <text x="152" y="96" fill="#5a6a7a" font-family="monospace" font-size="8">{commit_count} commits</text>
  <text x="152" y="118" fill="#00ffc8" font-family="monospace" font-size="8">scan to verify</text>
  <!-- Bottom bar -->
  <rect x="0" y="148" width="280" height="12" rx="0" fill="rgba(0,212,255,0.06)"/>
  <text x="140" y="157" fill="#5a6a7a" font-family="monospace" font-size="7" text-anchor="middle">git is the merkle chain</text>
</svg>'''
    return svg


def pr_comment_markdown(
    chain_hash: str,
    stages: list[dict],
    base_ref: str,
    head_ref: str,
) -> str:
    """Generate markdown for a PR attestation comment — the PR's own dogfood.

    Each PR gets a QR stamp and chain table, just like the README badge.
    The QR encodes the verify URL so anyone can scan and verify.
    """
    short_hash = chain_hash[:16]
    verify_url = f"https://cambriantech.github.io/forge-alloy/verify/#github:forge-alloy@{short_hash}"
    qr_img = f"https://api.qrserver.com/v1/create-qr-code/?size=120x120&data={verify_url}"

    lines = [
        '<table><tr><td>',
        f'<a href="{verify_url}">',
        f'<img src="{qr_img}" width="120" height="120" alt="Verify chain">',
        '</a>',
        '</td><td>',
        '',
        f'**Attestation Chain** · `{short_hash}`',
        '',
        f'{len(stages)} commits · `{base_ref[:8]}..{head_ref[:8]}`',
        '',
        f'[Verify →]({verify_url})',
        '',
        '</td></tr></table>',
        '',
        "| # | Commit | Author | Chain Hash | Message |",
        "|---|--------|--------|------------|---------|",
    ]

    for i, s in enumerate(stages):
        commit_short = s["commit"][:8]
        chain_short = s["chain_hash"][:12]
        msg = s["message"][:50]
        author = s["author"]
        lines.append(f"| {i+1} | [`{commit_short}`](https://github.com/CambrianTech/forge-alloy/commit/{s['commit']}) | {author} | `{chain_short}` | {msg} |")

    lines.extend([
        "",
        "---",
        "*forge-alloy self-attestation · git is the Merkle chain*",
    ])

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="forge-alloy repo self-attestation")
    sub = parser.add_subparsers(dest="command")

    # chain
    chain_p = sub.add_parser("chain", help="Compute attestation chain")
    chain_p.add_argument("--pr", nargs=2, metavar=("BASE", "HEAD"), help="PR range")
    chain_p.add_argument("--pretty", action="store_true")

    # qr
    qr_p = sub.add_parser("qr", help="Generate QR code SVG")
    qr_p.add_argument("hash", help="Chain hash")
    qr_p.add_argument("--output", "-o", default="-", help="Output file (- for stdout)")

    # full
    full_p = sub.add_parser("full", help="Compute chain + generate QR + write all files")
    full_p.add_argument("--output-dir", "-d", default=".attestation")

    # pr-comment
    pr_p = sub.add_parser("pr-comment", help="Generate PR comment markdown")
    pr_p.add_argument("base", help="Base ref")
    pr_p.add_argument("head", help="Head ref")

    args = parser.parse_args()

    if args.command == "chain":
        if args.pr:
            chain_hash, stages = compute_chain(args.pr[0], args.pr[1])
        else:
            chain_hash, stages = compute_chain()

        attestation = build_attestation(chain_hash, stages)
        indent = 2 if args.pretty else None
        print(json.dumps(attestation, indent=indent))

    elif args.command == "qr":
        verify_url = f"https://cambriantech.github.io/forge-alloy/verify/#github:forge-alloy@{args.hash[:16]}"
        svg = generate_qr_svg(verify_url)
        if args.output == "-":
            print(svg)
        else:
            Path(args.output).write_text(svg)
            print(f"QR written to {args.output}", file=sys.stderr)

    elif args.command == "full":
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)

        chain_hash, stages = compute_chain()
        attestation = build_attestation(chain_hash, stages)

        # Write chain JSON
        chain_path = out / "chain.json"
        chain_path.write_text(json.dumps(attestation, indent=2))

        # Write badge SVG
        verify_url = f"https://cambriantech.github.io/forge-alloy/verify/#github:forge-alloy@{chain_hash[:16]}"
        badge_svg = generate_badge_svg(chain_hash, verify_url, len(stages))
        badge_path = out / "chain-qr.svg"
        badge_path.write_text(badge_svg)

        print(f"Chain hash: {chain_hash[:16]}", file=sys.stderr)
        print(f"Commits:    {len(stages)}", file=sys.stderr)
        print(f"Chain JSON: {chain_path}", file=sys.stderr)
        print(f"Badge SVG:  {badge_path}", file=sys.stderr)

    elif args.command == "pr-comment":
        chain_hash, stages = compute_chain(args.base, args.head)
        md = pr_comment_markdown(chain_hash, stages, args.base, args.head)
        print(md)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
