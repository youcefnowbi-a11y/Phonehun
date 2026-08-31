package com.lo.syskit;

import android.content.Context;
import android.content.SharedPreferences;

/**
 * Config — the lightest possible remote reconfiguration. The relay
 * address lives in SharedPreferences; ops "config.set" changes it over
 * the existing link, so the agent never needs reinstalling to move.
 * Defaults point at the panel's LAN address.
 */
public final class Config {

    private static final String PREFS = "syskit";
    private static final String K_HOST = "host";
    private static final String K_PORT = "port";

    // TODO(lo): set your panel's LAN IP here before first build
    private static final String DEFAULT_HOST = "192.168.1.20";
    private static final int DEFAULT_PORT = 9876;

    private static Context appContext() {
        try {
            return AuditService.instance() != null
                    ? AuditService.instance()
                    : NlService.instance() != null ? NlService.instance() : null;
        } catch (Exception e) { return null; }
    }

    private static SharedPreferences prefs() {
        Context c = appContext();
        return c == null ? null
                : c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public static String host() {
        SharedPreferences p = prefs();
        return p == null ? DEFAULT_HOST : p.getString(K_HOST, DEFAULT_HOST);
    }

    public static int port() {
        SharedPreferences p = prefs();
        return p == null ? DEFAULT_PORT : p.getInt(K_PORT, DEFAULT_PORT);
    }

    public static void set(String host, int port) {
        SharedPreferences p = prefs();
        if (p == null) return;
        p.edit().putString(K_HOST, host).putInt(K_PORT, port).apply();
    }
}
