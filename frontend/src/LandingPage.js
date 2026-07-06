import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

// ── Animated particles/orbs background ──────────────────────────
function AnimatedBG() {
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 0, overflow: "hidden", pointerEvents: "none" }}>
      <div style={{ position: "absolute", inset: 0, background: "#09090b" }} />
      {/* Grid lines overlay */}
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: `linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)`,
        backgroundSize: "60px 60px",
      }} />
      <style>{`
        @keyframes fadeUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes countUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=IBM+Plex+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html { scroll-behavior: smooth; }
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #09090b; color: #fafafa; overflow-x: hidden; }
        ::-webkit-scrollbar { width: 4px; } 
        ::-webkit-scrollbar-thumb { background: #1e2733; border-radius: 4px; }
      `}</style>
    </div>
  );
}

// ── Glassmorphic card ────────────────────────────────────────────
function GlassCard({ children, style = {}, hover = true }) {
  const [hov, setHov] = useState(false);
  return (
    <div
      onMouseEnter={() => hover && setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: hov ? "rgba(255,255,255,0.07)" : "rgba(255,255,255,0.03)",
        border: `1px solid ${hov ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.08)"}`,
        borderRadius: 12, backdropFilter: "blur(10px)",
        transition: "all 0.25s ease",
        transform: hov ? "translateY(-2px)" : "translateY(0)",
        boxShadow: hov
          ? "0 12px 24px rgba(0,0,0,0.4)"
          : "0 4px 12px rgba(0,0,0,0.2)",
        ...style
      }}
    >
      {children}
    </div>
  );
}

// ── Animated stat counter ────────────────────────────────────────
function StatCounter({ end, label, suffix = "" }) {
  const [count, setCount] = useState(0);
  const ref = useRef();
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) {
        let start = 0;
        const step = end / 60;
        const timer = setInterval(() => {
          start += step;
          if (start >= end) { setCount(end); clearInterval(timer); }
          else setCount(Math.floor(start));
        }, 20);
      }
    }, { threshold: 0.5 });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, [end]);
  return (
    <div ref={ref} style={{ textAlign: "center" }}>
      <div style={{
        fontSize: 48, fontWeight: 900, letterSpacing: "-0.03em",
        color: "#fafafa"
      }}>
        {count.toLocaleString()}{suffix}
      </div>
      <div style={{ fontSize: 13, color: "#8b949e", marginTop: 6, fontWeight: 500 }}>{label}</div>
    </div>
  );
}

// ── Feature card data ─────────────────────────────────────────────
const FEATURES = [
  {
    icon: "🤖", title: "AI Chat Assistant",
    desc: "Ask questions in plain English. Get instant SQL-backed answers, charts, and business insights powered by Gemini.",
    color: "#4f9eff",
  },
  {
    icon: "🕸️", title: "Star Schema Mapper",
    desc: "Visually define relationships between databases. The AI automatically leverages these cross-DB JOINs when answering.",
    color: "#a371f7",
  },
  {
    icon: "📊", title: "Live Dashboard",
    desc: "Auto-generated KPI cards, revenue trends, and interactive Plotly charts — all driven by your real data.",
    color: "#2dd4bf",
  },
  {
    icon: "📋", title: "Policy Hub",
    desc: "Upload internal documents and ask compliance or pricing questions. Powered by ChromaDB vector search (RAG).",
    color: "#f0883e",
  },
];

const TECH = [
  { name: "Gemini 2.5", icon: "✦" },
  { name: "LangGraph", icon: "⬡" },
  { name: "FastAPI", icon: "⚡" },
  { name: "ChromaDB", icon: "◎" },
  { name: "React", icon: "⚛" },
  { name: "Plotly", icon: "📈" },
];

