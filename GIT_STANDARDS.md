---
version: 1.9.9
last_updated: 2026-08-29
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

- Repository bootstrap is the sole exception to the rules below. A
  human creates the project directory, initializes `main`, installs and
  customizes the scaffold, makes one signed initial commit, creates the
  empty GitHub repository, and pushes local `main`. Activate the
  scaffold hook and branch protection immediately afterward. The role
  lifecycle begins only once that remote `main` exists; the Architect
  does not initialize a project or repository.
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
git pull --ff-only origin main
git switch -c feat/add-csv-export
git push -u origin feat/add-csv-export
```

After GitHub reports the squash merge complete:

```text
set -euo pipefail

feature_branch="feat/add-csv-export"
merge_commit="$(gh pr view <PR#> --json state,mergedAt,mergeCommit \
  --jq 'if .state == "MERGED" and .mergedAt != null and .mergeCommit.oid != null then .mergeCommit.oid else error("PR is not verified as merged") end')"
if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: worktree or index is dirty; branch retained." >&2
  exit 1
fi
git switch main
git pull --ff-only origin main
if ! git merge-base --is-ancestor "$merge_commit" main; then
  echo "ERROR: verified merge commit is not on local main; branch retained." >&2
  exit 1
fi

if git ls-remote --exit-code --heads origin "$feature_branch" >/dev/null 2>&1; then
  git push origin --delete "$feature_branch"
else
  ls_remote_exit=$?
  if [ "$ls_remote_exit" -ne 2 ]; then
    echo "ERROR: remote branch lookup failed; branch retained." >&2
    exit "$ls_remote_exit"
  fi
fi

git fetch --prune origin
git branch -D "$feature_branch"
```

`git ls-remote --exit-code` returns `2` when no matching ref exists; that is
the expected result when GitHub already deleted the merged head. Any other
nonzero result is a lookup failure and must stop cleanup. Keep `set -e` active
for the remaining commands so a failed pull, remote deletion, or fetch cannot
fall through to local branch deletion.

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

| Type | Meaning | SemVer impact |
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

A breaking change always declares MAJOR SemVer impact regardless of
commit type. The user still supplies the target when initiating the
major release.

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
Code and Codex) — attribution must identify *which* tool, not just
disclose that "AI was involved."

### Claude Code

This project owns a stable Claude Code attribution identity rather than
inheriting a model-specific vendor default. Commit the following shared
project setting as `.claude/settings.json`:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "attribution": {
    "commit": "Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude Code <noreply@anthropic.com>",
    "pr": "Co-Authored-By: Claude Code <noreply@anthropic.com>"
  }
}
```

The canonical Claude Code trailer is:

```text
Co-Authored-By: Claude Code <noreply@anthropic.com>
```

It appears once at the end of the commit message, after any `Closes #N`
or `BREAKING CHANGE:` footers. The preceding `Generated with` line is
informational; the trailer is the normative tool identity.

Claude Code applies settings from multiple scopes, so a personal or
managed setting may override the shared project value. Before creating
or amending a commit or PR, inspect the resulting text. Restore the
canonical trailer when it is absent, replace a different Claude
identity, and remove duplicates. Do not set `attribution.commit` or
`attribution.pr` to empty strings. Personal project overrides belong in
gitignored `.claude/settings.local.json`, not the shared file.

GitHub's Squash-and-Merge UI rewrites `Co-Authored-By:` to lowercase
`Co-authored-by:` in the resulting commit on `main`. Both forms parse
identically for GitHub's contributor-attribution graph, so this is a
display artifact, not a problem to fix.

### Codex

Current Codex releases do not expose a supported automatic commit
attribution setting. Do not rely on the removed `codex_git_commit`
feature or `commit_attribution` configuration. Instead, append this
exact trailer manually to every Codex-assisted commit:

```text
Co-Authored-By: Codex <noreply@openai.com>
```

Put the trailer after the commit body and any issue or breaking-change
footers, separated by one blank line. The human developer remains the
commit author and responsible party; the trailer records which AI tool
assisted with the change. If Codex gains a supported automatic
attribution mechanism in the future, it may replace this manual step
only if the resulting commit retains equivalent tool-specific
attribution.

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

### PR and Squash Attribution (All Tools)

Every AI-assisted PR body ends with the exact `Co-Authored-By` trailer
for each tool that assisted with the delivered change. Use the same
identity required for commits above. Put the trailers after all PR
sections and checklist items, separated from the preceding text by one
blank line. They must be the final non-comment lines of the PR body and
each required tool identity must appear exactly once. Automatic tool
output does not excuse a missing trailer or justify a duplicate one.

