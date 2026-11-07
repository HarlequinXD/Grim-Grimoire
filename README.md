# Grim Grimoire

A PS1-style third-person game for Android. You play **Grim**, a skeleton in a suit and top hat, inside an old, fully furnished mansion.

## PS1 renderer
Everything the original PlayStation GPU/GTE did that gives the look, done in GLSL ES 2.0 (`Shaders.java`, `Ps1Renderer.java`):

- **240-line framebuffer**: the width follows the screen's aspect ratio. It's scaled up to the screen with nearest filtering.
- **Vertex snapping**: vertices snap to the low-res pixel grid, giving the wobbly polygons.
- **Affine texture mapping**: no perspective correction, so textures warp and swim.
- **Texture sampling**: nearest-neighbour texels and no mipmaps.
- **Gouraud vertex lighting**: the mansion's lighting is baked into the vertex colours (with ray-cast shadows from the furniture). Grim is lit per-vertex by the 4 nearest lights. Fire light flickers.
- **15-bit colour**: 5 bits per channel, with the PS1's 4×4 ordered dither.
- **Depth-cue fog** to black-violet.
- **Cut-out transparency**: balusters, cobwebs and candle flames.
- **Blob shadow**: a semi-transparent blob under Grim.
- **Rigid-segment character**: Grim's 11 body parts each have a pivot and a parent, posed procedurally.

## Assets (all generated, see `tools/assets/`)
- **Grim:** 300 triangles. The head is a box-modelled skull: one cube subdivided once, with the jaw shaped from the same mesh. He has a 128×128 pixel-art texture with lighting and shadows painted in.
- **Mansion hall:** about 5.5k triangles, every piece of furniture box-modelled. A 256×256 atlas holds 42 hand-shaded, dithered textures with lighting built in. The hall has:
  - a fireplace, a grand staircase and a gallery
  - a dining table with chairs, bookshelves and a grandfather clock
  - an upright piano, armchairs and a chesterfield
  - rugs, a chandelier, candelabras and sconces
  - moonlit windows with velvet curtains, portraits and cobwebs
- **Player start:** in the entrance hall, facing up the runner toward the staircase.

To rebuild the assets, run the scripts in `tools/assets/` with Python 3 + numpy + Pillow:
1. `build_skeleton.py` writes `grim.bin`.
2. `build_mansion.py` writes `mansion.bin` and `mansion_tex.png`.
3. `build_ui.py` writes `ui.png`.

## Controls (MediEvil-style)
Grim moves relative to the camera and walks where he faces. He turns at a limited rate, so sharp turns slow him down, and a full reversal pivots him on the spot. The camera lazily swings round behind him as he runs.

| Action | Touch | Gamepad | Keyboard |
|---|---|---|---|
| Move | left stick: light push = tiptoe, more = walk, full = run | left stick | WASD |
| Tiptoe (sneak) | — | d-pad | arrows |
| Jump (hold for higher) | ⬆ button | A | Space |
| Attack (alternating bony swings) | bone button | X | J |
| Block (hold) | shield button | B / R2 | K |
| Strafe (hold, locks facing) | ⇆ button | L2 | Shift |
| Rotate camera | ↶ ↷ top corners | L1 / R1 | Q / E |
| Recentre camera behind Grim | eye button | Y | R |
| Orbit / tilt camera | drag the right side of the screen | right stick | — |

## Build
GitHub Actions validates the shaders, runs the controller unit tests and builds the debug APK. Download it from the **GrimGrimoire-debug** artifact on each run.
