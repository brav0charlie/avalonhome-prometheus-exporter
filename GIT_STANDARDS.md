---
version: 1.6.0
last_updated: 2026-07-04
---

# Git & Version Control Standards

This document defines version control practices for all projects. It is
written to be consumed both by humans and by AI coding assistants. When
you are an AI assistant working in this codebase, treat every rule below
as binding unless the human operator explicitly overrides it for a
specific task.

The goal is a clean, auditable, professional history: the kind of repo a
future maintainer, App Store reviewer, or security auditor can read
without confusion.

---

## 1. Workflow Model: GitHub Flow

We use **GitHub Flow**: `main` is always deployable; all work happens on
short-lived branches that merge back via Pull Request.

**Rules:**

- `main` is the single long-lived branch. It must always be in a
  releasable state.
- Every change starts on a new branch off the latest `main`.
- Branches are short-lived. Aim to merge within 1–3 days. If a branch
  lives longer than a week, split the work.
- Pull Requests are mandatory. No direct commits to `main`, ever.
- Merges to `main` use **Squash and Merge** to keep history linear.
- After merge, the source branch is deleted.

**Why not Git Flow:** Git Flow's `develop`, `release/*`, and `hotfix/*`
branches exist to coordinate scheduled releases across large teams. A
one-person shop shipping App Store apps does not need that ceremony.

**Why not pure trunk-based:** Pure trunk-based assumes mature CI/CD with
strong automated test coverage gating every merge. Until that
infrastructure exists, the PR step provides a cheap quality gate:
self-review, CI checks if configured, and a deliberate pause before
merge.

---

## 2. Branching

### Naming

```text
<type>/<short-kebab-description>
```

- Lowercase, hyphens between words. No spaces, underscores, or slashes
  inside the description.
- Describe the **outcome**, not the session, date, or tool.
- Keep it under ~50 characters total.

Good: `feat/add-csv-export`, `fix/crash-on-empty-input`
Bad: `claude-session-4`, `bills-branch`, `wip-2026-04-25`

### Allowed Types

| Type | Use for |
| -------- | -------------------------------------------------------- |
| `feat/` | New user-visible features or capabilities |
| `fix/` | Bug fixes |
| `hotfix/` | Emergency production fixes |
| `chore/` | Maintenance: deps, config, tooling, no behavior change |
| `docs/` | Documentation-only changes |
| `refactor/` | Internal restructuring, no behavior change |
| `perf/` | Performance improvements |
| `test/` | Adding or updating tests |
| `build/` | Build system, dependencies, packaging |
| `ci/` | CI/CD pipeline changes |
| `release/` | Release preparation (version bump, changelog) |

### Branch Lifecycle

```text
git switch main
git pull origin main
git switch -c feat/add-csv-export
git push -u origin feat/add-csv-export
```

After merge:

```text
git branch -d feat/add-csv-export
git push origin --delete feat/add-csv-export
```

---

## 3. Commits

### Format: Conventional Commits 1.0.0

```text
<type>(<optional scope>): <description>

<optional body>

<optional footer(s)>
```

### Subject Line Rules

- Length: 50 characters or fewer. Hard limit: 72.
- Mood: imperative present tense. Write as if completing "If applied,
  this commit will…"
- No trailing period.
- Lowercase after the type prefix unless it is a proper noun.
- The type is **always** lowercase.

Good: `feat(export): add CSV export button to inventory list`
Bad: `Added CSV export button`, `Adds CSV export button`

### Allowed Commit Types

| Type | Meaning | SemVer bump |
| ---------- | ----------------------------------------------- | ----------- |
| `feat` | New user-visible feature | MINOR |
| `fix` | Bug fix | PATCH |
| `perf` | Performance improvement, no behavior change | PATCH |
| `refactor` | Code restructuring, no behavior change | None |
| `style` | Formatting, whitespace, no logic change | None |
| `test` | Adding or updating tests | None |
| `docs` | Documentation changes only | None |
| `build` | Build system, dependency updates, packaging | None |
| `ci` | CI/CD pipeline configuration | None |
| `chore` | Maintenance, no production code change | None |
| `revert` | Reverts a previous commit | Depends |

