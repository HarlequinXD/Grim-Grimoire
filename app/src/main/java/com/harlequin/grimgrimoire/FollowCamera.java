package com.harlequin.grimgrimoire;

/**
 * MediEvil-style "Dan cam": a lazy chase camera that drifts round behind Grim while he runs,
 * with L/R to rotate it, a recentre button that swings it straight behind him, and
 * (a modern extra) right-side drag / right stick to orbit and tilt. It pulls in when a wall
 * or furniture gets between it and Grim.
 */
public final class FollowCamera {
    public float yaw, pitch = 0.30f, dist = 3.5f, curDist = 3.5f;
    public float tx, ty, tz;              // smoothed look-at target
    public float ex, ey, ez;              // eye
    private float manualT = 10f, recenterT = 0f;

    public void reset(Player p) {
        yaw = p.yaw; tx = p.pos[0]; ty = p.pos[1] + 1.45f; tz = p.pos[2];
        curDist = dist;
        place();
    }

    public void update(float dt, Player p, Input.State in, Collision col) {
        boolean manual = false;
        float rot = (in.held[Input.B_CAMR] ? 1f : 0f) - (in.held[Input.B_CAML] ? 1f : 0f);
        if (rot != 0f) { yaw += rot * 2.3f * dt; manual = true; }
        if (in.orbitX != 0f || in.orbitY != 0f) {
            yaw -= in.orbitX; pitch += in.orbitY; manual = true;
        }
        pitch = Math.max(-0.15f, Math.min(1.1f, pitch));
        manualT = manual ? 0f : manualT + dt;
        if (in.pressed[Input.B_RECENTER]) recenterT = 0.35f;

        if (recenterT > 0f) {
            recenterT -= dt;
            float d = Player.wrap(p.yaw - yaw);
            yaw += d * Math.min(1f, dt * 12f);
            pitch += (0.30f - pitch) * Math.min(1f, dt * 8f);
        } else if (manualT > 0.8f && !p.strafing) {
            // lazy auto-follow: the faster Grim runs forward, the quicker the camera swings behind him
            float gs = p.groundSpeed();
            if (gs > 0.5f) {
                float d = Player.wrap(p.yaw - yaw);
                if (Math.abs(d) < 2.6f) yaw += d * Math.min(1f, dt * 1.5f * (gs / Player.RUN));
            }
        }
        yaw = Player.wrap(yaw);

        float k = Math.min(1f, dt * 10f), kv = Math.min(1f, dt * (p.grounded ? 8f : 3f));
        tx += (p.pos[0] - tx) * k;
        tz += (p.pos[2] - tz) * k;
        ty += (p.pos[1] + 1.45f - ty) * kv;

        // keep the camera on our side of walls/furniture
        float dx = -(float) (Math.sin(yaw) * Math.cos(pitch)), dy = (float) Math.sin(pitch), dz = -(float) (Math.cos(yaw) * Math.cos(pitch));
        float hit = col.ray(tx, ty, tz, dx, dy, dz, dist + 0.3f) - 0.3f;
        float want = Math.max(0.7f, Math.min(dist, hit));
        curDist = want < curDist ? want : curDist + (want - curDist) * Math.min(1f, dt * 2.5f);
        place();
    }

    private void place() {
        float cp = (float) Math.cos(pitch);
        ex = tx - (float) Math.sin(yaw) * cp * curDist;
        ey = ty + (float) Math.sin(pitch) * curDist;
        ez = tz - (float) Math.cos(yaw) * cp * curDist;
        if (ey > 5.3f) ey = 5.3f;   // stay under the ceiling
    }
}
