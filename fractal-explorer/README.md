# Fractal Explorer

An interactive Mandelbrot set viewer — self-contained single HTML file, no dependencies, no build step. Scroll to zoom toward the cursor, click and drag to pan, hover with "Live Julia preview" on to see the Julia set for whatever point is under your mouse.

```bash
start fractal-explorer.html      # Windows
open fractal-explorer.html       # macOS
xdg-open fractal-explorer.html   # Linux
```

## Controls

| Control | Effect |
|---|---|
| Scroll wheel | Zoom in/out, centered on the cursor — not the middle of the screen |
| Click + drag | Pan |
| **Reset view** | Back to the default framing |
| **Save PNG** | Downloads the current render |
| Palette | Fire / Ocean / Neon / Monochrome |
| Detail (max iterations) | Higher = sharper boundary detail when zoomed in, slower to render |
| Live Julia preview on hover | Small inset canvas renders the Julia set for whichever point is under your cursor, live |

## How it works

- Escape-time algorithm with **smooth (continuous) coloring** — rather than banding color purely by integer iteration count (which produces visible rings), the fractional part of the escape is computed from how far past the bailout radius the point actually landed, so gradients look continuous even at low iteration counts.
- **Render-on-demand, not a `requestAnimationFrame` animation loop.** Nothing here needs to animate continuously — it only needs to redraw when the view, palette, or detail level actually changes. That also means it doesn't fight for CPU when idle, and it renders correctly the instant it becomes visible even if it was opened in a background tab (see the note on that below).
- Zoom is computed by converting the cursor's screen position to its complex-plane coordinate *before* changing the zoom level, then solving for the new view center so that same complex-plane point stays under the cursor afterward — otherwise every scroll tick zooms toward the center of the screen instead of wherever you're actually pointing, which feels wrong almost immediately.

## Why it's built this way

This is the one project in this lab-and-friends collection where testing had to work around a real constraint rather than just catch bugs: while building it, the render never appeared in the preview pane, and direct inspection confirmed why — `document.hidden` was `true` and the page's own `setTimeout(0)`-scheduled render call simply never fired while the pane was in that state. That's genuine browser behavior (backgrounded/hidden tabs throttle or stall timers), not a flaw in the page — but it meant the actual page code couldn't be exercised end-to-end through its normal code path during development. Verification ended up happening two ways instead:

1. **The math, in isolation, via a standalone Node.js script** — known Mandelbrot set membership points (e.g. -0.5+0i and -1+0i are inside the set; 2+2i escapes almost immediately), and critically, a **zoom-toward-cursor invariant check**: simulate 10 zoom-in ticks centered on an off-center cursor position, then confirm the complex-plane point that was under the cursor before zooming is still there afterward (drift measured at effectively zero, `0.000e+0`). That invariant is exactly the kind of thing that's easy to get subtly backwards — zooming toward the center instead of the cursor, or having the view creep with every tick — and wouldn't necessarily be obvious just from looking at one rendered frame.
2. **The actual canvas rendering pipeline, by executing the identical render logic directly against the real `<canvas>` element**, bypassing the page's own stalled timer — confirmed it produces genuinely correct, richly colored output (verified both by sampling pixel data and by an actual screenshot showing a textbook-correct Mandelbrot set: the main cardioid, the period-2 bulb, and filament detail all exactly where they should be). The interactive Julia preview was verified the same way it'll actually be used — a real click to enable it, a real mouse-hover event — which fired correctly, because DOM input events aren't subject to the same timer throttling that blocked the scheduled render.

One real, if minor, gap this process surfaced: if this page is ever opened in a background tab (a middle-clicked link, for instance) rather than a foreground one, the same stalling that blocked testing here would leave the canvas blank until something else triggered a redraw. Fixed with a `visibilitychange` listener that fires a render the moment the tab actually becomes visible — a small addition, but one that came directly from watching the failure mode happen firsthand rather than guessing at it.
