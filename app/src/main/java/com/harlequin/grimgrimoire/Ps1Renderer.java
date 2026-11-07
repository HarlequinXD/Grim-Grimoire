package com.harlequin.grimgrimoire;

import android.opengl.GLES20;

import java.nio.FloatBuffer;

/**
 * Renders the 3D scene into a 240-line off-screen framebuffer (width follows the screen aspect),
 * then scales it up to the display with nearest filtering, like the PS1's 320x240 output on a TV.
 */
public final class Ps1Renderer {
    public static final int LINES = 240;

    // world program
    public int pWorld, wMVP, wRes, wJitter, wAffine, wFlick, wFog, wTex, wFogCol, wBlend, wDither;
    public int waPos, waUV, waCol;
    // rigid (Grim) program
    public int pRigid, rVP, rModel, rRes, rJitter, rAffine, rFog, rAmb, rLPos, rLCol, rTex, rFogCol, rBlend, rDither;
    public int raPos, raNrm, raUV;
    // present
    private int pPresent, prTex, prPos, quadVbo;

    private int fbo, fboTex, depthRb;
    public int lowW = 427, lowH = LINES, screenW = 1, screenH = 1;

    // PS1 feature switches
    public boolean jitter = true, affine = true, dither = true;
    public final float[] fogCol = {0.02f, 0.015f, 0.035f};
    public float fogNear = 9f, fogFar = 24f;

    public void init() {
        pWorld = GlUtil.program(Shaders.WORLD_VS, Shaders.WORLD_FS);
        wMVP = u(pWorld, "uMVP"); wRes = u(pWorld, "uRes"); wJitter = u(pWorld, "uJitter"); wAffine = u(pWorld, "uAffine");
        wFlick = u(pWorld, "uFlick"); wFog = u(pWorld, "uFog"); wTex = u(pWorld, "uTex"); wFogCol = u(pWorld, "uFogCol");
        wBlend = u(pWorld, "uBlend"); wDither = u(pWorld, "uDither");
        waPos = GLES20.glGetAttribLocation(pWorld, "aPos"); waUV = GLES20.glGetAttribLocation(pWorld, "aUV");
        waCol = GLES20.glGetAttribLocation(pWorld, "aCol");

        pRigid = GlUtil.program(Shaders.RIGID_VS, Shaders.WORLD_FS);
        rVP = u(pRigid, "uVP"); rModel = u(pRigid, "uModel"); rRes = u(pRigid, "uRes"); rJitter = u(pRigid, "uJitter");
        rAffine = u(pRigid, "uAffine"); rFog = u(pRigid, "uFog"); rAmb = u(pRigid, "uAmb"); rLPos = u(pRigid, "uLPos");
        rLCol = u(pRigid, "uLCol"); rTex = u(pRigid, "uTex"); rFogCol = u(pRigid, "uFogCol"); rBlend = u(pRigid, "uBlend");
        rDither = u(pRigid, "uDither");
        raPos = GLES20.glGetAttribLocation(pRigid, "aPos"); raNrm = GLES20.glGetAttribLocation(pRigid, "aNrm");
        raUV = GLES20.glGetAttribLocation(pRigid, "aUV");

        pPresent = GlUtil.program(Shaders.PRESENT_VS, Shaders.PRESENT_FS);
        prTex = u(pPresent, "uTex"); prPos = GLES20.glGetAttribLocation(pPresent, "aPos");
        FloatBuffer q = GlUtil.floats(12);
        q.put(new float[]{-1, -1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1});
        quadVbo = GlUtil.vbo(q, GLES20.GL_STATIC_DRAW);
        fbo = 0;
    }

    private static int u(int p, String n) { return GLES20.glGetUniformLocation(p, n); }

