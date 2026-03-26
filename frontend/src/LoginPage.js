import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

// ── Animated background ─────────────────────────────────────────
function LoginBG() {
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 0, overflow: "hidden" }}>
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(135deg, #050810 0%, #080d1a 50%, #050810 100%)"
      }} />
      {/* Glowing blobs */}
      <div style={{
        position: "absolute", width: 800, height: 800, borderRadius: "50%", top: "-20%", left: "-20%",
        background: "radial-gradient(circle, rgba(37,99,235,0.12) 0%, transparent 70%)",
        filter: "blur(40px)", animation: "blobFloat1 10s ease-in-out infinite alternate",
      }} />
      <div style={{
        position: "absolute", width: 600, height: 600, borderRadius: "50%", bottom: "-15%", right: "-15%",
        background: "radial-gradient(circle, rgba(124,58,237,0.1) 0%, transparent 70%)",
        filter: "blur(40px)", animation: "blobFloat2 8s ease-in-out infinite alternate",
      }} />
      <div style={{
        position: "absolute", width: 400, height: 400, borderRadius: "50%", top: "50%", right: "20%",
        background: "radial-gradient(circle, rgba(45,212,191,0.07) 0%, transparent 70%)",
        filter: "blur(30px)", animation: "blobFloat2 12s ease-in-out 2s infinite alternate",
      }} />
      {/* Subtle grid */}
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: `linear-gradient(rgba(79,158,255,0.035) 1px, transparent 1px),
                          linear-gradient(90deg, rgba(79,158,255,0.035) 1px, transparent 1px)`,
        backgroundSize: "60px 60px",
      }} />
      <style>{`
        @keyframes blobFloat1 { from{transform:translate(0,0) scale(1)} to{transform:translate(30px,-20px) scale(1.05)} }
        @keyframes blobFloat2 { from{transform:translate(0,0) scale(1)} to{transform:translate(-20px,30px) scale(1.08)} }
        @keyframes loginSlide { from{opacity:0;transform:translateY(24px)} to{opacity:1;transform:translateY(0)} }
        @keyframes spin { to{transform:rotate(360deg)} }
        @keyframes glow { 0%,100%{box-shadow:0 0 20px rgba(37,99,235,0.3)} 50%{box-shadow:0 0 50px rgba(37,99,235,0.6)} }
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');
        * { box-sizing:border-box; margin:0; padding:0; }
        body { font-family:'Plus Jakarta Sans',sans-serif; background:#050810; }
        input:-webkit-autofill { -webkit-box-shadow:0 0 0 1000px #0d1117 inset !important; -webkit-text-fill-color:#cdd9e5 !important; }
      `}</style>
    </div>
  );
}

