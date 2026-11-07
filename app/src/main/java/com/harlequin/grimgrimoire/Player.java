package com.harlequin.grimgrimoire;

/**
 * Grim's third-person controller, modelled on PS1 MediEvil (Sir Dan):
 *  - camera-relative analogue movement with speed tiers: a gentle push tiptoes, more walks, full runs;
 *    the d-pad always tiptoes (MediEvil's "sneak" on the d-pad)
 *  - Grim walks where he faces: he turns toward the stick at a limited rate, so sharp turns slow him,
 *    and a full reversal pivots on the spot (the weighty PS1 tank-ish feel, but analogue)
 *  - hold STRAFE to lock facing and side-step
 *  - JUMP with coyote time, a jump buffer and variable height (let go early for a hop); little air steering
 *  - ATTACK: alternating bony-arm swings with a small forward lunge; BLOCK: hold to guard, slows you
 * Animation is rigid-segment keyframe-free procedural posing, like many PS1 characters.
 */
public final class Player {
    public static final float RADIUS = 0.27f, HEIGHT = 1.88f;
    static final float TIPTOE = 1.1f, WALK = 2.3f, RUN = 4.6f;
    static final float GRAVITY = 16f, JUMP_V = 5.6f;

    public final float[] pos = new float[3];    // feet
    public float yaw;                           // facing; forward = (sin yaw, 0, cos yaw)
    public float vx, vz, vy, speed;
    public boolean grounded = true, strafing, blocking;
    float coyote, jumpBuf, attackT = -1f, idleT, phase, time, landT;
    int attackSide;
    boolean jumpCut;

    // pose: per part rotation (x pitch, y yaw, z roll) + body bob, smoothed toward targets
    final float[] rx = new float[11], ry = new float[11], rz = new float[11];
    final float[] tx = new float[11], ty = new float[11], tz = new float[11];
    float bob, tBob;
    public final float[] partMats = new float[11 * 16];
    private final float[] world = new float[16];
    private final float[] tmp = new float[16];

    public Player(float x, float y, float z, float yaw) {
        pos[0] = x; pos[1] = y; pos[2] = z; this.yaw = yaw;
    }

    static float wrap(float a) {
        while (a > Math.PI) a -= (float) (2 * Math.PI);
        while (a < -Math.PI) a += (float) (2 * Math.PI);
        return a;
    }

    static float approach(float v, float target, float step) {
        return v < target ? Math.min(target, v + step) : Math.max(target, v - step);
    }

    public float groundSpeed() { return (float) Math.hypot(vx, vz); }

    public void update(float dt, Input.State in, float camYaw, Collision col, boolean firstStep) {
        time += dt;
        // ---- input in world space (camera relative). camera forward = (sin camYaw, 0, cos camYaw), right = (-cos, 0, sin)
        float s = (float) Math.sin(camYaw), c = (float) Math.cos(camYaw);
        float wx = s * in.moveY - c * in.moveX;
        float wz = c * in.moveY + s * in.moveX;
        float mag = Math.min(1f, (float) Math.hypot(in.moveX, in.moveY));

        strafing = in.held[Input.B_STRAFE];
        blocking = in.held[Input.B_BLOCK] && grounded;
        if (firstStep && in.pressed[Input.B_JUMP]) jumpBuf = 0.13f;
        if (firstStep && in.pressed[Input.B_ATTACK] && attackT < 0f) {
            attackT = 0f; attackSide ^= 1;
            if (grounded) speed = Math.max(speed, 1.6f);   // lunge
        }

        float tier = mag < 0.05f ? 0f : in.tiptoe || mag < 0.42f ? TIPTOE : mag < 0.85f ? WALK : RUN;
        if (blocking) tier = Math.min(tier, 0.9f);
        if (attackT >= 0f) tier = Math.min(tier, 0.8f);

        if (strafing) {
            // facing locked, move freely in the stick direction
            float tvx = 0, tvz = 0;
            if (mag > 0.05f) { float l = (float) Math.hypot(wx, wz); tvx = wx / l * Math.min(tier, WALK); tvz = wz / l * Math.min(tier, WALK); }
            float a = (grounded ? 14f : 3f) * dt;
            vx = approach(vx, tvx, a); vz = approach(vz, tvz, a);
            speed = vx * (float) Math.sin(yaw) + vz * (float) Math.cos(yaw);
        } else {
            float target = 0f;
            if (mag > 0.05f) {
                float want = (float) Math.atan2(wx, wz);
                float diff = wrap(want - yaw);
                float turn = (grounded ? (speed > 3.2f ? 7.5f : 11f) : 3.2f) * dt;
                yaw = wrap(yaw + Math.max(-turn, Math.min(turn, diff)));
                float align = (float) Math.cos(Math.min(Math.abs(diff), Math.PI / 2));
                target = tier * Math.max(0f, align);
                if (Math.abs(diff) > 2.0f && grounded) target = 0f;       // pivot on the spot
            }
            float acc = grounded ? (target > speed ? 12f : 18f) : 3f;
            if (grounded || target > speed) speed = approach(speed, target, acc * dt);
            vx = (float) Math.sin(yaw) * speed; vz = (float) Math.cos(yaw) * speed;
        }

        // ---- jump
        if (grounded) coyote = 0.1f; else coyote -= dt;
        jumpBuf -= dt;
        if (jumpBuf > 0f && coyote > 0f && !blocking) {
            vy = JUMP_V; grounded = false; coyote = 0f; jumpBuf = 0f; jumpCut = false;
        }
        if (!in.held[Input.B_JUMP] && vy > 0f && !jumpCut) { vy *= 0.55f; jumpCut = true; }

        // ---- collide
        boolean wasGrounded = grounded;
        float prevFeet = pos[1];
        col.slide(pos, vx * dt, vz * dt, RADIUS, HEIGHT, grounded);
        vy -= GRAVITY * dt;
        pos[1] += vy * dt;
        float g = col.ground(pos[0], pos[2], RADIUS * 0.75f, Math.max(prevFeet, pos[1]), wasGrounded ? Collision.STEP : 0.05f);
        if (pos[1] <= g) {
            if (!wasGrounded && vy < -3f) landT = 0.18f;
            pos[1] = g; vy = 0f; grounded = true;
        } else if (wasGrounded && vy <= 0f && pos[1] - g < 0.42f) {
            pos[1] = g; vy = 0f; grounded = true;                     // stick to stairs going down
        } else {
            grounded = false;
        }
        if (vy > 0f) {
            float ceil = col.ceiling(pos[0], pos[2], RADIUS * 0.75f, prevFeet + HEIGHT);
            if (pos[1] + HEIGHT > ceil) { pos[1] = ceil - HEIGHT; vy = 0f; }
        }
        if (attackT >= 0f) { attackT += dt; if (attackT > 0.42f) attackT = -1f; }
        landT = Math.max(0f, landT - dt);
        float gs = groundSpeed();
        idleT = (gs < 0.1f && grounded && attackT < 0f) ? idleT + dt : 0f;
        if (grounded) phase += dt * (gs * 1.9f + (gs > 0.1f ? 1.6f : 0f));

        animate(dt, gs);
    }

