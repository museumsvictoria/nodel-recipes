# WebUI v2 Updater

Opt-in installer for [Nodel WebUI v2](https://github.com/mcartmel/nodel-webui-v2)
during the alpha and beta period. Deploy this recipe on any host that should
carry the V2 overlay.

## What it does

- Installs or updates the V2 entry pages (`nodes.html`, `nodel.html`,
  `toolkit.html`, and `components.html`) and the `v2/` asset tree under
  `<hostroot>/custom/content/`
- Verifies the release ZIP against its published SHA-256, then every extracted
  file against the per-file inventory in the release's `release.json`. It also
  requires a matching GitHub artifact attestation and checks the repository,
  tag, source commit, and publishable state before activation
- Bounds download and extraction sizes, then activates each release with a
  recoverable staged swap. Interrupted swaps are restored when the node starts
- Keeps the previous managed set for **Rollback**. Call **Rollback** again to
  return to the newer set
- Leaves `index.htm` alone by default so the V1 landing page stays in place.
  Enable **Also install index.htm** to make V2 the landing page. Roll back
  before changing this option for an existing installation
- Runs scheduled checks in notify-only mode. Installing is always an explicit
  operator action
- Requires no nodehost restart; the host picks up the pages immediately

## Integrity

After each successful install, the updater stores the SHA-256 inventory for
the files it activated. **CheckForUpdates** reports **InstallationIntegrity**
as:

- `Verified` when every managed file matches the installed release
- `Modified` when a managed file is missing or changed, or an unexpected file
  appears under `v2/`
- `Unknown` when no installed inventory is available, including after an
  upgrade from an earlier version of this recipe

Run **Update** with the installed release tag to replace local changes with a
fresh, verified copy of the published release. A verified same-version update
is a no-op, while a repair preserves the existing rollback generation.

## State

The updater keeps its state outside the web-served tree under
`<hostroot>/custom/.webui-v2-updater/`: the `installed.json` marker, one
`backup/` generation, and transient download, staging, and transaction files.
A host-wide file lock prevents two updater actions from changing this state at
the same time.

## Requirements

- Nodel host new enough to serve `custom/content` (2.2.1+, present since 2017)
- One WebUI v2 Updater node per host
- A tag-triggered GitHub release with an artifact attestation for the ZIP
- Outbound HTTPS to api.github.com / github.com
- For v2's WebSocket transport the host needs a jar with unified HTTP/WS
  ports (Nov 2022, rev 493+); older hosts fall back to polling