// ── Input component ─────────────────────────────────────────────
function LInput({ type = "text", placeholder, value, onChange, icon }) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ position: "relative", width: "100%" }}>
      {icon && (
        <span style={{
          position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)",
          fontSize: 16, pointerEvents: "none", zIndex: 1, opacity: focused ? 1 : 0.5,
          transition: "opacity 0.2s",
        }}>{icon}</span>
      )}
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          width: "100%", padding: `13px 16px 13px ${icon ? "44px" : "16px"}`,
          background: "rgba(255,255,255,0.05)",
          border: `1px solid ${focused ? "rgba(79,158,255,0.6)" : "rgba(255,255,255,0.1)"}`,
          borderRadius: 12, color: "#cdd9e5", fontSize: 14, outline: "none",
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          boxShadow: focused ? "0 0 0 3px rgba(79,158,255,0.12)" : "none",
          backdropFilter: "blur(8px)",
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

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError("Please enter your email and password.");
      return;
    }
    setLoading(true); setError("");

    // Simulate auth check — accept any non-empty credentials (demo mode)
    await new Promise(r => setTimeout(r, 1200));

    // Demo: accept any input, or check for specific creds:
    // if (email === "admin@example.com" && password === "admin123")
    setLoading(false);
    navigate("/app");
  };

  const triggerShake = () => {
    setShake(true);
    setTimeout(() => setShake(false), 500);
  };

  return (
    <div style={{ position: "relative", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <LoginBG />

      {/* Back to home */}
      <button onClick={() => navigate("/")} style={{
        position: "fixed", top: 20, left: 24, zIndex: 100,
        background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 10, padding: "8px 16px", color: "#8b949e", fontSize: 13,
        cursor: "pointer", fontFamily: "'Plus Jakarta Sans',sans-serif", transition: "all 0.2s",
        display: "flex", alignItems: "center", gap: 6,
      }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(79,158,255,0.4)"; e.currentTarget.style.color = "#cdd9e5"; }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)"; e.currentTarget.style.color = "#8b949e"; }}
      >
        ← Home
      </button>

      {/* LOGIN CARD */}
      <div style={{
        position: "relative", zIndex: 1,
        width: "100%", maxWidth: 440,
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 24, backdropFilter: "blur(30px)",
        boxShadow: "0 32px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.05) inset",
        padding: 44,
        animation: "loginSlide 0.5s ease both",
        ...(shake ? { animation: "loginSlide 0.5s ease both, shake 0.4s ease" } : {}),
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 36 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: "linear-gradient(135deg, #1a3a6e, #1e1040)",
            border: "1px solid rgba(79,158,255,0.35)",
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20,
            boxShadow: "0 4px 20px rgba(37,99,235,0.3)",
            animation: "glow 3s ease infinite",
          }}>⬡</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 16, letterSpacing: "-0.02em", color: "#cdd9e5" }}>
              DataAnalyst <span style={{ color: "#4f9eff" }}>AI</span>
            </div>
            <div style={{ fontSize: 11, color: "#545d68", fontFamily: "'IBM Plex Mono',monospace" }}>
              Enterprise Edition
            </div>
          </div>
        </div>

        <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: "-0.03em", color: "#cdd9e5", marginBottom: 6 }}>
          Welcome back
        </h1>
        <p style={{ fontSize: 14, color: "#8b949e", marginBottom: 32, lineHeight: 1.5 }}>
          Sign in to your analytics workspace
        </p>

        {/* Form */}
        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#8b949e", marginBottom: 8, letterSpacing: "0.02em" }}>
              EMAIL ADDRESS
            </label>
            <LInput
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={e => { setEmail(e.target.value); setError(""); }}
              icon="✉"
            />
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "#8b949e", letterSpacing: "0.02em" }}>
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
              width: 18, height: 18, borderRadius: 5,
              background: remember ? "linear-gradient(135deg, #2563eb, #7c3aed)" : "rgba(255,255,255,0.05)",
              border: `1px solid ${remember ? "#2563eb" : "rgba(255,255,255,0.15)"}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "all 0.2s", flexShrink: 0,
            }}>
              {remember && <span style={{ color: "#fff", fontSize: 11 }}>✓</span>}
            </div>
            <span style={{ fontSize: 13, color: "#8b949e" }}>Remember me for 30 days</span>
          </label>

          {/* Error */}
          {error && (
            <div style={{
              padding: "10px 14px", borderRadius: 10,
              background: "rgba(229,83,75,0.1)", border: "1px solid rgba(229,83,75,0.3)",
              fontSize: 13, color: "#e5534b",
            }}>⚠ {error}</div>
          )}

          {/* Submit */}
          <button type="submit" disabled={loading} style={{
            width: "100%", padding: "14px 0", borderRadius: 12, marginTop: 8,
            background: loading ? "rgba(37,99,235,0.4)" : "linear-gradient(135deg, #2563eb, #7c3aed)",
            border: "none", color: "#fff", fontSize: 15, fontWeight: 700, cursor: loading ? "not-allowed" : "pointer",
            boxShadow: loading ? "none" : "0 6px 30px rgba(37,99,235,0.4)",
            transition: "all 0.25s", display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
            fontFamily: "'Plus Jakarta Sans',sans-serif",
          }}
            onMouseEnter={e => { if(!loading) { e.currentTarget.style.transform = "translateY(-1px)"; e.currentTarget.style.boxShadow = "0 10px 40px rgba(37,99,235,0.55)"; }}}
            onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "0 6px 30px rgba(37,99,235,0.4)"; }}
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

        {/* SSO-style demo buttons */}
        <button onClick={() => navigate("/app")} style={{
          width: "100%", padding: "12px 0", borderRadius: 12,
          background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
          color: "#8b949e", fontSize: 13, fontWeight: 600, cursor: "pointer", transition: "all 0.2s",
          fontFamily: "'Plus Jakarta Sans',sans-serif",
        }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(79,158,255,0.35)"; e.currentTarget.style.color = "#cdd9e5"; e.currentTarget.style.background = "rgba(79,158,255,0.07)"; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)"; e.currentTarget.style.color = "#8b949e"; e.currentTarget.style.background = "rgba(255,255,255,0.04)"; }}
        >
          ⚡ Continue as Demo User
        </button>

        <p style={{ textAlign: "center", fontSize: 12, color: "#545d68", marginTop: 28 }}>
          By continuing, you agree to our{" "}
          <span style={{ color: "#4f9eff", cursor: "pointer" }}>Privacy Policy</span>
        </p>
      </div>
    </div>
  );
}
