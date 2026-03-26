import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

// ── Animated particles/orbs background ──────────────────────────
function AnimatedBG() {
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 0, overflow: "hidden", pointerEvents: "none" }}>
      {/* Deep gradient base */}
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(135deg, #050810 0%, #080d1a 40%, #060c18 70%, #050810 100%)"
      }} />
      {/* Ambient glowing orbs */}
      {[
        { size: 700, top: "-15%", left: "-10%", color: "rgba(79,158,255,0.07)", delay: 0 },
        { size: 600, bottom: "-20%", right: "-15%", color: "rgba(163,113,247,0.08)", delay: 2 },
        { size: 400, top: "35%", right: "5%", color: "rgba(45,212,191,0.05)", delay: 4 },
        { size: 300, top: "60%", left: "20%", color: "rgba(79,158,255,0.06)", delay: 1 },
      ].map((orb, i) => (
        <div key={i} style={{
          position: "absolute",
          width: orb.size, height: orb.size, borderRadius: "50%",
          background: `radial-gradient(circle, ${orb.color} 0%, transparent 70%)`,
          top: orb.top, bottom: orb.bottom, left: orb.left, right: orb.right,
          animation: `floatOrb ${8 + i * 2}s ease-in-out ${orb.delay}s infinite alternate`,
          filter: "blur(20px)",
        }} />
      ))}
      {/* Grid lines overlay */}
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: `linear-gradient(rgba(79,158,255,0.04) 1px, transparent 1px),
          linear-gradient(90deg, rgba(79,158,255,0.04) 1px, transparent 1px)`,
        backgroundSize: "60px 60px",
      }} />
      <style>{`
        @keyframes floatOrb { from { transform: translateY(0px) scale(1); } to { transform: translateY(-30px) scale(1.05); } }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes shimmer { 0%,100% { opacity: 0.6; } 50% { opacity: 1; } }
        @keyframes countUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse2 { 0%,100%{box-shadow:0 0 20px rgba(79,158,255,0.3)} 50%{box-shadow:0 0 40px rgba(79,158,255,0.6)} }
        @keyframes gradText { 0%{background-position:0%} 100%{background-position:200%} }
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=IBM+Plex+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html { scroll-behavior: smooth; }
        body { font-family: 'Plus Jakarta Sans', sans-serif; background: #050810; color: #cdd9e5; overflow-x: hidden; }
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
        background: hov ? "rgba(255,255,255,0.07)" : "rgba(255,255,255,0.04)",
        border: `1px solid ${hov ? "rgba(79,158,255,0.4)" : "rgba(255,255,255,0.08)"}`,
        borderRadius: 20, backdropFilter: "blur(20px)",
        transition: "all 0.35s cubic-bezier(0.4,0,0.2,1)",
        transform: hov ? "translateY(-4px)" : "translateY(0)",
        boxShadow: hov
          ? "0 20px 60px rgba(0,0,0,0.5), 0 0 30px rgba(79,158,255,0.1)"
          : "0 8px 32px rgba(0,0,0,0.3)",
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
        background: "linear-gradient(135deg, #4f9eff, #a371f7)",
        WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
        backgroundClip: "text",
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
        background: "rgba(5,8,16,0.7)", backdropFilter: "blur(20px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        padding: "0 40px", height: 64,
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: "linear-gradient(135deg, #1a3a6e, #1e1040)",
            border: "1px solid rgba(79,158,255,0.3)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 16,
          }}>⬡</div>
          <span style={{ fontWeight: 800, fontSize: 16, letterSpacing: "-0.02em", color: "#cdd9e5" }}>
            DataAnalyst <span style={{ color: "#4f9eff" }}>AI</span>
          </span>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <button onClick={() => navigate("/login")} style={{
            padding: "8px 20px", borderRadius: 10,
            background: "rgba(79,158,255,0.12)", border: "1px solid rgba(79,158,255,0.3)",
            color: "#4f9eff", fontSize: 13, fontWeight: 600, cursor: "pointer",
            transition: "all 0.2s",
          }}
            onMouseEnter={e => { e.currentTarget.style.background = "rgba(79,158,255,0.24)"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "rgba(79,158,255,0.12)"; }}
          >
            Sign In
          </button>
          <button onClick={() => navigate("/login")} style={{
            padding: "8px 20px", borderRadius: 10,
            background: "linear-gradient(135deg, #2563eb, #7c3aed)",
            border: "none", color: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer",
            boxShadow: "0 4px 20px rgba(37,99,235,0.35)", transition: "all 0.2s",
          }}
            onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-1px)"; e.currentTarget.style.boxShadow = "0 6px 28px rgba(37,99,235,0.5)"; }}
            onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "0 4px 20px rgba(37,99,235,0.35)"; }}
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
          background: "rgba(79,158,255,0.1)", border: "1px solid rgba(79,158,255,0.25)",
          borderRadius: 100, padding: "6px 16px", marginBottom: 32,
          animation: "fadeUp 0.6s ease both",
        }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#2ea87e", boxShadow: "0 0 8px #2ea87e" }} />
          <span style={{ fontSize: 12, color: "#4f9eff", fontWeight: 600, fontFamily: "'IBM Plex Mono',monospace" }}>
            POWERED BY GEMINI 2.5 FLASH
          </span>
        </div>

        <h1 style={{
          fontSize: "clamp(40px, 7vw, 80px)", fontWeight: 900,
          letterSpacing: "-0.04em", lineHeight: 1.08,
          animation: "fadeUp 0.6s 0.1s ease both", opacity: 0,
          animationFillMode: "forwards", maxWidth: 900, margin: "0 auto 24px",
        }}>
          <span style={{ color: "#cdd9e5" }}>Enterprise AI for</span>
          <br />
          <span style={{
            background: "linear-gradient(270deg, #a371f7, #4f9eff, #2dd4bf, #4f9eff)",
            backgroundSize: "400% 400%",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
            animation: "fadeUp 0.6s 0.1s ease both, gradText 4s linear infinite",
            animationFillMode: "forwards",
          }}>Your Business Data</span>
        </h1>

        <p style={{
          fontSize: "clamp(16px, 2.5vw, 20px)", color: "#8b949e", maxWidth: 600,
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
            padding: "14px 32px", borderRadius: 14,
            background: "linear-gradient(135deg, #2563eb, #7c3aed)",
            border: "none", color: "#fff", fontSize: 15, fontWeight: 700, cursor: "pointer",
            boxShadow: "0 6px 30px rgba(37,99,235,0.4)", transition: "all 0.25s",
            animation: "pulse2 3s ease infinite",
          }}
            onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; }}
            onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; }}
          >
            🚀 Get Started — It's Free
          </button>
          <a href="#features" style={{
            padding: "14px 32px", borderRadius: 14,
            background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.12)",
            color: "#cdd9e5", fontSize: 15, fontWeight: 600, cursor: "pointer",
            textDecoration: "none", backdropFilter: "blur(10px)", transition: "all 0.25s",
          }}
            onMouseEnter={e => { e.currentTarget.style.background = "rgba(255,255,255,0.1)"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "rgba(255,255,255,0.05)"; }}
          >
            ↓ See Features
          </a>
        </div>

        {/* Hero preview card */}
        <div style={{
          marginTop: 80, maxWidth: 900, width: "100%",
          animation: "fadeUp 0.8s 0.5s ease both", opacity: 0, animationFillMode: "forwards",
        }}>
          <GlassCard hover={false} style={{ padding: 24, textAlign: "left" }}>
            <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
              {["#ff5f56", "#ffbd2e", "#27c93f"].map((c, i) => (
                <div key={i} style={{ width: 12, height: 12, borderRadius: "50%", background: c }} />
              ))}
              <span style={{ marginLeft: 8, fontSize: 12, color: "#545d68", fontFamily: "'IBM Plex Mono',monospace" }}>
                AI Assistant — Terminal
              </span>
            </div>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 13, lineHeight: 2 }}>
              <div><span style={{ color: "#4f9eff" }}>You:</span> <span style={{ color: "#cdd9e5" }}>Who are the top 5 customers by revenue across all databases?</span></div>
              <div style={{ marginTop: 8 }}><span style={{ color: "#a371f7" }}>AI:</span> <span style={{ color: "#8b949e" }}>Running cross-database query using sales → customers relationship…</span></div>
              <div style={{ paddingLeft: 32, color: "#2ea87e", marginTop: 6 }}>
                1. Nicholas Lee — $61,637.52 | 2. Jerry Dunlap — $60,392.92 | 3. Amy Robinson — $59,512.31
              </div>
              <div style={{ marginTop: 8 }}><span style={{ color: "#545d68" }}>SQL ▶ SELECT c.name, SUM(s.Sales_Amount) ... JOIN customers.customers c ...</span></div>
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
              display: "inline-block", fontSize: 11, fontWeight: 700, letterSpacing: "0.12em",
              color: "#4f9eff", fontFamily: "'IBM Plex Mono',monospace",
              background: "rgba(79,158,255,0.1)", border: "1px solid rgba(79,158,255,0.2)",
              borderRadius: 100, padding: "4px 14px", marginBottom: 20, textTransform: "uppercase",
            }}>
              Capabilities
            </div>
            <h2 style={{
              fontSize: "clamp(28px, 5vw, 48px)", fontWeight: 800,
              letterSpacing: "-0.03em", color: "#cdd9e5",
            }}>
              Everything you need,<br /><span style={{ color: "#4f9eff" }}>nothing you don't</span>
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
                <h3 style={{ fontSize: 17, fontWeight: 700, color: "#cdd9e5", marginBottom: 12 }}>{f.title}</h3>
                <p style={{ fontSize: 14, color: "#8b949e", lineHeight: 1.7 }}>{f.desc}</p>
                <div style={{ marginTop: 20, display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}
                  onClick={() => navigate("/login")}>
                  <span style={{ fontSize: 13, color: f.color, fontWeight: 600 }}>Explore →</span>
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
          <h2 style={{ fontSize: "clamp(24px, 4vw, 40px)", fontWeight: 800, letterSpacing: "-0.03em", color: "#cdd9e5", marginBottom: 60 }}>
            From Question to Insight in <span style={{ color: "#a371f7" }}>Seconds</span>
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 24, textAlign: "left" }}>
            {[
              { num: "01", title: "Connect Your DB", desc: "Upload any SQLite database from the Settings panel.", icon: "🗄️" },
              { num: "02", title: "Define Relationships", desc: "Map FK/PK links in the Star Schema Mapper to enable cross-DB queries.", icon: "🕸️" },
              { num: "03", title: "Ask Anything", desc: "Type your business question. The AI queries, charts, and explains.", icon: "💬" },
              { num: "04", title: "Export & Schedule", desc: "Download reports or schedule daily email delivery automatically.", icon: "📧" },
            ].map((step, i) => (
              <GlassCard key={i} style={{ padding: 28 }}>
                <div style={{ fontSize: 11, fontFamily: "'IBM Plex Mono',monospace", color: "#4f9eff", fontWeight: 700, marginBottom: 12 }}>
                  {step.num}
                </div>
                <div style={{ fontSize: 26, marginBottom: 12 }}>{step.icon}</div>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: "#cdd9e5", marginBottom: 8 }}>{step.title}</h3>
                <p style={{ fontSize: 13, color: "#8b949e", lineHeight: 1.65 }}>{step.desc}</p>
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
              padding: "10px 22px", borderRadius: 12,
              background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.09)",
              backdropFilter: "blur(10px)", display: "flex", alignItems: "center", gap: 10,
              transition: "all 0.2s",
            }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(79,158,255,0.3)"; e.currentTarget.style.background = "rgba(79,158,255,0.05)"; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.09)"; e.currentTarget.style.background = "rgba(255,255,255,0.03)"; }}
            >
              <span style={{ color: "#4f9eff", fontSize: 14 }}>{t.icon}</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#8b949e" }}>{t.name}</span>
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
          background: "linear-gradient(135deg, rgba(37,99,235,0.12), rgba(124,58,237,0.12))",
          border: "1px solid rgba(79,158,255,0.25)",
        }}>
          <h2 style={{ fontSize: "clamp(24px, 4vw, 40px)", fontWeight: 800, letterSpacing: "-0.03em", color: "#cdd9e5", marginBottom: 16 }}>
            Ready to transform your data?
          </h2>
          <p style={{ fontSize: 16, color: "#8b949e", marginBottom: 36, lineHeight: 1.6 }}>
            Sign in and start asking questions instantly. No SQL expertise required.
          </p>
          <button onClick={() => navigate("/login")} style={{
            padding: "16px 48px", borderRadius: 14,
            background: "linear-gradient(135deg, #2563eb, #7c3aed)",
            border: "none", color: "#fff", fontSize: 16, fontWeight: 700, cursor: "pointer",
            boxShadow: "0 8px 32px rgba(37,99,235,0.45)", transition: "all 0.25s",
          }}
            onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = "0 14px 48px rgba(37,99,235,0.6)"; }}
            onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "0 8px 32px rgba(37,99,235,0.45)"; }}
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
