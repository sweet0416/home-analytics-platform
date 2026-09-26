# HAP login redesign QA

Source visual truth: `C:/Users/ediso/AppData/Local/Temp/codex-clipboard-38176369-7f79-490a-af90-db7f45a63392.png` (1672 × 941 px).

Implementation screenshots (all at device scale 1, native CSS viewport size):

- 1920 × 1080: `../../artifacts/hap-login-redesign/login-1920x1080.jpg`
- 3440 × 1440: `../../artifacts/hap-login-redesign/login-3440x1440.jpg`
- 390 × 844: `../../artifacts/hap-login-redesign/login-390x844.jpg`

State: logged out, username prefilled as in the existing HAP login. Reference and desktop implementation share a near-identical 16:9 aspect ratio; no density resampling was needed. The reference and implementation were viewed together at full-page scale. The card and heading were also reviewed as focused regions at native 1920 × 1080 capture size; labels, borders, gradient button, and focus controls remained legible.

## Findings and decisions

- Typography: headline hierarchy and cyan–blue–violet emphasis match the brief. The implementation uses the existing local system font stack; no external font request was introduced.
- Spacing: two-column desktop composition, 556 px card, generous field spacing, and 44+ px controls hold at 1920 × 1080. At 390 × 844 the complete card fits without horizontal or vertical overflow. At 3440 × 1440 the 1900 px maximum container prevents the two sides from drifting to the edges.
- Colors: midnight navy, restrained cyan/blue/violet accents, dark inputs, and inline red error state are coherent. Keyboard focus is visibly outlined.
- Imagery: the reference's photographic modern home was intentionally translated into local geometric SVG architecture, as explicitly requested for this task. Telemetry is labeled “ILLUSTRATIVE TELEMETRY”; no real account data or API call is implied.
- Copy: the reference's nonfunctional Remember me and Forgot password controls were intentionally omitted. The sign-in and security copy describes the actual single-admin flow without new security claims.
- Responsive: full telemetry and architecture hide on mobile. A 900 px tablet pass exposed overlapping telemetry readouts; the telemetry layer now hides from 768–1000 px. A subsequent 900 × 900 capture showed no collision or overflow. The 1366 × 768 compact-height layout also has no scroll.

## Comparison history

1. Initial desktop/mobile/ultrawide capture: the comfort readout was too close to the feature labels at desktop size. Moved it lower, then captured the final 1920 × 1080 view.
2. Intermediate 900 × 900 tablet capture: telemetry labels crowded the reduced-width hero. Hid telemetry only at that breakpoint and verified a clean tablet layout afterward.

Browser interactions checked against a local synthetic auth mock: protected-route redirect, invalid login with generic alert and cleared password, Enter submission, valid login redirect, session refresh, logout, password visibility toggle, and keyboard-visible focus. This does not replace production/backend integration acceptance. No production service or credential was used.

V1 result: passed

## V2 visual refinement — 2026-09-26

The V1 screenshot remains the comparison baseline. V2 was captured from the local frontend preview at native viewport sizes, logged out, with no production service or real credentials.

- 1920 × 1080 (primary): `../../artifacts/hap-login-redesign-v2/login-1920x1080.jpg`
- 1440 × 900: `../../artifacts/hap-login-redesign-v2/login-1440x900.jpg`
- 1366 × 768: `../../artifacts/hap-login-redesign-v2/login-1366x768.jpg`
- 3440 × 1440: `../../artifacts/hap-login-redesign-v2/login-3440x1440.jpg`
- 390 × 844: `../../artifacts/hap-login-redesign-v2/login-390x844.jpg`

### Fidelity and behavior review

- Composition and typography: the master shell now caps at 1650 px. At 1920 px the title starts at x=177 and the 576 px card occupies x=1209–1785, with a 135 px right margin. The title, top navigation, feature icons, and form labels are larger than V1; the cyan-to-blue-to-soft-violet gradient remains the approved visual anchor.
- Imagery and color: telemetry was widened, its sparse nodes and three illustrative readouts enlarged, and the explanatory heading removed. The lower architectural geometry uses darker glass planes and restrained warm light rather than bright outlined windows. Cyan and violet glows remain subdued. The small “AMBIENT HOME SIGNALS” label is atmospheric copy, not an account-data claim.
- Form and copy: the wider card, 59 px inputs, 60 px action button, larger security footer, and focus state remain readable. No fake controls or new API requests were added. V1's auth-facing copy and prefilled admin username remain unchanged.
- Responsive: all five requested viewport captures were checked for document overflow; none had horizontal or vertical overflow. At 1440 and 1366 the telemetry now clips to its hero zone and its comfort readout clears the feature strip. Mobile keeps only the hero copy and form.
- Interaction: against the existing synthetic local auth mock, the password visibility toggle, generic failed-login alert and cleared password, Enter submission, protected-route redirect to `/settings`, and logout back to `/login` passed. This is a local UI regression, not production integration acceptance.

### Comparison history

1. Initial V2 captures revealed the telemetry heading and comfort readout intersecting the feature strip at 1440/1366. Removed the heading, confined the telemetry to the hero at <=1450, and lowered the comfort label.
2. Recaptured all five sizes after the correction and confirmed the overflow measurements above. The primary 1920 and ultrawide images were visually compared with the V1 baseline.

V2 result: passed for local visual review; Edison approval pending. No merge or deployment performed.