### Scope

Optional. Indicates the affected area. Keep it short, lowercase, and
consistent across commits.

```text
feat(export): add CSV export button to inventory list
fix(sync): handle nil CloudKit record on first launch
refactor(models): extract Item value type from view layer
```

### Commit Body

- Use a body whenever the subject alone is not self-explanatory.
- Separate from subject with one blank line. Wrap at 72 characters.
- Explain **why**, not what. The diff shows what changed.

```text
fix(sync): handle nil CloudKit record on first launch

On a freshly installed device, CKQueryOperation can return a record
with all fields nil before the schema has propagated. Unwrapping
`record["name"]` directly caused a crash.

Now we treat any nil field as "not yet synced" and skip the row
until the next refresh.

Closes #42
```

### Footer Conventions

Footers go after the body, separated by one blank line. One line each,
`Token: value` format. Tokens use hyphens.

| Footer | Use |
| ---------------------- | ---------------------------------------- |
| `Closes #N` | Closes GitHub issue N when merged |
| `Refs #N` | References issue N without closing |
| `BREAKING CHANGE: …` | Documents a breaking change (required) |
| `Reviewed-by: Name` | Credits a reviewer |

### Breaking Changes

Indicate in either of two ways:

1. Append `!` after type/scope: `feat(api)!: rename FetchItems`
2. Add a `BREAKING CHANGE:` footer.

A breaking change always triggers a MAJOR version bump regardless of
commit type.

### Granularity

- Commit after each working, testable piece — not one giant commit at
  the end.
- Each commit should leave the codebase in a buildable state.
- It is acceptable to split a single logical change into separate
  commits when reviewers benefit from reading them individually (e.g.,
  generated changes vs. hand-written changes).

---

## 4. AI Attribution

Every commit produced with AI assistance carries attribution,
regardless of which tool wrote it. Repos may see commits from more
than one AI coding assistant acting as a Builder (currently Claude
Code and Codex CLI) — attribution must identify *which* tool, not just
disclose that "AI was involved."

### Claude Code

Attribution is **on by default**. Leave Claude Code's default settings
in place.

Default Claude Code trailers:

```text
Generated with Claude Code (https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>
```

These appear at the end of the commit message, after any `Closes #N` or
`BREAKING CHANGE:` footers.

Do not set `attribution.commit` or `attribution.pr` to empty strings in
any `settings.json`. If those overrides exist from earlier projects,
remove them.

GitHub's Squash-and-Merge UI rewrites `Co-Authored-By:` to lowercase
`Co-authored-by:` in the resulting commit on `main`. Both forms parse
identically for GitHub's contributor-attribution graph, so this is a
display artifact, not a problem to fix.

### Codex CLI

Unlike Claude Code, Codex's commit attribution is **off by default**.
The `codex_git_commit` feature and its `commit_attribution` trailer are
opt-in — without enabling them, a Codex-authored commit on this repo
carries no AI disclosure at all, silently, with nothing to flag it.
Enable both before using Codex as a Builder on any repo governed by
this standard.

One-time setup in `~/.codex/config.toml` (or a project-scoped
`.codex/config.toml` if you want it repo-specific rather than global):

```toml
[features]
codex_git_commit = true

commit_attribution = "Codex <noreply@openai.com>"
```

The value above is Codex's actual built-in default once the feature is
enabled — setting it explicitly here just guards against that default
changing silently in a future Codex release. Setting
`commit_attribution = ""` disables the trailer entirely; never do this
on a repo covered by this standard.

Mechanically this works differently from Claude Code: Codex injects
trailer instructions into its own prompt context rather than using a
git hook, so the model is *told* to append the trailer rather than
having it enforced mechanically. Treat the resulting disclosure the
same as Claude Code's for policy purposes regardless — the
authorship invariants below apply to both.

### Other AI Tools

If using an AI tool that does not support automatic `Co-Authored-By`
trailers at all, manually append one to maintain auditability:

