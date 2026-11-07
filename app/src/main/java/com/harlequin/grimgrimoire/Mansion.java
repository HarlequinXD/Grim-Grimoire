package com.harlequin.grimgrimoire;

import android.content.res.AssetManager;
import android.opengl.GLES20;

import java.nio.ByteBuffer;
import java.nio.FloatBuffer;

/**
 * The mansion hall: one static mesh with baked Gouraud lighting in the vertex colours
 * (alpha = how much of that light comes from flickering fire), collision boxes, lights and the spawn.
 */
public final class Mansion {
    public static final int STRIDE = 9; // pos3 uv2 col4
    public int vbo, vertexCount, tex;
    public final Collision collision;
    public final float[] lights;   // n * 8: pos3 rgb3 radius flicker
    public final int lightCount;
    public final float spawnX, spawnY, spawnZ, spawnYaw;

    public Mansion(AssetManager am) {
        ByteBuffer b = GlUtil.le(GlUtil.readAsset(am, "mansion.bin"));
        if (b.getInt() != 0x31534E4D) throw new RuntimeException("bad mansion.bin"); // "MNS1"
        vertexCount = b.getInt();
        FloatBuffer fb = GlUtil.floats(vertexCount * STRIDE);
        for (int i = 0; i < vertexCount * STRIDE; i++) fb.put(b.getFloat());
        vbo = GlUtil.vbo(fb, GLES20.GL_STATIC_DRAW);
        int nb = b.getInt();
        float[] boxes = new float[nb * 6];
        for (int i = 0; i < boxes.length; i++) boxes[i] = b.getFloat();
        collision = new Collision(boxes, nb);
        lightCount = b.getInt();
        lights = new float[lightCount * 8];
        for (int i = 0; i < lights.length; i++) lights[i] = b.getFloat();
        spawnX = b.getFloat(); spawnY = b.getFloat(); spawnZ = b.getFloat(); spawnYaw = b.getFloat();
        tex = GlUtil.texture(am, "mansion_tex.png");
    }

    public void draw(Ps1Renderer r, float[] mvp, float flick) {
        r.useWorld(mvp, flick, false);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, tex);
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vbo);
        int s = STRIDE * 4;
        GLES20.glEnableVertexAttribArray(r.waPos);
        GLES20.glEnableVertexAttribArray(r.waUV);
        GLES20.glEnableVertexAttribArray(r.waCol);
        GLES20.glVertexAttribPointer(r.waPos, 3, GLES20.GL_FLOAT, false, s, 0);
        GLES20.glVertexAttribPointer(r.waUV, 2, GLES20.GL_FLOAT, false, s, 12);
        GLES20.glVertexAttribPointer(r.waCol, 4, GLES20.GL_FLOAT, false, s, 20);
        GLES20.glDrawArrays(GLES20.GL_TRIANGLES, 0, vertexCount);
        GLES20.glDisableVertexAttribArray(r.waPos);
        GLES20.glDisableVertexAttribArray(r.waUV);
        GLES20.glDisableVertexAttribArray(r.waCol);
    }
}
