# DMG Installer Design QA

## Evidence

- Source visual truth: `installer/dmg-background.png`
- Rendered implementation: `assets/macos-dmg-installer-v3.2.2.png`
- Full-view comparison: `/private/tmp/antarctic-atlas-dmg-design-qa.png`
- Focused lower-region comparison: `/private/tmp/antarctic-atlas-dmg-design-qa-focus.png`
- Viewport: 680 × 440 Finder window, including the compact title bar
- Source pixels: 680 × 440
- Implementation pixels: 680 × 440
- CSS size: not applicable; this is a native Finder window
- Density normalization: both comparison inputs were normalized to 680 × 440 at 1×
- State: read-only DMG mounted by double-click, Finder icon view, app and
  `/Applications` shortcut visible

## Findings

- No actionable P0, P1, or P2 differences remain.
- Fonts and typography: the branded title, instruction, and system footer stay
  centered and readable. Finder supplies the two item labels in its native font,
  which is the expected platform behavior.
- Spacing and layout rhythm: the 112 px icons align with the two low-profile
  frosted pedestals, the drag arrow remains unobstructed, and the title and footer
  retain safe margins in the real Finder content area.
- Colors and visual tokens: the midnight navy, ice blue, and restrained cyan
  aurora remain consistent between the source asset and the mounted image.
- Image quality and asset fidelity: the final raster background remains sharp at
  its native 680 × 440 size; Finder uses the real app and Applications icons
  rather than baked-in approximations.
- Copy and content: `ANTARCTIC ATLAS`, `Drag to Applications to install`,
  `APPLE SILICON`, and `macOS 15+` are correct and unclipped.

## Focused Comparison

The lower-region comparison was required because the Finder labels, pedestal
alignment, alias badge, and system-requirements footer are too small to judge
reliably from the full view alone. The focused evidence confirms that both black
Finder labels sit on the pale pedestals and the footer is fully visible.

## Comparison History

1. The first mounted low-pedestal build (`/private/tmp/antarctic-atlas-dmg-before-footer-fix.jpeg`)
   had a P2 issue: the system-requirements footer was clipped by the bottom of
   Finder's content region.
2. The footer was moved upward while the selected low-profile pedestals and all
   other composition elements were preserved.
3. The DMG was rebuilt, mounted again by double-click, and recaptured at the same
   680 × 440 state. The final full and focused comparisons show the footer fully
   visible with no new P0, P1, or P2 issue.

## Follow-up Polish

- P3: Finder's native icon rasterization and screenshot compression soften the
  app and folder edges slightly compared with the source artwork. This is an
  expected system-rendering difference and does not require a product change.
- P3: the Applications icon is about 15 px left of the right pedestal's visual
  center. A future polish pass could move its Finder coordinate from 510 to
  approximately 525 without changing the selected background.
- P3: the baked arrow sits roughly 10–15 px below the icons' optical center;
  moving it slightly upward would improve geometric balance but is not needed
  for comprehension.
- P3: the requirements footer is fully visible but intentionally small and
  light at 1×. A future asset revision could increase its size or brightness
  slightly while preserving the current low-profile composition.

## Implementation Checklist

- [x] Selected low-profile pedestal direction preserved
- [x] Real Finder icons and labels used
- [x] Drag arrow clear and centered
- [x] Footer fully visible
- [x] Final mounted DMG visually recaptured and compared

final result: passed
