package com.harlequin.grimgrimoire;

/**
 * GLSL ES 1.00 shaders that reproduce the PlayStation GPU/GTE look:
 *  - vertex snapping to the low-res pixel grid (the GTE had no sub-pixel precision: "wobbly polygons")
 *  - affine texture mapping (no perspective correction: textures swim and warp)
 *  - nearest-neighbour texels, no mipmaps (set on the textures)
 *  - Gouraud vertex lighting only (baked for the level, per-vertex for Grim)
 *  - depth-cue fog to a dark colour
 *  - 15-bit colour (5 bits per channel) with the PS1's 4x4 ordered dither
 *  - cut-out transparency for alpha textures, semi-transparency for the blob shadow
 * Each shader is a separate constant so CI can extract and validate it with glslangValidator.
 */
public final class Shaders {
    private Shaders() {}

    public static final String WORLD_VS =
        "uniform mat4 uMVP;\n" +
        "uniform vec2 uRes;\n" +
        "uniform float uJitter;\n" +
        "uniform float uAffine;\n" +
        "uniform float uFlick;\n" +
        "uniform vec2 uFog;\n" +
        "attribute vec3 aPos;\n" +
        "attribute vec2 aUV;\n" +
        "attribute vec4 aCol;\n" +
        "varying vec3 vUVW;\n" +
        "varying vec3 vCol;\n" +
        "varying float vFog;\n" +
        "void main() {\n" +
        "  vec4 p = uMVP * vec4(aPos, 1.0);\n" +
        "  if (uJitter > 0.5 && p.w > 0.0) {\n" +
        "    vec2 g = uRes * 0.5;\n" +
        "    p.xy = floor(p.xy / p.w * g + 0.5) / g * p.w;\n" +
        "  }\n" +
        "  gl_Position = p;\n" +
        "  float w = mix(1.0, max(p.w, 0.05), uAffine);\n" +
        "  vUVW = vec3(aUV * w, w);\n" +
        "  vCol = aCol.rgb * (1.0 + aCol.a * uFlick);\n" +
        "  vFog = clamp((p.w - uFog.x) / (uFog.y - uFog.x), 0.0, 1.0);\n" +
        "}\n";

    /** Grim: rigid segments, one model matrix per body part, Gouraud lighting from the 4 nearest lights. */
    public static final String RIGID_VS =
        "uniform mat4 uVP;\n" +
        "uniform mat4 uModel;\n" +
        "uniform vec2 uRes;\n" +
        "uniform float uJitter;\n" +
        "uniform float uAffine;\n" +
        "uniform vec2 uFog;\n" +
        "uniform vec3 uAmb;\n" +
        "uniform vec4 uLPos[4];\n" +
        "uniform vec4 uLCol[4];\n" +
        "attribute vec3 aPos;\n" +
        "attribute vec3 aNrm;\n" +
        "attribute vec2 aUV;\n" +
        "varying vec3 vUVW;\n" +
        "varying vec3 vCol;\n" +
        "varying float vFog;\n" +
        "void main() {\n" +
        "  vec4 wp = uModel * vec4(aPos, 1.0);\n" +
        "  vec3 n = normalize((uModel * vec4(aNrm, 0.0)).xyz);\n" +
        "  vec3 light = uAmb + vec3(0.05, 0.05, 0.07) * max(n.y, 0.0);\n" +
        "  for (int i = 0; i < 4; i++) {\n" +
        "    vec3 d = uLPos[i].xyz - wp.xyz;\n" +
        "    float dist = length(d) + 0.0001;\n" +
        "    float att = clamp(1.0 - dist / uLPos[i].w, 0.0, 1.0);\n" +
        "    att *= att;\n" +
        "    float ndl = max(dot(n, d / dist), 0.0) * 0.8 + 0.2;\n" +
        "    light += uLCol[i].rgb * att * ndl;\n" +
        "  }\n" +
        "  vCol = min(light * 1.2, vec3(1.6));\n" +
        "  vec4 p = uVP * wp;\n" +
        "  if (uJitter > 0.5 && p.w > 0.0) {\n" +
        "    vec2 g = uRes * 0.5;\n" +
        "    p.xy = floor(p.xy / p.w * g + 0.5) / g * p.w;\n" +
        "  }\n" +
        "  gl_Position = p;\n" +
        "  float w = mix(1.0, max(p.w, 0.05), uAffine);\n" +
        "  vUVW = vec3(aUV * w, w);\n" +
        "  vFog = clamp((p.w - uFog.x) / (uFog.y - uFog.x), 0.0, 1.0);\n" +
        "}\n";

