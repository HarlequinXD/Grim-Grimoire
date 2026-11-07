package com.harlequin.grimgrimoire;

import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;

/**
 * Touch screen, gamepad and keyboard input, merged into one PS1-pad-like state.
 *
 * Touch layout (landscape):
 *   left side    floating analogue stick (push gently to tiptoe, further to walk, all the way to run)
 *   right side   ATTACK (big), JUMP, BLOCK (hold), STRAFE (hold); drag empty space to orbit the camera
 *   top corners  L / R rotate the camera, EYE recentres it behind Grim ("Dan cam")
 * Gamepad (MediEvil-style): left stick move, d-pad tiptoe, A jump, X attack, B block, Y recentre,
 *   L1/R1 rotate camera, L2 strafe, R2 block, right stick orbit.
 * Keyboard: WASD move, arrows tiptoe, Space jump, J attack, K block, Shift strafe, Q/E camera, R recentre.
 *
 * Written on the UI thread, read on the GL thread via snapshot().
 */
public final class Input {
    public static final int B_ATTACK = 0, B_JUMP = 1, B_BLOCK = 2, B_STRAFE = 3, B_CAML = 4, B_CAMR = 5, B_RECENTER = 6, NB = 7;

    /** A copy of the input for one frame. */
    public static final class State {
        public float moveX, moveY;       // stick, y = forward, magnitude 0..1
        public boolean tiptoe;           // d-pad / arrow keys (always the slow sneak, like MediEvil's d-pad)
        public final boolean[] held = new boolean[NB];
        public final boolean[] pressed = new boolean[NB];
        public final boolean[] released = new boolean[NB];
        public float orbitX, orbitY;     // camera orbit in radians this frame
        public boolean touchActive;
    }

    // ---- touch layout (screen pixels)
    public float sw = 1, sh = 1, unit = 100;
    public final float[] bx = new float[NB], by = new float[NB], br = new float[NB];
    public float stickHomeX, stickHomeY, stickR;

    // ---- touch state
    private int stickId = -1, orbitId = -1;
    public float stickOX, stickOY, stickX, stickY;   // origin + current finger
    private float orbitLX, orbitLY;
    private final int[] btnPointer = new int[NB];
    private final boolean[] touchHeld = new boolean[NB];
    private float pendOrbitX, pendOrbitY;
    public long lastTouch = 0, lastPad = -1;

    // ---- pad / keyboard
    private float padLX, padLY, padRX, padRY, hatX, hatY, lTrig, rTrig;
    private final boolean[] padHeld = new boolean[NB];
    private boolean kW, kA, kS, kD, kUp, kDown, kLeft, kRight;

    // edges
    private final boolean[] prevHeld = new boolean[NB];

    public Input() { for (int i = 0; i < NB; i++) btnPointer[i] = -1; }

    public synchronized void layout(float w, float h) {
        sw = w; sh = h;
        unit = Math.min(w, h) / 6.2f;
        stickR = unit * 1.05f;
        stickHomeX = unit * 1.9f; stickHomeY = h - unit * 1.7f;
        set(B_ATTACK, w - unit * 1.15f, h - unit * 1.15f, unit * 0.72f);
        set(B_JUMP, w - unit * 2.65f, h - unit * 0.85f, unit * 0.58f);
        set(B_BLOCK, w - unit * 1.05f, h - unit * 2.7f, unit * 0.55f);
        set(B_STRAFE, w - unit * 2.55f, h - unit * 2.35f, unit * 0.5f);
        set(B_CAML, unit * 0.8f, unit * 0.75f, unit * 0.48f);
        set(B_CAMR, w - unit * 0.8f, unit * 0.75f, unit * 0.48f);
        set(B_RECENTER, w - unit * 2.1f, unit * 0.75f, unit * 0.48f);
    }

    private void set(int i, float x, float y, float r) { bx[i] = x; by[i] = y; br[i] = r; }

    private int hitButton(float x, float y) {
        int best = -1; float bd = 1e9f;
        for (int i = 0; i < NB; i++) {
            float d = (float) Math.hypot(x - bx[i], y - by[i]);
            if (d < br[i] * 1.3f && d < bd) { bd = d; best = i; }
        }
        return best;
    }

