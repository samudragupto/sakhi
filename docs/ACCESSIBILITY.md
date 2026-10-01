# Accessibility Specification: Sakhi – आपकी आवाज़ दीदी

Sakhi is designed strictly according to **WCAG 2.2 Level AA guidelines**, optimized for **first-time smartphone users**, low-literacy rural citizens, and oral-first regional language speakers.

## 1. Zero-Digital-Knowledge Design Pillars
1. **Audio-First Autonomy:** Every piece of information rendered on screen is spoken aloud via clear Hindi (`hi-IN`) neural speech at a comfortable, natural pace (`0.9x`).
2. **Every Button Speaks:** Interactive cards and decision controls feature a speaker icon (`🔊`) allowing users to hear any option before making a decision.
3. **No Abstract Symbols or Complex Navigation:** No hamburger menus, navigation bars, dropdowns, or complex forms. All interactions proceed via giant primary buttons.
4. **Concrete Visuals:**
   - Giant thumbs up / down (`👍 हाँ` / `👎 नहीं`) for boolean questions.
   - 5 soft progress dots rather than confusing percentage calculations.
   - Large tactile checklist checkboxes for required documents.

## 2. Touch Target & Sizing Criteria
- **Touch Target Size:** All clickable elements have a minimum dimension of **48 × 48 CSS pixels** (the primary microphone button is **130 × 130 pixels**).
- **Spacing:** Touch targets maintain a minimum 12px bounding margin to prevent accidental taps.
- **Font Scaling:** Built using relative `rem` units to scale automatically with Android device accessibility settings.

## 3. High Contrast & Sensory Accessibility
- **Color Contrast:** Minimum contrast ratio exceeds **4.5:1** for standard text and **7:1** for headings and key buttons against their backgrounds.
- **Information Not Conveyed by Color Alone:** Every state (success, warning, error) is indicated through text, SVG icons, and spoken audio cues simultaneously.
- **High Contrast Mode:** Full support for `@media (prefers-contrast: more)` with bold black borders and deep purple accents.
- **Reduced Motion:** Animations (such as the mic pulse) are completely disabled when `@media (prefers-reduced-motion: reduce)` is signaled.

## 4. Screen Reader & Keyboard Navigation
- **Semantic HTML5:** Native `<header>`, `<main>`, `<section>`, `<aside>`, `<button>`, and `<input type="checkbox">` elements.
- **Skip Link:** Dedicated `.skip-link` at the top of the DOM for instant keyboard navigation to main content.
- **Live Captions:** Real-time updates delivered through `aria-live="polite"` containers so screen readers announce changes without disruption.
- **Focus Rings:** Distinct, high-visibility 4px focus outline (`#ff6f00`) on all interactive components.
