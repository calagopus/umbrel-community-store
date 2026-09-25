#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path

MAX_NOTES = 700

IMAGE_RE = re.compile(
    r"(?P<prefix>image:\s*ghcr\.io/calagopus/panel:)"
    r"(?P<version>\d+(?:\.\d+)*)(?P<variant>-[A-Za-z0-9.-]+?)?(?:@sha256:[0-9a-f]{64})?(?P<eol>[ \t]*$)",
    re.M,
)


def digest(ref: str) -> str:
    out = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", ref, "--format", "{{.Manifest.Digest}}"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", out):
        sys.exit(f"unexpected digest for {ref}: {out!r}")
    return out


def format_notes(body: str, version: str) -> str:
    lines = []
    for line in body.replace("\r", "").splitlines():
        line = line.rstrip()
        if line.startswith("**Full Changelog**"):
            continue
        line = re.sub(r"^#+\s*", "", line)
        lines.append(line)
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    link = f"https://github.com/calagopus/panel/releases/tag/release-{version}"
    if not text:
        return f"See {link}"
    if len(text) > MAX_NOTES:
        text = text[:MAX_NOTES].rsplit("\n", 1)[0].rstrip() + f"\n…\nFull notes: {link}"
    return text


def yaml_block(text: str) -> str:
    body = "\n".join(("  " + l) if l else "" for l in text.split("\n"))
    return f"releaseNotes: |-\n{body}\n"


def main() -> None:
    version, notes_file = sys.argv[1], sys.argv[2]
    notes = format_notes(Path(notes_file).read_text(), version)
    changed = []

    for compose in sorted(Path(".").glob("*/docker-compose.yml")):
        app_dir = compose.parent
        manifest = app_dir / "umbrel-app.yml"
        text = compose.read_text()
        m = IMAGE_RE.search(text)
        if not m or not manifest.exists():
            continue
        if m["version"] == version:
            continue

        tag = f"{version}{m['variant'] or ''}"
        ref = f"ghcr.io/calagopus/panel:{tag}"
        new_image = f"{m['prefix']}{tag}@{digest(ref)}{m['eol']}"
        compose.write_text(text[: m.start()] + new_image + text[m.end():])

        mtext = manifest.read_text()
        mtext, n = re.subn(r'^version:.*$', f'version: "{version}"', mtext, count=1, flags=re.M)
        if n != 1:
            sys.exit(f"no version: key in {manifest}")
        mtext, n = re.subn(r"^releaseNotes:.*?(?=^developer:)", lambda _: yaml_block(notes), mtext, count=1, flags=re.M | re.S)
        if n != 1:
            sys.exit(f"no releaseNotes: key in {manifest}")
        manifest.write_text(mtext)
        changed.append(app_dir.name)

    print("\n".join(changed))


main()
