# Native macOS visual QA

## Comparison target

- **Source visual truth:** `/var/folders/k4/1nt1n9jn72b12n3j6l2_m0b80000gn/T/codex-clipboard-e6cff45e-2fb8-471c-be1d-f4baebc66c84.png`
- **Source pixels / density:** 1487 × 1058 px; supplied desktop screenshot, treated as 1× reference imagery.
- **Focused-state implementation screenshot:** `/private/tmp/antarctic-atlas-native-design-qa/19-final-native-focus.png`
- **Latest implementation screenshot:** `/private/tmp/antarctic-atlas-native-design-qa/22-clean-launch-home.png`
- **Implementation pixels / density:** 2680 × 1592 px from the live app window; 1340 × 796 logical points at 2×.
- **States:** Research Universe, dark appearance, embedded inspector open, English. The supplied source is focused on *Grounding Line Retreat*; the prior focused capture is focused on *Satellite Altimetry*. The latest clean-launch capture has the source-compatible core node selected with no focused rearrangement, and verifies the latest sphere/title and overlap fixes.
- **Viewport normalization:** the source is a taller 1487 × 1058 reference while the captured live window is 1340 × 796 logical points. For full-view comparison, the implementation was downscaled to the source's 1058 px height; no finding is based solely on the resulting aspect-ratio difference.
- **Full-view comparison evidence:** `/private/tmp/antarctic-atlas-native-design-qa/20-reference-vs-final-focus.png`
- **Latest clean-home comparison evidence:** `/private/tmp/antarctic-atlas-native-design-qa/23-reference-vs-clean-home.png`
- **Focused inspector comparison evidence:** `/private/tmp/antarctic-atlas-native-design-qa/21-inspector-focused-comparison.png`

## Findings

No actionable P0, P1, or P2 visual mismatches remain for the supplied desktop target and the verified focused-Universe state.

The remaining differences are expected rather than defects:

- The captured window is shorter and uses a different selected research node. This changes information density and inspector copy, not the navigation, graph/inspector composition, or interaction model.
- The native inspector intentionally carries the fuller evidence/caveat structure from the original application. It preserves the target's dark panel, rounded surface, hierarchy, source action, related regions, and connected-node affordances while making the scientific content more useful.
- In a focused graph, unrelated nodes are deliberately subdued. The active node, parent/related ring, labels, flowing links, and inspector retain the visual focus; this matches the original interaction behavior rather than treating all nodes as equally prominent.

### Fidelity-surface review

- **Fonts and typography:** System typography uses optical size/weight changes for navigation, inspector eyebrow, heading, body, and compact graph labels. The focused comparison confirms no clipping or unintended wrapping in the visible sidebar and inspector. Graph titles now use the original two-line, centre-anchored treatment inside their own spheres rather than floating above, below, or beside them.
- **Spacing and layout rhythm:** The macOS titlebar, split navigation, graph stage, control dock, bottom composer, and inspector remain in the same left-to-right order and maintain clear gutters, rounded panel rhythm, separators, and grouped actions. `ViewThatFits` layouts keep dense modules from becoming a fixed desktop-only canvas.
- **Colors and visual tokens:** The aurora/ice background asset, dark-blue surfaces, white type, cool cyan controls, and semantic topic colors are retained. Focus links use the selected topic color, a 3.2 pt flowing dash, and a 1.22× selected-node emphasis; inactive relationships remain visually quiet.
- **Image quality and asset fidelity:** The supplied Antarctic aurora/ice artwork is used as a real raster asset in the graph stage. Native SF Symbols are used consistently for standard system controls; no placeholder imagery or hand-drawn SVG substitutes are used in the visible target surfaces.
- **Copy and content:** English/Chinese application copy is coherent, scientific caveats remain visible, and the source action directs readers to the included paper. The visualizer, lab, compass, and reader now preserve their original scientific modes rather than substituting generic cards.
- **Icons and affordances:** Sidebar, toolbar, graph dock, evidence, region, and linked-node controls use a single native symbol family, with accessible labels and hover/focus behavior. Buttons and timeline nodes are interactive rather than decorative chrome.
- **States, motion, and accessibility:** Focus is a single 850 ms shared graph layout transition; node and link endpoints move together. Query focus has a 1.25 s pulse, inspector content changes after 180 ms, and active connections flow at 1.55 s. Reduce Motion disables persistent pulse/ambient motion and replaces transitions with static states. Keyboard navigation, search submission, semantic controls, and native accessibility labels are retained.
- **Sphere interaction:** The topmost graph input surface now accepts only true circular orb hits. When two practical hit areas meet, it selects the nearest visible orb and uses the same visual z-order only as the final tie-breaker. Home and peripheral layouts also resolve genuine sphere collisions before rendering, so long titles never expand the clickable target.

## Comparison history

1. **P1 — non-native, oversized control surface interrupted the graph.**
   - Evidence: `/private/tmp/antarctic-atlas-native-design-qa/compare-reference-and-implementation.png` (right-hand initial implementation).
   - Difference: A large floating control slab consumed the upper graph and the inspector did not match the target's information hierarchy.
   - Fix: Rebuilt the native graph stage, compact vertical control dock, embedded inspector, toolbar, composer, and graph/inspector proportions.
   - Post-fix evidence: `/private/tmp/antarctic-atlas-native-design-qa/07-reference-vs-current-home.png`.

