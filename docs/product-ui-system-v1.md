# HAP Product UI System V1

The approved Login V2.1 is the visual reference for authenticated screens. This pass keeps the existing sidebar, routes, Element Plus controls, and module behavior.

## Design language

- Deep navy background (`--hap-bg-0`, `--hap-bg-1`) with one quiet blue ambient field.
- Cyan marks focus and active navigation; blue marks primary actions; violet appears sparingly on secondary modules.
- Three surface levels: the overview field, regular panels, and flatter utility rows. Only the overview field carries a stronger gradient and shadow.
- Text roles: primary for decisions and values, secondary for explanations, muted for metadata. Values use tabular numerals.
- Spacing follows 4/8 px steps; radii and shadows are shared CSS tokens in `frontend/src/styles/variables.css`.
- Motion is limited to hover transitions and existing content reveal. `prefers-reduced-motion` removes these transitions.

## V1 scope

- Shell: static HAP wordmark, quieter sidebar, active navigation (auto-scrolled with a swipe cue on mobile), current page context and health in the top bar.
- Home overview: actual health, database, backend version, lottery draw/sync state, and configured Docker/PVE state. Loading, failed requests, and confirmed empty or unconfigured states are distinguished.
- Settings: grouped backup and notification panels, collapsible backup explanation, and clearer recovery warning near backup actions.
- Fund, lottery and reports inherit shared panel, metric, control, table, empty-state and focus styling. Their calculations and API calls are untouched.

## Visual QA

Screenshots in `artifacts/hap-product-ui-v1/` were captured from the local Vite frontend against an isolated local backend with an empty SQLite database and a synthetic administrator login. They do not contain production data. The screenshot set covers dashboard widths 1920, 1440, 1366, 3440 and 390; settings 1920 and 390; fund, lottery and reports at 1920. No page had document-level horizontal overflow in those captures.

The local preview disabled backup, infrastructure notification, lottery sync, and fund NAV schedulers. Docker and PVE integrations were unconfigured. Screenshots therefore show real empty-state responses from the current backend, not invented production metrics. Dashboard layouts at 1024×768 and 768×1024 were also checked for two-column layout and zero document overflow.
