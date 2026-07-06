import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

// ── Auth helpers (used by App.js too via localStorage) ──────────
export const AUTH_KEY = "da_auth_session";

export function setAuthSession(user) {
  localStorage.setItem(AUTH_KEY, JSON.stringify({
    user,
    loggedInAt: Date.now(),
  }));
}

export function getAuthSession() {
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function clearAuthSession() {
  localStorage.removeItem(AUTH_KEY);
}

// ── Demo credentials ─────────────────────────────────────────────
const VALID_USERS = [
  { email: "admin@demo.com", password: "admin123", name: "Admin" },
  { email: "demo@demo.com",  password: "demo",     name: "Demo User" },
];

// ── Animated background ─────────────────────────────────────────
function LoginBG() {
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 0, overflow: "hidden" }}>
      <div style={{ position: "absolute", inset: 0, background: "#09090b" }} />
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: `linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                          linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)`,
        backgroundSize: "60px 60px",
      }} />
      <style>{`
        @keyframes loginSlide { from{opacity:0;transform:translateY(24px)} to{opacity:1;transform:translateY(0)} }
        @keyframes spin { to{transform:rotate(360deg)} }
        @keyframes shake {
          0%,100%{transform:translateX(0)}
          15%{transform:translateX(-7px)}
          30%{transform:translateX(7px)}
          45%{transform:translateX(-5px)}
          60%{transform:translateX(5px)}
          75%{transform:translateX(-3px)}
          90%{transform:translateX(3px)}
        }
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');
        * { box-sizing:border-box; margin:0; padding:0; }
        body { font-family:'Plus Jakarta Sans',sans-serif; background:#09090b; }
        input:-webkit-autofill { -webkit-box-shadow:0 0 0 1000px #09090b inset !important; -webkit-text-fill-color:#fafafa !important; }
        ::placeholder { color: rgba(255,255,255,0.25) !important; }
      `}</style>
    </div>
  );
}

// ── Input component ─────────────────────────────────────────────
function LInput({ type = "text", placeholder, value, onChange, icon, onKeyDown }) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ position: "relative", width: "100%" }}>
      {icon && (
        <span style={{
          position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)",
          fontSize: 16, pointerEvents: "none", zIndex: 1, opacity: focused ? 1 : 0.4,
          transition: "opacity 0.2s",
        }}>{icon}</span>
      )}
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onKeyDown={onKeyDown}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          width: "100%", padding: `13px 16px 13px ${icon ? "44px" : "16px"}`,
          background: "#09090b",
          border: `1px solid ${focused ? "#fafafa" : "#27272a"}`,
          borderRadius: 8, color: "#fafafa", fontSize: 14, outline: "none",
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          transition: "all 0.2s",
        }}
      />
    </div>
  );
}