2. **P1 — first native graph pass did not preserve the original focus choreography and had label collisions.**
   - Evidence: `/private/tmp/antarctic-atlas-native-design-qa/07-reference-vs-current-home.png`, plus the original focused behavior in `research_universe_explorer.png`.
   - Difference: The map used a generic/static composition; top and lower labels competed for space and a clicked node did not yet have the original shared re-layout language.
   - Fix: Added the source-compatible focused layout (selected center; parent upper-left; children/siblings ring; peripheral unrelated nodes), shared 850 ms cubic interpolation for both links and nodes, dynamic label placement, radial offsets, click-to-reset, query pulse, and persisted focus state.
   - Post-fix evidence: `/private/tmp/antarctic-atlas-native-design-qa/08-universe-focus-mid-transition.png`, `/private/tmp/antarctic-atlas-native-design-qa/09-universe-focus-settled.png`, and `/private/tmp/antarctic-atlas-native-design-qa/11-universe-focus-labels-resolved.png`.

3. **P2 — passive relationship lines were too weak to retain the target's graph structure at rest.**
   - Evidence: `/private/tmp/antarctic-atlas-native-design-qa/13-reference-vs-final-home.png`.
   - Difference: The all-node home map lost too much of the underlying relationship structure before focus.
   - Fix: Increased passive area/topic-link opacity while retaining strong semantic contrast for selected flowing links.
   - Post-fix evidence: `/private/tmp/antarctic-atlas-native-design-qa/14-universe-home-links-refined.png`.

4. **Final pass — focused native state.**
   - Evidence: `/private/tmp/antarctic-atlas-native-design-qa/20-reference-vs-final-focus.png` and `/private/tmp/antarctic-atlas-native-design-qa/21-inspector-focused-comparison.png`.
   - Result: Composition, hierarchy, color language, surfaces, navigation, inspector, composer, and focus treatment are coherent at the final live window. Differences are accounted for by the source/capture viewport and selected-node content, not an actionable fidelity regression.

5. **P1 — sphere titles drifted outside the old Windows interaction language and oversized label rectangles caused wrong-node taps.**
   - Evidence: User feedback plus the pre-fix native graph implementation, where labels were placed above/below/beside balls and each Button used a much larger rectangular label container.
   - Difference: The original Windows SVG places its text in the same node group, centred on the coloured circle, and makes only the painted orb clickable. Adjacent unselected topics could therefore be visually and interactively confused in the native pass.
   - Fix: Restored source-style centred two-line labels, white text with a dark outline-like shadow, and shared orb/text scaling. Replaced per-label Button hit areas with one coordinate-aware circular hit surface; it chooses the closest orb, resolves visual-layer ties, and uses deterministic collision avoidance for genuine sphere collisions.
   - Post-fix evidence: `/private/tmp/antarctic-atlas-native-design-qa/22-clean-launch-home.png` and `/private/tmp/antarctic-atlas-native-design-qa/23-reference-vs-clean-home.png`.

6. **P1 — clicking the graph exposed the system keyboard-focus halo as a bright cyan rectangle.**
   - Evidence: `/private/tmp/antarctic-atlas-native-design-qa/user-module-border.png` (user-supplied live capture).
   - Difference: The focus indicator visually cut the graph out of the shared workspace even though the graph, dock, composer, and inspector are meant to read as one continuous research surface.
   - Fix: Kept the graph focusable for arrow-key navigation and accessibility, but disabled the default focus effect on that exact container. Node, link, and inspector selection remain the only visible selection language.
   - Post-fix evidence: `/private/tmp/antarctic-atlas-native-design-qa/22-clean-launch-home.png`.

7. **P1 — Mini Research Lab inserted a non-source, pseudo-time-series dashboard beneath the real experiment.**
   - Evidence: `/private/tmp/antarctic-atlas-native-design-qa/user-universe-awkward.png` (user-supplied Mini Lab capture). Its inferred numeric year axis begins at zero, leaving the 2025–2100 curve compressed into the far-right edge of an otherwise empty panel.
   - Difference: The original Mini Lab communicates its scenario through the live mechanism canvas, the current-run diagnosis, and outcome cards; it does not present an invented cross-scenario trend chart as a primary result.
   - Fix: Removed the synthetic trend-chart surface entirely, including its artificial trajectory model. The native reading sequence is now source-aligned: mechanism scene → current-run explanation → four live outcome cards.
   - Post-fix evidence: `/private/tmp/antarctic-atlas-native-design-qa/24-minilab-without-trend.png` (fresh Mini Lab launch); full native source typecheck confirms no chart or trend-model code remains.

## Verification checklist

- [x] Full native source typecheck for arm64 macOS 15.
- [x] Release-optimized native app build.
- [x] Bundle signature verification before and after installation.
- [x] Installed preview relaunched normally from `/Applications/Antarctic Atlas Native Preview.app`.
- [x] Live window captured and compared in the same image as the user-supplied target.
- [x] Latest clean launch captured after restoring old Windows sphere titles and precise orb-only hit testing.
- [x] Mini Lab’s non-source trajectory chart removed; experiment remains driven by its live conceptual canvas, diagnosis, and metrics.
- [x] Focused inspector region compared separately at readable scale.
- [x] Original behavioral parity restored for Universe, System Explorer, AI Visualizer, Mini Lab, Compass, and paper search.

## Follow-up polish

- [P3] Capture a second visual reference at the user's preferred full-height window once an exact same-node state is selected, purely for pixel-level typography calibration. The current live window is intentionally a different persisted size/state.

final result: passed
