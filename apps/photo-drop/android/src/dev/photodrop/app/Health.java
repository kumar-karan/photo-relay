package dev.photodrop.app;

import org.json.JSONObject;

/**
 * Value object representing /healthz diagnostics.
 */
public final class Health {
    public final boolean up;
    public final long free;
    public final long total;
    public final long reserve;
    public final int sessions;
    public final String publicUrl;
    public final String lanIp;

    public Health(boolean up, long free, long total, long reserve, int sessions, String publicUrl, String lanIp) {
        this.up = up;
        this.free = free;
        this.total = total;
        this.reserve = reserve;
        this.sessions = sessions;
        this.publicUrl = publicUrl != null ? publicUrl.trim() : "";
        this.lanIp = lanIp != null ? lanIp.trim() : "";
    }

    public static Health down() {
        return new Health(false, -1, -1, -1, 0, "", "");
    }

    public static Health parse(String body) {
        if (body == null || body.trim().isEmpty()) {
            return down();
        }
        try {
            JSONObject j = new JSONObject(body);
            boolean ok = j.optBoolean("ok", false);
            long free = j.optLong("free", -1);
            long total = j.optLong("dest_size", -1);
            long reserve = j.optLong("reserve", -1);
            int sessions = j.optInt("sessions", 0);
            String pubUrl = j.optString("public_url", "");
            String lan = j.optString("lan_ip", "");
            return new Health(ok, free, total, reserve, sessions, pubUrl, lan);
        } catch (Exception e) {
            return down();
        }
    }

    public boolean known() {
        return free >= 0;
    }

    public boolean isLow() {
        return known() && reserve > 0 && free <= reserve;
    }

    public float freeRatio() {
        if (total <= 0 || free < 0) return 0f;
        return (float) free / (float) total;
    }

    public float reserveRatio() {
        if (total <= 0 || reserve < 0) return 0f;
        return (float) reserve / (float) total;
    }
}
