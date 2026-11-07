package com.harlequin.grimgrimoire;

import android.content.res.AssetManager;
import android.opengl.GLES20;
import android.opengl.GLSurfaceView;

import java.nio.FloatBuffer;

import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;

/** Game loop: fixed 60 Hz simulation, PS1-style render at 240 lines, touch controls on top. */
public final class GameRenderer implements GLSurfaceView.Renderer {
    private static final float STEP = 1f / 60f;
    private final AssetManager am;
    private final Input input;
    private final Input.State state = new Input.State();

    private final Ps1Renderer ps1 = new Ps1Renderer();
    private final Hud hud = new Hud();
    private Mansion mansion;
    private GrimModel grim;
    private Player player;
    private final FollowCamera cam = new FollowCamera();

    private final float[] proj = new float[16], view = new float[16], vp = new float[16];
    private final float[] lpos = new float[16], lcol = new float[16];
    private final float[] amb = {0.26f, 0.23f, 0.32f};
    private long last;
    private float acc, time;

    // blob shadow
    private int blobVbo;
    private final FloatBuffer blob = GlUtil.floats(6 * 9);
    private static final float BLOB_U = 96f / 256f, BLOB_V = 160f / 256f, BLOB_S = 32f / 256f;

    public GameRenderer(AssetManager am, Input input) { this.am = am; this.input = input; }

    @Override
    public void onSurfaceCreated(GL10 unused, EGLConfig config) {
        ps1.init();
        hud.init(am);
        mansion = new Mansion(am);
        grim = new GrimModel(am);
        if (player == null) player = new Player(mansion.spawnX, mansion.spawnY, mansion.spawnZ, mansion.spawnYaw);
        cam.reset(player);
        int[] id = new int[1];
        GLES20.glGenBuffers(1, id, 0);
        blobVbo = id[0];
        last = System.nanoTime();
    }

    @Override
    public void onSurfaceChanged(GL10 unused, int w, int h) {
        ps1.resize(w, h);
        hud.resize(w, h);
        input.layout(w, h);
    }

    @Override
    public void onDrawFrame(GL10 unused) {
        long now = System.nanoTime();
        float dt = Math.min(0.1f, (now - last) / 1e9f);
        last = now;
        time += dt;
        input.snapshot(state);

        acc += dt;
        boolean first = true;
        while (acc >= STEP) {
            player.update(STEP, state, cam.yaw, mansion.collision, first);
            first = false;
            acc -= STEP;
        }
        cam.update(dt, player, state, mansion.collision);
        player.pose(grim);

        // fire flicker shared by the baked lighting and Grim's lights
        float flick = 0.10f * (float) (Math.sin(time * 11.0) + 0.5 * Math.sin(time * 17.3 + 1.0) + 0.3 * Math.sin(time * 5.1)) / 1.8f;

        Mat4.perspective(proj, (float) Math.toRadians(62), ps1.lowW / (float) ps1.lowH, 0.08f, 40f);
        Mat4.lookAt(view, cam.ex, cam.ey, cam.ez, cam.tx, cam.ty, cam.tz);
        Mat4.mul(vp, proj, view);

        ps1.beginScene();
        mansion.draw(ps1, vp, flick);
        pickLights(flick);
        grim.draw(ps1, vp, player.partMats, amb, lpos, lcol);
        drawBlob();
        ps1.endScene();
        hud.draw(input, state);
    }

