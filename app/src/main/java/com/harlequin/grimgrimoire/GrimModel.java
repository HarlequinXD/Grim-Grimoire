package com.harlequin.grimgrimoire;

import android.content.res.AssetManager;
import android.opengl.GLES20;

import java.nio.ByteBuffer;
import java.nio.FloatBuffer;

/**
 * Grim, the suited skeleton (300 triangles, 128x128 texture with painted lighting).
 * Stored as rigid segments like PS1 character models: each body part has a pivot and a parent,
 * and is drawn with its own matrix.
 */
public final class GrimModel {
    public static final int TORSO = 0, HEAD = 1, HAT = 2, UARM_L = 3, FARM_L = 4, UARM_R = 5, FARM_R = 6,
            THIGH_L = 7, SHIN_L = 8, THIGH_R = 9, SHIN_R = 10;
    public final int partCount;
    public final String[] names;
    public final int[] parent, start, count;
    public final float[] pivot;   // partCount * 3
    public int vbo, tex;

    public GrimModel(AssetManager am) {
        ByteBuffer b = GlUtil.le(GlUtil.readAsset(am, "grim.bin"));
        if (b.getInt() != 0x314D5247) throw new RuntimeException("bad grim.bin"); // "GRM1"
        partCount = b.getInt();
        names = new String[partCount]; parent = new int[partCount]; start = new int[partCount]; count = new int[partCount];
        pivot = new float[partCount * 3];
        for (int i = 0; i < partCount; i++) {
            byte[] nb = new byte[b.getInt()];
            b.get(nb);
            names[i] = new String(nb);
            parent[i] = b.getInt();
            pivot[i * 3] = b.getFloat(); pivot[i * 3 + 1] = b.getFloat(); pivot[i * 3 + 2] = b.getFloat();
            start[i] = b.getInt(); count[i] = b.getInt();
        }
        int nv = b.getInt();
        FloatBuffer fb = GlUtil.floats(nv * 8);
        for (int i = 0; i < nv * 8; i++) fb.put(b.getFloat());
        vbo = GlUtil.vbo(fb, GLES20.GL_STATIC_DRAW);
        tex = GlUtil.texture(am, "grim_tex.png");
    }

    /** partMats: partCount * 16 world matrices (from Player.pose). */
    public void draw(Ps1Renderer r, float[] vp, float[] partMats, float[] amb, float[] lpos, float[] lcol) {
        r.useRigid(vp, amb, lpos, lcol);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, tex);
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vbo);
        GLES20.glEnableVertexAttribArray(r.raPos);
        GLES20.glEnableVertexAttribArray(r.raNrm);
        GLES20.glEnableVertexAttribArray(r.raUV);
        GLES20.glVertexAttribPointer(r.raPos, 3, GLES20.GL_FLOAT, false, 32, 0);
        GLES20.glVertexAttribPointer(r.raNrm, 3, GLES20.GL_FLOAT, false, 32, 12);
        GLES20.glVertexAttribPointer(r.raUV, 2, GLES20.GL_FLOAT, false, 32, 24);
        for (int i = 0; i < partCount; i++) {
            GLES20.glUniformMatrix4fv(r.rModel, 1, false, partMats, i * 16);
            GLES20.glDrawArrays(GLES20.GL_TRIANGLES, start[i], count[i]);
        }
        GLES20.glDisableVertexAttribArray(r.raPos);
        GLES20.glDisableVertexAttribArray(r.raNrm);
        GLES20.glDisableVertexAttribArray(r.raUV);
    }
}
