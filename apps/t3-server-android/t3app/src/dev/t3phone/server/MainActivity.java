package dev.t3phone.server;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.net.HttpURLConnection;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.URL;
import java.util.Collections;
import java.util.Enumeration;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    static final String TERMUX_PKG = "com.termux";
    static final String RUN_CMD = "com.termux.RUN_COMMAND";
    static final String RUN_PERM = "com.termux.permission.RUN_COMMAND";
    static final String P_PATH = "com.termux.RUN_COMMAND_PATH";
    static final String P_ARGS = "com.termux.RUN_COMMAND_ARGUMENTS";
    static final String P_WORKDIR = "com.termux.RUN_COMMAND_WORKDIR";
    static final String P_BG = "com.termux.RUN_COMMAND_BACKGROUND";
    static final String HOME = "/data/data/com.termux/files/home";
    static final int OP_PORT = 4096;
    static final int T3_PORT = 3773;

    // Active 30-day pairing token
    static String pairToken = "";

    final ExecutorService exec = Executors.newSingleThreadExecutor();
    final Handler handler = new Handler(Looper.getMainLooper());
    Runnable poller;

    TextView tvOverall, tvOpStatus, tvT3Status, tvAgStatus, tvAgDesc, tvPairUrl, tvLan, tvTail, tvSsh;
    EditText etOpKey, etAgKey;
    String lanIp = null;
    String tailIp = null;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        setContentView(R.layout.activity_main);

        tvOverall = findViewById(R.id.tvOverall);
        tvOpStatus = findViewById(R.id.tvOpStatus);
        tvT3Status = findViewById(R.id.tvT3Status);
        tvAgStatus = findViewById(R.id.tvAgStatus);
        tvAgDesc = findViewById(R.id.tvAgDesc);
        tvPairUrl = findViewById(R.id.tvPairUrl);
        tvLan = findViewById(R.id.tvLan);
        tvTail = findViewById(R.id.tvTail);
        tvSsh = findViewById(R.id.tvSsh);

        etOpKey = findViewById(R.id.etOpKey);
        etAgKey = findViewById(R.id.etAgKey);

        // Client Connection Actions
        ((Button) findViewById(R.id.btnCopyLan)).setOnClickListener(v -> {
            String url = getPairUrl(lanIp != null ? lanIp : "127.0.0.1");
            copy(url);
            toast("Copied Wi-Fi pairing URL to clipboard");
        });

        ((Button) findViewById(R.id.btnCopyTail)).setOnClickListener(v -> {
            String url = getPairUrl(tailIp != null ? tailIp : "100.101.66.102");
            copy(url);
            toast("Copied Tailscale pairing URL to clipboard");
        });

        ((Button) findViewById(R.id.btnT3Open)).setOnClickListener(v -> {
            openUrl("http://127.0.0.1:" + T3_PORT + "/");
        });

        ((Button) findViewById(R.id.btnMintToken)).setOnClickListener(v -> {
            sendCmd(HOME + "/generate-pair-token.sh", null, "Minting new 30-day pairing token...");
            handler.postDelayed(() -> {
                loadTokenFromFile();
                refresh();
            }, 3500);
        });

        // Service Lifecycle Actions
        ((Button) findViewById(R.id.btnStart)).setOnClickListener(v -> {
            sendCmd(HOME + "/.shortcuts/start-servers.sh", null, "Starting services...");
            handler.postDelayed(this::refresh, 4000);
        });

        ((Button) findViewById(R.id.btnRestart)).setOnClickListener(v -> {
            sendCmd(HOME + "/restart-servers.sh", null, "Restarting services...");
            handler.postDelayed(this::refresh, 4000);
        });

        ((Button) findViewById(R.id.btnStop)).setOnClickListener(v -> {
            sendCmd(HOME + "/.shortcuts/stop-servers.sh", null, "Stopping services...");
            handler.postDelayed(this::refresh, 3000);
        });

        ((Button) findViewById(R.id.btnRefresh)).setOnClickListener(v -> {
            loadTokenFromFile();
            refresh();
            toast("Refreshed status");
        });

        // OpenCode Authentication Actions
        ((Button) findViewById(R.id.btnOpSave)).setOnClickListener(v -> {
            String k = etOpKey.getText().toString().trim();
            if (k.isEmpty()) {
                toast("Please enter an OpenCode API key");
                return;
            }
            sendCmd(HOME + "/save-opencode-key.sh", new String[]{k}, "Saved OpenCode key. Reloading...");
            etOpKey.setText("");
            handler.postDelayed(this::refresh, 3000);
        });

        ((Button) findViewById(R.id.btnOpClear)).setOnClickListener(v -> {
            sendCmd(HOME + "/save-opencode-key.sh", new String[]{"clear"}, "Reset OpenCode to free models.");
            etOpKey.setText("");
            handler.postDelayed(this::refresh, 3000);
        });

        // Antigravity Authentication Actions
        ((Button) findViewById(R.id.btnAgSave)).setOnClickListener(v -> {
            String k = etAgKey.getText().toString().trim();
            if (k.isEmpty()) {
                toast("Please enter a Gemini API key");
                return;
            }
            sendCmd(HOME + "/save-antigravity-key.sh", new String[]{k}, "Configured Gemini API Key for Antigravity.");
            etAgKey.setText("");
            handler.postDelayed(this::refresh, 3000);
        });

        ((Button) findViewById(R.id.btnAgOAuth)).setOnClickListener(v -> {
            sendCmd(HOME + "/save-antigravity-key.sh", new String[]{"oauth"}, "Switched Antigravity to Workstation OAuth.");
            etAgKey.setText("");
            handler.postDelayed(this::refresh, 3000);
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        loadTokenFromFile();
        refresh();
        poller = new Runnable() {
            @Override public void run() { refresh(); handler.postDelayed(poller, 8000); }
        };
        handler.postDelayed(poller, 8000);
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (poller != null) handler.removeCallbacks(poller);
    }

    void loadTokenFromFile() {
        File[] candidates = new File[]{
            new File(getExternalFilesDir(null), "t3-pair-token.txt"),
            new File("/sdcard/Android/data/dev.t3phone.server/files/t3-pair-token.txt"),
            new File("/sdcard/Download/t3-pair-token.txt")
        };
        for (File f : candidates) {
            try {
                if (f != null && f.exists() && f.canRead()) {
                    BufferedReader br = new BufferedReader(new FileReader(f));
                    String line = br.readLine();
                    br.close();
                    if (line != null && !line.trim().isEmpty()) {
                        pairToken = line.trim();
                        return;
                    }
                }
            } catch (Exception ignored) {}
        }
    }

    String getPairUrl(String host) {
        if (pairToken == null || pairToken.isEmpty()) {
            return "http://" + host + ":" + T3_PORT + "/";
        }
        return "http://" + host + ":" + T3_PORT + "/pair#token=" + pairToken;
    }

    void refresh() {
        exec.execute(() -> {
            loadTokenFromFile();
            final int op = httpCode(OP_PORT);
            final int t3 = httpCode(T3_PORT);
            final String wlan = ipv4("wlan0", "eth0");
            final String tail = ipv4("tailscale0", "utun", "tun0");

            handler.post(() -> {
                lanIp = wlan;
                tailIp = tail;
                boolean opUp = op > 0;
                boolean t3Up = t3 > 0;
                boolean allUp = opUp && t3Up;

                if (allUp) {
                    tvOverall.setText("ALL SYSTEMS ONLINE");
                    tvOverall.setTextColor(getColor(R.color.up_text));
                    tvOverall.setBackgroundResource(R.drawable.pill_up);
                } else if (opUp || t3Up) {
                    tvOverall.setText("PARTIAL SERVICE");
                    tvOverall.setTextColor(getColor(R.color.neutral_text));
                    tvOverall.setBackgroundResource(R.drawable.pill_neutral);
                } else {
                    tvOverall.setText("SERVICES STOPPED");
                    tvOverall.setTextColor(getColor(R.color.down_text));
                    tvOverall.setBackgroundResource(R.drawable.pill_down);
                }

                if (opUp) {
                    tvOpStatus.setText("ONLINE");
                    tvOpStatus.setTextColor(getColor(R.color.up_text));
                    tvOpStatus.setBackgroundResource(R.drawable.pill_up);
                } else {
                    tvOpStatus.setText("OFFLINE");
                    tvOpStatus.setTextColor(getColor(R.color.down_text));
                    tvOpStatus.setBackgroundResource(R.drawable.pill_down);
                }

                if (t3Up) {
                    tvT3Status.setText("ONLINE");
                    tvT3Status.setTextColor(getColor(R.color.up_text));
                    tvT3Status.setBackgroundResource(R.drawable.pill_up);
                } else {
                    tvT3Status.setText("OFFLINE");
                    tvT3Status.setTextColor(getColor(R.color.down_text));
                    tvT3Status.setBackgroundResource(R.drawable.pill_down);
                }

                tvAgStatus.setText("AUTHENTICATED");
                tvAgStatus.setTextColor(getColor(R.color.up_text));
                tvAgStatus.setBackgroundResource(R.drawable.pill_up);

                String displayHost = wlan != null ? wlan : (tail != null ? tail : "127.0.0.1");
                tvPairUrl.setText(getPairUrl(displayHost));

                tvLan.setText("Wi-Fi Interface: " + (wlan != null ? ("http://" + wlan + ":3773") : "disconnected"));
                tvTail.setText("Tailscale Interface: " + (tail != null ? ("http://" + tail + ":3773") : (tailIp != null ? ("http://" + tailIp + ":3773") : "inactive")));
                tvSsh.setText("SSH Endpoint: ssh -p 8022 root@" + (wlan != null ? wlan : "127.0.0.1"));
            });
        });
    }

    int httpCode(int port) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL("http://127.0.0.1:" + port + "/").openConnection();
            c.setConnectTimeout(2500);
            c.setReadTimeout(2500);
            c.setInstanceFollowRedirects(false);
            return c.getResponseCode();
        } catch (Exception e) {
            return -1;
        } finally {
            if (c != null) c.disconnect();
        }
    }

    String ipv4(String... names) {
        try {
            Enumeration<NetworkInterface> nis = NetworkInterface.getNetworkInterfaces();
            for (NetworkInterface ni : Collections.list(nis)) {
                String n = ni.getName();
                boolean want = false;
                for (String w : names) if (n.equals(w) || n.startsWith(w)) want = true;
                if (!want || !ni.isUp() || ni.isLoopback()) continue;
                for (InetAddress a : Collections.list(ni.getInetAddresses())) {
                    if (a instanceof Inet4Address && !a.isLoopbackAddress()) return a.getHostAddress();
                }
            }
        } catch (Exception ignored) {}
        return null;
    }

    void sendCmd(String path, String[] args, String msg) {
        if (checkSelfPermission(RUN_PERM) != PackageManager.PERMISSION_GRANTED) {
            toast("Grant 'Run commands in Termux' permission in settings");
            openAppInfo();
            return;
        }
        try {
            Intent i = new Intent(RUN_CMD);
            i.setClassName(TERMUX_PKG, TERMUX_PKG + ".app.RunCommandService");
            i.putExtra(P_PATH, path);
            if (args != null) i.putExtra(P_ARGS, args);
            i.putExtra(P_WORKDIR, HOME);
            i.putExtra(P_BG, true);
            startService(i);
            toast(msg);
        } catch (Exception e) {
            toast("Command failed: " + e.getMessage());
        }
    }

    void openUrl(String u) {
        try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(u))); }
        catch (Exception e) { toast("Cannot open URL: " + u); }
    }

    void copy(String s) {
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        cm.setPrimaryClip(ClipData.newPlainText("t3-pair-url", s));
    }

    void openAppInfo() {
        try {
            startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:" + getPackageName())));
        } catch (Exception ignored) {}
    }

    void toast(String s) { Toast.makeText(this, s, Toast.LENGTH_SHORT).show(); }
}
