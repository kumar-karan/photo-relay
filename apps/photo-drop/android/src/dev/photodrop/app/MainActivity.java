package dev.photodrop.app;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowInsets;
import android.view.animation.PathInterpolator;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.SecureRandom;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Launcher for the Photo Drop server.
 *
 * The server is the Python service running in Termux. This app does not
 * reimplement it: it drives Termux over RUN_COMMAND and reads status back over
 * loopback HTTP, the same pattern as the T3 server app.
 *
 * The app owns the tokens. It mints them once, persists them, and pushes them
 * into Termux on every resume, so the link it shows is always the link the
 * server actually serves. An earlier version had Termux as the owner and the
 * two silently drifted apart, which left the app displaying a link that 404'd.
 */
public class MainActivity extends Activity {
    static final String TERMUX_PKG = "com.termux";
    static final String RUN_CMD = "com.termux.RUN_COMMAND";
    static final String RUN_PERM = "com.termux.permission.RUN_COMMAND";
    static final String P_PATH = "com.termux.RUN_COMMAND_PATH";
    static final String P_ARGS = "com.termux.RUN_COMMAND_ARGUMENTS";
    static final String P_WORKDIR = "com.termux.RUN_COMMAND_WORKDIR";
    static final String P_BG = "com.termux.RUN_COMMAND_BACKGROUND";
    static final String HOME = "/data/data/com.termux/files/home";
    static final String CONTROL = HOME + "/pd-control.sh";
    static final int PORT = 8080;

    static final String PREFS = "photodrop";
    static final String K_DROP = "drop_token";
    static final String K_OWNER = "owner_token";

    /** Material standard easing, used for the press scale. */
    static final PathInterpolator EASE = new PathInterpolator(0.2f, 0f, 0f, 1f);

    final ExecutorService exec = Executors.newSingleThreadExecutor();
    final Handler handler = new Handler(Looper.getMainLooper());
    Runnable poller;

    TextView tvStatus, tvSubtitle, tvFree, tvCapacity, tvUploads, tvScan;
    TextView tvDropDomain, tvDropUrl, tvDropHint, tvFooter, btnRefresh;
    StorageBarView storageBar;
    Button btnStart, btnStop, btnCopy;

    String dropToken = "";
    String ownerToken = "";
    String publicUrl = "";

    boolean starting = false;
    boolean up = false;
    int stop = 0;
    Runnable copyReset;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        setContentView(R.layout.activity_main);

        tvStatus = findViewById(R.id.tvStatus);
        tvSubtitle = findViewById(R.id.tvSubtitle);
        tvFree = findViewById(R.id.tvFree);
        tvCapacity = findViewById(R.id.tvCapacity);
        tvUploads = findViewById(R.id.tvUploads);
        tvScan = findViewById(R.id.tvScan);
        tvDropDomain = findViewById(R.id.tvDropDomain);
        tvDropUrl = findViewById(R.id.tvDropUrl);
        tvDropHint = findViewById(R.id.tvDropHint);
        tvFooter = findViewById(R.id.tvFooter);
        btnRefresh = findViewById(R.id.btnRefresh);
        storageBar = findViewById(R.id.storageBar);
        btnStart = findViewById(R.id.btnStart);
        btnStop = findViewById(R.id.btnStop);
        btnCopy = findViewById(R.id.btnCopy);

        applyInsets();

        tvFooter.setText("The server runs inside Termux. Set Termux battery to "
                + "\"Unrestricted\", or Android will pause an upload part way through.");

        loadTokens();
        ensureExternalDir();
        renderLink();

        btnStart.setOnClickListener(v -> {
            starting = true;
            btnStart.setEnabled(false);
            tvStatus.setText("STARTING");
            tvStatus.setBackgroundResource(R.drawable.pill_warning);
            tvStatus.setTextColor(getColor(R.color.warning));
            sendCmd(new String[]{"start"}, "Starting Photo Drop");
            handler.postDelayed(this::refresh, 8000);
        });

        btnStop.setOnClickListener(v -> {
            sendCmd(new String[]{"stop"}, "Stopping Photo Drop");
            handler.postDelayed(this::refresh, 3500);
        });

        btnRefresh.setOnClickListener(v -> { refresh(); toast("Refreshed"); });

