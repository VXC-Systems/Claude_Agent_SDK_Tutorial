---
name: publish-audit
description: Audit this project for anything that must not reach a public GitHub repo — live API keys, tokens, .env files, credentials in URLs, private or employer data, and machine-specific paths that leak a username. Triggers - "security audit", "is this safe to publish", "check for secrets", "before I push to GitHub", "audit before publishing", "any leaks". Read-only; reports findings and never edits or deletes.
argument-hint: [optional path to audit; defaults to the whole Agent SDK project]
allowed-tools: Read, Glob, Grep, Bash
context: fork
---

# Publish audit

Assume everything in this project is about to become **permanently public**. Find what should not
be. A secret pushed once is compromised even if the next commit removes it — git keeps history,
and scrapers index public repos within minutes.

Default scope: the whole `Agent SDK` project, including `README.md`, `CLAUDE.md`, every step
folder, and config files. Audit the path given as an argument if there is one.

## Read-only, always

Report findings. **Never** edit a file, delete anything, rewrite history, or run a git command
that writes. `git log`, `git ls-files`, `git check-ignore`, `git status` are fine; anything that
mutates is out of bounds. Rotating a leaked key is the user's call and the user's hands.

## What to check

### 1. Live credentials in tracked content

Search every file — code, markdown, notebooks, config, comments — for:

- Anthropic keys: `sk-ant-`
- Generic provider keys: `sk-`, `api[_-]?key`, `secret`, `token`, `password`, `bearer`
- Atlassian tokens (`ATATT`), AWS (`AKIA`), GitHub (`ghp_`, `github_pat_`), Google (`AIza`)
- Long opaque strings: 32+ characters of hex or base64 sitting in an assignment or URL
- Private key blocks: `BEGIN RSA PRIVATE KEY`, `BEGIN OPENSSH PRIVATE KEY`

**Distinguish a real secret from a placeholder.** `sk-ant-api03-your-key-here` is documentation and
is fine. A high-entropy string that looks like the real thing is a `BLOCKER`. When you genuinely
cannot tell, report it and say you could not tell — never guess it is safe.

**Never print a suspected live secret in full.** Give the file, the line, and enough of a prefix to
identify it (e.g. `sk-ant-api03-TXK…`). The audit report is itself a document that may be shared.

### 2. Credentials in URLs

A key in a query string (`?apiKey=…`, `?token=…`) is worse than one in a header: URLs are written
to server logs, proxy logs, browser history, and stack traces. Flag every occurrence — including
ones built by string interpolation at runtime from an environment variable, because the assembled
URL still reaches the logs.

### 3. Files that should never be committed

- `.env`, `.env.*`, anything ending `.env`
- `*.pem`, `*.key`, `credentials.json`, `service-account*.json`
- `.venv/`, `__pycache__/`, `*.pyc`
- `uv.lock` is fine to commit; a lockfile is not a secret

For each, check whether it is actually **tracked or ignored**:

```
git ls-files --error-unmatch <path>     # tracked?
git check-ignore -v <path>              # ignored, and by which rule?
```

An untracked-but-unignored secret file is still a `BLOCKER` — one `git add .` away from disaster.

### 4. `.gitignore` fitness for a standalone repo

This project currently sits inside a larger workspace and may be relying on **that** workspace's
`.gitignore`. Those rules do not travel when the folder becomes its own repo. Verify this project
has its own `.gitignore` covering at minimum `.venv/`, `.env`, `__pycache__/`, `*.pyc`. Missing =
`BLOCKER` before first push.

### 5. Private, employer, or personal data

This is a public certification-prep project. It must not contain:

- Employer-internal names, systems, customer names, ticket IDs, or business data
- Internal hostnames, private endpoints, or credential file paths belonging to work systems
- Real personal data of any third party
- Anything under NDA

### 6. Machine-specific paths and identity leakage

Absolute paths like `/Users/<name>/…` leak the author's username and break for every reader. Flag
them in code as a portability defect and in prose as minor identity leakage. Paths inside a
`~`-relative form are fine.

### 7. Git history

If a `.git` directory exists, check whether any currently-flagged secret also appears in history:

```
git log --oneline -S'<distinctive-fragment>' --all
```

A secret removed from the working tree but present in history is **still leaked** and needs key
rotation, not a delete. Say so explicitly.

## Output

Order findings by severity, worst first:

| Severity | Meaning |
|---|---|
| `BLOCKER` | Do not push. A live secret, or a path to one. |
| `SHOULD-FIX` | Not a live secret, but a real risk or a leak of private detail. |
| `NICE-TO-HAVE` | Hygiene and portability. |

For each:

```
[SEVERITY] file:line
What: <the issue, secret value redacted>
Why it matters: <one line>
Remedy: <what the user should do — including "rotate this key" where it has been exposed>
```

Finish with an explicit go/no-go: **"Safe to publish"** or **"Do not publish — N blockers"**. If
any live credential was ever committed, state plainly that removing it is not enough and the key
must be rotated.

A clean audit is a real and expected result. Report it as clean rather than manufacturing findings.