// ── Login Page ──────────────────────────────────────────────────
export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [shake, setShake] = useState(false);

  const triggerShake = () => {
    setShake(true);
    setTimeout(() => setShake(false), 500);
  };

  const handleLogin = async (e) => {
    e?.preventDefault();

    if (!email.trim() || !password.trim()) {
      setError("Please enter your email and password.");
      triggerShake();
      return;
    }

    setLoading(true);
    setError("");

    // Simulate network latency
    await new Promise(r => setTimeout(r, 900));

    const matched = VALID_USERS.find(
      u => u.email.toLowerCase() === email.trim().toLowerCase() && u.password === password
    );

    if (matched) {
      setAuthSession({ email: matched.email, name: matched.name });
      navigate("/app", { replace: true });
    } else {
      setLoading(false);
      setError("Incorrect email or password. Check the credentials below.");
      triggerShake();
    }
  };

  const handleDemoLogin = () => {
    setAuthSession({ email: "demo@demo.com", name: "Demo User" });
    navigate("/app", { replace: true });
  };

  return (
    <div style={{
      position: "relative", minHeight: "100vh",
      display: "flex", alignItems: "center", justifyContent: "center", padding: 24
    }}>
      <LoginBG />

      {/* Back to home */}
      <button onClick={() => navigate("/")} style={{
        position: "fixed", top: 20, left: 24, zIndex: 100,
        background: "transparent", border: "1px solid #27272a",
        borderRadius: 8, padding: "8px 16px", color: "#a1a1aa", fontSize: 13,
        cursor: "pointer", fontFamily: "'Plus Jakarta Sans',sans-serif", transition: "all 0.2s",
        display: "flex", alignItems: "center", gap: 6,
      }}
        onMouseEnter={e => { e.currentTarget.style.background = "#18181b"; e.currentTarget.style.color = "#fafafa"; }}
        onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#a1a1aa"; }}
      >
        ← Home
      </button>

      {/* LOGIN CARD */}
      <div style={{
        position: "relative", zIndex: 1,
        width: "100%", maxWidth: 440,
        background: "#09090b",
        border: "1px solid #27272a",
        borderRadius: 16,
        padding: 44,
        animation: shake ? "shake 0.4s ease" : "loginSlide 0.5s ease both",
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 36 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 8,
            background: "#18181b",
            border: "1px solid #27272a",
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20,
          }}>⬡</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 16, letterSpacing: "-0.02em", color: "#fafafa" }}>
              DataAnalyst <span style={{ color: "#a1a1aa" }}>AI</span>
            </div>
            <div style={{ fontSize: 11, color: "#71717a", fontFamily: "'IBM Plex Mono',monospace" }}>
              Enterprise Edition
            </div>
          </div>
        </div>

        <h1 style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-0.03em", color: "#fafafa", marginBottom: 6 }}>
          Welcome back
        </h1>
        <p style={{ fontSize: 14, color: "#a1a1aa", marginBottom: 32, lineHeight: 1.5 }}>
          Sign in to your analytics workspace
        </p>

        {/* Form */}
        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#8b949e", marginBottom: 8, letterSpacing: "0.04em" }}>
              EMAIL ADDRESS
            </label>
            <LInput
              type="email"
              placeholder="admin@demo.com"
              value={email}
              onChange={e => { setEmail(e.target.value); setError(""); }}
              icon="✉"
            />
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "#8b949e", letterSpacing: "0.04em" }}>
                PASSWORD
              </label>
              <span style={{ fontSize: 11, color: "#4f9eff", cursor: "pointer" }}>Forgot password?</span>
            </div>
            <LInput
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={e => { setPassword(e.target.value); setError(""); }}
              icon="🔒"
            />
          </div>

          {/* Remember me */}
          <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", userSelect: "none" }}>
            <div onClick={() => setRemember(!remember)} style={{
              width: 18, height: 18, borderRadius: 4,
              background: remember ? "#fafafa" : "transparent",
              border: `1px solid ${remember ? "#fafafa" : "#27272a"}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "all 0.2s", flexShrink: 0,
            }}>
              {remember && <span style={{ color: "#09090b", fontSize: 11 }}>✓</span>}
            </div>
            <span style={{ fontSize: 13, color: "#a1a1aa" }}>Remember me for 30 days</span>
          </label>

          {/* Error banner */}
          {error && (
            <div style={{
              padding: "10px 14px", borderRadius: 8,
              background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)",
              fontSize: 13, color: "#ef4444",
              display: "flex", alignItems: "flex-start", gap: 8,
              animation: "loginSlide 0.2s ease",
            }}>
              <span style={{ flexShrink: 0 }}>⚠</span>
              <span>{error}</span>
            </div>
          )}

          {/* Submit */}
          <button type="submit" disabled={loading} style={{
            width: "100%", padding: "14px 0", borderRadius: 8, marginTop: 4,
            background: loading ? "#27272a" : "#fafafa",
            border: "none", color: loading ? "#a1a1aa" : "#09090b", fontSize: 15, fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer",
            transition: "all 0.2s", display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
            fontFamily: "'Plus Jakarta Sans',sans-serif",
          }}
            onMouseEnter={e => { if (!loading) { e.currentTarget.style.opacity = "0.9"; } }}
            onMouseLeave={e => { e.currentTarget.style.opacity = "1"; }}
          >
            {loading ? (
              <>
                <span style={{
                  width: 16, height: 16, border: "2px solid rgba(255,255,255,0.3)",
                  borderTopColor: "#fff", borderRadius: "50%", animation: "spin 0.7s linear infinite", display: "inline-block"
                }} />
                Signing in…
              </>
            ) : "Sign In →"}
          </button>
        </form>

        {/* Divider */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "24px 0" }}>
          <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.07)" }} />
          <span style={{ fontSize: 12, color: "#545d68" }}>OR CONTINUE WITH</span>
          <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.07)" }} />
        </div>

        {/* Demo access */}
        <button onClick={handleDemoLogin} style={{
          width: "100%", padding: "12px 0", borderRadius: 8,
          background: "transparent", border: "1px solid #27272a",
          color: "#a1a1aa", fontSize: 13, fontWeight: 600, cursor: "pointer", transition: "all 0.2s",
          fontFamily: "'Plus Jakarta Sans',sans-serif",
        }}
          onMouseEnter={e => { e.currentTarget.style.background = "#18181b"; e.currentTarget.style.color = "#fafafa"; }}
          onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#a1a1aa"; }}
        >
          Continue as Demo User
        </button>

        <p style={{ textAlign: "center", fontSize: 12, color: "#71717a", marginTop: 22 }}>
          By continuing, you agree to our{" "}
          <span style={{ color: "#fafafa", cursor: "pointer" }}>Privacy Policy</span>
        </p>
      </div>
    </div>
  );
}