        btnCopy.setOnClickListener(v -> { copyLink(); });
        findViewById(R.id.cardLink).setOnClickListener(v -> { copyLink(); });

        findViewById(R.id.btnUpload).setOnClickListener(v ->
            openWeb(base() + "/d/" + dropToken + "/"));
        findViewById(R.id.btnOwner).setOnClickListener(v ->
            openWeb(base() + "/owner/" + ownerToken));
        findViewById(R.id.btnScan).setOnClickListener(v ->
            openWeb(base() + "/owner/" + ownerToken));

        pressFeedback(btnStart);
        pressFeedback(btnStop);
        pressFeedback(btnCopy);
        pressFeedback(findViewById(R.id.btnUpload));
        pressFeedback(findViewById(R.id.btnOwner));
        pressFeedback(findViewById(R.id.btnScan));
        pressFeedback(btnRefresh);
    }

    /**
     * targetSdk 34 on Android 16 lets us opt out of edge-to-edge, but the
     * deprecated SYSTEM_UI_FLAG_* path is gone from API 30. Use the modern
     * setter and pad the root ourselves.
     */
    void applyInsets() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            getWindow().setDecorFitsSystemWindows(false);
        }
        final LinearLayout root = findViewById(R.id.root);
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            int top = dp(24), bottom = dp(32);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                Insets bars = insets.getInsets(
                        WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                top += bars.top;
                bottom += bars.bottom;
            } else {
                top += insets.getSystemWindowInsetTop();
                bottom += insets.getSystemWindowInsetBottom();
            }
            root.setPadding(dp(16), top, dp(16), bottom);
            return insets;
        });
        root.requestApplyInsets();
    }

    void pressFeedback(View v) {
        v.setOnTouchListener((view, e) -> {
            int a = e.getActionMasked();
            if (a == MotionEvent.ACTION_DOWN) {
                view.animate().cancel();
                view.animate().scaleX(0.97f).scaleY(0.97f).setDuration(120).setInterpolator(EASE).start();
            } else if (a == MotionEvent.ACTION_UP || a == MotionEvent.ACTION_CANCEL) {
                view.animate().scaleX(1f).scaleY(1f).setDuration(120).setInterpolator(EASE).start();
            }
            return false;
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        stop = 0;
        bootstrap();
        refresh();
        poller = new Runnable() {
            @Override public void run() {
                if (stop != 0) return;
                refresh();
                handler.postDelayed(poller, 7000);
            }
        };
        handler.postDelayed(poller, 7000);
    }

    @Override
    protected void onPause() {
        super.onPause();
        stop = 1;
        if (poller != null) handler.removeCallbacks(poller);
    }

    // ---- tokens -----------------------------------------------------------

    static String mintToken() {
        final String alphabet =
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
        SecureRandom r = new SecureRandom();
        StringBuilder sb = new StringBuilder(24);
        for (int i = 0; i < 24; i++) sb.append(alphabet.charAt(r.nextInt(alphabet.length())));
        return sb.toString();
    }

    void loadTokens() {
        SharedPreferences p = getSharedPreferences(PREFS, MODE_PRIVATE);
        dropToken = p.getString(K_DROP, "");
        ownerToken = p.getString(K_OWNER, "");
        if (dropToken.isEmpty() || ownerToken.isEmpty()) {
            if (dropToken.isEmpty()) dropToken = mintToken();
            if (ownerToken.isEmpty()) ownerToken = mintToken();
            p.edit().putString(K_DROP, dropToken).putString(K_OWNER, ownerToken).apply();
        }
    }

    void ensureExternalDir() {
        try {
            File d = getExternalFilesDir(null);
            if (d != null && !d.exists()) d.mkdirs();
        } catch (Exception ignored) {}
    }

    void bootstrap() {
        sendCmdQuietly(new String[]{"bootstrap", dropToken, ownerToken});
    }

    // ---- status -----------------------------------------------------------

    void refresh() {
        exec.execute(() -> {
            String health = httpGet("http://127.0.0.1:" + PORT + "/healthz", dropToken);
            String url = readPublicUrl();
            handler.post(() -> {
                if (stop != 0) return;
                publicUrl = url;
                renderLink();
                render(health);
            });
        });
    }

    void render(String health) {
        boolean wasUp = up;
        up = health != null && health.contains("\"ok\"");

        long free = parseLong(pick(health, "\"free\":", ",", "}"));
        long reserve = parseLong(pick(health, "\"reserve\":", ",", "}"));
        long total = parseLong(pick(health, "\"dest_size\":", ",", "}"));

        if (up && starting) {
            pill("STARTING", R.drawable.pill_warning, R.color.warning);
            btnStart.setEnabled(false);
        } else if (up) {
            starting = false;
            btnStart.setEnabled(false);
            btnStop.setAlpha(1f);
            if (free > 0 && reserve > 0 && free <= reserve) {
                pill("STORAGE LOW", R.drawable.pill_danger, R.color.danger);
            } else if (publicUrl.isEmpty()) {
                pill("ON LOCALLY", R.drawable.pill_neutral, R.color.text_muted);
            } else {
                pill("ONLINE", R.drawable.pill_success, R.color.success);
            }
        } else {
            starting = false;
            btnStart.setEnabled(true);
            btnStop.setAlpha(0.45f);
            pill("STOPPED", R.drawable.pill_neutral, R.color.text_muted);
        }

        tvSubtitle.setText(up
                ? "Photos go straight to this phone"
                : "Start the server to accept uploads");

        if (free < 0) {
            tvFree.setText("Storage unknown");
            tvCapacity.setText("Start the server to read storage from the phone.");
            storageBar.setState(0f, 0f);
        } else {
            boolean low = reserve > 0 && free <= reserve;
            tvFree.setText(human(free) + " free of " + human(total));
            tvFree.setTextColor(low ? getColor(R.color.danger) : getColor(R.color.text_main));
            tvCapacity.setText(low
                    ? "Uploads are paused until there is more than "
                      + human(reserve) + " free."
                    : "Uploads pause at " + human(reserve) + " free, so the phone "
                      + "never fills up.");
            storageBar.setState(
                    total > 0 ? (float) free / (float) total : 0f,
                    total > 0 ? (float) reserve / (float) total : 0f);
        }

        if (!wasUp && up) toast("Server is online");

        tvUploads.setText("No uploads in this session yet");
        tvScan.setText(publicUrl.isEmpty()
                ? "Media scan: open the report to see which method works"
                : "Media scan: see the report");
    }

    void pill(String text, int bg, int fg) {
        tvStatus.setText(text);
        tvStatus.setBackgroundResource(bg);
        tvStatus.setTextColor(getColor(fg));
    }

    /**
     * The link is the whole point of the app, so it gets a readable anchor plus
     * the full string. The domain carries the glance; the URL carries the copy.
     */
    void renderLink() {
        if (!up) {
            tvDropDomain.setText("Server not started");
            tvDropUrl.setText("--");
            tvDropHint.setText("Start the server to get a link you can send.");
            btnCopy.setEnabled(false);
            btnCopy.setAlpha(0.4f);
            return;
        }
        btnCopy.setEnabled(true);
        btnCopy.setAlpha(1f);
        String full = currentShareUrl();
        tvDropDomain.setText(domainOf(full));
        tvDropUrl.setText(full);
        tvDropHint.setText(publicUrl.isEmpty()
                ? "Reachable on this Wi-Fi only. Start the tunnel for a link that works anywhere."
                : "Works anywhere. It is the password, so send it only to your friend.");
    }

    /**
     * A 60 character URL is unreadable as a headline. Show the readable part of
     * the host and keep the full string underneath for the copy.
     * "releases-martin-termination-obviously.trycloudflare.com" -> "trycloudflare.com"
     * "127.0.0.1:8080" -> "this phone"
     */
    static String domainOf(String url) {
        String rest = url;
        int i = rest.indexOf("://");
        if (i >= 0) rest = rest.substring(i + 3);
        int slash = rest.indexOf('/');
        String host = slash >= 0 ? rest.substring(0, slash) : rest;
        // Drop the port. Not IPv6 safe, but nothing here serves on a literal v6 host.
        int colon = host.lastIndexOf(':');
        if (colon > 0 && host.indexOf(':') == colon) host = host.substring(0, colon);
        if (host.isEmpty() || host.equals("127.0.0.1") || host.equals("localhost")
                || host.equals("0.0.0.0")) {
            return "this phone";
        }
        // A bare IPv4 literal has no readable registrable part.
        if (host.matches("\\d{1,3}(\\.\\d{1,3}){3}")) return host;
        String[] parts = host.split("\\.");
        if (parts.length >= 2) return parts[parts.length - 2] + "." + parts[parts.length - 1];
        return host;
    }

    void copyLink() {
        if (!up) { toast("Start the server first"); return; }
        String url = currentShareUrl();
        copy(url);
        btnCopy.setText("Copied to clipboard");
        if (copyReset != null) handler.removeCallbacks(copyReset);
        copyReset = () -> btnCopy.setText("Copy link to send");
        handler.postDelayed(copyReset, 2000);
    }

    String base() {
        return publicUrl.isEmpty() ? "http://127.0.0.1:" + PORT : publicUrl;
    }

    String currentShareUrl() {
        return base() + "/d/" + dropToken + "/";
    }

    String readPublicUrl() {
        File[] cands = new File[]{
            new File(getExternalFilesDir(null), "public-url.txt"),
            new File("/sdcard/Android/data/dev.photodrop.app/files/public-url.txt")
        };
        for (File f : cands) {
            try {
                if (f == null || !f.exists() || !f.canRead()) continue;
                BufferedReader br = new BufferedReader(new FileReader(f));
                String line = br.readLine();
                br.close();
                if (line != null && !line.trim().isEmpty()) return line.trim();
            } catch (Exception ignored) {}
        }
        return "";
    }

    // ---- plumbing ---------------------------------------------------------

    String httpGet(String url, String token) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(url).openConnection();
            c.setConnectTimeout(2500);
            c.setReadTimeout(3500);
            if (token != null) c.setRequestProperty("X-PD-Token", token);
            c.setInstanceFollowRedirects(false);
            if (c.getResponseCode() != 200) return null;
            BufferedReader br = new BufferedReader(
                    new java.io.InputStreamReader(c.getInputStream()));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) sb.append(line);
            br.close();
            return sb.toString();
        } catch (Exception e) {
            return null;
        } finally {
            if (c != null) c.disconnect();
        }
    }

    static String pick(String json, String key, String stopA, String stopB) {
        if (json == null) return null;
        int i = json.indexOf(key);
        if (i < 0) return null;
        int from = i + key.length();
        int to = json.indexOf(stopA, from);
        if (to < 0) to = json.indexOf(stopB, from);
        return to < 0 ? null : json.substring(from, to);
    }

    static long parseLong(String s) {
        try { return s == null ? -1 : Long.parseLong(s.trim()); }
        catch (Exception e) { return -1; }
    }

    static String human(long n) {
        if (n < 0) return "--";
        String[] u = {"B", "KB", "MB", "GB", "TB"};
        double v = n;
        int i = 0;
        while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
        return (i == 0 ? String.valueOf((long) v) : String.format("%.1f", v)) + " " + u[i];
    }

    void sendCmd(String[] args, String msg) {
        if (checkSelfPermission(RUN_PERM) != PackageManager.PERMISSION_GRANTED) {
            toast("Grant \"Run commands in Termux\" for Photo Drop");
            openAppInfo();
            return;
        }
        if (runCmd(args)) toast(msg);
        else toast("Could not reach Termux. Open it once and run: bash ~/pd-control.sh bootstrap");
    }

    void sendCmdQuietly(String[] args) {
        if (checkSelfPermission(RUN_PERM) != PackageManager.PERMISSION_GRANTED) return;
        runCmd(args);
    }

    boolean runCmd(String[] args) {
        try {
            Intent i = new Intent(RUN_CMD);
            i.setClassName(TERMUX_PKG, TERMUX_PKG + ".app.RunCommandService");
            i.putExtra(P_PATH, CONTROL);
            i.putExtra(P_ARGS, args);
            i.putExtra(P_WORKDIR, HOME);
            i.putExtra(P_BG, true);
            startService(i);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    void openWeb(String url) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        } catch (Exception e) {
            toast("Nothing on this phone can open that link");
        }
    }

    void copy(String s) {
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        cm.setPrimaryClip(ClipData.newPlainText("photo-drop-link", s));
    }

    void openAppInfo() {
        try {
            startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:" + getPackageName())));
        } catch (Exception ignored) {}
    }

    int dp(int v) {
        return (int) (v * getResources().getDisplayMetrics().density + 0.5f);
    }

    void toast(String s) { Toast.makeText(this, s, Toast.LENGTH_SHORT).show(); }
}