    // ------------------------------------------------------------------ procedural rigid-segment animation
    private void animate(float dt, float gs) {
        for (int i = 0; i < 11; i++) { tx[i] = 0; ty[i] = 0; tz[i] = 0; }
        tBob = 0f;
        float sp = (float) Math.sin(phase), cp = (float) Math.cos(phase);
        float moving = Math.min(1f, gs / 0.6f);
        float run = clamp01((gs - 2.4f) / 2.2f);
        float tip = (gs > 0.1f && gs < 1.6f && grounded) ? 1f - clamp01((gs - 1.2f) / 0.4f) : 0f;

        if (grounded) {
            float A = (0.32f + 0.38f * run + 0.25f * tip) * moving, K = (0.45f + 0.75f * run + 0.7f * tip) * moving;
            float Aa = (0.35f + 0.5f * run) * moving * (1f - tip);
            tx[GrimModel.THIGH_L] = -sp * A - 0.15f * tip;
            tx[GrimModel.THIGH_R] = sp * A - 0.15f * tip;
            tx[GrimModel.SHIN_L] = K * Math.max(0f, cp) + 0.08f + 0.2f * tip;
            tx[GrimModel.SHIN_R] = K * Math.max(0f, -cp) + 0.08f + 0.2f * tip;
            tx[GrimModel.UARM_L] = sp * Aa - 0.55f * tip;
            tx[GrimModel.UARM_R] = -sp * Aa - 0.55f * tip;
            tx[GrimModel.FARM_L] = -(0.25f + 0.65f * run + 1.0f * tip);
            tx[GrimModel.FARM_R] = -(0.25f + 0.65f * run + 1.0f * tip);
            tz[GrimModel.UARM_L] = 0.1f * tip; tz[GrimModel.UARM_R] = -0.1f * tip;
            tx[GrimModel.TORSO] = (0.05f + 0.16f * run + 0.28f * tip) * moving;
            ty[GrimModel.TORSO] = sp * 0.12f * moving;
            tBob = (Math.abs(cp) - 0.6f) * (0.05f + 0.04f * run + 0.06f * tip) * moving - 0.04f * tip;
            tx[GrimModel.HEAD] = -tx[GrimModel.TORSO] * 0.6f + 0.05f * Math.abs(sp) * moving;
            tz[GrimModel.HAT] = sp * 0.06f * moving;
            if (idleT > 0f) {                         // idle: breathing, looking around, hat wobble
                float br = (float) Math.sin(time * 2.1f);
                tx[GrimModel.TORSO] += br * 0.025f;
                tBob += br * 0.008f;
                tz[GrimModel.UARM_L] += 0.05f + br * 0.02f; tz[GrimModel.UARM_R] -= 0.05f + br * 0.02f;
                if (idleT > 2.5f) {
                    ty[GrimModel.HEAD] = (float) Math.sin(time * 0.7f) * 0.55f;
                    tx[GrimModel.HEAD] += (float) Math.sin(time * 0.45f) * 0.12f;
                    tz[GrimModel.HAT] = (float) Math.sin(time * 1.3f) * 0.05f;
                }
            }
            if (landT > 0f) {                         // landing squash
                float k = landT / 0.18f;
                tBob -= 0.12f * k; tx[GrimModel.THIGH_L] -= 0.5f * k; tx[GrimModel.THIGH_R] -= 0.5f * k;
                tx[GrimModel.SHIN_L] += 0.9f * k; tx[GrimModel.SHIN_R] += 0.9f * k;
            }
        } else {
            float rising = vy > 0f ? 1f : 0f;
            tx[GrimModel.THIGH_L] = -0.75f; tx[GrimModel.THIGH_R] = -0.15f;
            tx[GrimModel.SHIN_L] = 1.1f; tx[GrimModel.SHIN_R] = 0.5f;
            tx[GrimModel.UARM_L] = -0.9f * rising - 0.3f; tx[GrimModel.UARM_R] = -0.9f * rising - 0.3f;
            tz[GrimModel.UARM_L] = 0.6f; tz[GrimModel.UARM_R] = -0.6f;
            tx[GrimModel.FARM_L] = -0.5f; tx[GrimModel.FARM_R] = -0.5f;
            tx[GrimModel.TORSO] = 0.12f; tx[GrimModel.HEAD] = -0.15f;
            tz[GrimModel.HAT] = -0.12f;
        }

        if (blocking) {                               // guard: forearms crossed in front of the ribs
            tx[GrimModel.UARM_L] = -1.25f; tx[GrimModel.UARM_R] = -1.25f;
            tz[GrimModel.UARM_L] = -0.35f; tz[GrimModel.UARM_R] = 0.35f;
            tx[GrimModel.FARM_L] = -1.35f; tx[GrimModel.FARM_R] = -1.35f;
            tx[GrimModel.TORSO] += 0.12f; tx[GrimModel.HEAD] += 0.15f;
        }

        if (attackT >= 0f) {                          // overhead bony swing
            float k = attackT / 0.42f;
            int ua = attackSide == 0 ? GrimModel.UARM_R : GrimModel.UARM_L;
            int fa = attackSide == 0 ? GrimModel.FARM_R : GrimModel.FARM_L;
            float side = attackSide == 0 ? 1f : -1f;
            float arm, fore, twist;
            if (k < 0.32f) { float w = k / 0.32f; arm = -2.7f * w; fore = -0.5f * w; twist = -0.35f * w * side; }
            else if (k < 0.55f) { float w = (k - 0.32f) / 0.23f; arm = -2.7f + 2.5f * w; fore = -0.5f + 0.3f * w; twist = (-0.35f + 0.75f * w) * side; }
            else { float w = (k - 0.55f) / 0.45f; arm = -0.2f * (1 - w); fore = -0.2f * (1 - w); twist = 0.4f * (1 - w) * side; }
            tx[ua] = arm; tx[fa] = fore; tz[ua] = 0f;
            ty[GrimModel.TORSO] = twist;
            tx[GrimModel.TORSO] += 0.1f;
        }

        float rate = Math.min(1f, dt * (attackT >= 0f ? 30f : 14f));
        for (int i = 0; i < 11; i++) {
            rx[i] += (tx[i] - rx[i]) * rate;
            ry[i] += (ty[i] - ry[i]) * rate;
            rz[i] += (tz[i] - rz[i]) * rate;
        }
        bob += (tBob - bob) * rate;
    }

    static float clamp01(float v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

    /** Builds world matrices for every body part (parents always come before children in grim.bin). */
    public void pose(GrimModel m) {
        Mat4.identity(world);
        Mat4.translate(world, pos[0], pos[1] + bob, pos[2]);
        Mat4.rotate(world, 1, yaw);
        for (int i = 0; i < m.partCount; i++) {
            int p = m.parent[i];
            if (p < 0) System.arraycopy(world, 0, tmp, 0, 16);
            else System.arraycopy(partMats, p * 16, tmp, 0, 16);
            float px = m.pivot[i * 3], py = m.pivot[i * 3 + 1], pz = m.pivot[i * 3 + 2];
            Mat4.translate(tmp, px, py, pz);
            Mat4.rotate(tmp, 1, ry[i]);
            Mat4.rotate(tmp, 0, rx[i]);
            Mat4.rotate(tmp, 2, rz[i]);
            Mat4.translate(tmp, -px, -py, -pz);
            System.arraycopy(tmp, 0, partMats, i * 16, 16);
        }
    }
}