```text
Co-Authored-By: <Tool Name> <noreply@example.com>
```

### Authorship Invariants (All Tools)

- The commit `Author` field is always the developer's verified GitHub
  email — never an AI identity, regardless of which AI tool produced
  the diff.
- Commits are GPG/SSH-signed (Section 7).
- The legal author and responsible party for every commit is the human
  developer. A `Co-Authored-By` trailer is a disclosure of which tool
  was involved, not a co-ownership claim or a transfer of authorship —
  this applies equally to Claude Code, Codex, or any other tool's
  trailer.

**Why keep attribution on:** The EU AI Act's transparency obligations and
California's expanding AI disclosure regime are pushing toward "disclose
AI involvement by default." Erring toward disclosure now is cheaper than
retrofitting it later. This is exactly why Codex's attribution needs to
be explicitly enabled rather than left at its out-of-the-box behavior —
a commit with no trailer at all defeats the purpose whether that
silence was deliberate or just an unconfigured default.

---

## 5. Pull Requests

### When to Open

- When the feature branch implements something coherent and reviewable.
- Open draft PRs early if you want CI to run while work continues.
- Do not let branches accumulate weeks of work before opening a PR.

### PR Title

Use the same Conventional Commits format as commit subjects. This title
lands on `main` when squash-merged.

```text
feat(export): add CSV export button to inventory list
```

### PR Description Template

```markdown
## What

Brief summary of what this PR changes.

## Why

The motivation. Link to issue, ticket, or context.

## How

Notable implementation decisions, especially anything non-obvious or
anything reviewers should pay extra attention to.

## Testing

How this was verified. Screenshots for UI changes. Build/test output
for non-trivial logic.

## Checklist

- [ ] Builds without warnings
- [ ] Tests pass locally
- [ ] No secrets, API keys, or credentials in the diff
- [ ] CHANGELOG updated (if user-visible change)
- [ ] Documentation updated (if behavior or API changed)
```

### Merging

- **Always Squash and Merge.** Never "Create a merge commit." Never
  "Rebase and Merge."
- The squash commit message is the PR title plus the PR body.
- Delete the branch after merge, both on GitHub and locally.

**Why squash:** One commit per PR keeps `main` history linear and
readable. `git revert` becomes a one-commit operation. `git bisect`
works cleanly because each commit on `main` represents a complete,
working change.

**What signs the merge commit.** Squash-and-Merge (and Rebase-and-Merge)
commits are constructed by GitHub's servers and signed with GitHub's
web-flow GPG key, not your local SSH key. This is expected: your key
isn't accessible to GitHub's servers, so attributing the signature to it
would be inaccurate. The `Author` field still names you (you authored
the content), and the original PR commit retains your signature on the
PR record. For local verification of merge commits, import GitHub's
web-flow public key per Section 7 ("Local Verification").

---

## 6. Releases & Tags

### Semantic Versioning 2.0.0

Format: `MAJOR.MINOR.PATCH`

| Bump | When |
| ----- | ------------------------------------------------------ |
| MAJOR | Breaking change |
| MINOR | New backward-compatible feature |
| PATCH | Backward-compatible bug fix or internal change |

For App Store apps, the SemVer version maps to
`CFBundleShortVersionString` (marketing version). The `CFBundleVersion`
(build number) is independent and increments per submission.

While pre-1.0, any change can bump MINOR or PATCH freely, and breaking
changes do not require a MAJOR bump until `1.0.0`.

### Tagging

Tag after merging a release commit (typically a `release/` branch that
bumps the version and updates the changelog):

```text
git switch main
git pull origin main
git tag -s v1.2.0 -m "Release 1.2.0"
git push origin v1.2.0
```

**Tag rules:**

- Always prefix with lowercase `v`: `v1.2.0`.
- Use annotated, signed tags (`-s`). Lightweight tags are forbidden for
  releases.
- Tag message can be short: `Release 1.2.0`. The CHANGELOG carries the
  detail.
- Once pushed, tags are **never** moved or rewritten. If a tag was
  created in error, create a new tag with a new name and document the
  mistake in the CHANGELOG.