// ── Landing Page ─────────────────────────────────────────────────
export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div style={{ position: "relative", minHeight: "100vh" }}>
      <AnimatedBG />

      {/* ── NAV ── */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        background: "rgba(9,9,11,0.8)", backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        padding: "0 40px", height: 64,
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: "#18181b",
            border: "1px solid #27272a",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 16,
          }}>⬡</div>
          <span style={{ fontWeight: 800, fontSize: 16, letterSpacing: "-0.02em", color: "#fafafa" }}>
            DataAnalyst <span style={{ color: "#a1a1aa" }}>AI</span>
          </span>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <button onClick={() => navigate("/login")} style={{
            padding: "8px 20px", borderRadius: 8,
            background: "transparent", border: "1px solid #27272a",
            color: "#fafafa", fontSize: 13, fontWeight: 600, cursor: "pointer",
            transition: "all 0.2s",
          }}
            onMouseEnter={e => { e.currentTarget.style.background = "#18181b"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
          >
            Sign In
          </button>
          <button onClick={() => navigate("/login")} style={{
            padding: "8px 20px", borderRadius: 8,
            background: "#fafafa",
            border: "none", color: "#09090b", fontSize: 13, fontWeight: 600, cursor: "pointer",
            transition: "all 0.2s",
          }}
            onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-1px)"; e.currentTarget.style.opacity = "0.9"; }}
            onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.opacity = "1"; }}
          >
            Get Started →
          </button>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section style={{
        minHeight: "100vh", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        padding: "120px 24px 80px", position: "relative", zIndex: 1,
        textAlign: "center",
      }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 8,
          background: "#18181b", border: "1px solid #27272a",
          borderRadius: 100, padding: "6px 16px", marginBottom: 32,
          animation: "fadeUp 0.6s ease both",
        }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#10b981" }} />
          <span style={{ fontSize: 12, color: "#a1a1aa", fontWeight: 600, fontFamily: "'IBM Plex Mono',monospace" }}>
            POWERED BY GEMINI 2.5 FLASH
          </span>
        </div>

        <h1 style={{
          fontSize: "clamp(40px, 7vw, 80px)", fontWeight: 800,
          letterSpacing: "-0.04em", lineHeight: 1.08,
          animation: "fadeUp 0.6s 0.1s ease both", opacity: 0,
          animationFillMode: "forwards", maxWidth: 900, margin: "0 auto 24px",
        }}>
          <span style={{ color: "#fafafa" }}>Enterprise AI for</span>
          <br />
          <span style={{ color: "#a1a1aa" }}>Your Business Data</span>
        </h1>

        <p style={{
          fontSize: "clamp(16px, 2.5vw, 20px)", color: "#a1a1aa", maxWidth: 600,
          lineHeight: 1.65, animation: "fadeUp 0.6s 0.2s ease both", opacity: 0,
          animationFillMode: "forwards", marginBottom: 48,
        }}>
          Ask questions in plain English. Get instant SQL-backed analytics, interactive charts, and AI-generated executive reports — across multiple databases, in seconds.
        </p>

        <div style={{
          display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center",
          animation: "fadeUp 0.6s 0.3s ease both", opacity: 0, animationFillMode: "forwards",
        }}>
          <button onClick={() => navigate("/login")} style={{
            padding: "14px 32px", borderRadius: 8,
            background: "#fafafa",
            border: "none", color: "#09090b", fontSize: 15, fontWeight: 600, cursor: "pointer",
            transition: "all 0.2s",
          }}
            onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.opacity = "0.9"; }}
            onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.opacity = "1"; }}
          >
            Get Started — It's Free
          </button>
          <a href="#features" style={{
            padding: "14px 32px", borderRadius: 8,
            background: "transparent", border: "1px solid #27272a",
            color: "#fafafa", fontSize: 15, fontWeight: 600, cursor: "pointer",
            textDecoration: "none", transition: "all 0.2s",
          }}
            onMouseEnter={e => { e.currentTarget.style.background = "#18181b"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
          >
            See Features
          </a>
        </div>

        {/* Hero preview card */}
        <div style={{
          marginTop: 80, maxWidth: 900, width: "100%",
          animation: "fadeUp 0.8s 0.5s ease both", opacity: 0, animationFillMode: "forwards",
        }}>
          <GlassCard hover={false} style={{ padding: 24, textAlign: "left" }}>
            <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
              {["#3f3f46", "#3f3f46", "#3f3f46"].map((c, i) => (
                <div key={i} style={{ width: 12, height: 12, borderRadius: "50%", background: c }} />
              ))}
              <span style={{ marginLeft: 8, fontSize: 12, color: "#71717a", fontFamily: "'IBM Plex Mono',monospace" }}>
                AI Assistant — Terminal
              </span>
            </div>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 13, lineHeight: 2 }}>
              <div><span style={{ color: "#a1a1aa" }}>You:</span> <span style={{ color: "#fafafa" }}>Who are the top 5 customers by revenue across all databases?</span></div>
              <div style={{ marginTop: 8 }}><span style={{ color: "#a1a1aa" }}>AI:</span> <span style={{ color: "#71717a" }}>Running cross-database query using sales → customers relationship…</span></div>
              <div style={{ paddingLeft: 32, color: "#fafafa", marginTop: 6 }}>
                1. Nicholas Lee — $61,637.52 | 2. Jerry Dunlap — $60,392.92 | 3. Amy Robinson — $59,512.31
              </div>
              <div style={{ marginTop: 8 }}><span style={{ color: "#52525b" }}>SQL ▶ SELECT c.name, SUM(s.Sales_Amount) ... JOIN customers.customers c ...</span></div>
            </div>
          </GlassCard>
        </div>
      </section>

      {/* ── STATS BAR ── */}
      <section style={{
        position: "relative", zIndex: 1, padding: "60px 40px",
        borderTop: "1px solid rgba(255,255,255,0.06)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        background: "rgba(255,255,255,0.02)",
      }}>
        <div style={{ maxWidth: 900, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 40 }}>
          <StatCounter end={280000} label="Sales Records Analyzed" suffix="+" />
          <StatCounter end={12} label="DB Sources Supported" suffix="+" />
          <StatCounter end={5} label="Chart Types Built-In" />
          <StatCounter end={99} label="AI Accuracy Rate" suffix="%" />
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section id="features" style={{ position: "relative", zIndex: 1, padding: "100px 40px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 70 }}>
            <div style={{
              display: "inline-block", fontSize: 11, fontWeight: 600, letterSpacing: "0.12em",
              color: "#a1a1aa", fontFamily: "'IBM Plex Mono',monospace",
              background: "#18181b", border: "1px solid #27272a",
              borderRadius: 100, padding: "4px 14px", marginBottom: 20, textTransform: "uppercase",
            }}>
              Capabilities
            </div>
            <h2 style={{
              fontSize: "clamp(28px, 5vw, 48px)", fontWeight: 700,
              letterSpacing: "-0.03em", color: "#fafafa",
            }}>
              Everything you need,<br /><span style={{ color: "#a1a1aa" }}>nothing you don't</span>
            </h2>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 24 }}>
            {FEATURES.map((f, i) => (
              <GlassCard key={i} style={{ padding: 32 }}>
                <div style={{
                  width: 52, height: 52, borderRadius: 14, marginBottom: 20,
                  background: `${f.color}18`, border: `1px solid ${f.color}30`,
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: 26,
                }}>{f.icon}</div>
                <h3 style={{ fontSize: 17, fontWeight: 600, color: "#fafafa", marginBottom: 12 }}>{f.title}</h3>
                <p style={{ fontSize: 14, color: "#a1a1aa", lineHeight: 1.7 }}>{f.desc}</p>
                <div style={{ marginTop: 20, display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}
                  onClick={() => navigate("/login")}>
                  <span style={{ fontSize: 13, color: "#fafafa", fontWeight: 600 }}>Explore →</span>
                </div>
              </GlassCard>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section style={{
        position: "relative", zIndex: 1, padding: "80px 40px",
        background: "rgba(255,255,255,0.02)",
        borderTop: "1px solid rgba(255,255,255,0.06)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <div style={{ maxWidth: 900, margin: "0 auto", textAlign: "center" }}>
          <h2 style={{ fontSize: "clamp(24px, 4vw, 40px)", fontWeight: 700, letterSpacing: "-0.03em", color: "#fafafa", marginBottom: 60 }}>
            From Question to Insight in <span style={{ color: "#a1a1aa" }}>Seconds</span>
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 24, textAlign: "left" }}>
            {[
              { num: "01", title: "Connect Your DB", desc: "Upload any SQLite database from the Settings panel.", icon: "🗄️" },
              { num: "02", title: "Define Relationships", desc: "Map FK/PK links in the Star Schema Mapper to enable cross-DB queries.", icon: "🕸️" },
              { num: "03", title: "Ask Anything", desc: "Type your business question. The AI queries, charts, and explains.", icon: "💬" },
              { num: "04", title: "Export & Schedule", desc: "Download reports or schedule daily email delivery automatically.", icon: "📧" },
            ].map((step, i) => (
              <GlassCard key={i} style={{ padding: 28 }}>
                <div style={{ fontSize: 11, fontFamily: "'IBM Plex Mono',monospace", color: "#a1a1aa", fontWeight: 600, marginBottom: 12 }}>
                  {step.num}
                </div>
                <div style={{ fontSize: 26, marginBottom: 12 }}>{step.icon}</div>
                <h3 style={{ fontSize: 15, fontWeight: 600, color: "#fafafa", marginBottom: 8 }}>{step.title}</h3>
                <p style={{ fontSize: 13, color: "#a1a1aa", lineHeight: 1.65 }}>{step.desc}</p>
              </GlassCard>
            ))}
          </div>
        </div>
      </section>

      {/* ── TECH STRIP ── */}
      <section style={{ position: "relative", zIndex: 1, padding: "60px 40px", textAlign: "center" }}>
        <p style={{ fontSize: 12, color: "#545d68", marginBottom: 32, fontFamily: "'IBM Plex Mono',monospace", letterSpacing: "0.1em", textTransform: "uppercase" }}>
          Built with industry-grade technology
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, justifyContent: "center" }}>
          {TECH.map((t, i) => (
            <div key={i} style={{
              padding: "10px 22px", borderRadius: 8,
              background: "#18181b", border: "1px solid #27272a",
              display: "flex", alignItems: "center", gap: 10,
              transition: "all 0.2s",
            }}>
              <span style={{ color: "#fafafa", fontSize: 14 }}>{t.icon}</span>
              <span style={{ fontSize: 13, fontWeight: 500, color: "#a1a1aa" }}>{t.name}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA FOOTER ── */}
      <section style={{
        position: "relative", zIndex: 1, padding: "100px 40px",
        borderTop: "1px solid rgba(255,255,255,0.06)",
        textAlign: "center",
      }}>
        <GlassCard hover={false} style={{
          maxWidth: 700, margin: "0 auto", padding: "60px 40px",
          background: "transparent",
          border: "1px solid #27272a",
        }}>
          <h2 style={{ fontSize: "clamp(24px, 4vw, 40px)", fontWeight: 700, letterSpacing: "-0.03em", color: "#fafafa", marginBottom: 16 }}>
            Ready to transform your data?
          </h2>
          <p style={{ fontSize: 16, color: "#a1a1aa", marginBottom: 36, lineHeight: 1.6 }}>
            Sign in and start asking questions instantly. No SQL expertise required.
          </p>
          <button onClick={() => navigate("/login")} style={{
            padding: "16px 48px", borderRadius: 8,
            background: "#fafafa",
            border: "none", color: "#09090b", fontSize: 16, fontWeight: 600, cursor: "pointer",
            transition: "all 0.2s",
          }}
            onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.opacity = "0.9"; }}
            onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.opacity = "1"; }}
          >
            Launch DataAnalyst AI →
          </button>
        </GlassCard>

        <div style={{ marginTop: 60, fontSize: 12, color: "#2a3240", fontFamily: "'IBM Plex Mono',monospace" }}>
          © 2026 DataAnalyst AI · Built with React, FastAPI & Gemini
        </div>
      </section>
    </div>
  );
}
