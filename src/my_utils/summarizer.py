# src/my_utils/summarizer.py
from __future__ import annotations
import argparse, mimetypes, os, sys, textwrap
from pathlib import Path

try:
    from pathspec import PathSpec
    from pathspec.patterns import GitWildMatchPattern
except ImportError:
    print("Missing dependency: pathspec.  pip install pathspec", file=sys.stderr)
    sys.exit(1)

MAX_BYTES = 100_000  # skip giant binaries by default

def load_gitignore(repo_root: Path) -> PathSpec:
    gitignore = repo_root / ".gitignore"
    if not gitignore.exists():
        return PathSpec.from_lines(GitWildMatchPattern, [])
    return PathSpec.from_lines(GitWildMatchPattern, gitignore.read_text().splitlines())

def is_binary(p: Path) -> bool:
    t, _ = mimetypes.guess_type(p.name)
    return t is not None and not t.startswith("text")
# --- NEW helper inside summarizer.py --------------------
def get_utils_dir(repo_root: Path) -> Path | None:
    """Return Path to the installed my_utils source *if it lives in this repo*."""
    utils_path = Path(__file__).resolve().parent      # …/my_utils/
    try:
        return utils_path.relative_to(repo_root)
    except ValueError:
        # utils lives in site‑packages or another repo → nothing to skip
        return None
def summarize(repo_root: Path, outfile: Path, max_bytes=MAX_BYTES):
    spec = load_gitignore(repo_root)
    all_paths = sorted(p.relative_to(repo_root) for p in repo_root.rglob("*") if p.is_file())
    utils_dir = get_utils_dir(repo_root)
    if utils_dir:
        all_paths = [p for p in all_paths if not str(p).startswith(str(utils_dir))]
    with outfile.open("w", encoding="utf-8") as out:
        # 1) tree
        out.write("### Repository structure\n\n")
        for p in all_paths:
            if spec.match_file(str(p)): continue
            out.write(str(p) + "\n")
        out.write("\n")

        # 2) README first
        readme = next((p for p in all_paths if p.name.lower().startswith("readme")), None)
        if readme and not spec.match_file(str(readme)):
            out.write(f"### {readme}\n\n{(repo_root/readme).read_text(errors='ignore')}\n\n")

        # 3) file contents
        for p in all_paths:
            if spec.match_file(str(p)) or p == readme: continue
            abs_p = repo_root / p
            if abs_p.stat().st_size > max_bytes or is_binary(abs_p): continue
            out.write(f"### {p}\n\n")
            out.write(abs_p.read_text(errors="ignore"))
            out.write("\n\n")

def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate repo_summary.txt")
    ap.add_argument("--root", type=Path, default=Path.cwd(), help="Repo root (defaults to CWD)")
    ap.add_argument("--out", type=Path, default=None, help="Output file")
    ap.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    args = ap.parse_args(argv)

    root = args.root.resolve()
    out = args.out or root / "repo_summary.txt"
    summarize(root, out, args.max_bytes)
    print(f"Summary written to {out}")

if __name__ == "__main__":
    main()
