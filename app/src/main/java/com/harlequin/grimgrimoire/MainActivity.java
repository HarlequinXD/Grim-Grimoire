package com.harlequin.grimgrimoire;

import android.app.Activity;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;

public final class MainActivity extends Activity {
    private GLSurfaceView view;
    private final Input input = new Input();

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON | WindowManager.LayoutParams.FLAG_FULLSCREEN);
        view = new GLSurfaceView(this);
        view.setEGLContextClientVersion(2);
        view.setEGLConfigChooser(8, 8, 8, 8, 16, 0);
        view.setPreserveEGLContextOnPause(true);
        view.setRenderer(new GameRenderer(getAssets(), input));
        view.setOnTouchListener((v, e) -> input.onTouch(e));
        view.setFocusable(true);
        view.setFocusableInTouchMode(true);
        setContentView(view);
        immersive();
    }

    private void immersive() {
        view.setSystemUiVisibility(View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) immersive();
    }

    @Override
    protected void onPause() { super.onPause(); view.onPause(); }

    @Override
    protected void onResume() { super.onResume(); view.onResume(); immersive(); }

    @Override
    public boolean dispatchGenericMotionEvent(MotionEvent e) {
        if (input.onGenericMotion(e)) return true;
        return super.dispatchGenericMotionEvent(e);
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent e) {
        if (e.getKeyCode() == KeyEvent.KEYCODE_BACK) return super.dispatchKeyEvent(e);
        int a = e.getAction();
        if (a == KeyEvent.ACTION_DOWN || a == KeyEvent.ACTION_UP) {
            if (e.getRepeatCount() > 0) return true;
            if (input.onKey(e.getKeyCode(), a == KeyEvent.ACTION_DOWN)) return true;
        }
        return super.dispatchKeyEvent(e);
    }
}
