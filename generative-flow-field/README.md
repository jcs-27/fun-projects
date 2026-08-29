# Flow Field

A generative art piece: particles drifting through a Perlin-noise vector field, leaving colored trails. Self-contained single HTML file — no build step, no dependencies, no CDN. Open it and it runs.

```bash
# just open it
start flow-field-art.html      # Windows
open flow-field-art.html       # macOS
xdg-open flow-field-art.html   # Linux
```

Or drag it straight into a browser tab. It also works fine served statically (e.g. GitHub Pages) since it has zero external requests.

## Controls

| Control | Effect |
|---|---|
| **Regenerate** | New random seed — reshapes the whole field and resets all particles |
| **Save PNG** | Downloads the current canvas as a PNG, named with its seed |
| **Pause / Resume** | Freezes the animation without clearing it |
| **Clear trails** | Wipes the canvas without touching the particles or the field |
| Particles / Noise scale / Speed sliders | Reshape the flow live — no need to regenerate to feel the effect |

## How it works

- A seeded PRNG (`mulberry32`) builds the Perlin permutation table, so every seed is a fully reproducible starting point — same seed, same field, every time.
- Each particle samples 2D Perlin noise at its own position (plus a slowly advancing time offset, so the field itself drifts rather than staying perfectly static) to get a flow angle, then steps forward along it.
- The canvas is faded by a small alpha-blended fill each frame instead of being cleared outright — that's what produces the streak trails rather than a field of disconnected dots.
- Particles that wander off-screen or exceed a randomized lifespan respawn at a new random point with a new random color, so the field keeps circulating instead of eventually draining to nothing.

## Verification note

This was written and reasoned through carefully, but I want to be upfront about one gap: the live rendering couldn't be visually confirmed in-browser during development because the preview pane was in a hidden/backgrounded state, and `requestAnimationFrame` is throttled to zero by every browser when its tab or window isn't visible — that's standard browser behavior, not a flaw in the page. To still verify correctness without relying on that, I extracted the exact noise/particle-update math into a standalone Node.js script and ran it through 5000 simulated steps across 300 particles with a fixed seed: no `NaN`/`Infinity` ever appeared, the noise field varies properly across space (not flat/constant), and particles move at exactly the configured speed. That gives real confidence the math is sound; it just doesn't substitute for actually watching it animate. Open it yourself to see the actual visual result — it should look immediately alive.

One real (cosmetic) bug this process did catch: the "Noise scale" label showed a stale placeholder value on first load instead of the slider's actual starting value, because it was only ever updated on the slider's `input` event, never synced at boot. Fixed by syncing all three labels to their sliders' real values on load instead of trusting hardcoded HTML text to match.
