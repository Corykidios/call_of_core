# Security Policy

## The core premise and its implications

Call of Core is a clipboard-mediated protocol layer that lets any AI capable
of emitting a fenced JSON block invoke local or remote capabilities. This is
powerful. It means the attack surface is your clipboard.

Read this document before running the watcher in any context beyond personal
experimentation.

---

## Credential handling

**Never commit tokens to git.** The watcher reads `MEMORY_PLUGIN_TOKEN` from
the environment. Set it in your shell profile or a local `.env` file that is
listed in `.gitignore`. Never paste a real token into `mp-watcher.py` itself.

If you believe a token has been exposed in a public repo (even briefly, even
after a history rewrite), treat it as compromised:
1. Revoke it immediately in MemoryPlugin's dashboard
2. Generate a new token
3. Update your local environment

---

## Clipboard trust boundary

The watcher fires on **any clipboard content** containing a valid fenced block.
This includes content you copied from:
- Untrusted websites
- Attacker-controlled AI outputs
- Shared documents with hidden text
- Emails or chat messages with embedded blocks

**Current behavior:** the watcher waits 2 seconds and fires unless you copy
something else. This is a cancel window, not a permission model.

**Do not run the watcher** while copying content from sources you don't trust.

---

## Action categories

The watcher currently supports two protocols with the following risk profiles:

| Action | Protocol | Risk | Auto-fire safe? |
|---|---|---|---|
| ua_info | ua | Read-only | Yes |
| ua_search | ua | Read-only | Yes |
| ua_node | ua | Read-only | Yes |
| ua_layer | ua | Read-only | Yes |
| ua_tour | ua | Read-only | Yes |
| mp search | mp | Read-only | Yes |
| mp get | mp | Read-only | Yes |
| mp get_buckets | mp | Read-only | Yes |
| mp recall_chat | mp | Read-only | Yes |
| mp store | mp | **Write** | Use caution |

Future protocols that mutate files, send messages, execute commands, or
control devices should require explicit confirmation before the watcher fires.
This confirmation model is planned for a future version.

---

## Planned security improvements

- Per-action confirmation tiers (read / write / dangerous)
- Allowlist of permitted actions via config
- `--dry-run` mode that parses blocks but makes no calls
- `--confirm-writes` flag requiring keypress before write actions
- Schema validation per protocol before dispatch
- Local audit log with timestamp, protocol, action, result status

---

## Reporting vulnerabilities

If you find a security issue in this repository, please open a GitHub issue
marked **[SECURITY]** or contact the maintainer directly before public
disclosure. This is a small personal project; response time is best-effort.

---

## The honest summary

This is a bridge. Bridges can be crossed from both directions. The 2-second
cancel window is enough for personal use with trusted AI sessions. It is not
enough for any deployment where untrusted text can reach your clipboard. Build
accordingly.