    /** The 4 lights that matter most at Grim's position. */
    private void pickLights(float flick) {
        float[] L = mansion.lights;
        int[] best = {-1, -1, -1, -1};
        float[] score = {0, 0, 0, 0};
        float px = player.pos[0], py = player.pos[1] + 1.0f, pz = player.pos[2];
        for (int i = 0; i < mansion.lightCount; i++) {
            int o = i * 8;
            float d = (float) Math.sqrt((L[o] - px) * (L[o] - px) + (L[o + 1] - py) * (L[o + 1] - py) + (L[o + 2] - pz) * (L[o + 2] - pz));
            float a = Math.max(0f, 1f - d / L[o + 6]);
            float sc = a * a * (L[o + 3] + L[o + 4] + L[o + 5]);
            for (int k = 0; k < 4; k++) {
                if (sc > score[k]) {
                    for (int j = 3; j > k; j--) { score[j] = score[j - 1]; best[j] = best[j - 1]; }
                    score[k] = sc; best[k] = i;
                    break;
                }
            }
        }
        for (int k = 0; k < 4; k++) {
            int i = best[k];
            if (i < 0) {
                lpos[k * 4] = 0; lpos[k * 4 + 1] = -100; lpos[k * 4 + 2] = 0; lpos[k * 4 + 3] = 1;
                lcol[k * 4] = 0; lcol[k * 4 + 1] = 0; lcol[k * 4 + 2] = 0; lcol[k * 4 + 3] = 0;
                continue;
            }
            int o = i * 8;
            float f = 1f + flick * L[o + 7] * 1.5f;
            lpos[k * 4] = L[o]; lpos[k * 4 + 1] = L[o + 1]; lpos[k * 4 + 2] = L[o + 2]; lpos[k * 4 + 3] = L[o + 6];
            lcol[k * 4] = L[o + 3] * f; lcol[k * 4 + 1] = L[o + 4] * f; lcol[k * 4 + 2] = L[o + 5] * f; lcol[k * 4 + 3] = 0;
        }
    }

    /** PS1-classic round blob shadow under Grim on whatever he's standing over. */
    private void drawBlob() {
        float g = mansion.collision.ground(player.pos[0], player.pos[2], 0.05f, player.pos[1] + 0.05f, 0.0f) + 0.02f;
        float h = player.pos[1] - g;
        float s = 0.42f * Math.max(0.4f, 1f - h * 0.35f);
        float x0 = player.pos[0] - s, x1 = player.pos[0] + s, z0 = player.pos[2] - s, z1 = player.pos[2] + s;
        float u0 = BLOB_U, v0 = BLOB_V, u1 = BLOB_U + BLOB_S, v1 = BLOB_V + BLOB_S;
        float[][] c = {{x0, z1, u0, v1}, {x1, z1, u1, v1}, {x1, z0, u1, v0}, {x0, z1, u0, v1}, {x1, z0, u1, v0}, {x0, z0, u0, v0}};
        blob.clear();
        for (float[] p : c) {
            blob.put(p[0]); blob.put(g); blob.put(p[1]); blob.put(p[2]); blob.put(p[3]);
            blob.put(1f); blob.put(1f); blob.put(1f); blob.put(0f);
        }
        blob.flip();
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, blobVbo);
        GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, 6 * 9 * 4, blob, GLES20.GL_STREAM_DRAW);
        GLES20.glEnable(GLES20.GL_BLEND);
        GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA);
        GLES20.glDepthMask(false);
        ps1.useWorld(vp, 0f, true);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, mansion.tex);
        GLES20.glEnableVertexAttribArray(ps1.waPos);
        GLES20.glEnableVertexAttribArray(ps1.waUV);
        GLES20.glEnableVertexAttribArray(ps1.waCol);
        GLES20.glVertexAttribPointer(ps1.waPos, 3, GLES20.GL_FLOAT, false, 36, 0);
        GLES20.glVertexAttribPointer(ps1.waUV, 2, GLES20.GL_FLOAT, false, 36, 12);
        GLES20.glVertexAttribPointer(ps1.waCol, 4, GLES20.GL_FLOAT, false, 36, 20);
        GLES20.glDrawArrays(GLES20.GL_TRIANGLES, 0, 6);
        GLES20.glDisableVertexAttribArray(ps1.waPos);
        GLES20.glDisableVertexAttribArray(ps1.waUV);
        GLES20.glDisableVertexAttribArray(ps1.waCol);
        GLES20.glDepthMask(true);
        GLES20.glDisable(GLES20.GL_BLEND);
    }
}