### App Store Releases

1. Tag the exact commit that was archived and submitted.
2. Use `v<marketing-version>.<build-number>` when multiple builds of
   the same marketing version are submitted (e.g., `v1.2.0.42`);
   otherwise just `v1.2.0`.
3. Push the tag to GitHub immediately after submission, before any
   further commits to `main`.
4. If Apple rejects the build, tag the replacement separately. Do not
   move existing tags.

---

## 7. Signed Commits and Tags

All commits and tags must be cryptographically signed using SSH signing
(Git ≥ 2.34) backed by 1Password.

**Why:** Proves the commit was authored by the holder of the signing key.
Cryptographically binds the commit content — any tampering breaks the
signature. GitHub displays a "Verified" badge on signed commits,
signaling an intact chain of custody to anyone reading the history.

### Configuration

One-time global setup (replicate on any new machine):

```text
git config --global gpg.format ssh
# With 1Password managing the key, use the inline public-key string
# (not a file path). Copy it from 1Password → SSH key → Public Key.
git config --global user.signingkey "ssh-ed25519 AAAA...<base64-key-body>"
git config --global gpg.ssh.program "/Applications/1Password.app/Contents/MacOS/op-ssh-sign"
git config --global commit.gpgsign true
git config --global tag.gpgSign true
```

For stable multi-identity setups (e.g., personal and organization), prefer
the `includeIf` pattern in "Multi-Identity Setup" below over per-repo
overrides — overrides have to be set manually on every clone and drift
silently. Per-repo `git config` overrides remain valid for genuinely
one-off cases:

```text
git config gpg.format ssh
git config user.signingkey "ssh-ed25519 AAAA...<base64-key-body>"
```

### GitHub Registration

The signing public key must be registered on GitHub as a **signing key**
(not just an authentication key) under Settings → SSH and GPG keys.
Without this, GitHub cannot verify signatures and commits show as
"Unverified."

### Local Verification

Signing and verification are independent paths. Git dispatches each
commit's verification based on the signature's format:

| Signature on the commit | Verifier consults |
| ----------------------- | ----------------- |
| `BEGIN SSH SIGNATURE` | `~/.config/git/allowed_signers` (set via `gpg.ssh.allowedSignersFile`) |
| `BEGIN PGP SIGNATURE` | the local GPG keyring (`~/.gnupg/`) |

Both paths need one-time setup, separate from the signing config above.
Without setup, `git log --show-signature` reports the signature as
unverifiable on the local machine — even though GitHub still verifies it
fine, since GitHub has its own copy of your registered keys.

**SSH side — `allowed_signers` file.** One line per signer, mapping email
(the principal) to a public key:

```text
mkdir -p ~/.config/git
printf '%s namespaces="git" %s\n' \
  '<your-email>' \
  'ssh-ed25519 AAAA...<base64-key-body>' \
  > ~/.config/git/allowed_signers

git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
```

The `namespaces="git"` qualifier scopes the entry to git signing
specifically — without it, the same key could verify other SSH signatures
(e.g., file signing). For multiple identities, append more lines; each
is independent.

**GPG side — GitHub web-flow key.** Squash-and-Merge commits on `main`
are signed by GitHub's web-flow GPG key (see Section 5, "What signs the
merge commit"). Import GitHub's public key so local verification of those
commits works:

```text
curl -sL https://github.com/web-flow.gpg | gpg --import
```

**Expected output.** After both setups, `git log --show-signature -1` on
a verified commit prints something like:

```text
Good "git" signature for you@example.com with ED25519 key SHA256:...
```

for your own SSH-signed commits, and:

```text
gpg: Good signature from "GitHub <noreply@github.com>" [unknown]
gpg: WARNING: This key is not certified with a trusted signature!
```

for GitHub-signed merge commits. The `Good signature` line is the
verification pass; the WARNING is GPG's web-of-trust noise (you imported
the key but haven't locally certified it). Harmless. To suppress the
WARNING locally:

```text
gpg --lsign-key <github-web-flow-fingerprint>
```

**Verification commands:**

