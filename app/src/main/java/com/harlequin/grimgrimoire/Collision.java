package com.harlequin.grimgrimoire;

/**
 * Axis-aligned box collision for the mansion. The player is an upright box (radius r, height h).
 * Boxes low enough to step onto (stairs, plinths) don't block sideways movement; the ground
 * query lifts the player onto them instead.
 */
public final class Collision {
    public static final float STEP = 0.36f;
    final float[] b; // n * (minx miny minz maxx maxy maxz)
    final int n;

    public Collision(float[] boxes, int count) { b = boxes; n = count; }

    private boolean overlapsY(int i, float feet, float h) {
        return b[i * 6 + 4] > feet + 0.001f && b[i * 6 + 1] < feet + h;
    }

    private boolean overlapsXZ(int i, float x, float z, float r) {
        int o = i * 6;
        return x + r > b[o] && x - r < b[o + 3] && z + r > b[o + 2] && z - r < b[o + 5];
    }

    /** Move along x then z, sliding along walls. pos = {x, feetY, z}. */
    public void slide(float[] pos, float dx, float dz, float r, float h, boolean grounded) {
        float stepUp = grounded ? STEP : 0.05f;
        pos[0] += dx;
        for (int i = 0; i < n; i++) {
            if (!overlapsY(i, pos[1], h) || !overlapsXZ(i, pos[0], pos[2], r)) continue;
            if (b[i * 6 + 4] - pos[1] <= stepUp) continue;
            if (dx > 0) pos[0] = b[i * 6] - r - 0.001f;
            else if (dx < 0) pos[0] = b[i * 6 + 3] + r + 0.001f;
        }
        pos[2] += dz;
        for (int i = 0; i < n; i++) {
            if (!overlapsY(i, pos[1], h) || !overlapsXZ(i, pos[0], pos[2], r)) continue;
            if (b[i * 6 + 4] - pos[1] <= stepUp) continue;
            if (dz > 0) pos[2] = b[i * 6 + 2] - r - 0.001f;
            else if (dz < 0) pos[2] = b[i * 6 + 5] + r + 0.001f;
        }
    }

    /** Highest walkable surface under the footprint that is at most `reach` above feetY (floor = 0). */
    public float ground(float x, float z, float r, float feetY, float reach) {
        float g = 0f;
        for (int i = 0; i < n; i++) {
            if (!overlapsXZ(i, x, z, r)) continue;
            float top = b[i * 6 + 4];
            if (top <= feetY + reach && top > g) g = top;
        }
        return g;
    }

    /** Lowest box bottom above the head (for jumping into the gallery underside etc.). */
    public float ceiling(float x, float z, float r, float headY) {
        float c = 1e9f;
        for (int i = 0; i < n; i++) {
            if (!overlapsXZ(i, x, z, r)) continue;
            float bot = b[i * 6 + 1];
            if (bot >= headY - 0.12f && bot < c) c = bot;
        }
        return c;
    }

    /** Ray (origin o, unit dir d) vs all boxes; returns hit distance or maxT. Boxes containing o are ignored. */
    public float ray(float ox, float oy, float oz, float dx, float dy, float dz, float maxT) {
        float best = maxT;
        float[] o3 = {ox, oy, oz}, d3 = {dx, dy, dz};
        for (int i = 0; i < n; i++) {
            int k = i * 6;
            if (ox > b[k] && ox < b[k + 3] && oy > b[k + 1] && oy < b[k + 4] && oz > b[k + 2] && oz < b[k + 5]) continue;
            float tmin = 0f, tmax = best;
            boolean miss = false;
            for (int a = 0; a < 3 && !miss; a++) {
                float lo = b[k + a], hi = b[k + 3 + a];
                if (Math.abs(d3[a]) < 1e-6f) {
                    if (o3[a] < lo || o3[a] > hi) miss = true;
                } else {
                    float t1 = (lo - o3[a]) / d3[a], t2 = (hi - o3[a]) / d3[a];
                    if (t1 > t2) { float t = t1; t1 = t2; t2 = t; }
                    if (t1 > tmin) tmin = t1;
                    if (t2 < tmax) tmax = t2;
                    if (tmin > tmax) miss = true;
                }
            }
            if (!miss && tmin < best) best = tmin;
        }
        return best;
    }
}