    public synchronized boolean onTouch(MotionEvent e) {
        lastTouch = System.currentTimeMillis();
        int act = e.getActionMasked();
        int idx = e.getActionIndex();
        switch (act) {
            case MotionEvent.ACTION_DOWN:
            case MotionEvent.ACTION_POINTER_DOWN: {
                int id = e.getPointerId(idx);
                float x = e.getX(idx), y = e.getY(idx);
                int btn = hitButton(x, y);
                if (btn >= 0) { btnPointer[btn] = id; touchHeld[btn] = true; }
                else if (x < sw * 0.45f && y > sh * 0.22f && stickId < 0) {
                    stickId = id; stickOX = x; stickOY = y; stickX = x; stickY = y;
                } else if (orbitId < 0) { orbitId = id; orbitLX = x; orbitLY = y; }
                break;
            }
            case MotionEvent.ACTION_MOVE:
                for (int p = 0; p < e.getPointerCount(); p++) {
                    int id = e.getPointerId(p);
                    float x = e.getX(p), y = e.getY(p);
                    if (id == stickId) {
                        stickX = x; stickY = y;
                        float dx = x - stickOX, dy = y - stickOY, d = (float) Math.hypot(dx, dy);
                        if (d > stickR * 1.25f) {         // drag the base along when the thumb slides past it
                            stickOX = x - dx / d * stickR * 1.25f; stickOY = y - dy / d * stickR * 1.25f;
                        }
                    } else if (id == orbitId) {
                        pendOrbitX += (x - orbitLX) / unit * 0.9f;
                        pendOrbitY += (y - orbitLY) / unit * 0.6f;
                        orbitLX = x; orbitLY = y;
                    }
                }
                break;
            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_POINTER_UP:
            case MotionEvent.ACTION_CANCEL: {
                if (act == MotionEvent.ACTION_CANCEL) { releaseAll(); break; }
                int id = e.getPointerId(idx);
                release(id);
                if (act == MotionEvent.ACTION_UP) releaseAll();
                break;
            }
            default: break;
        }
        return true;
    }

    private void release(int id) {
        if (id == stickId) stickId = -1;
        if (id == orbitId) orbitId = -1;
        for (int i = 0; i < NB; i++) if (btnPointer[i] == id) { btnPointer[i] = -1; touchHeld[i] = false; }
    }

    private void releaseAll() {
        stickId = -1; orbitId = -1;
        for (int i = 0; i < NB; i++) { btnPointer[i] = -1; touchHeld[i] = false; }
    }

    public synchronized boolean stickActive() { return stickId >= 0; }

    public synchronized boolean touchHeld(int b) { return touchHeld[b]; }

    // ---------------------------------------------------------------- gamepad / keyboard
    public static boolean isPad(InputDevice dev) {
        if (dev == null) return false;
        int s = dev.getSources();
        return (s & InputDevice.SOURCE_JOYSTICK) == InputDevice.SOURCE_JOYSTICK
            || (s & InputDevice.SOURCE_GAMEPAD) == InputDevice.SOURCE_GAMEPAD;
    }

    public synchronized boolean onGenericMotion(MotionEvent e) {
        if ((e.getSource() & InputDevice.SOURCE_JOYSTICK) != InputDevice.SOURCE_JOYSTICK) return false;
        lastPad = System.currentTimeMillis();
        padLX = e.getAxisValue(MotionEvent.AXIS_X); padLY = e.getAxisValue(MotionEvent.AXIS_Y);
        padRX = e.getAxisValue(MotionEvent.AXIS_Z); padRY = e.getAxisValue(MotionEvent.AXIS_RZ);
        hatX = e.getAxisValue(MotionEvent.AXIS_HAT_X); hatY = e.getAxisValue(MotionEvent.AXIS_HAT_Y);
        lTrig = Math.max(e.getAxisValue(MotionEvent.AXIS_LTRIGGER), e.getAxisValue(MotionEvent.AXIS_BRAKE));
        rTrig = Math.max(e.getAxisValue(MotionEvent.AXIS_RTRIGGER), e.getAxisValue(MotionEvent.AXIS_GAS));
        return true;
    }

    /** Returns true if handled. */
    public synchronized boolean onKey(int code, boolean down) {
        boolean handled = handleKey(code, down);
        if (handled) lastPad = System.currentTimeMillis();
        return handled;
    }

