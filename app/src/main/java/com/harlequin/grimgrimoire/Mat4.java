package com.harlequin.grimgrimoire;

/** Minimal column-major 4x4 matrix helpers (same layout OpenGL expects). */
public final class Mat4 {
    private Mat4() {}

    public static float[] identity(float[] m) {
        for (int i = 0; i < 16; i++) m[i] = (i % 5 == 0) ? 1f : 0f;
        return m;
    }

    /** out = a * b (out may alias neither a nor b). */
    public static void mul(float[] out, float[] a, float[] b) {
        for (int c = 0; c < 4; c++) {
            for (int r = 0; r < 4; r++) {
                float s = 0f;
                for (int k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k];
                out[c * 4 + r] = s;
            }
        }
    }

    public static void perspective(float[] m, float fovY, float aspect, float near, float far) {
        float f = (float) (1.0 / Math.tan(fovY * 0.5));
        identity(m);
        m[0] = f / aspect; m[5] = f;
        m[10] = (far + near) / (near - far); m[11] = -1f;
        m[14] = 2f * far * near / (near - far); m[15] = 0f;
    }

    public static void lookAt(float[] m, float ex, float ey, float ez, float cx, float cy, float cz) {
        float zx = ex - cx, zy = ey - cy, zz = ez - cz;
        float l = (float) Math.sqrt(zx * zx + zy * zy + zz * zz);
        zx /= l; zy /= l; zz /= l;
        float xx = zz, xy = 0f, xz = -zx;                    // up(0,1,0) x z
        l = (float) Math.sqrt(xx * xx + xz * xz);
        if (l < 1e-5f) { xx = 1f; xz = 0f; l = 1f; }
        xx /= l; xz /= l;
        float yx = zy * xz - zz * xy, yy = zz * xx - zx * xz, yz = zx * xy - zy * xx;
        m[0] = xx; m[1] = yx; m[2] = zx; m[3] = 0f;
        m[4] = xy; m[5] = yy; m[6] = zy; m[7] = 0f;
        m[8] = xz; m[9] = yz; m[10] = zz; m[11] = 0f;
        m[12] = -(xx * ex + xy * ey + xz * ez);
        m[13] = -(yx * ex + yy * ey + yz * ez);
        m[14] = -(zx * ex + zy * ey + zz * ez);
        m[15] = 1f;
    }

    private static final float[] T = new float[16];
    private static final float[] R = new float[16];

    /** m = m * translate(x,y,z) */
    public static void translate(float[] m, float x, float y, float z) {
        for (int r = 0; r < 4; r++) m[12 + r] += m[r] * x + m[4 + r] * y + m[8 + r] * z;
    }

    /** m = m * rot(axis, angle radians) for axis 0=x 1=y 2=z */
    public static void rotate(float[] m, int axis, float a) {
        if (a == 0f) return;
        float c = (float) Math.cos(a), s = (float) Math.sin(a);
        identity(R);
        if (axis == 0) { R[5] = c; R[6] = s; R[9] = -s; R[10] = c; }
        else if (axis == 1) { R[0] = c; R[2] = -s; R[8] = s; R[10] = c; }
        else { R[0] = c; R[1] = s; R[4] = -s; R[5] = c; }
        System.arraycopy(m, 0, T, 0, 16);
        mul(m, T, R);
    }
}
