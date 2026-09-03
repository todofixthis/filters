---
name: release
description: Use when preparing or publishing a new release of phx-filters — covers release notes, version bump, build, PyPI upload, and GitHub release creation
---
# Release

## Phase 1 — Research & draft (before touching any files)

### 1. Gather changes since last release
```bash
gh release list --limit 1 --json tagName --jq '.[0].tagName'   # find last release tag
git log <last-tag>..HEAD --oneline                              # all commits since
```

### 2. Look up PR and issue context
For every merge commit, extract the PR number and fetch its description:
```bash
git log <last-tag>..HEAD --oneline --merges
gh pr view <number> --json title,body,labels
```

For every `#<number>` reference in commit messages, fetch the issue:
```bash
gh issue view <number> --json title,body,labels
```

### 3. Draft release notes
Using the commit list, PR descriptions, and issue context, draft the release notes following the _Writing Release Notes_ guide below. When a bullet relates to a GitHub issue, prefix it with `[#number]`. Run the `nz-english` skill on the draft, then present it to the developer for review and incorporate feedback before proceeding.

### 4. Recommend version number
Based on the changes, recommend a semver bump:
- **major** — breaking changes
- **minor** — new features or behaviour changes, fully backwards-compatible
- **patch** — bug fixes only

**Stop here. Get explicit confirmation of the release notes and version number before continuing.**

---

## Phase 2 — Publish (after confirmation)

### 5. Bump version on `develop`
```bash
uv version <version>
```
This updates `pyproject.toml` and re-locks `uv.lock` in one step. Commit both files and push to `develop`.

### 6. Open release PR
```bash
gh pr create --base main --title "Release v<version>" --body-file release-<version>.md
```
**Stop here. Wait for the user to confirm the PR is merged before continuing.**

### 7. Switch to `main`
```bash
git checkout main && git pull
```

### 8. Build
```bash
uv sync --group=dev
rm -rf dist
uv build
```
Sync first — pulling `main` may have brought in dependency changes. Artefacts
land in `dist/`. Nothing under `dist/` is tracked, so removing the whole
directory is safe — and necessary: under zsh `rm -f dist/*` aborts with `no
matches found` when `dist/` is empty or absent, and otherwise skips uv's
`.gitignore`. `uv build` recreates both.

### 9. Tag and push
```bash
git tag -a <version> -m "Release <version>"
git push origin <version>
```
`<version>` must match `pyproject.toml`.

### 10. Create GitHub release

**a. Append checksums to the release notes file:**
```bash
echo -e "\n# SHA256 Checksums" >> release-<version>.md
shasum -a 256 dist/phx_filters-* >> release-<version>.md
```

**b. GPG-sign the document and each build artefact:**
```bash
GPG_KEY=$(git config user.email)
gpg --local-user "$GPG_KEY" --clearsign release-<version>.md   # → release-<version>.md.asc
for f in dist/phx_filters-*; do gpg --local-user "$GPG_KEY" --detach-sign "$f"; done
# Creates dist/phx_filters-*.sig alongside each artefact
```

**c. Build the release body** — concatenate the notes and the signed copy:
```
<contents of release-<version>.md>

---

````
<contents of release-<version>.md.asc>
````
```
Write this to `release-<version>-body.md`.

**d. Create the release and upload all artefacts:**
```bash
gh release create <version> dist/* \
  --title "Filters v<version>" \
  --notes-file release-<version>-body.md
```
`dist/*` picks up the `.whl`, `.tar.gz`, and `.sig` files.

### 11. Upload to PyPI
```bash
# Publishes only if the keyring can supply the token
keyring get https://upload.pypi.org/legacy/ __token__ >/dev/null 2>&1 && \
  uv publish --username __token__
```
The token comes from the developer's keyring: `[tool.uv]` in `pyproject.toml`
sets `keyring-provider = "subprocess"`, so uv shells out to a `keyring`
executable on `PATH`. Run the check first — it exits non-zero when the keyring
cannot supply the token, and prints nothing either way. Never echo the token to
confirm it; that puts a live credential in the transcript.

**If the check fails, stop here** and ask the developer to set
`UV_PUBLISH_TOKEN` (which takes precedence over the keyring) and run the publish
themselves. You cannot export it into their shell, and discovering this by
running the upload means failing the release's one irreversible step.

### 12. Clean up
```bash
rm -f release-<version>.md release-<version>.md.asc release-<version>-body.md
rm -rf dist
git checkout develop && git pull
```
`-f` so a re-run does not fail on a file already removed. `dist` goes too — its
artefacts and `.sig` files are on the GitHub release and PyPI by now. To correct
a release afterwards, fetch those assets back with `gh release download
<version>`: a rebuilt wheel may not be byte-identical, so its checksums would
disagree with the published notes.

### 13. Close related GitHub issues
For every issue referenced in the release notes, close it with a comment:
```bash
gh issue close <number> --comment "Implemented in [v<version>](https://github.com/todofixthis/filters/releases/tag/<version>)."
```

### 14. Rebase `develop` onto `main`
```bash
git rebase origin/main
git push
```
Because `develop` now contains all of `main`'s commits, the histories no longer diverge and a regular (non-force) push succeeds.

---

## Writing Release Notes

### Structure
```markdown
# Filters v<version>
<one-sentence summary of the release character>

> [!WARNING]
> **Breaking changes**
> - {what changed}
>   - {migration instructions}
>   - {error you'll see if you don't migrate}

## New features
## Enhancements
## Bug fixes

> [!NOTE]
> **Verifying release artefacts**
> 1. Import the signing key: `curl https://github.com/todofixthis.gpg | gpg --import`
> 2. Download the `.whl` or `.tar.gz` and its matching `.sig` file from the release assets
> 3. Verify: `gpg --verify phx_filters-<version>-py3-none-any.whl.sig phx_filters-<version>-py3-none-any.whl`
>
> Key fingerprint: `457997A2A506270F918D7BD1925CC6E316680401`

# SHA256 Checksums
```

Only include the `[!WARNING]` block if there are breaking changes. Omit any section that has no entries.

### Grouping related items
- **2–4 related bullets:** nest as a hierarchical sublist under the parent bullet
- **5+ related bullets:** promote to a `###` subheading within the section

### Content filter

**Always include**
- New capabilities developers can use
- Architectural decisions
- Behaviour changes
- Breaking changes

**Usually omit**
- Technical details of how something works internally
- Configuration consolidation (unless it changes developer-facing behaviour)
- Code organisation changes
- Dependency updates (include only if resolving a critical or high-severity vulnerability)
- Improvements to coding agent instructions

**Always omit**
- Formatting, linting, minor refactoring
- Test coverage updates

### Breaking changes alert
```markdown
> [!WARNING]
> **Breaking changes**
> - `SomeClass.old_method()` removed
>   - Replace with `SomeClass.new_method()`
>   - You'll know you need to migrate if you see: `AttributeError: 'SomeClass' object has no attribute 'old_method'`
```