```text
git log --show-signature -1
git tag -v v1.2.0
```

### Multi-Identity Setup

Many developers sign for both personal and organization contexts with
different identities — different email, different signing key, sometimes
different signing format. Git's `includeIf` directive maps directory
trees to identities cleanly, so new clones under the matching path pick
up the right identity automatically.

Pattern:

```ini
# ~/.gitconfig (shared, in dotfiles)
[include]
        path = ~/.gitconfig.local         # personal default identity

# ... shared aliases, color, core, push, pull ...

# Organization identity — activates for repos under ~/code/<org>/
[includeIf "gitdir:~/code/<org>/"]
        path = ~/.gitconfig.<org>
```

Each identity file declares its own `[user]`, signing key, and signing
format:

```ini
# ~/.gitconfig.<org>
[user]
        email = you@<org>.com
        signingkey = ssh-ed25519 AAAA...<base64-key-body>
[gpg]
        format = ssh
[gpg "ssh"]
        program = /Applications/1Password.app/Contents/MacOS/op-ssh-sign
[commit]
        gpgsign = true
[tag]
        gpgsign = true
```

Three semantic notes (each is a footgun otherwise):

- **Trailing slash matters.** `gitdir:~/code/<org>/` auto-expands to
  `~/code/<org>/**` and matches recursively. Without the trailing slash,
  it matches only the literal path string.
- **Last include wins.** Both `[include]` and matching `[includeIf]`
  blocks parse in file order. Put the organization override **after** the
  personal include so it overrides.
- **Local `.git/config` still beats global includes.** Any per-repo
  `git config --local` overrides will continue to win over `includeIf`.
  When switching to `includeIf` from an earlier per-repo setup, run
  `git config --local --unset <key>` or
  `git config --local --remove-section <name>` to let the global include
  take over.

On macOS's case-insensitive default filesystem, `gitdir/i:` (the
case-insensitive variant) defends against path-capitalization drift.

---

## 8. The `.gitignore`

Every repository has a `.gitignore` committed at the root from the first
commit. Never commit secrets; if one is committed accidentally, rotate
the secret first, then remove it from history with `git-filter-repo` or
the BFG Repo-Cleaner.

### Swift / Xcode Projects

```gitignore
# macOS
.DS_Store
.AppleDouble
.LSOverride
Icon?

# Xcode
build/
DerivedData/
*.xcuserstate
*.xcuserdatad/
xcuserdata/
*.xccheckout
*.moved-aside
*.hmap
*.ipa
*.dSYM.zip
*.dSYM

# Swift Package Manager
.build/
Packages/
Package.pins
Package.resolved
*.xcodeproj/project.xcworkspace/xcuserdata/
*.xcworkspace/xcuserdata/

# CocoaPods (if used)
Pods/

# Carthage (if used)
Carthage/Build/

# fastlane
fastlane/report.xml
fastlane/Preview.html
fastlane/screenshots/**/*.png
fastlane/test_output

# Secrets and local config
*.env
.env.local
*.p12
*.p8
*.cer
*.mobileprovision
AuthKey_*.p8
GoogleService-Info.plist
secrets.plist

# Editor / OS
*.swp
*.swo
*~
.idea/
.vscode/
```

### General Projects

```gitignore
.DS_Store
.env
.env.local
.env.*.local
*.log
node_modules/
__pycache__/
.venv/
venv/
.idea/
.vscode/
```

### Rules

- Never commit secrets. If a secret is committed by accident, rotate it
  immediately — removing from history is not sufficient on its own.
- Never commit machine-specific paths or absolute paths.
- Never commit binary build artifacts that can be regenerated.
- When in doubt, ignore it. Adding to `.gitignore` later is harder than
  removing if you change your mind.

---

## 9. Repository Hygiene

### Required Root Files

| File | Purpose |
| ---------------- | ---------------------------------------------------- |
| `README.md` | What the project is, how to build/run it |
| `LICENSE` | License text. Default: MIT |
| `.gitignore` | See Section 8 |
| `CHANGELOG.md` | Human-readable release history (Keep a Changelog) |
| `.gitattributes` | Line-ending normalization |

