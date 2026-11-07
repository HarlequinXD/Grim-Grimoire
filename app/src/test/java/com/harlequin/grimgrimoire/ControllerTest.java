package com.harlequin.grimgrimoire;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.io.File;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;

/** Drives Grim's controller through the real mansion collision data (no GL needed). */
public class ControllerTest {
    static float[] spawn = new float[4];

    static Collision load() throws Exception {
        File f = new File("src/main/assets/mansion.bin");
        if (!f.exists()) f = new File("app/src/main/assets/mansion.bin");
        ByteBuffer b = ByteBuffer.wrap(Files.readAllBytes(f.toPath())).order(ByteOrder.LITTLE_ENDIAN);
        b.getInt();
        int vc = b.getInt();
        b.position(b.position() + vc * Mansion.STRIDE * 4);
        int nb = b.getInt();
        float[] boxes = new float[nb * 6];
        for (int i = 0; i < boxes.length; i++) boxes[i] = b.getFloat();
        int nl = b.getInt();
        b.position(b.position() + nl * 8 * 4);
        for (int i = 0; i < 4; i++) spawn[i] = b.getFloat();
        return new Collision(boxes, nb);
    }

    /** Hold the stick for `secs`, camera fixed at camYaw. */
    static void run(Player p, Collision c, float mx, float my, boolean jump, float secs, float camYaw) {
        Input.State s = new Input.State();
        s.moveX = mx; s.moveY = my;
        int steps = Math.round(secs * 60);
        for (int i = 0; i < steps; i++) {
            s.held[Input.B_JUMP] = jump;
            s.pressed[Input.B_JUMP] = jump && i == 0;
            p.update(1f / 60f, s, camYaw, c, true);
        }
    }

    @Test
    public void spawnsOnTheFloorFacingTheHall() throws Exception {
        Collision c = load();
        Player p = new Player(spawn[0], spawn[1], spawn[2], spawn[3]);
        run(p, c, 0, 0, false, 0.5f, p.yaw);
        assertEquals(0f, p.pos[1], 0.01f);
        assertTrue(p.grounded);
    }

    @Test
    public void walksUpTheStairsOntoTheGallery() throws Exception {
        Collision c = load();
        Player p = new Player(0f, 0f, 4.0f, (float) Math.PI);
        run(p, c, 0, 1, false, 4.0f, (float) Math.PI);      // full stick forward (-z) for 4 s
        assertTrue("should reach the gallery, y=" + p.pos[1] + " z=" + p.pos[2], p.pos[1] > 2.5f);
        assertTrue(p.pos[2] < -5.0f);
        assertTrue(p.pos[2] > -7.0f + Player.RADIUS - 0.01f);   // stopped by the north wall
    }

    @Test
    public void wallsStopGrim() throws Exception {
        Collision c = load();
        Player p = new Player(0f, 0f, 3.0f, (float) Math.PI / 2);
        run(p, c, 0, 1, false, 4.0f, (float) Math.PI / 2);   // run east into the dining table / wall
        assertTrue("x=" + p.pos[0], p.pos[0] < 9.0f - Player.RADIUS + 0.01f);
    }

    @Test
    public void jumpsAndLands() throws Exception {
        Collision c = load();
        Player p = new Player(0f, 0f, 3.0f, 0f);
        Input.State s = new Input.State();
        float maxY = 0;
        for (int i = 0; i < 120; i++) {
            s.held[Input.B_JUMP] = i < 30; s.pressed[Input.B_JUMP] = i == 0;
            p.update(1f / 60f, s, 0f, c, true);
            maxY = Math.max(maxY, p.pos[1]);
        }
        assertTrue("apex " + maxY, maxY > 0.8f && maxY < 1.2f);
        assertEquals(0f, p.pos[1], 0.01f);
        assertTrue(p.grounded);
    }

    @Test
    public void tiptoeIsSlowerThanRunning() throws Exception {
        Collision c = load();
        Player a = new Player(0f, 0f, 4.0f, 0f), b = new Player(0f, 0f, 4.0f, 0f);
        run(a, c, 0.3f, 0, false, 0.6f, (float) Math.PI / 2);
        run(b, c, 1.0f, 0, false, 0.6f, (float) Math.PI / 2);
        assertTrue(a.groundSpeed() < 1.3f);
        assertTrue(b.groundSpeed() > 3.5f);
    }
}
