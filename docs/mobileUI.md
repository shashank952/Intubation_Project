# Airway MD — Mobile UI Customization Prompts

> **What this file is:** A collection of ready-to-paste prompts you can give to your AI agent to customize the mobile app's UI. Each prompt is self-contained — copy it, paste it in chat, and the agent will implement the change.
>
> **Project location:** `D:\Minor_Project\mobile\`
> **Design system source of truth:** `mobile/src/theme/tokens.ts` (colors, shadows, radii, spacing)
> **Theme hook:** `useTheme()` → `{ c, isDark, theme, toggleTheme }` (from `mobile/src/theme/ThemeProvider.tsx`)
> **UI primitives:** `mobile/src/components/ui/` (AppButton, AppInput, Card, Select, Badge, SegmentedTabs, Banner, Skeleton, EmptyState, AppHeader)

---

## Table of Contents

1. [How to Use These Prompts](#how-to-use-these-prompts)
2. [A. Color & Theme Prompts](#a-color--theme-prompts)
3. [B. Typography Prompts](#b-typography-prompts)
4. [C. Layout & Spacing Prompts](#c-layout--spacing-prompts)
5. [D. Component-Style Prompts](#d-component-style-prompts)
6. [E. Screen-Specific Prompts](#e-screen-specific-prompts)
7. [F. Navigation & Tab Bar Prompts](#f-navigation--tab-bar-prompts)
8. [G. Animation & Motion Prompts](#g-animation--motion-prompts)
9. [H. Dark Mode Prompts](#h-dark-mode-prompts)
10. [I. Branding & Polish Prompts](#i-branding--polish-prompts)
11. [J. Advanced / Combined Prompts](#j-advanced--combined-prompts)

---

## How to Use These Prompts

1. **Copy** the prompt you want from the sections below
2. **Paste** it in the chat
3. The agent will make the change **in the design tokens first** (so it applies app-wide), then in specific components if needed
4. **To undo:** tell the agent "revert the last UI change" — the design tokens make this quick

> **Tip for consistent results:** Each prompt includes the exact file to edit, what to change, and how to verify. The agent should always keep changes inside `mobile/` and follow the neo-brutalist identity unless you ask otherwise.

---

## A. Color & Theme Prompts

### A1 — Change the primary (brand) color app-wide
```
In the Airway MD mobile app (D:\Minor_Project\mobile), change the primary brand color 
from the current yellow (#FFD900) to [NEW COLOR HERE] across the whole app.

1. Edit mobile/src/theme/tokens.ts — update the entire `brand` scale (50→950) around the new color,
   and the neo.yellow token if it maps to the brand.
2. Make sure the risk gauge, buttons (AppButton primary), active tab highlight, and AI assessment 
   cards all pick up the new color automatically (they use the tokens, so they should).
3. Verify in both light and dark mode. Keep text contrast readable (black text on the brand color).

Do not change the semantic colors (success/warning/danger) unless I ask.
```

### A2 — Change page background color
```
In the Airway MD mobile app, change the page background color used by all screens.
Edit mobile/src/theme/tokens.ts — update `colors.page.light` (currently #F5F1DC, the cream paper) 
and optionally `colors.page.dark` (currently #121212). Pick a color that keeps the neo-brutalist 
feel and doesn't clash with the white cards and black borders. Verify Login, Dashboard, and 
Settings screens render with the new background.
```

### A3 — Change card background / surface color
```
In the Airway MD mobile app, change the card/surface background color.
Edit mobile/src/theme/tokens.ts — update `colors.card.light` (currently #FFFFFF) and 
`colors.card.dark` (currently #18181B). Make sure text on cards stays readable 
(check the neutral text tokens). Verify the dashboard cards, form card, and result cards.
```

### A4 — Change the semantic class colors (Easy / Moderate / Difficult)
```
In the Airway MD mobile app, change the class colors used for the three airway predictions.
Edit mobile/src/theme/tokens.ts:
- success (Easy) — currently teal #16C2C8
- warning (Moderate) — currently amber #EAB308
- danger (Difficult) — currently red #FF5A5F
Replace [TARGET CLASS] with [NEW COLOR]: update the full 50→700 scale for that semantic family 
and make sure CLASS_STYLES and the risk gauge/legend/probability bars pick it up automatically.
Keep the colors distinguishable from each other (colorblind-friendly if possible).
```

### A5 — Custom color theme (complete redesign prompt)
```
In the Airway MD mobile app, apply a complete custom color theme:
- Primary brand: [COLOR]
- Page background (light): [COLOR]
- Page background (dark): [COLOR]
- Card background (light): [COLOR]
- Card background (dark): [COLOR]
- Easy class: [COLOR]
- Moderate class: [COLOR]
- Difficult class: [COLOR]
- Ink/borders: [COLOR]
Update mobile/src/theme/tokens.ts fully, rebuild the scales (50→950 for brand, 50→700 for 
semantic colors), and verify every screen in both light and dark mode. Ensure WCAG AA 
contrast (4.5:1) for body text and 3:1 for large text.
```

---

## B. Typography Prompts

### B1 — Change the app font
```
In the Airway MD mobile app, replace the current Inter font with [FONT NAME] from Google Fonts.
1. Install the font package with expo (e.g. npx expo install @expo-google-fonts/[font]).
2. Update mobile/src/theme/tokens.ts if it references fonts, and App.tsx (useFonts) to load 
   the new family + weights (400/500/600/700/800).
3. Update every component that sets fontFamily (they use 'Inter_400Regular', 
   'Inter_600SemiBold', 'Inter_800ExtraBold', etc.) to the new family names.
4. Keep JetBrains Mono for numbers/IDs (or replace it too if I say so).
5. Verify all screens render with the new font and that Chinese/Unicode text isn't broken.
```

### B2 — Make numbers/headings more prominent
```
In the Airway MD mobile app, make the big numbers and headings more prominent:
- The risk gauge center number (RiskPredictionCard bigNumber): increase size and make it bolder.
- Section headings (AppHeader title, card titles): increase font size slightly.
- Keep the mono font for tabular numbers. Make sure nothing clips on a small phone 
  (e.g. iPhone SE width 375).
```

### B3 — Adjust micro-label styling
```
In the Airway MD mobile app, restyle the small uppercase micro-labels (like "AIRWAY RISK SCORE", 
"CONFIDENCE", "RECENT RECORDS", "OVERVIEW"):
- Increase letter-spacing to [X]px
- Change their color to [COLOR] 
- Change their size to [X]px
These appear in StatsCard, MiniHistory, RiskPredictionCard, AiClinicalAssessment, and ReportDetail.
Update all of them consistently.
```

---

## C. Layout & Spacing Prompts

### C1 — Increase/decrease global spacing
```
In the Airway MD mobile app, adjust the global spacing rhythm.
Edit mobile/src/theme/tokens.ts — the `spacing` scale (xs/sm/md/lg/xl/2xl/3xl). 
Multiply all values by [FACTOR or new values]. Then audit the screens that use padding 
directly (styles in each screen file) and align them. Target: a consistent, breathing 
layout on a 6.1" phone. Verify no screen overflows vertically and the login card fits.
```

### C2 — Make the app more compact (dense data view)
```
In the Airway MD mobile app, make the UI more compact/dense so more data fits on screen:
- Reduce card padding from 16 to 12
- Reduce gaps between rows/items
- Make the history/reports list rows tighter
- Slightly reduce button padding (AppButton)
Keep tap targets at least 44x44pt for accessibility. Verify on a small phone.
```

### C3 — Centered vs left-aligned login card
```
In the Airway MD mobile app, change the login screen layout:
- Currently the card is centered vertically with decorative corner blocks.
- Change it to [top-aligned with the brand header at the top | card full-width with no 
  max-width | keep centered but remove the decorative blocks].
Edit mobile/src/screens/auth/LoginScreen.tsx styles accordingly.
```

### C4 — Make cards rounded vs sharp
```
In the Airway MD mobile app, change the border radius style across all cards and buttons.
Edit mobile/src/theme/tokens.ts — the `radii` scale. Currently: sm=4, md=6, lg=8, xl=10.
Change to: [VALUES]. The neo-brutalist look uses small/zero radii — if you go large, 
soften the hard shadows too so it doesn't look inconsistent.
```

---

## D. Component-Style Prompts

### D1 — Restyle buttons
```
In the Airway MD mobile app, restyle all buttons (mobile/src/components/ui/AppButton.tsx):
- Change the corner radius to [X]
- Change the shadow offset/size (currently 4x4 hard shadow)
- Change the primary button background to [COLOR] and border to [COLOR]
- Add a [new hover/pressed effect — e.g. scale down, different shadow, color shift]
This affects Login, Assessment, History export, and Settings buttons app-wide.
```

### D2 — Restyle inputs
```
In the Airway MD mobile app, restyle all text inputs (mobile/src/components/ui/AppInput.tsx):
- Change border width from 2 to [X]
- Change focus highlight color (currently brand yellow) to [COLOR]
- Change the input background to [COLOR]
- Make the error state more/less prominent (currently red border + red message)
Verify in Login (username/password), Assessment wizard, and Settings (API URL).
```

### D3 — Restyle the dropdown/select
```
In the Airway MD mobile app, restyle the Select component (mobile/src/components/ui/Select.tsx):
- Change the trigger (closed state) styling: border, shadow, height
- Change the bottom-sheet modal styling: background, handle, option highlight color
- Make the options list [scrollable with checkmark | radio-dot style | larger touch rows]
Verify in the Assessment wizard (gender, mallampati, yes/no fields).
```

### D4 — Restyle cards (global)
```
In the Airway MD mobile app, restyle all Cards (mobile/src/components/ui/Card.tsx):
- Border: currently 1px neutral. Change to [width + color]
- Shadow: currently 5x5 hard black. Change to [softer | colored | larger | none]
- Corner radius: change to [X]
Make sure the neo-brutalist identity is either preserved or intentionally replaced 
as I'm asking. Verify Dashboard, Result, History, Reports.
```

### D5 — Restyle badges / pills
```
In the Airway MD mobile app, restyle the prediction Badges (mobile/src/components/ui/Badge.tsx):
- Change to pill shape (fully rounded) OR keep square
- Add a subtle [border color change | background tint change | shadow]
- Increase/decrease size
These appear on Dashboard recent records, History rows, Reports, and ReportDetail.
```

### D6 — Restyle skeleton loaders
```
In the Airway MD mobile app, restyle the loading skeletons (mobile/src/components/ui/Skeleton.tsx):
- Change the shimmer effect from opacity pulse to [a gradient shimmer sweep | a spinner | 
  nothing (static gray blocks)]
- Change skeleton color to [COLOR]
- Make skeletons match the actual content height better (avatar circle, text lines)
```

---

## E. Screen-Specific Prompts

### E1 — Redesign the Login screen
```
In the Airway MD mobile app, redesign the login screen (mobile/src/screens/auth/LoginScreen.tsx):
- Layout: [single centered card | split layout with brand panel | full-bleed background image]
- Add: [the app logo bigger | a tagline | a version number at the bottom]
- Style the card: [shadow | border | rounded corners]
- Keep the username/password fields, show/hide password toggle, error banner, 
  Sign In button, and the "Server address" section (they're functional — don't remove them).
```

### E2 — Redesign the Dashboard (Home) screen
```
In the Airway MD mobile app, redesign the Home/Dashboard screen 
(mobile/src/screens/home/DashboardScreen.tsx):
- Currently: header (logo + title + theme toggle + LLM dot), stats card, 
  "New Assessment" CTA card, recent records list.
- Change to: [two-column stats | a hero card with total assessments | a prominent 
  gradient/prominent CTA | move recent records to a swipeable horizontal list]
- Keep pull-to-refresh and the LLM status indicator.
```

### E3 — Redesign the Assessment wizard
```
In the Airway MD mobile app, improve the Assessment wizard 
(mobile/src/screens/home/AssessmentScreen.tsx):
- Step indicator: change from the top segmented bar to [a progress bar with step numbers | 
  a vertical stepper | cards that expand]
- Make each step a separate full screen pushed via navigation (instead of one scroll with 
  switching content) — OR keep one screen but improve transitions.
- Add a [review-summary screen before submitting | sticky submit bar at the bottom]
- Keep the E/M/D/Random test buttons and all validation behavior identical.
```

### E4 — Redesign the Prediction Result screen
```
In the Airway MD mobile app, redesign the Prediction Result screen 
(mobile/src/screens/home/PredictionResultScreen.tsx):
- The risk gauge: keep the 270° arc but [make it bigger | add a color gradient | add 
  tick marks | add an animated counter that counts up to the score]
- Reorder sections: [AI report first, gauge second | gauge, probabilities, then AI]
- Add a "share result" button (uses expo-sharing) to share the prediction summary.
- Add a "save to history" confirmation or auto-note.
```

### E5 — Redesign the History screen
```
In the Airway MD mobile app, redesign the History screen (mobile/src/screens/history/HistoryScreen.tsx):
- Change the filter tabs (All/Easy/Moderate/Difficult) to [chips | a dropdown | swipeable 
  pages]
- Add [date grouping (Today/Yesterday/Older) | a date-range filter | sorting toggle]
- Keep search, CSV export, delete (admin), and pull-to-refresh.
```

### E6 — Redesign the Reports screen
```
In the Airway MD mobile app, redesign the Reports screen 
(mobile/src/screens/reports/ReportsScreen.tsx + ReportDetailScreen.tsx):
- Add [a filter by class | a search bar | a summary header with total reports]
- Report detail: improve the summary/recommendations sections with [better typography, 
  section dividers, copy-to-clipboard on the report]
- Keep the lazy report loading and fallback-source indicators.
```

### E7 — Redesign the Settings screen
```
In the Airway MD mobile app, redesign the Settings screen 
(mobile/src/screens/settings/SettingsScreen.tsx):
- Change the sections from stacked cards to [a grouped list style (iOS-like) | tiles | 
  accordion]
- Add [a version footer | an app icon preview at top | a "reset all settings" button]
- Keep: profile, dark mode toggle, API URL editor + Test Connection, system info, 
  About link, Sign Out.
```

---

## F. Navigation & Tab Bar Prompts

### F1 — Change the tab bar style
```
### F1 — Redesign the tab bar as a floating minimalist homebar

```text
In the Airway MD mobile app, redesign the bottom tab bar in
mobile/src/navigation/index.tsx (MainTabs) to match the provided reference design.

REFERENCE STYLE:
The desired navigation is a floating, minimalist black homebar:
- A single horizontal black/dark pill-shaped container floats above the bottom edge of the screen.
- The container has a large rounded/pill radius.
- It should NOT be a full-width edge-to-edge navigation bar.
- It should have clear horizontal and bottom spacing from the screen edges and respect the device safe-area inset.
- The navigation should feel visually similar to the reference: a compact floating black bar with four evenly distributed icon positions.
- Use icons only. Remove the visible "Home", "Records", "Reports", and "Settings" text labels from the tab bar.
- The active tab is indicated by a white circular/near-circular background behind the icon.
- The active icon itself should be dark/black so it has strong contrast against the white active background.
- Inactive icons should remain light/white against the black bar.
- Do NOT use the current yellow active-state pill/background.
- Do NOT add separate borders, cards, shadows, or extra boxes around individual inactive icons.
- Keep the visual treatment simple and clean; the navigation bar itself is the primary container.

LAYOUT:
- Keep exactly 4 tabs in this order:
  1. Home
  2. Records
  3. Reports
  4. Settings
- Distribute the four icons evenly across the black pill.
- Give each tab a sufficiently large press/touch area (minimum 44x44pt), even though the visible icon/background is compact.
- Keep the active white circle centered within its tab slot and sized consistently for all four tabs.
- The floating bar must not overlap or cover screen content.
- Position it above the bottom safe area rather than flush against the physical screen edge.
- Ensure the layout works correctly on small phones, large phones, and devices with gesture-navigation/home indicators.
- Ensure keyboard appearance does not create an awkward overlap or permanently push the bar into the content.

VISUAL DETAILS:
- Use the existing theme tokens and theme system where appropriate, but do not use the existing yellow brand token for the active tab.
- Black/dark navigation container.
- White active-state circle.
- Black active icon.
- White/light inactive icons.
- Keep the bar's corners strongly rounded, similar to the reference image.
- Avoid excessive shadows. If a shadow is needed to visually separate the floating bar from the page, keep it subtle and consistent with the reference.
- Do not change the page content, screen layouts, cards, typography, colors, or other components as part of this prompt.
- Do not change navigation routes, tab functionality, stack behavior, or existing navigation logic except what is required to visually implement this tab bar.

IMPLEMENTATION:
1. Inspect mobile/src/navigation/index.tsx and the existing MainTabs implementation before editing.
2. Remove the current labeled/yellow active-tab presentation.
3. Implement the floating black pill container and the white circular active indicator.
4. Preserve all existing routes, navigation behavior, screen stacks, and tab press behavior.
5. Reuse existing theme values where possible instead of introducing unnecessary hard-coded colors.
6. If the current navigation library requires a custom tabBar component to achieve this design, implement the custom tab bar inside the navigation layer rather than modifying unrelated screens.
7. Account for safe-area insets so the bar remains usable above the system gesture/home area.
8. Verify all four active states individually: Home, Records, Reports, and Settings.
9. Verify light and dark mode.
10. Verify on a narrow phone width (around 375px) and a larger phone width.
11. Run TypeScript/build checks after the change and fix only issues caused by this navigation update.

STRICT SCOPE:
- This prompt changes ONLY the bottom navigation/tab-bar UI.
- Do not redesign the Dashboard, Login, Assessment, Result, History, Reports, Settings, headers, cards, buttons, or other components.
- Do not remove any existing functionality.
- Do not rename the four tabs.
- Do not modify application content.
- Do not globally replace the Airway MD neo-brutalist design system; this is a targeted navigation component redesign.
- The final result should visually match the provided reference: a floating black rounded homebar with four icons and a white circular active state, without text labels.
```

::: 

```

### F2 — Add a 5th tab or rename tabs
```
In the Airway MD mobile app, [add a new tab called [NAME] | rename the [X] tab to [NAME]] 
in the tab navigator (mobile/src/navigation/index.tsx). If adding: create the new screen 
under mobile/src/screens/ and wire a new stack. If renaming: update the tab label and 
any navigation.navigate('...') calls that reference it.
```

### F3 — Add header styles
```
In the Airway MD mobile app, change the screen headers (mobile/src/components/ui/AppHeader.tsx):
- Currently: back button + title + subtitle on a card-colored bar.
- Change to: [transparent header over page background | larger title with a subtitle 
  below | centered title | a colored header bar]
- Apply consistently to History, Reports, ReportDetail, Settings, About, PredictionResult.
```

---

## G. Animation & Motion Prompts

### G1 — Add screen transition animations
```
In the Airway MD mobile app, add smooth screen transitions between screens.
In mobile/src/navigation/index.tsx, configure the stack navigators with 
animation options: [slide-from-right (iOS default) | fade | none | a custom 
transition]. Keep it fast (under 300ms) so it feels snappy, and respect 
AccessibilityInfo.isReduceMotionEnabled (skip animations if reduce motion is on).
```

### G2 — Animate the risk gauge counter
```
In the Airway MD mobile app, animate the risk score number in RiskPredictionCard 
(mobile/src/components/result/RiskPredictionCard.tsx) so it counts up from 0 to the 
final score over ~1 second alongside the arc sweep (currently only the arc animates). 
Use Animated with useNativeDriver: false for the text value. Respect reduce-motion.
```

### G3 — Add list item entrance animations
```
In the Airway MD mobile app, add subtle entrance animations to list items:
- History rows and Reports cards should fade+slide in when the screen loads 
  (staggered by index, ~50ms apart, max 300ms total).
- Respect AccessibilityInfo.isReduceMotionEnabled.
Implement in mobile/src/screens/history/HistoryScreen.tsx and 
mobile/src/screens/reports/ReportsScreen.tsx.
```

### G4 — Add button feedback micro-interactions
```
In the Airway MD mobile app, enhance the button press feedback in 
mobile/src/components/ui/AppButton.tsx:
- Currently: translate(2,2) + shadow shrink.
- Add: [a quick scale-down (0.98) | a brief background flash | a ripple-like highlight].
Keep it subtle and under 150ms.
```

---

## H. Dark Mode Prompts

### H1 — Tune the dark palette
```
In the Airway MD mobile app, improve the dark mode palette 
(mobile/src/theme/tokens.ts + ThemeProvider.tsx):
- Page background: currently #121212. Change to [COLOR].
- Card background: currently #18181B. Change to [COLOR].
- Borders: currently neutral.700 (#3F3F46). Change to [COLOR].
- Ensure text stays readable: check the textMuted/textFaint values against the new surfaces.
Audit all screens in dark mode after the change.
```

### H2 — Change default theme behavior
```
In the Airway MD mobile app, change how the theme is chosen on first launch:
- Currently: follows the system setting unless the user picked one.
- Change to: [always light | always dark | always ask | keep system].
Edit mobile/src/theme/ThemeProvider.tsx accordingly.
```

### H3 — Add a system/light/dark tri-state toggle
```
In the Airway MD mobile app, replace the single light/dark toggle in Settings with a 
three-option selector: System / Light / Dark (like iOS). 
Edit mobile/src/theme/ThemeProvider.tsx to store the tri-state preference 
('system' | 'light' | 'dark') and update mobile/src/screens/settings/SettingsScreen.tsx 
to render the segmented control.
```

---

## I. Branding & Polish Prompts

### I1 — Update app name, icon, and splash
```
In the Airway MD mobile app, update the app branding:
- app.json: change "name" to "[APP NAME]" and keep slug "airway-md-mobile".
- Replace assets/icon.png and the android adaptive icon foreground with [NEW ICON 
  SPEC: e.g. a stethoscope on a black square with yellow accent].
- Update the splash/loading screen colors to [COLOR].
Keep the neo-brutalist visual identity (black + yellow + cream).
```

### I2 — Add a custom app logo component
```
In the Airway MD mobile app, create a reusable Logo component 
(mobile/src/components/ui/Logo.tsx) that renders the Airway MD brand mark 
(stethoscope icon in a black rounded square with a hard shadow) at a configurable size, 
and use it in LoginScreen (large), DashboardScreen header (small), and the loading screen.
```

### I3 — Add a version footer
```
In the Airway MD mobile app, add a small version footer showing the app version 
(read from app.json via expo-constants: Constants.expoConfig.version) at the bottom of 
the Login screen and the Settings screen. Style it as a subtle mono-font text in neutral 
gray, e.g. "v1.0.0".
```

### I4 — Add a "Made with" / about splash detail
```
In the Airway MD mobile app, add a subtle footer line on the Login screen below the card: 
"Multimodal Difficult Airway Prediction — Clinical Decision Support" in small muted text, 
matching the existing neo-brutalist typography (uppercase, letter-spaced).
```

### I5 — Improve empty states
```
In the Airway MD mobile app, upgrade all empty states (mobile/src/components/ui/EmptyState.tsx):
- Add [an illustration/icon in a decorative border box | a dashed-border container | 
  a helpful action button below the text]
- Ensure copy stays: "No records yet" / "No reports yet" / "No assessment history yet".
Apply across History, Reports, and Dashboard recent records.
```

---

## J. Advanced / Combined Prompts

### J1 — Full "clean medical" theme overhaul
```
In the Airway MD mobile app, replace the neo-brutalist (hard shadows, thick borders, 
cream background) style with a clean, modern medical aesthetic:
- Remove all hard offset shadows; use soft subtle shadows (e.g. rgba black 10%, blur 12).
- Replace 2px black borders with 1px light gray borders.
- Switch the page background to a very light neutral (#F7F8FA) and cards to white.
- Keep the semantic colors for Easy/Moderate/Difficult and the brand color 
  (soften it to a more clinical blue if appropriate).
- Increase border radius on cards/buttons to 12-16px.
- Update tokens.ts and audit EVERY component + screen so nothing still uses the old 
  hard shadows. Verify light + dark mode.
```

### J2 — Full "dark tech" theme overhaul
```
In the Airway MD mobile app, replace the current look with a dark, high-tech clinical 
theme:
- Dark page background (#0A0E14), slightly lighter cards (#12181F), cyan/teal accents.
- Keep Easy/Moderate/Difficult colors but adjust their dark-mode variants for contrast.
- Thin 1px borders, subtle glow shadows on the risk gauge.
- Update tokens.ts and audit all screens.
```

### J3 — Reorder the whole app flow
```
In the Airway MD mobile app, change the primary user flow:
- Make the Assessment wizard the FIRST thing shown after login instead of the Dashboard 
  (Home tab root becomes the assessment, with stats/recent moved into a secondary tab).
- OR: keep Dashboard but auto-navigate to a fresh Assessment when it has no data yet.
Update mobile/src/navigation/index.tsx and the affected screens. Keep all existing 
features reachable.
```

### J4 — Make the app tablet-friendly
```
In the Airway MD mobile app, improve tablet support:
- On screens wider than 700px, show the Dashboard as a two-column layout 
  (stats + recent records on the left, a preview of the latest report on the right).
- Cap content width on large screens (maxWidth ~900, centered).
- Make the risk gauge and AI assessment sit side-by-side on tablets.
Use useWindowDimensions() for responsive layout. Verify in landscape and on a tablet 
simulator if available.
```

### J5 — Localization / language change
```
In the Airway MD mobile app, prepare the UI for [LANGUAGE NAME]:
- Extract all user-facing strings into a single strings file (mobile/src/i18n/strings.ts).
- Add a [LANGUAGE] translation and a language picker in Settings.
- Keep the clinical terms (Easy/Moderate/Difficult, Mallampati, TMD, BMI) in English 
  unless I specify translations for them.
- The app currently uses English copy ported from the web app — match that tone.
```

### J6 — Accessibility pass
```
In the Airway MD mobile app, run an accessibility improvement pass:
- Ensure all icon-only buttons have accessibilityLabel (Eye, Trash2, theme toggle, 
  password show/hide, back button).
- Ensure tap targets are ≥44x44pt.
- Add accessibilityRole/accessibilityState to switches, tabs, and selects.
- Verify color contrast for all text (4.5:1 body, 3:1 large).
- Respect AccessibilityInfo.isReduceMotionEnabled for the gauge, skeletons, and 
  any entrance animations.
- Test with screen reader (TalkBack/VoiceOver) narration order on Login and Assessment.
```

### J7 — Performance pass
```
In the Airway MD mobile app, run a performance pass:
- Memoize list items in History and Reports (React.memo) to avoid re-renders on scroll.
- Use useMemo for derived data (filtered lists, counts) where missing.
- Lazy-load the Assessment and Result screens (React.lazy / Suspense) if feasible 
  with React Navigation.
- Profile: avoid re-rendering the whole screen on every keystroke in the wizard 
  (check handleChange in AssessmentScreen).
- Verify 60fps scrolling on the History list.
```

### J8 — Revert to original design
```
In the Airway MD mobile app, revert the last [N] UI change(s). Restore the files to 
their committed state from git (mobile branch, commit c7eb5c2). After reverting, 
run tsc --noEmit and confirm the app still builds with npx expo export.
```

---

## Quick Reference — Files You'll Hear About

| File | What it controls |
|------|------------------|
| `mobile/src/theme/tokens.ts` | All colors, shadows, radii, spacing, class styles |
| `mobile/src/theme/ThemeProvider.tsx` | Light/dark theme logic |
| `mobile/src/components/ui/*` | AppButton, AppInput, Card, Select, Badge, SegmentedTabs, Banner, Skeleton, EmptyState, AppHeader |
| `mobile/src/components/dashboard/*` | StatsCard, MiniHistory |
| `mobile/src/components/result/*` | RiskPredictionCard (gauge), AiClinicalAssessment |
| `mobile/src/screens/auth/LoginScreen.tsx` | Login |
| `mobile/src/screens/home/*` | Dashboard, Assessment wizard, PredictionResult |
| `mobile/src/screens/history/HistoryScreen.tsx` | Patient Records |
| `mobile/src/screens/reports/*` | Reports list + detail |
| `mobile/src/screens/settings/*` | Settings + About |
| `mobile/src/navigation/index.tsx` | Tab bar, stacks, transitions |
| `mobile/App.tsx` | Fonts, providers, splash |
| `mobile/app.json` | App name, icon, splash config |


# Mobile UI Broken Layout — Responsive UI Fix

In the Airway MD mobile app, perform a **focused UI debugging and responsive-layout correction pass** based on the provided screenshots.

The screenshots show several UI elements that are currently rendering incorrectly on a mobile viewport. Your job is to inspect the existing implementation, identify the root causes, and fix the layout properly rather than applying one-off pixel hacks.

## IMPORTANT — SCOPE

This is a **UI/layout bug-fixing task**.

Do NOT:

* Redesign the application.
* Change the application's content.
* Change navigation functionality.
* Remove existing features.
* Change API/data/model logic.
* Change the assessment workflow.
* Replace the existing design system.
* Arbitrarily reduce font sizes just to make content fit.
* Hide overflowing content.
* Use hard-coded positioning that only works for one device width.

Preserve the existing Airway MD neo-brutalist visual identity and existing functionality.

The goal is to make the existing UI **properly responsive and visually stable on mobile devices**.

---

# 1. SCREENSHOT — PREDICTION RESULT

The Prediction Result screenshot shows multiple layout problems.

### Problems to fix

#### A. Bottom navigation is incorrect

The current bottom navigation is rendering as a full-width white bar attached to the bottom of the screen.

It should use the new floating navigation design specified in the updated navigation prompt:

* Floating black/dark rounded pill.
* Four evenly spaced icons.
* No visible text labels.
* White circular active indicator.
* Black active icon.
* White inactive icons.
* Proper spacing from the screen edges.
* Respect bottom safe-area insets.
* Must not cover screen content.

Do not allow the navigation bar to overlap the AI Clinical Assessment content.

---

#### B. Prediction Result content is being cut off

The screenshot shows the AI Clinical Assessment section continuing underneath/behind the bottom navigation.

Fix the screen's layout so that:

* Scrollable content can be completely accessed.
* The bottom navigation never covers content.
* The final content has sufficient bottom padding.
* Scrolling reaches the true end of the content.
* Cards are not clipped by the viewport.
* The Prediction Result screen works on small phones as well as larger phones.

If the screen uses `ScrollView`, `FlatList`, or another scroll container, inspect its `contentContainerStyle`, bottom padding, safe-area handling, and parent flex layout.

Do NOT simply move the navigation upward with an arbitrary absolute `bottom` value.

---

#### C. Risk Prediction Card sizing

The risk prediction card currently occupies a large amount of vertical space and must remain readable without creating unnecessary overflow.

Keep:

* Airway Risk Score
* Predicted intubation difficulty
* Risk gauge
* Score
* `% RISK`
* Difficulty classification
* Confidence
* Probability distribution
* Easy / Moderate / Difficult legend

Do not remove any information.

Make the internal layout responsive so the gauge and probability information remain correctly contained inside the card.

---

#### D. Risk gauge background/overflow

Inspect the gauge carefully.

The gauge should remain visually centered inside its container.

Make sure:

* The arc does not clip against the card.
* The central score remains centered.
* The gauge background does not create unintended overflow.
* The gauge scales appropriately with screen width.
* The gauge does not overlap surrounding text.
* The gauge maintains its intended proportions.

Use responsive dimensions where necessary rather than fixed dimensions that exceed the available width.

---

# 2. SCREENSHOT — PATIENT ENTRY / ASSESSMENT

The Patient Entry screenshot has a much more serious responsive-layout problem.

The assessment fields are being compressed into extremely narrow columns.

For example, labels such as:

* Previous Airway Records
* Arthritis
* Diabetes
* Down Syndrome
* Snoring
* Sleep Apnea
* Voice Changes
* Difficulty Swallowing
* Can't Lie Flat
* Swelling
* Previous Neck Fracture
* Previous Emergencies/ICU

are wrapping almost every word onto a separate line.

This indicates that the form is attempting to render too many fields horizontally inside a mobile-width container.

## REQUIRED FIX

Do NOT solve this by simply reducing the font size.

The assessment form must have a proper mobile-responsive layout.

Inspect the existing assessment form implementation and determine whether it is using:

* a fixed-width grid,
* fixed column widths,
* a desktop-oriented flex row,
* percentage widths that become too small,
* or another layout causing the compression.

Then implement an appropriate responsive layout.

### Mobile behavior

On narrow mobile screens:

* Do not force 12+ assessment fields into one horizontal row.
* Fields must have enough width for their labels.
* Labels should wrap naturally at reasonable word boundaries.
* Dropdown/select controls must remain usable.
* Controls must not overlap.
* Text must not be clipped.
* Each field must have an adequate touch target.
* Maintain clear spacing between fields.

A responsive grid is acceptable, for example:

* 1 column on very narrow screens.
* 2 columns where there is enough width.
* More columns only when the available width genuinely supports them.

Use the actual available screen width to determine the layout.

---

# 3. ASSESSMENT CARD RESPONSIVENESS

The large assessment card currently contains:

* Patient Entry header
* E / M / D / Random test controls
* Basic / Airway / Physical / History tabs
* Assessment fields
* Back button
* Assess Patient button

The card must adapt to mobile width.

Ensure:

* Horizontal padding is responsive.
* Internal content never exceeds the card width.
* Controls do not collide.
* Buttons fit side-by-side only when there is enough width.
* On narrower devices, buttons may stack vertically if required.
* The card can grow vertically based on its content.
* No fixed height should clip the assessment form.
* Tab controls should remain usable and readable.

---

# 4. BASIC / AIRWAY / PHYSICAL / HISTORY TABS

The tab bar is currently close to the available width and must be checked for responsive behavior.

Keep the existing four tabs:

* Basic
* Airway
* Physical
* History

Do not rename or remove them.

Ensure:

* Each tab has an adequate touch target.
* Text remains readable.
* Icons and labels do not overlap.
* The active tab remains visually obvious.
* The tab container does not overflow horizontally unless horizontal scrolling is intentionally required.
* The tab bar scales correctly on narrow phones.

If necessary, allow the tabs to scroll horizontally rather than compressing them into unusable widths.

---

# 5. E / M / D / RANDOM CONTROLS

The E, M, D, and Random controls at the top of the Patient Entry screen should remain functional and visually consistent.

Check:

* Width.
* Height.
* Spacing.
* Icon alignment.
* Text alignment.
* Touch targets.
* Wrapping.
* Horizontal overflow.

They should never overlap the Patient Entry header or each other.

On narrow screens, use a responsive arrangement instead of forcing everything into a fixed-width row.

---

# 6. TYPOGRAPHY

Do not globally shrink typography to fix the problem.

The current screenshots show text becoming vertically compressed because the containers are too narrow.

Fix the **layout first**.

Typography should:

* Remain readable.
* Wrap naturally.
* Avoid individual-word-per-line wrapping where unnecessary.
* Maintain the existing hierarchy.
* Preserve existing font families and weights.
* Avoid clipping.
* Avoid horizontal overflow.

Only make small typography adjustments where absolutely necessary after fixing the layout.

---

# 7. RESPONSIVE BREAKPOINTS

Inspect the application's existing responsive strategy before adding new breakpoints.

If responsive breakpoints do not exist, introduce a simple and maintainable strategy.

The UI must be tested conceptually/locally at minimum around:

* 320px width
* 375px width
* 390px width
* 414px width
* larger phone widths

Do not optimize exclusively for the 738px screenshot image size.

The screenshots are representations of the mobile UI; the actual application must respond to the device's available width.

Use React Native APIs such as `useWindowDimensions()` when appropriate.

---

# 8. SAFE AREA AND BOTTOM NAVIGATION

Audit the entire interaction between:

* Screen content
* Scroll containers
* Bottom navigation
* Android gesture/navigation area
* iOS home indicator
* Safe-area insets

The bottom navigation must:

* Remain visually floating.
* Have sufficient bottom spacing.
* Never cover interactive content.
* Never cover the last card/button/list item.
* Remain accessible above the system gesture area.

Scrollable screens should include sufficient bottom content inset/padding to account for the floating navigation.

Do this consistently for:

* Dashboard
* Assessment
* Prediction Result
* Records/History
* Reports
* Settings

---

# 9. REMOVE FIXED-DIMENSION ASSUMPTIONS

Search the relevant mobile UI code for problematic patterns such as:

* Fixed widths that exceed available screen width.
* Fixed heights around dynamic content.
* Large hard-coded horizontal margins.
* `position: absolute` used for normal layout.
* Excessively large `minWidth`.
* Fixed grid column widths.
* Negative margins.
* Overflow hidden being used to hide layout problems.
* Components whose dimensions assume a desktop/tablet width.

Do not blindly remove every fixed dimension.

Keep fixed dimensions where they are intentional, such as:

* icon sizes,
* button minimum heights,
* touch targets,
* controlled gauge dimensions.

Change only dimensions that are causing responsive failures.

---

# 10. COMPONENTS TO INSPECT

Inspect the relevant implementation files, especially:

* `mobile/src/navigation/index.tsx`
* `mobile/src/screens/home/AssessmentScreen.tsx`
* `mobile/src/screens/home/PredictionResultScreen.tsx`
* `mobile/src/components/result/RiskPredictionCard.tsx`
* `mobile/src/components/result/AiClinicalAssessment.tsx`
* `mobile/src/components/ui/AppHeader.tsx`
* `mobile/src/components/ui/Card.tsx`
* `mobile/src/components/ui/Select.tsx`
* `mobile/src/components/ui/SegmentedTabs.tsx`
* Any assessment/form components used by `AssessmentScreen`
* Theme/token files if spacing or sizing comes from tokens

Do not edit unrelated files unless the investigation shows that they are contributing to the layout problem.

---

# 11. IMPLEMENTATION APPROACH

Before modifying anything:

1. Inspect the existing layout hierarchy.
2. Identify the parent containers controlling width and height.
3. Identify which components are using fixed dimensions.
4. Identify the source of the compressed assessment grid.
5. Identify why the Prediction Result content is being hidden behind the bottom navigation.
6. Identify how safe-area insets are currently handled.
7. Identify whether the navigation bar is rendered inside or outside the screen content hierarchy.
8. Fix the underlying layout constraints.
9. Then make the smallest responsive changes necessary.

Do not patch individual labels one by one.

If 12 fields are compressed because of a bad grid configuration, fix the grid configuration rather than adding custom widths to each individual field.

---

# 12. VALIDATION CHECKLIST

After implementing the changes, verify:

### Prediction Result

* [ ] Full Prediction Result can be scrolled from top to bottom.
* [ ] AI Clinical Assessment is not hidden behind navigation.
* [ ] Risk card fits within screen width.
* [ ] Gauge is centered and not clipped.
* [ ] Probability distribution fits inside the card.
* [ ] Difficulty label remains readable.
* [ ] Bottom navigation does not cover content.

### Patient Entry

* [ ] Assessment fields no longer collapse into extremely narrow columns.
* [ ] Labels wrap naturally.
* [ ] Dropdowns/selects remain usable.
* [ ] No horizontal overflow.
* [ ] No controls overlap.
* [ ] Basic/Airway/Physical/History tabs remain usable.
* [ ] E/M/D/Random controls remain usable.
* [ ] Back and Assess Patient buttons remain accessible.
* [ ] Assessment card grows naturally with content.

### Navigation

* [ ] Floating black pill navigation is visible.
* [ ] No text labels are shown in the bottom navigation.
* [ ] Active tab uses the white circular indicator.
* [ ] Inactive icons remain visible.
* [ ] Navigation respects safe-area insets.
* [ ] Navigation never covers screen content.

### Responsive testing

* [ ] ~320px width
* [ ] ~375px width
* [ ] ~390px width
* [ ] ~414px width
* [ ] Larger phone width

### Technical

* [ ] No TypeScript errors.
* [ ] No new React Native warnings.
* [ ] No navigation regressions.
* [ ] Existing functionality remains unchanged.
* [ ] Do not introduce unnecessary dependencies.
* [ ] Do not use screenshot-specific pixel hacks.

---

# 13. FINAL DESIGN PRINCIPLE

The screenshots demonstrate a **responsive-layout failure**, not a need for a complete redesign.

Therefore:

**Fix the layout system, not the screenshot.**

The final mobile UI should preserve the existing Airway MD visual language while ensuring that every component receives enough space to remain readable, touchable, and visually stable across different mobile screen widths.

The most important fixes are:

1. Prevent assessment fields from being squeezed into tiny columns.
2. Make dynamic content containers grow naturally.
3. Prevent bottom navigation from covering screen content.
4. Correct safe-area and scroll-container handling.
5. Make cards, tabs, buttons, selects, and grids responsive.
6. Preserve all existing content and functionality.
7. Validate the result across multiple mobile widths rather than optimizing for a single screenshot.



---

*Paste any prompt above, replace `[BRACKETED]` placeholders with your choices, and the agent will implement it. The design-token-first approach means most color/typography/spacing changes propagate across the entire app automatically.*