### `CHANGELOG.md`

Follow [Keep a Changelog](https://keepachangelog.com) format. Standard
sections per version: `Added`, `Changed`, `Deprecated`, `Removed`,
`Fixed`, `Security`. Also use `Changed (internal)` for engineering-only
changes with no user-visible effect (refactors, dependency bumps,
tooling) - not every internal change earns an entry, but ones worth a
future reader knowing about do. Keep an `[Unreleased]` section at the
top at all times, even when empty (a placeholder like `_Nothing yet._`
beats omitting the heading and having to remember to add it back).
This is the single changelog for the project - there is no separate
weekly or internal-status changelog to keep in sync with it.

Each bullet references the change it came from, but *what* it
references depends on whether the change has been released yet:

- **While unreleased:** reference the PR number - `[#42]` - not a
  commit hash. The PR number is assigned on creation and never
  changes. A feature-branch commit's hash is not stable the same way:
  Squash and Merge (Section 5) discards the branch's individual
  commits and constructs a brand-new commit on `main` at merge time,
  so any hash written into the changelog before that merge would be
  wrong the moment it happens.
- **At release/tag time:** when moving `[Unreleased]` entries under
  the new version heading, swap each `[#42]` for that PR's actual
  squash-commit short hash. The commit now exists on `main` and its
  hash is permanent - this is the first point a stable hash reference
  is even possible, not before. Find it with `gh pr view 42 --json
  mergeCommit` or by matching the PR title in `git log --oneline`.

Where a change was governed by or produced an ADR, cite it inline in
parentheses at the end of the bullet - `(ADR-0007)`. This is a
separate reference from the PR/hash: PR and hash point to the diff,
the ADR points to the reasoning. Not every entry has one; add it
wherever an ADR exists for that change.

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- [#44] CSV export from inventory list
  - Exports visible columns only, respects the active filter

## [1.2.0] - 2026-04-15

### Added
- [a2b3c4d] iCloud sync for inventory items
- [e5f6g7h] Search across all fields

### Fixed
- [9c8d7e6] Crash when launching with no items on first install
```

Update `CHANGELOG.md` in the same PR that introduces the change, in the
`[Unreleased]` section. Release PRs move `[Unreleased]` content under a
new versioned heading and perform the `#PR` -> short-hash swap
described above.

### `.gitattributes`

```text
* text=auto eol=lf
*.bat text eol=crlf
*.png binary
*.jpg binary
*.pdf binary
```

---

## 10. Branch Protection

Enable on `main` for every repo. Even solo, this prevents accidents.

**Required settings:**

- Require a pull request before merging: ON
  - Required approvals: 0 (solo) or 1 (when collaborating)
  - Dismiss stale approvals on new commits: ON
- Require status checks to pass before merging: ON (once CI exists)
  - Require branches to be up to date before merging: ON
- Require linear history: ON
- Require signed commits: ON
- Do not allow bypassing the above settings: ON
- Restrict who can push to matching branches: yourself only
- Allow force pushes: OFF
- Allow deletions: OFF

Default branch is `main`. Migrate any legacy `master` branches to `main`
on first touch.

**Default merge settings** (Settings → General → Pull Requests):

- Allow squash merging: ON
- Allow merge commits: OFF
- Allow rebase merging: OFF
- Always suggest updating pull request branches: ON
- Automatically delete head branches: ON

Local rebasing of feature branches is allowed to keep history clean.
Never rebase `main`. If a PR requires rebasing due to conflicts, rebase
locally and force-push with `--force-with-lease` only — only on your own
branch, and never after merge.

---

## 11. Things That Must Never Happen

These are hard rules, not style preferences.

- **Never force-push to `main`.** Branch protection enforces this. If
  you find yourself wanting to, stop and examine what went wrong.
- **Never rewrite published history.** Once a commit is pushed and may
  have been pulled, it is immutable. Use `git revert` to undo. The
  exception is your own feature branch before it is merged — rebasing
  locally is fine; force-pushing after a PR is open requires
  `--force-with-lease` only.
- **Never commit secrets.** API keys, signing keys, passwords, OAuth
  tokens, certificates, private keys, App Store Connect API keys — none
  of this goes in the repo. Not even temporarily. Not even in a comment.
  Not even base64-encoded. Rotate the secret first, then deal with the
  repo.
- **Never commit generated artifacts.** Build outputs, compiled
  binaries, `DerivedData/`, `node_modules/`, `.build/`, log files.
  These belong in `.gitignore`.
- **Never commit personal or machine-specific config.** `xcuserdata/`,
  `.idea/workspace.xml`, local `.env` files, absolute paths.
- **Never use `git add .` blindly.** Always review what is about to be
  committed. Run `git status` and `git diff --staged` before every
  commit.
- **Never commit broken builds to `main`.** If a PR breaks `main`,
  revert the PR immediately, then fix forward in a new PR. Do not push
  a direct fix to `main`.

---

## 12. Quick Reference: The Happy Path

```text
# Start of work
git switch main
git pull origin main
git switch -c feat/add-csv-export

# During work — repeat after each working, testable piece
git status
git diff
git add <specific files>
git diff --staged
git commit -m "feat(export): add CSV export button to inventory list"

# Push and open PR
git push -u origin feat/add-csv-export
gh pr create --base main --fill

# After squash merge on GitHub
git switch main
git pull origin main
git branch -d feat/add-csv-export
```

---

## 13. Instructions for AI Coding Assistants

When you are an AI assistant working in this repository, the following
are non-negotiable:

1. **Read this document at the start of every session** before making
   any commits or branch operations.
2. **Never commit directly to `main`.** Always create a properly named
   feature branch first.
3. **Preserve default AI attribution for your tool** (Section 4):
   - **Claude Code:** do not strip the `Co-Authored-By: Claude` trailer
     or the `Generated with Claude Code` line from commits or PRs. Do
     not set `attribution.commit` or `attribution.pr` to empty strings
     in any `settings.json`.
   - **Codex CLI:** confirm `[features] codex_git_commit` is enabled
     and `commit_attribution` is not set to `""` in `config.toml`
     before committing. Missing attribution on a Codex-authored commit
     is a configuration problem to flag and fix — not something to
     paper over by hand-typing a substitute trailer.
   - **Any other tool:** if it has no built-in attribution mechanism,
     manually append a `Co-Authored-By: <Tool Name> <noreply@...>`
     trailer per Section 4.
4. **Always show the diff before staging.** Run `git status` and
   `git diff` and surface the output before running `git add`.
5. **Use Conventional Commits format** for every commit subject,
   matching the types listed in Section 3.
6. **Commit incrementally.** Multiple small commits are preferred over
   one large commit at the end of a task.
7. **Never force-push, never rewrite published history, never commit
   secrets.** See Section 11.
8. **If unsure, ask.** A 30-second clarifying question is cheaper than
   a 30-minute history-rewrite cleanup.
9. **Updates to this file** must follow Conventional Commits. Use `docs`
   or `chore` as appropriate. Do not edit this file directly in the UI;
   always commit via CLI.

---

## Appendix A: Recommended `git config` Defaults

Set on any new development machine:

```text
git config --global init.defaultBranch main
git config --global pull.rebase false
git config --global pull.ff only
git config --global push.default simple
git config --global push.autoSetupRemote true
git config --global rebase.autosquash true
git config --global rerere.enabled true
git config --global fetch.prune true
git config --global diff.colorMoved zebra
git config --global merge.conflictStyle zdiff3
git config --global commit.gpgsign true
git config --global tag.gpgSign true
git config --global gpg.format ssh
```

## Appendix B: Useful Aliases

Add to `~/.gitconfig` under `[alias]`:

```text
[alias]
    s = status -sb
    co = checkout
    sw = switch
    br = branch
    last = log -1 HEAD --show-signature
    lg = log --oneline --graph --decorate --all -20
    pushf = push --force-with-lease
    unstage = reset HEAD --
    amend = commit --amend --no-edit
```