    public void resize(int w, int h) {
        screenW = w; screenH = h;
        lowH = LINES;
        lowW = Math.max(320, Math.round(LINES * (float) w / h)) & ~1;
        if (fbo != 0) {
            GLES20.glDeleteFramebuffers(1, new int[]{fbo}, 0);
            GLES20.glDeleteTextures(1, new int[]{fboTex}, 0);
            GLES20.glDeleteRenderbuffers(1, new int[]{depthRb}, 0);
        }
        int[] id = new int[1];
        GLES20.glGenTextures(1, id, 0); fboTex = id[0];
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, fboTex);
        GLES20.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES20.GL_RGBA, lowW, lowH, 0, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, null);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_NEAREST);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_NEAREST);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE);
        GLES20.glGenRenderbuffers(1, id, 0); depthRb = id[0];
        GLES20.glBindRenderbuffer(GLES20.GL_RENDERBUFFER, depthRb);
        GLES20.glRenderbufferStorage(GLES20.GL_RENDERBUFFER, GLES20.GL_DEPTH_COMPONENT16, lowW, lowH);
        GLES20.glGenFramebuffers(1, id, 0); fbo = id[0];
        GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, fbo);
        GLES20.glFramebufferTexture2D(GLES20.GL_FRAMEBUFFER, GLES20.GL_COLOR_ATTACHMENT0, GLES20.GL_TEXTURE_2D, fboTex, 0);
        GLES20.glFramebufferRenderbuffer(GLES20.GL_FRAMEBUFFER, GLES20.GL_DEPTH_ATTACHMENT, GLES20.GL_RENDERBUFFER, depthRb);
        GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0);
    }

    public void beginScene() {
        GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, fbo);
        GLES20.glViewport(0, 0, lowW, lowH);
        GLES20.glClearColor(fogCol[0], fogCol[1], fogCol[2], 1f);
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT | GLES20.GL_DEPTH_BUFFER_BIT);
        GLES20.glEnable(GLES20.GL_DEPTH_TEST);
        GLES20.glDepthFunc(GLES20.GL_LEQUAL);
        GLES20.glEnable(GLES20.GL_CULL_FACE);
        GLES20.glCullFace(GLES20.GL_BACK);
        GLES20.glDisable(GLES20.GL_BLEND);
        GLES20.glDepthMask(true);
    }

    /** Common uniforms for the world program. */
    public void useWorld(float[] mvp, float flick, boolean blend) {
        GLES20.glUseProgram(pWorld);
        GLES20.glUniformMatrix4fv(wMVP, 1, false, mvp, 0);
        GLES20.glUniform2f(wRes, lowW, lowH);
        GLES20.glUniform1f(wJitter, jitter ? 1f : 0f);
        GLES20.glUniform1f(wAffine, affine ? 1f : 0f);
        GLES20.glUniform1f(wFlick, flick);
        GLES20.glUniform2f(wFog, fogNear, fogFar);
        GLES20.glUniform3f(wFogCol, fogCol[0], fogCol[1], fogCol[2]);
        GLES20.glUniform1f(wBlend, blend ? 1f : 0f);
        GLES20.glUniform1f(wDither, dither ? 1f : 0f);
        GLES20.glUniform1i(wTex, 0);
    }

    public void useRigid(float[] vp, float[] amb, float[] lpos, float[] lcol) {
        GLES20.glUseProgram(pRigid);
        GLES20.glUniformMatrix4fv(rVP, 1, false, vp, 0);
        GLES20.glUniform2f(rRes, lowW, lowH);
        GLES20.glUniform1f(rJitter, jitter ? 1f : 0f);
        GLES20.glUniform1f(rAffine, affine ? 1f : 0f);
        GLES20.glUniform2f(rFog, fogNear, fogFar);
        GLES20.glUniform3f(rFogCol, fogCol[0], fogCol[1], fogCol[2]);
        GLES20.glUniform3f(rAmb, amb[0], amb[1], amb[2]);
        GLES20.glUniform4fv(rLPos, 4, lpos, 0);
        GLES20.glUniform4fv(rLCol, 4, lcol, 0);
        GLES20.glUniform1f(rBlend, 0f);
        GLES20.glUniform1f(rDither, dither ? 1f : 0f);
        GLES20.glUniform1i(rTex, 0);
    }

    public void endScene() {
        GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0);
        GLES20.glViewport(0, 0, screenW, screenH);
        GLES20.glDisable(GLES20.GL_DEPTH_TEST);
        GLES20.glDisable(GLES20.GL_CULL_FACE);
        GLES20.glDisable(GLES20.GL_BLEND);
        GLES20.glUseProgram(pPresent);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, fboTex);
        GLES20.glUniform1i(prTex, 0);
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, quadVbo);
        GLES20.glEnableVertexAttribArray(prPos);
        GLES20.glVertexAttribPointer(prPos, 2, GLES20.GL_FLOAT, false, 8, 0);
        GLES20.glDrawArrays(GLES20.GL_TRIANGLES, 0, 6);
        GLES20.glDisableVertexAttribArray(prPos);
    }
}
