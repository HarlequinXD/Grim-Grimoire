package com.harlequin.grimgrimoire;

import android.content.res.AssetManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.opengl.GLES20;
import android.opengl.GLUtils;
import android.util.Log;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;

/** Shader/texture/asset helpers. */
public final class GlUtil {
    private static final String TAG = "GrimGrimoire";
    private GlUtil() {}

    public static int program(String vs, String fs) {
        int v = shader(GLES20.GL_VERTEX_SHADER, vs), f = shader(GLES20.GL_FRAGMENT_SHADER, fs);
        int p = GLES20.glCreateProgram();
        GLES20.glAttachShader(p, v);
        GLES20.glAttachShader(p, f);
        GLES20.glLinkProgram(p);
        int[] ok = new int[1];
        GLES20.glGetProgramiv(p, GLES20.GL_LINK_STATUS, ok, 0);
        if (ok[0] == 0) throw new RuntimeException("link: " + GLES20.glGetProgramInfoLog(p));
        return p;
    }

    private static int shader(int type, String src) {
        int s = GLES20.glCreateShader(type);
        GLES20.glShaderSource(s, src);
        GLES20.glCompileShader(s);
        int[] ok = new int[1];
        GLES20.glGetShaderiv(s, GLES20.GL_COMPILE_STATUS, ok, 0);
        if (ok[0] == 0) {
            String log = GLES20.glGetShaderInfoLog(s);
            Log.e(TAG, "shader compile failed: " + log + "\n" + src);
            throw new RuntimeException("shader: " + log);
        }
        return s;
    }

    public static byte[] readAsset(AssetManager am, String name) {
        try (InputStream in = am.open(name)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[16384];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            return out.toByteArray();
        } catch (IOException e) {
            throw new RuntimeException("missing asset " + name, e);
        }
    }

    public static ByteBuffer le(byte[] data) {
        return ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN);
    }

    /** Nearest-filtered, clamped, no mipmaps: PS1 texture sampling. */
    public static int texture(AssetManager am, String name) {
        BitmapFactory.Options o = new BitmapFactory.Options();
        o.inScaled = false;
        o.inPremultiplied = false;
        byte[] d = readAsset(am, name);
        Bitmap bmp = BitmapFactory.decodeByteArray(d, 0, d.length, o);
        int[] id = new int[1];
        GLES20.glGenTextures(1, id, 0);
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, id[0]);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_NEAREST);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_NEAREST);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE);
        GLUtils.texImage2D(GLES20.GL_TEXTURE_2D, 0, bmp, 0);
        bmp.recycle();
        return id[0];
    }

    public static FloatBuffer floats(int count) {
        return ByteBuffer.allocateDirect(count * 4).order(ByteOrder.nativeOrder()).asFloatBuffer();
    }

    public static int vbo(FloatBuffer fb, int usage) {
        int[] id = new int[1];
        GLES20.glGenBuffers(1, id, 0);
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, id[0]);
        fb.position(0);
        GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, fb.capacity() * 4, fb, usage);
        return id[0];
    }
}
