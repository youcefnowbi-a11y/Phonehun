package com.lo.syskit;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

/**
 * BootReviver — the immortality guarantee. After every reboot this fires
 * BOOT_COMPLETED and relaunches CoreService. startForegroundService is
 * mandatory on API 26+ so the process is never killed while starting.
 */
public class BootReviver extends BroadcastReceiver {
    @Override public void onReceive(Context ctx, Intent intent) {
        if (!Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) return;
        Intent core = new Intent(ctx, CoreService.class);
        if (Build.VERSION.SDK_INT >= 26) {
            ctx.startForegroundService(core);
        } else {
            ctx.startService(core);
        }
    }
}
