package com.harlequin.grimgrimoire;

import android.content.res.AssetManager;
import android.opengl.GLES20;

import java.nio.FloatBuffer;

/** Draws the touch controls from the pixel-art UI atlas (ui.png, 128x128). */
public final class Hud {
    private int prog, uScreen, uTex, aPos, aUV, aCol, tex, vbo;
    private final FloatBuffer fb = GlUtil.floats(64 * 6 * 8);
    private int verts;
    private float w = 1, h = 1;

    // atlas rects (x, y, w, h) in pixels
    private static final int[] STICK = {0, 0, 64, 64}, KNOB = {64, 0, 32, 32}, BTN = {96, 0, 32, 32};
    private static final int[][] ICON = {
        {0, 64, 32, 32},   // attack
        {32, 64, 32, 32},  // jump
        {64, 64, 32, 32},  // block
        {96, 64, 32, 32},  // strafe
        {0, 96, 32, 32},   // cam L
        {32, 96, 32, 32},  // cam R
        {64, 96, 32, 32},  // recentre
    };

    public void init(AssetManager am) {
        prog = GlUtil.program(Shaders.HUD_VS, Shaders.HUD_FS);
        uScreen = GLES20.glGetUniformLocation(prog, "uScreen");
        uTex = GLES20.glGetUniformLocation(prog, "uTex");
        aPos = GLES20.glGetAttribLocation(prog, "aPos");
        aUV = GLES20.glGetAttribLocation(prog, "aUV");
        aCol = GLES20.glGetAttribLocation(prog, "aCol");
        tex = GlUtil.texture(am, "ui.png");
        int[] id = new int[1];
        GLES20.glGenBuffers(1, id, 0);
        vbo = id[0];
    }

    public void resize(int sw, int sh) { w = sw; h = sh; }

    private void quad(float cx, float cy, float half, int[] r, float a, float tint) {
        float x0 = cx - half, y0 = cy - half, x1 = cx + half, y1 = cy + half;
        float u0 = r[0] / 128f, v0 = r[1] / 128f, u1 = (r[0] + r[2]) / 128f, v1 = (r[1] + r[3]) / 128f;
        float[][] c = {{x0, y0, u0, v0}, {x1, y0, u1, v0}, {x1, y1, u1, v1}, {x0, y0, u0, v0}, {x1, y1, u1, v1}, {x0, y1, u0, v1}};
        for (float[] p : c) {
            fb.put(p[0]); fb.put(p[1]); fb.put(p[2]); fb.put(p[3]);
            fb.put(tint); fb.put(tint); fb.put(tint); fb.put(a);
            verts++;
        }
    }

    public void draw(Input in, Input.State st) {
        if (!st.touchActive) return;
        fb.clear(); verts = 0;
        // stick: shows at its home spot until touched, then follows the thumb
        boolean act;
        float ox, oy, kx, ky;
        synchronized (in) {
            act = in.stickActive();
            ox = act ? in.stickOX : in.stickHomeX; oy = act ? in.stickOY : in.stickHomeY;
            kx = act ? in.stickX : ox; ky = act ? in.stickY : oy;
            float dx = kx - ox, dy = ky - oy, d = (float) Math.hypot(dx, dy);
            if (d > in.stickR) { kx = ox + dx / d * in.stickR; ky = oy + dy / d * in.stickR; }
        }
        quad(ox, oy, in.stickR, STICK, act ? 0.85f : 0.45f, 1f);
        quad(kx, ky, in.stickR * 0.42f, KNOB, act ? 0.95f : 0.5f, 1f);
        for (int i = 0; i < Input.NB; i++) {
            boolean held = in.touchHeld(i);
            float r = in.br[i];
            quad(in.bx[i], in.by[i], r, BTN, held ? 0.95f : 0.6f, held ? 1.6f : 1f);
            quad(in.bx[i], in.by[i], r * 0.66f, ICON[i], held ? 1f : 0.75f, held ? 1.25f : 1f);
        }
        fb.flip();
        GLES20.glEnable(GLES20.GL_BLEND);
        GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA);
        GLES20.glUseProgram(prog);
        GLES20.glUniform2f(uScreen, w, h);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, tex);
        GLES20.glUniform1i(uTex, 0);
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vbo);
        GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, verts * 32, fb, GLES20.GL_STREAM_DRAW);
        GLES20.glEnableVertexAttribArray(aPos);
        GLES20.glEnableVertexAttribArray(aUV);
        GLES20.glEnableVertexAttribArray(aCol);
        GLES20.glVertexAttribPointer(aPos, 2, GLES20.GL_FLOAT, false, 32, 0);
        GLES20.glVertexAttribPointer(aUV, 2, GLES20.GL_FLOAT, false, 32, 8);
        GLES20.glVertexAttribPointer(aCol, 4, GLES20.GL_FLOAT, false, 32, 16);
        GLES20.glDrawArrays(GLES20.GL_TRIANGLES, 0, verts);
        GLES20.glDisableVertexAttribArray(aPos);
        GLES20.glDisableVertexAttribArray(aUV);
        GLES20.glDisableVertexAttribArray(aCol);
        GLES20.glDisable(GLES20.GL_BLEND);
    }
}