This is not redundant with feature-branch commit attribution. Squash
and Merge creates a new commit on `main`; this workflow configures that
commit to use the PR title and description, so the PR-body trailers are
what preserve tool-specific provenance on the lasting commit. Before
merging, confirm the generated squash message still ends with every
required trailer.

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

### Governance Changes

A PR is governed by the binding instructions and rule documents at the
PR's exact base commit. If the PR changes `AGENTS.md`,
`GIT_STANDARDS.md`, a routed `*_RULES.md` file, a role skill, or another
binding governance artifact, the candidate version is reviewed as
proposed content; it cannot redefine or waive the rules used to judge
its own PR. The new version becomes binding only after merge.

Reviewers record the exact base and head SHAs. They read the base
governance files from the base SHA and the proposed replacements from
the head SHA, keeping the two roles explicit throughout the review.

### Review Readiness

Before issuing a verdict, the Reviewer records a PR metadata snapshot
that includes its open/draft state, base and head branches and SHAs,
mergeability, merge-state details, review decision and requests, latest
reviews, complete paginated review history, inline review comments,
issue-level PR comments, review-thread resolution and outdated state, and
status-check rollup. Complete comment content comes from the paginated REST
surfaces; thread state comes from GitHub's paginated GraphQL
[`PullRequestReviewThread`](https://docs.github.com/en/graphql/reference/objects#pullrequestreviewthread)
surface. Detailed CI results come from `gh pr checks`; if the repository has
no checks, say so
explicitly rather than treating the absence as a passing run.

A `PASS` verdict requires all of the following:

- The PR is open, is not a draft, and targets `main`.
- GitHub does not report the PR as conflicting. Any other merge-state
  blocker is identified and evaluated rather than ignored.
- Every required status check has completed successfully. Pending,
  failing, cancelled, or action-required checks block `PASS` until they
  are resolved. Passing CI supports the review but does not replace
  independent verification of the task contract.
- Review requests, the aggregate review decision, latest reviews, the
  complete paginated review history, inline review comments, and
  issue-level PR comments have been inspected. Outstanding requests are
  reported; every prior request-changes verdict is explicitly accounted
  for during re-review.
- Every review thread's resolution and outdated state has been inspected.
  An unresolved, non-outdated thread blocks `PASS`. An unresolved outdated
  thread also blocks when its concern still applies, branch protection
  still reports it as a blocker, or resolution cannot be established.

Immediately before leaving the review, fetch the metadata, complete
review history, inline and issue-level PR comments, review-thread state,
and checks again. If either the base or head SHA changed since the initial
snapshot, the prior analysis is stale: do not post it, and restart the
review against the new exact SHAs. If readiness state changed without a
SHA change, apply the current state to the verdict and withhold `PASS`
while any required gate above is unsatisfied.

### PR Description Template

```markdown
## What

Brief summary of what this PR changes.

Implements: history/tasks/TASK-YYYYMMDDTHHMMSSZ-ssss-short-slug.md

Constrained by: history/decisions/ADR-YYYYMMDDTHHMMSSZ-ssss-short-slug.md
(omit when no ADR applies)

## Why

The motivation. Link to issue, ticket, or context.

## How

A concise, review-facing summary of notable implementation decisions,
especially anything non-obvious or anything reviewers should pay extra
attention to. Do not paste a private Builder prompt, chronological
session transcript, or complete Builder record here.

## Testing

How this was verified. Screenshots for UI changes. Build/test output
for non-trivial logic.

## Release impact

SemVer impact: major | minor | patch | none

For a release PR only: Release target: X.Y.Z

## Checklist

- [ ] Builds without warnings
- [ ] Tests pass locally
- [ ] No secrets, API keys, or credentials in the diff
- [ ] CHANGELOG updated (if user-visible change)
- [ ] SemVer impact declared and supported by the diff
- [ ] Project version unchanged (unless this is a release PR)
- [ ] Documentation updated (if behavior or API changed)

Co-Authored-By: <Tool Name> <noreply@example.com>
```

Replace the final attribution placeholder with the exact tool identity
from Section 4. Add one final trailer line per assisting tool.

### Merging

- **Always Squash and Merge.** Never "Create a merge commit." Never
  "Rebase and Merge."
- The squash commit message is the PR title plus the PR body. Configure
  the repository's default to **Pull request title and description**. Verify
  the two independent API fields: `.squash_merge_commit_title` must be
  `PR_TITLE`, and `.squash_merge_commit_message` must be `PR_BODY`:

  ```text
  gh api repos/{owner}/{repo} --jq '
    if .squash_merge_commit_title == "PR_TITLE"
       and .squash_merge_commit_message == "PR_BODY"
    then {
      title: .squash_merge_commit_title,
      message: .squash_merge_commit_message
    }
    else error("squash title/message defaults are not PR_TITLE and PR_BODY")
    end'
  ```

  Verify the final tool-attribution trailers are present before merging.
- Delete the branch after merge, both on GitHub and locally. First verify the
  PR is merged and its reported merge commit is on updated local `main`.
  Remote deletion is conditional because the repository normally deletes
  merged heads automatically. A squash creates a new commit instead of
  making the feature tip an ancestor of `main`, so local cleanup uses `-D`
  only after those merge checks succeed; ordinary `-d` is expected to refuse.

**Why squash:** One commit per PR keeps `main` history linear and
readable. `git revert` becomes a one-commit operation. `git bisect`
works cleanly because each commit on `main` represents a complete,
working change.

**What signs the squash commit.** A Squash-and-Merge commit is
constructed by GitHub's servers and signed with GitHub's web-flow GPG
key, not your local SSH key. This is expected: your key isn't accessible
to GitHub's servers, so attributing the signature to it would be
inaccurate. The `Author` field still names you (you authored the
content), and the original PR commit retains your signature on the PR
record. For local verification of squash commits, import GitHub's
web-flow public key per Section 7 ("Local Verification"). GitHub's
Rebase-and-Merge option instead creates modified commits without commit
signature verification; that is another reason this workflow prohibits
it. See GitHub's [signature-verification
documentation](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification#signature-verification-for-rebase-and-merge).

---

## 6. Releases & Tags

### Semantic Versioning 2.0.0

Format: `MAJOR.MINOR.PATCH`

| Impact | When |
| ------ | --------------------------------------------------- |
| MAJOR | Breaking product or API change |
| MINOR | New backward-compatible feature or capability |
| PATCH | Backward-compatible bug fix or performance correction |
| None | Internal refactor, docs, tests, build, CI, or maintenance |

Each ordinary task PR declares its highest impact using
`major > minor > patch > none`. Record it as `SemVer impact:` in the PR
description and as `semver_impact` in the Builder receipt. Update
`CHANGELOG.md` under `[Unreleased]` in the same PR, but do **not** change
the project's version declarations. Commit type is a useful default;
the actual compatibility impact of the complete task is authoritative.

Versions change only in dedicated, user-initiated release PRs. A
release is not a build step and never happens automatically when an
ordinary task finishes.

### Release PR workflow

1. The user explicitly initiates a release. The Architect inspects the
   latest release tag and the receipt corresponding to every
   `[Unreleased]` entry to derive a MINOR target (increment MINOR and
   reset PATCH) or PATCH target (increment PATCH), then creates the task
   and `release/vX.Y.Z` branch from current `main`. An exact major target
   supplied by the user takes precedence and may represent a standalone
   product milestone even when no unreleased task declares `major`. If
   a task does declare `major` and the user supplied no target, stop and
   ask for it. Agents never choose a major target.
2. The Builder independently recomputes the highest unreleased impact
   and verifies that the result matches the task brief and branch name.
   Stop and report any mismatch before changing a version declaration.
   If an unreleased entry has no receipt or declared impact, ask the
   user to classify it. If no tag or authoritative base version exists,
   ask the user for the initial target.
3. Update every authoritative version declaration to the target. Move
   all `[Unreleased]` entries under a dated version heading, restore an
   empty `[Unreleased]` section, and replace each `[#PR]` reference with
   that PR's actual squash-commit short hash. The release-preparation PR
   does not add an entry for itself back under `[Unreleased]`.
4. Draft paste-ready release notes from the released changelog entries.
   Do not tag or publish them before the release PR is reviewed and
   merged and the user authorizes the publication step.
5. The release task receipt records `semver_impact: none` and
   `release_target: "X.Y.Z"`. The release PR packages already-reviewed
   changes; it does not create an additional product impact.

For App Store apps, the SemVer version maps to
`CFBundleShortVersionString` (marketing version). The `CFBundleVersion`
(build number) is independent and increments per submission.

While pre-1.0, user-visible compatibility changes normally declare
`minor`; fixes normally declare `patch`. The user still decides when
the product is ready for `1.0.0`, and agents do not cross that major
boundary automatically.

### Tagging

Tag after merging a release commit (typically a `release/` branch that
bumps the version and updates the changelog):

```text
set -euo pipefail

release_version="1.2.0"
release_merge_commit="$(gh pr view <PR#> --json state,mergedAt,mergeCommit \
  --jq 'if .state == "MERGED" and .mergedAt != null and .mergeCommit.oid != null then .mergeCommit.oid else error("release PR is not verified as merged") end')"
git switch main
git pull --ff-only origin main
if ! git merge-base --is-ancestor "$release_merge_commit" main; then
  echo "ERROR: verified release merge commit is not on local main; tag not created." >&2
  exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: worktree or index is dirty; tag not created." >&2
  exit 1
fi
git tag -s "v$release_version" -m "Release $release_version"
git push origin "v$release_version"
```

Run this only after the user authorizes tagging and publication. Every merge
query, synchronization, ancestry, and cleanliness check must succeed before
creating the tag; do not continue manually after an earlier command fails.

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

Every repository has a project-specific `.gitignore` committed at the
root from the first commit. Start with the workflow-safe scaffold seed,
then add only the language, toolchain, IDE, generated-output, local
configuration, and secret patterns that apply to that project. The
examples below are menus, not universal blocks to copy unchanged.

Never commit secrets; if one is committed accidentally, rotate the
secret first, then remove it from history with `git-filter-repo` or the
BFG Repo-Cleaner.

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
- Keep `history/prompts/*` ignored while allowing
  `history/prompts/.gitkeep`; the Architect-to-Builder handoff depends
  on this boundary.
- Add an ignore only when the project actually produces or locally owns
  that path. Do not hide potentially meaningful source files merely
  because another language or editor treats the same name as generated.

---

## 9. Repository Hygiene

### Root Project Files

| File | Purpose |
| ---------------- | ---------------------------------------------------- |
| `README.md` | What the project is, how to build/run it |
| `LICENSE` | License text when a license has been selected; may be absent for a private proprietary project |
| `.gitignore` | See Section 8 |
| `CHANGELOG.md` | Human-readable release history (Keep a Changelog) |
| `.gitattributes` | Line-ending normalization |

`README.md`, `.gitignore`, `.gitattributes`, and any `LICENSE` are
project-specific. Fill in or tailor their scaffold versions before the
first commit. Do not assume an open-source license: when a private
project has not selected one, omit `LICENSE` and state in the README
that the project is proprietary and no license is granted.

### Workflow identifiers

New task and decision records use distributed, chronologically sortable
identifiers:

```text
TASK-YYYYMMDDTHHMMSSZ-ssss-short-slug.md
ADR-YYYYMMDDTHHMMSSZ-ssss-short-slug.md
```

The timestamp is the record's UTC creation time. The suffix is four
lowercase base32 characters (`[a-z2-7]{4}`). The stable identifier stops
before the human-readable filename slug. Confirm the candidate ID is
unused and regenerate the suffix on collision; never allocate by
scanning for a "next" number. Historical sequential IDs remain valid
and must not be renamed.

### Builder receipt schema

Each new or migrated task-scoped Builder record begins with
schema-versioned, strict JSON front matter. JSON is valid YAML, but the
stricter serialization lets every scaffold validate receipts with
Python's standard library instead of adding a project-language YAML
dependency.

- `history/logs/receipt.schema.json` is the normative object schema.
- `.git/hooks/validate-builder-receipt.py` enforces that schema plus
  cross-field invariants that JSON Schema cannot express concisely. It is
  installed beside `.git/hooks/pre-commit`; both are local Git runtime files,
  not tracked project artifacts.
- `.git/hooks/pre-commit` validates each staged task-record blob with the
  installed validator and the schema from the same index snapshot. It
  self-tests that runtime/schema pair whenever a receipt or schema changes.
  Its integrity inventory includes deletions of tracked workflow records, so
  a deletion-only change cannot orphan a task or record.
- A task brief and its sole Builder record use the same filename under
  `history/tasks/` and `history/logs/`. The validator enforces that
  exact filename identity; the hook enforces one task and one record per
  stable task ID in the resulting index.
- Schema version 3 defines typed evidence, automated/manual
  verification, and known-deviation objects. Unknown fields fail
  validation. Automated `passed` results require exit code `0`, `failed`
  results require a nonzero exit code, and `not_run` requires null;
  incompatible changes require a schema-version bump.
- Historical receipts keep their recorded schema version. If an old
  receipt is edited, migrate its front matter to the current schema as
  part of that change.
- The active hook and validator are installed under the private Git directory,
  so content checks scan every staged project file without a hook-source
  exception.

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

Choose the section from the delivered outcome, not mechanically from
the Conventional Commit type. Apply the first matching row to each
distinct release-facing outcome; one PR reference may appear in more
than one section only when the PR genuinely delivers independent
outcomes. Nested detail under one entry is preferable to splitting one
outcome into several bullets.

| Delivered outcome | Changelog section | Typical commit type |
| ----------------- | ----------------- | ------------------- |
| Security vulnerability fixed or security posture materially hardened | `Security` | `fix`, `build`, `chore` |
| Supported capability, API, or behavior removed | `Removed` | `feat`, `refactor`, `chore` |
| Capability, API, or behavior marked for future removal | `Deprecated` | `feat`, `docs`, `chore` |
| Defect corrected, including a backward-compatible performance correction | `Fixed` | `fix`, `perf` |
| New backward-compatible user or developer capability | `Added` | `feat` |
| Existing user-visible behavior, API, or shipped documentation changed | `Changed` | `feat`, `refactor`, `docs` |
| Noteworthy engineering-only change with no user-visible effect | `Changed (internal)` | `refactor`, `build`, `ci`, `test`, `chore`, `docs` |
| No notable release-facing or future-maintainer value | no entry | `style`, routine internal maintenance |

The commit type remains a useful consistency check, but it cannot be
the classifier: Conventional Commits has no required `security`,
`removed`, or `deprecated` type, and the same type can produce different
release outcomes. If one change appears to fit multiple rows, use the
most specific outcome; `Security`, `Removed`, and `Deprecated` take
precedence over generic `Fixed`, `Added`, or `Changed` wording.

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
parentheses at the end of the bullet, such as
`(ADR-20260828T154703Z-a7f2)`. This is a
separate reference from the PR/hash: PR and hash point to the diff,
the ADR points to the reasoning. Not every entry has one; add it
wherever an ADR exists for that change. Always use the ADR's full
stable ID.

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
- Require conversation resolution before merging: ON
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
  - Default commit title: Pull request title (`PR_TITLE`)
  - Default commit message: Pull request title and description (`PR_BODY`)
- Allow merge commits: OFF
- Allow rebase merging: OFF
- Always suggest updating pull request branches: ON
- Automatically delete head branches: ON

Local rebasing, amending, and commit reordering are allowed only before
a branch's first push. Never rebase `main`. After a feature branch is
published, its history is append-only: add corrective commits, or merge
the latest `origin/main` into the feature branch to resolve divergence,
then push normally. Squash and Merge will still produce one commit on
`main`.

---

## 11. Things That Must Never Happen

These are hard rules, not style preferences.

- **Never force-push any branch.** Do not use `--force` or
  `--force-with-lease`. Branch protection enforces this on `main`; this
  policy extends the same rule to feature and release branches.
- **Never rewrite published history.** Once a commit is pushed, it is
  immutable. Add a corrective commit, use `git revert` to undo, or merge
  the latest `origin/main` into the feature branch when it must be
  brought up to date. Unpublished local commits may still be reordered,
  squashed, or amended before the branch's first push.
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
git pull --ff-only origin main
git switch -c feat/add-csv-export

# During work — repeat after each working, testable piece
git status
git diff
git add <specific files>
git diff --staged
git commit -m "feat(export): add CSV export button to inventory list"

# Push and open PR
git push -u origin feat/add-csv-export
gh pr create --base main \
  --title "feat(export): add CSV export button to inventory list" \
  --body-file /tmp/pr-description.md

# After squash merge on GitHub
# Run the complete fail-closed post-merge cleanup block from Section 2.
# Do not omit its merge, ancestry, remote-lookup, fetch, or deletion gates.
```

---

## 13. Instructions for AI Coding Assistants

When you are an AI assistant working in this repository, the following
are non-negotiable:

1. **Read this document at the start of every session** before making
   any commits or branch operations.
2. **Never commit directly to `main`.** Always create a properly named
   feature branch first.
3. **Preserve the project-owned AI attribution for your tool** (Section
   4):
   - **Claude Code:** use the shared `.claude/settings.json`, then
     inspect the actual commit or PR text and ensure it contains exactly
     one `Co-Authored-By: Claude Code <noreply@anthropic.com>` trailer.
     Do not set `attribution.commit` or `attribution.pr` to empty strings
     in any settings file.
   - **Codex:** manually append
     `Co-Authored-By: Codex <noreply@openai.com>` to every
     Codex-assisted commit. Do not rely on the removed
     `codex_git_commit` feature or `commit_attribution` setting.
   - **Any other tool:** if it has no built-in attribution mechanism,
     manually append a `Co-Authored-By: <Tool Name> <noreply@...>`
     trailer per Section 4.
   - Put the same exact trailer or trailers exactly once at the end of
     the PR body so Squash and Merge preserves attribution on `main`.
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
    unstage = reset HEAD --
    amend = commit --amend --no-edit
```
