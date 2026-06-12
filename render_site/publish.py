"""
Asset sync + git publish for the static `website/` repo.

`sync_assets` keeps `website/assets/` in step with the source assets in this
package. `publish_run` stages + commits a run's page and (by default) pushes
it. Push is best-effort and env-gated so test runs don't publish and a failed
push never aborts a pipeline whose PDF already rendered.
"""

# =============================================================
# packages
# =============================================================

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PKG_DIR = Path(__file__).parent
STATIC_DIR = PKG_DIR / "static"

ASSET_NAMES = ("site.css", "site.js")


# =============================================================
# assets
# =============================================================

def sync_assets(website_root: Path) -> None:
    """
    Copy the package's source assets into `website_root/assets/` when missing
    or changed. A single edit in render_site/static/ thus restyles every page
    on the next render, without duplicating CSS/JS into each index.html.
    """
    assets_dir = website_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    for name in ASSET_NAMES:
        src = STATIC_DIR / name
        if not src.exists():
            continue
        dst = assets_dir / name
        src_bytes = src.read_bytes()
        if not dst.exists() or dst.read_bytes() != src_bytes:
            dst.write_bytes(src_bytes)


# =============================================================
# git publish
# =============================================================

def _git(website_root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(website_root), *args],
        capture_output=True,
        text=True,
    )


def publish_run(
    run_id: str,
    website_root: Path,
    push: bool | None = None,
) -> None:
    """
    Stage and commit `cv/<run_id>` plus any changed `assets/`, then push.

    `push` defaults to the `WEBSITE_PUBLISH` env var (push unless it is "0").
    Everything here is best-effort: a "nothing to commit" state is a no-op,
    and a failed push only logs a warning so the caller's run still completes.
    """
    if push is None:
        push = os.environ.get("WEBSITE_PUBLISH", "1") != "0"

    add = _git(website_root, "add", f"cv/{run_id}", "assets")
    if add.returncode != 0:
        print(f"[render_site] git add failed: {add.stderr.strip()}", file=sys.stderr)
        return

    commit = _git(website_root, "commit", "-m", f"Add run {run_id} page")
    if commit.returncode != 0:
        # Most commonly: nothing staged (re-render of an unchanged run).
        detail = (commit.stdout + commit.stderr).strip()
        if "nothing to commit" in detail:
            print(f"[render_site] no changes to commit for run {run_id}.")
        else:
            print(f"[render_site] git commit failed: {detail}", file=sys.stderr)
        return

    if not push:
        print(f"[render_site] committed run {run_id} (push skipped).")
        return

    pushed = _git(website_root, "push")
    if pushed.returncode != 0:
        print(
            f"[render_site] WARNING: git push failed for run {run_id}; "
            f"commit is local only. Push manually when ready.\n"
            f"{pushed.stderr.strip()}",
            file=sys.stderr,
        )
    else:
        print(f"[render_site] published run {run_id}.")