    private boolean handleKey(int code, boolean down) {
        switch (code) {
            case KeyEvent.KEYCODE_BUTTON_A: case KeyEvent.KEYCODE_SPACE: padHeld[B_JUMP] = down; return true;
            case KeyEvent.KEYCODE_BUTTON_X: case KeyEvent.KEYCODE_J: padHeld[B_ATTACK] = down; return true;
            case KeyEvent.KEYCODE_BUTTON_B: case KeyEvent.KEYCODE_K: case KeyEvent.KEYCODE_BUTTON_R2: padHeld[B_BLOCK] = down; return true;
            case KeyEvent.KEYCODE_BUTTON_Y: case KeyEvent.KEYCODE_R: padHeld[B_RECENTER] = down; return true;
            case KeyEvent.KEYCODE_BUTTON_L1: case KeyEvent.KEYCODE_Q: padHeld[B_CAML] = down; return true;
            case KeyEvent.KEYCODE_BUTTON_R1: case KeyEvent.KEYCODE_E: padHeld[B_CAMR] = down; return true;
            case KeyEvent.KEYCODE_BUTTON_L2: case KeyEvent.KEYCODE_SHIFT_LEFT: padHeld[B_STRAFE] = down; return true;
            case KeyEvent.KEYCODE_W: kW = down; return true;
            case KeyEvent.KEYCODE_A: kA = down; return true;
            case KeyEvent.KEYCODE_S: kS = down; return true;
            case KeyEvent.KEYCODE_D: kD = down; return true;
            case KeyEvent.KEYCODE_DPAD_UP: kUp = down; return true;
            case KeyEvent.KEYCODE_DPAD_DOWN: kDown = down; return true;
            case KeyEvent.KEYCODE_DPAD_LEFT: kLeft = down; return true;
            case KeyEvent.KEYCODE_DPAD_RIGHT: kRight = down; return true;
            default: return false;
        }
    }

    private static float dead(float v) { return Math.abs(v) < 0.18f ? 0f : (v - Math.signum(v) * 0.18f) / 0.82f; }

    /** Builds this frame's state and clears one-shot deltas. */
    public synchronized void snapshot(State s) {
        float mx = 0, my = 0;
        s.tiptoe = false;
        if (stickId >= 0) {
            float dx = stickX - stickOX, dy = stickY - stickOY;
            float d = (float) Math.hypot(dx, dy) / stickR;
            if (d > 0.12f) {
                float m = Math.min(1f, (d - 0.12f) / 0.88f);
                float l = (float) Math.hypot(dx, dy);
                mx = dx / l * m; my = -dy / l * m;
            }
        }
        float lx = dead(padLX), ly = dead(padLY);
        if (lx != 0 || ly != 0) { mx = lx; my = -ly; }
        float kx = (kD ? 1 : 0) - (kA ? 1 : 0), ky = (kW ? 1 : 0) - (kS ? 1 : 0);
        if (kx != 0 || ky != 0) { float l = (float) Math.hypot(kx, ky); mx = kx / l; my = ky / l; }
        float hx = hatX + (kRight ? 1 : 0) - (kLeft ? 1 : 0), hy = -hatY + (kUp ? 1 : 0) - (kDown ? 1 : 0);
        if (Math.abs(hx) > 0.5f || Math.abs(hy) > 0.5f) {
            float l = (float) Math.hypot(hx, hy); mx = hx / l * 0.3f; my = hy / l * 0.3f; s.tiptoe = true;
        }
        float m = (float) Math.hypot(mx, my);
        if (m > 1f) { mx /= m; my /= m; }
        s.moveX = mx; s.moveY = my;

        for (int i = 0; i < NB; i++) {
            boolean h = touchHeld[i] || padHeld[i];
            if (i == B_STRAFE && lTrig > 0.4f) h = true;
            if (i == B_BLOCK && rTrig > 0.4f) h = true;
            s.held[i] = h;
            s.pressed[i] = h && !prevHeld[i];
            s.released[i] = !h && prevHeld[i];
            prevHeld[i] = h;
        }
        s.orbitX = pendOrbitX + dead(padRX) * 0.045f;
        s.orbitY = pendOrbitY + dead(padRY) * 0.03f;
        pendOrbitX = 0; pendOrbitY = 0;
        s.touchActive = lastTouch >= lastPad;
    }
}