    public static final String WORLD_FS =
        "#ifdef GL_FRAGMENT_PRECISION_HIGH\n" +
        "precision highp float;\n" +
        "#else\n" +
        "precision mediump float;\n" +
        "#endif\n" +
        "uniform sampler2D uTex;\n" +
        "uniform vec3 uFogCol;\n" +
        "uniform float uBlend;\n" +
        "uniform float uDither;\n" +
        "varying vec3 vUVW;\n" +
        "varying vec3 vCol;\n" +
        "varying float vFog;\n" +
        "float bayer2(vec2 a) { a = floor(a); return fract(dot(a, vec2(0.5, a.y * 0.75))); }\n" +
        "float bayer4(vec2 a) { return bayer2(0.5 * a) * 0.25 + bayer2(a); }\n" +
        "void main() {\n" +
        "  vec4 t = texture2D(uTex, vUVW.xy / vUVW.z);\n" +
        "  if (uBlend < 0.5 && t.a < 0.5) discard;\n" +
        "  vec3 c = t.rgb * vCol;\n" +
        "  c = mix(c, uFogCol, vFog);\n" +
        "  float b = (bayer4(gl_FragCoord.xy) - 0.5) * uDither;\n" +
        "  c = floor(clamp(c, 0.0, 1.0) * 31.0 + b + 0.5) / 31.0;\n" +
        "  gl_FragColor = vec4(c, uBlend < 0.5 ? 1.0 : t.a);\n" +
        "}\n";

    /** Upscales the 240-line frame to the screen with nearest filtering. */
    public static final String PRESENT_VS =
        "attribute vec2 aPos;\n" +
        "varying vec2 vUV;\n" +
        "void main() {\n" +
        "  vUV = aPos * 0.5 + 0.5;\n" +
        "  gl_Position = vec4(aPos, 0.0, 1.0);\n" +
        "}\n";

    public static final String PRESENT_FS =
        "precision mediump float;\n" +
        "uniform sampler2D uTex;\n" +
        "varying vec2 vUV;\n" +
        "void main() {\n" +
        "  gl_FragColor = vec4(texture2D(uTex, vUV).rgb, 1.0);\n" +
        "}\n";

    /** Touch controls, drawn at screen resolution in screen pixels. */
    public static final String HUD_VS =
        "uniform vec2 uScreen;\n" +
        "attribute vec2 aPos;\n" +
        "attribute vec2 aUV;\n" +
        "attribute vec4 aCol;\n" +
        "varying vec2 vUV;\n" +
        "varying vec4 vCol;\n" +
        "void main() {\n" +
        "  vUV = aUV;\n" +
        "  vCol = aCol;\n" +
        "  vec2 p = aPos / uScreen * 2.0 - 1.0;\n" +
        "  gl_Position = vec4(p.x, -p.y, 0.0, 1.0);\n" +
        "}\n";

    public static final String HUD_FS =
        "precision mediump float;\n" +
        "uniform sampler2D uTex;\n" +
        "varying vec2 vUV;\n" +
        "varying vec4 vCol;\n" +
        "void main() {\n" +
        "  gl_FragColor = texture2D(uTex, vUV) * vCol;\n" +
        "}\n";
}
