import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import LandingPage from "./LandingPage";
import LoginPage, { getAuthSession, clearAuthSession } from "./LoginPage";
import {
  MessageSquare, Database, Settings,
  Send, Trash2, RefreshCw, Download, Mail, Upload,
  Zap, Activity, Filter, SortAsc, SortDesc, ArrowRight, Bot, User,
  GitFork, Unlink, CheckCircle, AlertCircle, TrendingUp, Plus, Sun, Moon,
  Maximize2, Minimize2, ZoomIn, ZoomOut, Eye, EyeOff, FileText, LogOut
} from "lucide-react";
import Plot from "react-plotly.js";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API = process.env.REACT_APP_API_URL || "http://localhost:8000";
// --- GLOBAL API ERROR HANDLING ---
const safeFetch = async (url, options = {}) => {
  try {
    const res = await fetch(url, options);
    const json = await res.json().catch(() => null);
    if (!res.ok) {
      // Preserve the backend FastAPI error detail
      console.error(`[API FAIL ${res.status}] ${url}:`, json);
      return { _error: true, detail: json?.detail || `HTTP ${res.status}` };
    }
    return json;
  } catch (err) {
    console.error(`[API FAIL] ${url}:`, err);
    return { _error: true, detail: err.message };
  }
};

// ─── THEME PALETTES ───────────────────────────────────────────
const DARK = {
  bg:          "#0d0f14",
  surface:     "#13161d",
  card:        "#13161d",
  cardRaised:  "#1a1e28",
  border:      "#252836",
  borderSoft:  "#1a1e28",
  accent:      "#6c63ff",
  accentAlt:   "#818cf8",
  accentGlow:  "rgba(108,99,255,0.18)",
  accentDim:   "rgba(108,99,255,0.10)",
  green:       "#22d3a5",
  greenDim:    "rgba(34,211,165,0.10)",
  yellow:      "#fbbf24",
  yellowDim:   "rgba(251,191,36,0.10)",
  red:         "#f87171",
  redDim:      "rgba(248,113,113,0.10)",
  purple:      "#a78bfa",
  purpleDim:   "rgba(167,139,250,0.10)",
  teal:        "#2dd4bf",
  orange:      "#fb923c",
  text:        "#e8eaf0",
  textSoft:    "#9198b0",
  muted:       "#5a6080",
  hover:       "#1e2230",
  sidebarBg:   "#0f1118",
};
const LIGHT = {
  bg:          "#f5f6fa",
  surface:     "#ffffff",
  card:        "#ffffff",
  cardRaised:  "#eef0f8",
  border:      "#dde0ef",
  borderSoft:  "#eef0f8",
  accent:      "#5b50f0",
  accentAlt:   "#7c74f5",
  accentGlow:  "rgba(91,80,240,0.14)",
  accentDim:   "rgba(91,80,240,0.08)",
  green:       "#10b981",
  greenDim:    "rgba(16,185,129,0.10)",
  yellow:      "#f59e0b",
  yellowDim:   "rgba(245,158,11,0.10)",
  red:         "#ef4444",
  redDim:      "rgba(239,68,68,0.10)",
  purple:      "#8b5cf6",
  purpleDim:   "rgba(139,92,246,0.10)",
  teal:        "#14b8a6",
  orange:      "#f97316",
  text:        "#1a1d2e",
  textSoft:    "#4a5070",
  muted:       "#8890b0",
  hover:       "#eef0f8",
  sidebarBg:   "#ffffff",
};

// Proxy — reads window.__theme at access time so all components always get live colors
const C = new Proxy({}, { get(_, k) { return (window.__theme === "light" ? LIGHT : DARK)[k]; } });

const ThemeCtx = React.createContext({ theme: "dark", toggle: () => { } });
function useTheme() { return React.useContext(ThemeCtx); }

function makeStyle(theme) {
  const t = theme === "light" ? LIGHT : DARK;
  const isDark = theme !== "light";
  return `
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600;700;800&display=swap');
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    html,body,#root{height:100%;background:${t.bg};color:${t.text};font-family:'Inter',sans-serif}
    ::-webkit-scrollbar{width:5px;height:5px}
    ::-webkit-scrollbar-track{background:transparent}
    ::-webkit-scrollbar-thumb{background:${t.border};border-radius:99px}
    ::-webkit-scrollbar-thumb:hover{background:${t.accent}60}
    input,select,textarea,button{font-family:inherit}
    a{color:${t.accent};text-decoration:none}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
    @keyframes slideIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
    @keyframes spin{to{transform:rotate(360deg)}}
    @keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
    @keyframes glow{0%,100%{box-shadow:0 0 8px ${t.accent}40}50%{box-shadow:0 0 20px ${t.accent}80}}
    .markdown-body ul,.markdown-body ol{padding-left:1.6em;margin:0.8em 0}
    .markdown-body li{margin-bottom:0.4em;line-height:1.7}
    .markdown-body p{margin-bottom:0.8em;line-height:1.75}
    .markdown-body h1,.markdown-body h2,.markdown-body h3{margin:1em 0 0.5em;font-weight:700;color:${t.text}}
    .markdown-body strong{color:${t.text};font-weight:700}
    .markdown-body pre{background:${isDark?"#0d0f14":"#f0f1f8"};padding:14px;border-radius:10px;border:1px solid ${t.border};font-family:'IBM Plex Mono',monospace;margin:0.8em 0;overflow-x:auto;font-size:12px}
    .markdown-body code{background:${isDark?"rgba(108,99,255,0.12)":"rgba(91,80,240,0.08)"};color:${t.accent};padding:2px 6px;border-radius:5px;font-family:'IBM Plex Mono',monospace;font-size:0.88em}
    .markdown-body table{width:100%;border-collapse:collapse;margin:1em 0;font-size:13px}
    .markdown-body th{background:${t.cardRaised};padding:8px 12px;text-align:left;font-weight:600;border-bottom:2px solid ${t.border};font-size:11px;letter-spacing:0.06em;text-transform:uppercase;color:${t.muted}}
    .markdown-body td{padding:8px 12px;border-bottom:1px solid ${t.border};color:${t.textSoft}}
    .markdown-body tr:last-child td{border-bottom:none}
    .markdown-body blockquote{border-left:3px solid ${t.accent};padding:8px 14px;margin:1em 0;background:${t.accentDim};border-radius:0 8px 8px 0;color:${t.textSoft};font-style:italic}
  `;
}

// ─── SHARED COMPONENTS ────────────────────────────────────────
const Spinner = ({ size = 16 }) => (
  <span style={{
    display: "inline-block", width: size, height: size,
    border: `2px solid ${C.border}`,
    borderTopColor: C.accent, borderRadius: "50%",
    animation: "spin .65s linear infinite", flexShrink: 0
  }} />
);

const Badge = ({ children, color = C.accent }) => (
  <span style={{
    display: "inline-flex", alignItems: "center", gap: 4, padding: "3px 10px", borderRadius: 99,
    background: `${color}18`, color, fontSize: 10, fontWeight: 700, border: `1px solid ${color}35`,
    fontFamily: "'IBM Plex Mono',monospace", letterSpacing: "0.05em", textTransform: "uppercase"
  }}>
    {children}
  </span>
);

const Card = ({ children, style = {} }) => (
  <div style={{
    background: C.cardRaised, border: `1px solid ${C.border}`, borderRadius: 16, padding: 20,
    boxShadow: `0 1px 0 rgba(255,255,255,0.04) inset, 0 4px 24px rgba(0,0,0,0.18)`, ...style
  }}>{children}</div>
);

const Divider = ({ style = {} }) => (
  <div style={{
    height: 1, background: `linear-gradient(90deg,transparent,${C.border},transparent)`,
    margin: "4px 0", ...style
  }} />
);

const Btn = ({ children, onClick, variant = "primary", disabled = false, style = {}, icon, size = "md" }) => {
  const [hov, setHov] = React.useState(false);
  const pad = size === "sm" ? "5px 13px" : "8px 18px";
  const fs = size === "sm" ? 12 : 13;
  const V = {
    primary: {
      background: hov ? `linear-gradient(135deg,${C.accentAlt},${C.accent})` : `linear-gradient(135deg,${C.accent},${C.purple}60)`,
      color: "#fff",
      boxShadow: hov ? `0 4px 20px ${C.accentGlow}` : `0 2px 10px ${C.accentGlow}`
    },
    secondary: { background: C.surface, color: C.text, border: `1px solid ${C.border}`, boxShadow: "none" },
    danger: { background: C.redDim, color: C.red, border: `1px solid ${C.red}30`, boxShadow: "none" },
    ghost: { background: "transparent", color: C.textSoft, boxShadow: "none" },
    success: { background: C.greenDim, color: C.green, border: `1px solid ${C.green}30`, boxShadow: "none" },
  };
  return (
    <button onClick={onClick} disabled={disabled} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6, padding: pad, borderRadius: 10, fontSize: fs,
        fontWeight: 600, border: "none", transition: "all .18s", cursor: disabled ? "not-allowed" : "pointer",
        letterSpacing: "0.01em", opacity: disabled ? .4 : 1,
        transform: hov && !disabled ? "translateY(-1px)" : "none", ...V[variant], ...style
      }}>
      {icon && React.createElement(icon, { size: size === "sm" ? 12 : 14 })}{children}
    </button>
  );
};

const Input = ({ value, onChange, placeholder, style = {}, type = "text", onKeyDown }) => {
  const [f, setF] = React.useState(false);
  return (
    <input type={type} value={value} onChange={onChange} placeholder={placeholder} onKeyDown={onKeyDown}
      onFocus={() => setF(true)} onBlur={() => setF(false)}
      style={{
        background: f ? C.cardRaised : C.surface, border: `1px solid ${f ? C.accent : C.border}`, borderRadius: 8,
        padding: "8px 12px", color: C.text, fontSize: 13, outline: "none", width: "100%", transition: "all .15s",
        fontFamily: "'Plus Jakarta Sans',sans-serif", boxShadow: f ? `0 0 0 3px ${C.accentGlow}` : "none", ...style
      }} />
  );
};

const Select = ({ value, onChange, children, style = {} }) => {
  const [f, setF] = React.useState(false);
  return (
    <select value={value} onChange={onChange} onFocus={() => setF(true)} onBlur={() => setF(false)}
      style={{
        background: C.surface, border: `1px solid ${f ? C.accent : C.border}`, borderRadius: 8,
        padding: "8px 12px", color: C.text, fontSize: 13, outline: "none", width: "100%", cursor: "pointer",
        boxShadow: f ? `0 0 0 3px ${C.accentGlow}` : "none", transition: "all .15s", ...style
      }}>
      {children}
    </select>
  );
};

const PlotlyChart = ({ plotlyJson, style = {} }) => {
  if (!plotlyJson) return null;
  let fig;
  try { fig = typeof plotlyJson === "string" ? JSON.parse(plotlyJson) : plotlyJson; }
  catch { return <p style={{ color: C.red }}>Chart parse error</p>; }
  const layout = {
    ...fig.layout, paper_bgcolor: "transparent", plot_bgcolor: "transparent",
    font: { color: C.text, family: "'Plus Jakarta Sans',sans-serif", size: 12 },
    margin: { t: 40, r: 20, b: 60, l: 60 },
    xaxis: { ...fig.layout?.xaxis, gridcolor: C.border, linecolor: C.border, tickfont: { color: C.muted } },
    yaxis: { ...fig.layout?.yaxis, gridcolor: C.border, linecolor: C.border, tickfont: { color: C.muted } },
    legend: { bgcolor: "transparent", font: { color: C.muted } },
  };
  return <Plot data={fig.data} layout={layout}
    config={{ displayModeBar: true, displaylogo: false, responsive: true }}
    style={{ width: "100%", ...style }} />;
};

// ─── CHAT TAB ─────────────────────────────────────────────────
function ChatTab() {
  useTheme();
  const WELCOME_MESSAGE = `## 👋 Welcome to your AI Data Analyst

I'm connected to your live database and ready to help. Here's what I can do:

| Capability | Example |
|---|---|
| 📊 **Visualize & Analyze** | *"Show me monthly revenue as a line chart"* |
| 🔍 **Deep-Dive Queries** | *"Which top 5 products had the highest return rate last quarter?"* |
| 🤝 **Multi-table Joins** | *"Compare customer lifetime value across different store regions"* |
| 📋 **Data Quality Audit** | *"Scan the orders table for anomalies"* |
| 📝 **Executive Reports** | *"Generate a full sales report and email it to me"* |
| ⏰ **Scheduled Reports** | *"Email me a daily sales summary every morning at 8 AM"* |
| 📂 **Policy Research** | *"What does our return policy say about damaged goods?"* |

> 💡 **Pro tip:** You can drill down after any answer — just say *"Now show me only the North region"* and I'll remember the context of our conversation.

What would you like to explore first?`;

  const [messages, setMessages] = useState([{
    role: "assistant",
    content: WELCOME_MESSAGE,
    ts: new Date()
  }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState([]);
  const bottomRef = useRef();

  const [suggestions, setSuggestions] = useState([]);
  const [suggestLoading, setSuggestLoading] = useState(true); // start loading immediately

  const fetchSuggestions = async (context = "") => {
    setSuggestLoading(true);
    try {
      const qs = context ? `?context=${encodeURIComponent(context)}` : "";
      const data = await safeFetch(`${API}/api/chat/suggestions${qs}`);
      if (data && data.suggestions && data.suggestions.length > 0) {
        setSuggestions(data.suggestions);
      }
    } catch { }
    setSuggestLoading(false);
  };

  useEffect(() => { fetchSuggestions(); }, []);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, steps]);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || loading) return;
    const userMsg = { role: "user", content: input.trim(), ts: new Date() };
    setMessages(p => [...p, userMsg]);
    setInput(""); setLoading(true); setSteps([]);

    let response;
    try {
      response = await fetch(`${API}/api/chat/stream`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg.content })
      });
      if (!response.ok) throw new Error("Stream error");
    } catch (err) {
      console.error("Chat Stream Error:", err);
      setMessages(p => [...p, { role: "assistant", content: "Error: Could not reach the AI analytical engine. Please check your connection or restart the backend." }]);
      setLoading(false);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let pendingSql = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const raw = line.slice(5).trim();
        if (!raw) continue;
        try {
          const evt = JSON.parse(raw);
          if (evt.type === "tool_call") {
            setSteps(p => [...p, { type: "call", name: evt.name, args: evt.args }]);
            if (evt.name === "sql_query_tool") {
              console.log("[SQL DEBUG] tool_call args:", evt.args, typeof evt.args);
              try {
                // evt.args can be: an object, a JSON string, or a Python dict string like "{'query': 'SELECT...'}"
                let args = evt.args;
                if (typeof args === "string") {
                  try {
                    args = JSON.parse(args);
                  } catch {
                    // Python dict format: replace single quotes, True/False/None
                    const fixed = args
                      .replace(/'/g, '"')
                      .replace(/\bTrue\b/g, "true")
                      .replace(/\bFalse\b/g, "false")
                      .replace(/\bNone\b/g, "null");
                    try { args = JSON.parse(fixed); } catch { args = {}; }
                  }
                }
                const q = args.query || args.input || args.sql_query || args.sql
                  || args.statement || args.command || Object.values(args)[0];
                if (q && typeof q === "string" && q.trim().length > 5) {
                  pendingSql = q.trim();
                }
              } catch { }
            }
          } else if (evt.type === "tool_result") {
            setSteps(p => [...p, { type: "result", content: evt.content }]);
            // Fallback: extract SELECT from the tool result content
            if (!pendingSql && evt.content) {
              const m = evt.content.match(/(SELECT[\s\S]{5,500}?)(;|\n\n|$)/i);
              if (m) pendingSql = m[1].trim();
            }
          } else if (evt.type === "response") {
            let sql = pendingSql;
            // Absolute Fallback: Even if stream tool_call parsing failed, extract the SQL block the AI (or backend override) appended
            if (!sql && evt.content) {
              const match = evt.content.match(/```sql\n([\s\S]*?)\n```/i);
              if (match) sql = match[1].trim();
            }
            setMessages(p => [...p, {
              role: "assistant", content: evt.content,
              plotlyJson: evt.plotly_json, sqlQuery: sql || null, tokens: evt.tokens || null, ts: new Date()
            }]);
            pendingSql = null; setSteps([]); setLoading(false);
            fetchSuggestions(userMsg.content); // get context-aware follow up questions
          } else if (evt.type === "error") {
            setMessages(p => [...p, { role: "assistant", content: `Error: ${evt.content}`, ts: new Date(), error: true }]);
            setSteps([]); setLoading(false);
          }
        } catch { }
      }
    }
    setLoading(false);
  }, [input, loading]);

  const clearChat = async () => {
    await safeFetch(`${API}/api/chat/clear`, { method: "POST" });
    setMessages([{ role: "assistant", content: "Memory cleared. Starting fresh.", ts: new Date() }]);
    setSteps([]);
    fetchSuggestions(); // reset to general suggestions
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "14px 24px", borderBottom: `1px solid ${C.border}`,
        background: C.surface, flexShrink: 0,
        boxShadow: `0 1px 0 ${C.border}`
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 38, height: 38, borderRadius: 12,
            background: `linear-gradient(135deg,${C.accent},${C.purple})`,
            border: `1px solid ${C.accent}40`,
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: `0 4px 14px ${C.accentGlow}`
          }}>
            <Bot size={17} color="#fff" />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: C.text, letterSpacing: "-0.01em" }}>AI Assistant</div>
            <div style={{ fontSize: 11, color: C.green, display: "flex", alignItems: "center", gap: 5, marginTop: 2 }}>
              <span style={{
                width: 6, height: 6, borderRadius: "50%", background: C.green,
                boxShadow: `0 0 6px ${C.green}`, display: "inline-block", animation: "glow 2s ease infinite"
              }} />
              Live · Gemini 2.5 Pro
            </div>
          </div>
        </div>
        <Btn variant="ghost" onClick={clearChat} icon={Trash2} size="sm">Clear</Btn>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "24px", display: "flex", flexDirection: "column", gap: 18 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{
            display: "flex", gap: 10, alignItems: "flex-start",
            flexDirection: msg.role === "user" ? "row-reverse" : "row", animation: "slideIn .22s ease"
          }}>
            <div style={{
              width: 32, height: 32, borderRadius: 10, flexShrink: 0, display: "flex",
              alignItems: "center", justifyContent: "center",
              background: msg.role === "user"
                ? `linear-gradient(135deg,${C.accent}80,${C.purple}80)`
                : `linear-gradient(135deg,${C.teal}40,${C.accent}40)`,
              border: `1px solid ${msg.role === "user" ? C.accent + "50" : C.border}`
            }}>
              {msg.role === "user" ? <User size={14} color={C.accent} /> : <Bot size={14} color={C.teal} />}
            </div>
            <div style={{ maxWidth: "78%", display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{
                background: msg.role === "user"
                  ? `linear-gradient(135deg,${C.accent}22,${C.purple}18)`
                  : C.cardRaised,
                border: `1px solid ${msg.error ? C.red : msg.role === "user" ? C.accent + "40" : C.border}`,
                borderRadius: msg.role === "user" ? "16px 4px 16px 16px" : "4px 16px 16px 16px",
                borderLeft: msg.role === "assistant" ? `3px solid ${C.accent}60` : undefined,
                padding: "12px 16px", fontSize: 13.5, lineHeight: 1.65,
                wordBreak: "break-word", color: C.text,
                boxShadow: msg.role === "user" ? `0 2px 12px ${C.accentGlow}` : `0 2px 12px rgba(0,0,0,0.15)`
              }}>
                <div className="markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content ? msg.content.replace(/```sql[\s\S]*?```/gi, "").replace(/\[CHART\]/gi, "").trim() : ""}
                  </ReactMarkdown>
                </div>
              </div>

              {msg.plotlyJson && (
                <div style={{
                  background: C.cardRaised, border: `1px solid ${C.border}`,
                  borderRadius: 12, padding: 8, overflow: "hidden"
                }}>
                  <PlotlyChart plotlyJson={msg.plotlyJson} style={{ height: 320 }} />
                </div>
              )}

              {msg.sqlQuery && (
                <details open>
                  <summary style={{
                    fontSize: 11, color: C.accent, cursor: "pointer", listStyle: "none",
                    display: "inline-flex", alignItems: "center", gap: 6, padding: "5px 10px",
                    background: C.accentDim, border: `1px solid ${C.accent}25`, borderRadius: 7,
                    userSelect: "none", fontWeight: 600, fontFamily: "'IBM Plex Mono',monospace"
                  }}>
                    <span>▶</span> SQL Query
                  </summary>
                  <div style={{
                    marginTop: 6, background: C.surface, border: `1px solid ${C.border}`,
                    borderLeft: `3px solid ${C.accent}`, borderRadius: "0 8px 8px 8px",
                    padding: "12px 14px", fontFamily: "'IBM Plex Mono',monospace",
                    fontSize: 12, color: C.teal, lineHeight: 1.7, whiteSpace: "pre-wrap", wordBreak: "break-word"
                  }}>
                    {msg.sqlQuery}
                  </div>
                </details>
              )}

              <div style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                marginTop: 4, width: "100%"
              }}>
                <span style={{ fontSize: 10, color: C.muted, fontFamily: "'IBM Plex Mono',monospace" }}>
                  {msg.ts?.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                {msg.tokens && (
                  <span style={{
                    fontSize: 9, color: C.muted, background: C.borderSoft,
                    padding: "2px 6px", borderRadius: 4, fontFamily: "'IBM Plex Mono',monospace",
                    display: "flex", alignItems: "center", gap: 3
                  }}>
                    <Zap size={8} /> {msg.tokens} tokens
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}

        {loading && steps.length > 0 && (
          <div style={{ background: C.cardRaised, border: `1px solid ${C.border}`, borderRadius: 12, padding: 14, animation: "slideIn .2s ease" }}>
            <div style={{
              display: "flex", alignItems: "center", gap: 8, marginBottom: 10,
              color: C.textSoft, fontSize: 11, fontFamily: "'IBM Plex Mono',monospace"
            }}>
              <Spinner size={11} /> Agent reasoning…
            </div>
            {steps.map((s, i) => (
              <div key={i} style={{
                display: "flex", gap: 8, alignItems: "flex-start", marginBottom: 5,
                padding: "6px 10px", background: C.surface, borderRadius: 7,
                borderLeft: `2px solid ${s.type === "call" ? C.yellow : C.green}`
              }}>
                {s.type === "call"
                  ? <><Zap size={11} color={C.yellow} style={{ marginTop: 2, flexShrink: 0 }} />
                    <span style={{ fontSize: 11 }}>
                      <span style={{ color: C.yellow, fontWeight: 600 }}>Calling </span>
                      <code style={{ color: C.accent, fontFamily: "'IBM Plex Mono',monospace" }}>{s.name}</code>
                    </span></>
                  : <><CheckCircle size={11} color={C.green} style={{ marginTop: 2, flexShrink: 0 }} />
                    <span style={{
                      fontSize: 11, color: C.muted, fontFamily: "'IBM Plex Mono',monospace",
                      maxWidth: 460, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap"
                    }}>
                      {s.content}
                    </span></>}
              </div>
            ))}
          </div>
        )}

        {loading && steps.length === 0 && (
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <div style={{
              width: 30, height: 30, borderRadius: 8, display: "flex", alignItems: "center",
              justifyContent: "center", background: C.surface, border: `1px solid ${C.border}`
            }}>
              <Bot size={13} color={C.purple} />
            </div>
            <div style={{
              display: "flex", gap: 5, padding: "12px 16px", background: C.cardRaised,
              border: `1px solid ${C.border}`, borderRadius: "4px 14px 14px 14px"
            }}>
              {[0, 1, 2].map(n => (
                <span key={n} style={{
                  width: 5, height: 5, borderRadius: "50%", background: C.muted,
                  animation: `pulse 1.3s ease ${n * .22}s infinite`
                }} />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions after last reply */}
      {!loading && messages.length > 1 && messages[messages.length - 1].role === 'assistant' && (
        <div style={{ padding: "0 24px 12px", display: "flex", gap: 7, flexWrap: "wrap", animation: "slideIn .25s ease" }}>
          <span style={{
            fontSize: 10, color: C.muted, width: '100%', marginBottom: 4,
            fontFamily: "'IBM Plex Mono',monospace", letterSpacing: "0.05em", textTransform: "uppercase"
          }}>
            {suggestLoading ? <><Spinner size={9} /> &nbsp;Generating…</> : "✦ Suggested follow-ups"}
          </span>
          {!suggestLoading && suggestions.map((s, i) => (
            <button key={i} onClick={() => { setInput(s); }}
              style={{
                padding: "6px 13px", borderRadius: 99,
                background: C.accentDim,
                border: `1px solid ${C.accent}35`,
                color: C.accent, fontSize: 11.5, cursor: "pointer",
                transition: "all .18s", fontWeight: 500
              }}
              onMouseEnter={e => { e.currentTarget.style.background = C.accent; e.currentTarget.style.color = "#fff"; e.currentTarget.style.boxShadow = `0 4px 16px ${C.accentGlow}`; e.currentTarget.style.transform = "translateY(-1px)"; }}
              onMouseLeave={e => { e.currentTarget.style.background = C.accentDim; e.currentTarget.style.color = C.accent; e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "none"; }}>
              {s}
            </button>
          ))}
        </div>
      )}

      {messages.length <= 1 && (
        <div style={{ padding: "0 24px 14px", display: "flex", gap: 7, flexWrap: "wrap" }}>
          {suggestLoading ? (
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: C.muted, fontSize: 11 }}>
              <Spinner size={11} />
              <span style={{ fontFamily: "'IBM Plex Mono',monospace", letterSpacing: "0.04em" }}>Generating smart questions from your database…</span>
            </div>
          ) : suggestions.map((s, i) => (
            <button key={i} onClick={() => setInput(s)}
              style={{
                padding: "7px 15px", borderRadius: 99,
                background: C.cardRaised,
                border: `1px solid ${C.border}`,
                color: C.textSoft, fontSize: 12, cursor: "pointer",
                transition: "all .18s", fontWeight: 500
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = C.accent; e.currentTarget.style.color = C.text; e.currentTarget.style.background = C.accentDim; e.currentTarget.style.boxShadow = `0 2px 12px ${C.accentGlow}`; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.color = C.textSoft; e.currentTarget.style.background = C.cardRaised; e.currentTarget.style.boxShadow = "none"; }}>
              ✦ {s}
            </button>
          ))}
        </div>
      )}

      <div style={{
        padding: "12px 20px 18px", borderTop: `1px solid ${C.border}`,
        background: C.surface, display: "flex", gap: 10, alignItems: "flex-end"
      }}>
        <textarea value={input} onChange={e => setInput(e.target.value)}
          placeholder="Ask anything about your data…" rows={2}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
          style={{
            flex: 1, background: C.cardRaised, border: `1px solid ${C.border}`, borderRadius: 12,
            padding: "10px 14px", color: C.text, fontSize: 13.5, outline: "none", resize: "none",
            lineHeight: 1.6, transition: "border .18s,box-shadow .18s",
            boxShadow: "none"
          }}
          onFocus={e => { e.target.style.borderColor = C.accent; e.target.style.boxShadow = `0 0 0 3px ${C.accentGlow}`; }}
          onBlur={e => { e.target.style.borderColor = C.border; e.target.style.boxShadow = "none"; }} />
        <Btn onClick={sendMessage} disabled={!input.trim() || loading} icon={Send}
          style={{ height: 44, paddingLeft: 20, paddingRight: 20, borderRadius: 12 }}>
          {loading ? <Spinner size={13} /> : "Send"}
        </Btn>
      </div>
    </div>
  );
}

// ─── DATA EXPLORER TAB ────────────────────────────────────────
function DataExplorerTab({ activeDb, schemaVersion = 0 }) {
  useTheme();
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState("");
  const [columns, setColumns] = useState([]);
  const [data, setData] = useState({ rows: [], total: 0, total_pages: 1, page: 1 });
  const [page, setPage] = useState(1);
  const [globalSearch, setGlobalSearch] = useState("");
  const [filterCol, setFilterCol] = useState("");
  const [filterVal, setFilterVal] = useState("");
  const [sortCol, setSortCol] = useState("");
  const [sortOrder, setSortOrder] = useState("ASC");
  const [loadingData, setLoadingData] = useState(false);
  const [scanLoading, setScanLoading] = useState(false);

  useEffect(() => {
    // Reset all state so we start completely fresh with the new database
    setSelectedTable("");
    setColumns([]);
    setData({ rows: [], total: 0, total_pages: 1, page: 1 });
    setPage(1);
    setGlobalSearch(""); setFilterCol(""); setFilterVal(""); setSortCol("");
    setAiIssues([]);

    safeFetch(`${API}/api/tables`).then(d => {
      if (d && d.tables) {
        setTables(d.tables);
        if (d.tables.length) setSelectedTable(d.tables[0]);
      }
    });
  }, [activeDb, schemaVersion]);

  useEffect(() => {
    if (!selectedTable) return;
    safeFetch(`${API}/api/tables/${selectedTable}/columns`)
      .then(d => { if (d && Array.isArray(d.columns)) setColumns(d.columns); })
      .catch(() => { });
  }, [selectedTable]);

  const fetchData = useCallback(async (p = page) => {
    if (!selectedTable) return;
    setLoadingData(true);
    const params = new URLSearchParams({ page: p, page_size: 10 });
    if (globalSearch.trim()) {
      params.append("global_search", globalSearch.trim());
    }
    if (filterCol && filterCol !== "None" && filterVal.trim()) {
      params.append("filter_col", filterCol);
      params.append("filter_val", filterVal.trim());
    }
    if (sortCol) { params.append("sort_col", sortCol); params.append("sort_order", sortOrder); }
    const d = await safeFetch(`${API}/api/tables/${selectedTable}/data?${params}`);
    if (d) {
      setData(d);
    }
    setLoadingData(false);
  }, [selectedTable, globalSearch, sortCol, sortOrder, page, filterCol, filterVal]);

  useEffect(() => { fetchData(1); setPage(1); }, [selectedTable]); // eslint-disable-line

  // Auto-refetch when sort column or sort direction changes (fixes the toggle button).
  // Guard with sortCol so this doesn't fire on initial mount when sortCol is empty.
  useEffect(() => {
    if (selectedTable && sortCol) { setPage(1); fetchData(1); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortCol, sortOrder]);

  const [aiIssues, setAiIssues] = useState([]);

  const runScan = async () => {
    setScanLoading(true); setAiIssues([]);
    const d = await safeFetch(`${API}/api/tables/${selectedTable}/ai-scan`, { method: "POST" });
    if (d && d.issues) {
      setAiIssues(d.issues);
    }
    setScanLoading(false);
  };

  const colNames = Array.isArray(columns) ? columns.map(c => c.name) : [];

  const PaginationBar = () => (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "10px 16px", background: C.surface, borderTop: `1px solid ${C.border}`
    }}>
      <span style={{ fontSize: 11, color: C.muted, fontFamily: "'IBM Plex Mono',monospace" }}>
        {loadingData ? "Loading…" : `Page ${page} of ${data.total_pages} · ${data.total.toLocaleString()} rows`}
      </span>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <Btn variant="secondary" size="sm" disabled={page <= 1}
          onClick={() => { const p = 1; setPage(p); fetchData(p); }}>« First</Btn>
        <Btn variant="secondary" size="sm" disabled={page <= 1}
          onClick={() => { const p = page - 1; setPage(p); fetchData(p); }}>‹ Prev</Btn>
        <span style={{
          padding: "4px 12px", background: C.accentDim, border: `1px solid ${C.accent}30`,
          borderRadius: 6, fontSize: 11, color: C.accent, fontFamily: "'IBM Plex Mono',monospace", fontWeight: 600
        }}>
          {page} / {data.total_pages}
        </span>
        <Btn variant="secondary" size="sm" disabled={page >= data.total_pages}
          onClick={() => { const p = page + 1; setPage(p); fetchData(p); }}>Next ›</Btn>
        <Btn variant="secondary" size="sm" disabled={page >= data.total_pages}
          onClick={() => { const p = data.total_pages; setPage(p); fetchData(p); }}>Last »</Btn>
      </div>
    </div>
  );

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h2 style={{ fontSize: 19, fontWeight: 700, color: C.text, letterSpacing: "-0.02em" }}>Data Explorer</h2>
          <p style={{ color: C.muted, fontSize: 12, marginTop: 3, fontFamily: "'IBM Plex Mono',monospace" }}>{activeDb || "No DB connected"}</p>
        </div>
        <Badge color={C.purple}>{data.total.toLocaleString()} rows</Badge>
      </div>

      <Card>
        {/* Global search — searches across ALL columns */}
        <div style={{ marginBottom: 14 }}>
          <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>
            🔍 Search Entire Table
          </label>
          <div style={{ display: "flex", gap: 8 }}>
            <Input value={globalSearch} onChange={e => setGlobalSearch(e.target.value)}
              placeholder="Type anything to search across all columns…"
              onKeyDown={e => { if (e.key === "Enter") { setPage(1); fetchData(1); } }}
              style={{ fontSize: 14 }} />
            {globalSearch && (
              <Btn variant="ghost" onClick={() => { setGlobalSearch(""); setPage(1); setTimeout(() => fetchData(1), 0); }}>✕</Btn>
            )}
          </div>
        </div>
        <Divider style={{ margin: "0 0 14px" }} />
        {/* Unified column picker — same column for filter + sort */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 12 }}>
          <div>
            <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>Table</label>
            <Select value={selectedTable} onChange={e => setSelectedTable(e.target.value)}>
              {tables.map(t => <option key={t} value={t}>{t}</option>)}
            </Select>
          </div>
          <div>
            <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>Column</label>
            <Select value={filterCol} onChange={e => { setFilterCol(e.target.value); setSortCol(e.target.value); }}>
              <option value="">— none —</option>
              {colNames.map(c => <option key={c} value={c}>{c}</option>)}
            </Select>
          </div>
          <div>
            <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>Column Value</label>
            <div style={{ display: "flex", gap: 6 }}>
              <Input value={filterVal} onChange={e => setFilterVal(e.target.value)}
                placeholder="Filter matches..." disabled={!filterCol}
                onKeyDown={e => { if (e.key === "Enter") { setPage(1); fetchData(1); } }}
                style={{ flex: 1 }} />
              <Btn variant="secondary" disabled={!filterCol}
                onClick={() => setSortOrder(o => o === "ASC" ? "DESC" : "ASC")}
                icon={sortOrder === "ASC" ? SortAsc : SortDesc} />
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn onClick={() => { setPage(1); fetchData(1); }} icon={Filter}>Apply All (Search, Filter, Sort)</Btn>
          <Btn variant="secondary" onClick={() => {
            setGlobalSearch(""); setFilterCol(""); setFilterVal(""); setSortCol("");
            setPage(1); setTimeout(() => fetchData(1), 0);
          }}>Reset All</Btn>
        </div>
      </Card>

      <Card style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          {loadingData
            ? <div style={{ padding: 40, textAlign: "center" }}><Spinner size={24} /></div>
            : data.rows.length === 0
              ? <div style={{ padding: 40, textAlign: "center", color: C.muted }}>No data found.</div>
              : (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: C.surface }}>
                      {columns.map(col => (
                        <th key={col.name}
                          onClick={() => { setSortCol(col.name); setSortOrder(o => o === "ASC" ? "DESC" : "ASC"); }}
                          style={{
                            padding: "9px 14px", textAlign: "left", cursor: "pointer",
                            borderBottom: `1px solid ${C.border}`, color: C.muted,
                            fontWeight: 600, fontSize: 11, whiteSpace: "nowrap",
                            userSelect: "none", letterSpacing: "0.04em", textTransform: "uppercase"
                          }}>
                          {col.name}
                          <span style={{
                            fontSize: 9, color: C.accent, opacity: .5, marginLeft: 4,
                            fontFamily: "'IBM Plex Mono',monospace"
                          }}>{col.type}</span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.rows.map((row, i) => (
                      <tr key={i} style={{ borderBottom: `1px solid ${C.border}` }}
                        onMouseEnter={e => e.currentTarget.style.background = C.hover}
                        onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                        {columns.map(col => (
                          <td key={col.name} style={{
                            padding: "9px 14px", maxWidth: 200, overflow: "hidden",
                            textOverflow: "ellipsis", whiteSpace: "nowrap"
                          }}>
                            {String(row[col.name] ?? "")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
        </div>
        <PaginationBar />
      </Card>

      <Card>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <div>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: C.text }}>🔬 AI Data Quality Scan</h3>
            <p style={{ fontSize: 11, color: C.muted, marginTop: 3 }}>Analyses the table schema and a 10-row sample to detect quality issues</p>
          </div>
          <Btn onClick={runScan} disabled={scanLoading || !selectedTable} icon={Zap}>
            {scanLoading ? <><Spinner size={13} /> Scanning…</> : "Run Scan"}
          </Btn>
        </div>

        {/* Skeleton while scanning */}
        {scanLoading && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {[0, 1].map(i => (
              <div key={i} style={{
                height: 90, borderRadius: 10, background: C.surface,
                border: `1px solid ${C.border}`, animation: "pulse 1.4s ease infinite"
              }} />
            ))}
          </div>
        )}

        {/* Issue cards */}
        {!scanLoading && aiIssues.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {aiIssues.map((issue, i) => {
              const sevColor = issue.severity === "high" ? C.red
                : issue.severity === "medium" ? C.yellow : C.green;
              const sevBg = issue.severity === "high" ? C.redDim
                : issue.severity === "medium" ? C.yellowDim : C.greenDim;
              return (
                <div key={i} style={{
                  background: C.surface, borderRadius: 10,
                  border: `1px solid ${C.border}`,
                  borderLeft: `4px solid ${sevColor}`,
                  padding: "14px 16px", display: "flex", flexDirection: "column", gap: 8
                }}>
                  {/* Header row */}
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                    <span style={{
                      display: "inline-flex", alignItems: "center", gap: 4,
                      padding: "3px 9px", borderRadius: 20,
                      background: sevBg, color: sevColor,
                      fontSize: 10, fontWeight: 700, border: `1px solid ${sevColor}30`,
                      fontFamily: "'IBM Plex Mono',monospace", textTransform: "uppercase", letterSpacing: "0.06em"
                    }}>
                      {issue.severity === "high" ? "⚠ HIGH" : issue.severity === "medium" ? "◆ MEDIUM" : "✓ LOW"}
                    </span>
                    <span style={{ fontSize: 14, fontWeight: 700, color: C.text }}>{issue.title}</span>
                    {issue.affected && (
                      <span style={{
                        marginLeft: "auto", fontSize: 10, color: C.muted,
                        background: C.cardRaised, border: `1px solid ${C.border}`,
                        borderRadius: 6, padding: "2px 8px",
                        fontFamily: "'IBM Plex Mono',monospace"
                      }}>
                        {issue.affected}
                      </span>
                    )}
                  </div>

                  {/* Description */}
                  <p style={{ fontSize: 13, color: C.text, lineHeight: 1.65, margin: 0 }}>
                    {issue.description}
                  </p>

                  {/* Recommendation */}
                  {issue.recommendation && (
                    <div style={{
                      display: "flex", alignItems: "flex-start", gap: 8,
                      background: `${sevColor}0d`, border: `1px solid ${sevColor}22`,
                      borderRadius: 7, padding: "8px 12px"
                    }}>
                      <span style={{ fontSize: 12, color: sevColor, flexShrink: 0, marginTop: 1 }}>→</span>
                      <span style={{ fontSize: 12, color: C.textSoft, lineHeight: 1.6 }}>
                        <strong style={{ color: sevColor }}>Fix: </strong>{issue.recommendation}
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Empty state */}
        {!scanLoading && aiIssues.length === 0 && (
          <div style={{ textAlign: "center", padding: "28px 0", color: C.muted }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>🔬</div>
            <p style={{ fontSize: 13 }}>Click <strong>Run Scan</strong> to detect data quality issues in <code style={{ color: C.accent }}>{selectedTable || "a table"}</code></p>
          </div>
        )}
      </Card>
    </div>
  );
}



// ─── POLICY HUB TAB ───────────────────────────────────────────
function PolicyTab() {
  useTheme();
  const [messages, setMessages] = useState([{
    role: "assistant",
    content: "Welcome to the AI Policy Hub! Ask me any questions about internal company documents or product catalogs."
  }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("");
  const [rebuildStatus, setRebuildStatus] = useState("");
  const [rebuildLoading, setRebuildLoading] = useState(false);
  const bottomRef = useRef();

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const search = async () => {
    if (!input.trim() || loading) return;
    const q = input.trim();
    setMessages(p => [...p, { role: "user", content: q }]);
    setInput(""); setLoading(true);
    const d = await safeFetch(`${API}/api/policy/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: q })
    });
    if (d) {
      setMessages(p => [...p, { role: "assistant", content: d.answer, chunks: d.chunks }]);
    }
    setLoading(false);
  };

  const uploadDoc = async () => {
    if (!uploadFile) return;
    const fd = new FormData(); fd.append("file", uploadFile);
    const d = await safeFetch(`${API}/api/policy/upload`, { method: "POST", body: fd });
    if (d) {
      setUploadStatus(d.success ? `✅ Uploaded: ${d.filename}` : "❌ Upload failed");
    }
  };

  const rebuildVectorDb = async () => {
    setRebuildLoading(true); setRebuildStatus("");
    const d = await safeFetch(`${API}/api/policy/rebuild-vectordb`, { method: "POST" });
    if (d) {
      setRebuildStatus(d.success ? "✅ Vector DB rebuilt!" : "❌ Rebuild failed");
    }
    setRebuildLoading(false);
  };

  return (
    <div style={{ padding: 24, display: "flex", gap: 20 }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
        <h2 style={{ fontSize: 19, fontWeight: 700, color: C.text, letterSpacing: "-0.02em" }}>AI Policy Hub</h2>
        <Card style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 400 }}>
          <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12, padding: 4 }}>
            {messages.map((msg, i) => (
              <div key={i} style={{ animation: "slideIn .2s ease" }}>
                <div style={{
                  display: "inline-block", maxWidth: "90%",
                  background: msg.role === "user" ? C.accentDim : C.surface,
                  border: `1px solid ${C.border}`,
                  borderRadius: msg.role === "user" ? "12px 4px 12px 12px" : "4px 12px 12px 12px",
                  padding: "10px 14px", fontSize: 13, lineHeight: 1.6, color: C.text,
                  float: msg.role === "user" ? "right" : "left"
                }}>{msg.content}</div>
                {msg.chunks?.length > 0 && (
                  <details style={{ marginTop: 8, clear: "both" }}>
                    <summary style={{ fontSize: 12, color: C.accent, cursor: "pointer" }}>
                      View {msg.chunks.length} source document(s)
                    </summary>
                    <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
                      {msg.chunks.map((c, j) => (
                        <div key={j} style={{
                          background: C.surface, borderLeft: `2px solid ${C.accent}`,
                          borderRadius: 6, padding: "8px 12px", fontSize: 12, color: C.muted,
                          fontFamily: "'IBM Plex Mono',monospace"
                        }}>
                          {c.slice(0, 300)}{c.length > 300 ? "..." : ""}
                        </div>
                      ))}
                    </div>
                  </details>
                )}
                <div style={{ clear: "both" }} />
              </div>
            ))}
            {loading && (
              <div style={{
                display: "flex", gap: 4, padding: "12px 14px", background: C.surface,
                border: `1px solid ${C.border}`, borderRadius: "4px 12px 12px 12px", width: "fit-content"
              }}>
                {[0, 1, 2].map(n => (
                  <span key={n} style={{
                    width: 6, height: 6, borderRadius: "50%", background: C.muted,
                    animation: `pulse 1.2s ease ${n * .2}s infinite`
                  }} />
                ))}
              </div>
            )}
            <div ref={bottomRef} />
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <Input value={input} onChange={e => setInput(e.target.value)}
              placeholder="Ask a policy question..." onKeyDown={e => e.key === "Enter" && search()} />
            <Btn onClick={search} disabled={!input.trim() || loading} icon={Send}>Ask</Btn>
          </div>
        </Card>
      </div>
      <div style={{ width: 300, display: "flex", flexDirection: "column", gap: 16 }}>
        <Card>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: C.text }}>📄 Upload Policy Document</h3>
          <input type="file" accept=".txt" onChange={e => setUploadFile(e.target.files[0])}
            style={{ fontSize: 12, color: C.muted, marginBottom: 10, width: "100%" }} />
          <Btn onClick={uploadDoc} disabled={!uploadFile} icon={Upload} style={{ width: "100%" }}>Upload .txt</Btn>
          {uploadStatus && <p style={{ fontSize: 12, marginTop: 8, color: C.green }}>{uploadStatus}</p>}
        </Card>
        <Card>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: C.text }}>⚙️ Rebuild Vector DB</h3>
          <p style={{ fontSize: 12, color: C.muted, marginBottom: 12, lineHeight: 1.5 }}>
            Re-ingests all documents in <code>/docs/</code> and regenerates ChromaDB embeddings.
          </p>
          <Btn onClick={rebuildVectorDb} disabled={rebuildLoading} variant="secondary"
            icon={RefreshCw} style={{ width: "100%" }}>
            {rebuildLoading ? <><Spinner size={13} /> Rebuilding…</> : "Rebuild Vector DB"}
          </Btn>
          {rebuildStatus && <p style={{ fontSize: 12, marginTop: 8, color: C.green }}>{rebuildStatus}</p>}
        </Card>
      </div>
    </div>
  );
}

// ─── SETTINGS TAB ─────────────────────────────────────────────
function SettingsTab({ activeDb, setActiveDb }) {
  useTheme();
  const [databases, setDatabases] = useState([]);
  const [selectedDb, setSelectedDb] = useState("");

  useEffect(() => {
    safeFetch(`${API}/api/databases`).then(d => {
      if (d && d.databases) { setDatabases(d.databases); setSelectedDb(d.databases[0] || ""); }
    }).catch(() => { });
  }, []);

  const connectDb = async () => {
    const d = await safeFetch(`${API}/api/databases/connect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ db_filename: selectedDb })
    });
    if (d && d.success) setActiveDb(d.uri);
  };

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      <h2 style={{ fontSize: 19, fontWeight: 700, color: C.text, letterSpacing: "-0.02em" }}>Settings</h2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 20, maxWidth: 600 }}>
        <Card>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14, display: "flex", gap: 8, alignItems: "center", color: C.text }}>
            <Database size={16} color={C.accent} /> Database Connection
          </h3>
          <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>Select Database File</label>
          <Select value={selectedDb} onChange={e => setSelectedDb(e.target.value)} style={{ marginBottom: 12 }}>
            {databases.map(db => <option key={db} value={db}>{db}</option>)}
          </Select>
          <Btn onClick={connectDb} disabled={!selectedDb} icon={ArrowRight}>Connect</Btn>
          <p style={{ fontSize: 12, color: C.muted, marginTop: 10 }}>
            Active: <code style={{ color: C.accent }}>{activeDb || "—"}</code>
          </p>
        </Card>
      </div>
    </div>
  );
}

// ─── EXECUTIVE REPORTS TAB ────────────────────────────────────
function ReportsTab() {
  useTheme();
  const [scheduleTime, setScheduleTime] = useState("09:00");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [schedEnabled, setSchedEnabled] = useState(true);
  const [schedStatus, setSchedStatus] = useState(null);
  const [reportHtml, setReportHtml] = useState("");
  const [reportLoading, setReportLoading] = useState(false);
  const [emailStatus, setEmailStatus] = useState("");
  const [emailReport, setEmailReport] = useState("");
  const [sendNowLoading, setSendNowLoading] = useState(false);
  const [schedUpdateStatus, setSchedUpdateStatus] = useState("");
  const [schedUpdateLoading, setSchedUpdateLoading] = useState(false);

  useEffect(() => {
    safeFetch(`${API}/api/scheduler/status`).then(r => r).then(setSchedStatus).catch(() => { });
  }, []);

  const updateSchedule = async () => {
    if (!recipientEmail && schedEnabled) { setSchedUpdateStatus("❌ Please enter a recipient email."); return; }
    setSchedUpdateLoading(true); setSchedUpdateStatus("");
    const d = await safeFetch(`${API}/api/scheduler/update`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ time_str: scheduleTime, recipient_email: recipientEmail, enabled: schedEnabled })
    });
    if (d && d.success) {
      setSchedUpdateStatus("✅ Scheduler updated successfully!");
      const status = await safeFetch(`${API}/api/scheduler/status`);
      if (status && !status._error) setSchedStatus(status);
    } else {
      const msg = d?.detail || "Unknown error — check backend logs.";
      setSchedUpdateStatus(`❌ Failed: ${msg}`);
    }
    setSchedUpdateLoading(false);
  };

  const sendNow = async () => {
    if (!recipientEmail) return; setSendNowLoading(true);
    const fd = new FormData(); fd.append("recipient_email", recipientEmail);
    const d = await safeFetch(`${API}/api/scheduler/send-now`, { method: "POST", body: fd });
    if (d) {
      setEmailStatus(d.success ? "✅ Report sent!" : `❌ ${d.detail}`);
    }
    setSendNowLoading(false);
  };

  const generateReport = async () => {
    setReportLoading(true); setReportHtml("");
    const d = await safeFetch(`${API}/api/report/generate`, { method: "POST" });
    if (d) {
      setReportHtml(d.html);
    }
    setReportLoading(false);
  };

  const emailGeneratedReport = async () => {
    if (!emailReport || !reportHtml) return;
    const d = await safeFetch(`${API}/api/report/email`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recipient_email: emailReport, html_content: reportHtml })
    });
    if (d) {
      setEmailStatus(d.success ? "✅ Report emailed!" : `❌ ${d.detail}`);
    }
  };

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20, height: "100%", overflowY: "auto" }}>
      <h2 style={{ fontSize: 19, fontWeight: 700, color: C.text, letterSpacing: "-0.02em" }}>Executive Reports</h2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 20, maxWidth: 800 }}>
        <Card>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14, display: "flex", gap: 8, alignItems: "center", color: C.text }}>
            <Activity size={16} color={C.accent} /> Report Scheduler
          </h3>
          {schedStatus && (
            <Badge color={schedStatus.status === "active" ? C.green : C.red} style={{ marginBottom: 12, display: "inline-flex" }}>
              {schedStatus.status === "active" ? `● Active — ${schedStatus.next_run}` : "● Not Scheduled"}
            </Badge>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div><label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>Daily Time</label>
              <Input type="time" value={scheduleTime} onChange={e => setScheduleTime(e.target.value)} /></div>
            <div><label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>Recipient Email</label>
              <Input value={recipientEmail} onChange={e => setRecipientEmail(e.target.value)} placeholder="manager@company.com" /></div>
            <label style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13, cursor: "pointer", color: C.text }}>
              <input type="checkbox" checked={schedEnabled} onChange={e => setSchedEnabled(e.target.checked)} /> Enable daily email report
            </label>
            <div style={{ display: "flex", gap: 8 }}>
              <Btn onClick={updateSchedule} disabled={schedUpdateLoading} icon={RefreshCw}>
                {schedUpdateLoading ? <><Spinner size={13} /> Updating…</> : "Update"}
              </Btn>
              <Btn variant="secondary" onClick={sendNow} disabled={sendNowLoading || !recipientEmail} icon={Mail}>
                {sendNowLoading ? <><Spinner size={13} /> Sending…</> : "Send Now"}
              </Btn>
            </div>
            {schedUpdateStatus && <p style={{ fontSize: 12, color: schedUpdateStatus.startsWith("✅") ? C.green : C.red }}>{schedUpdateStatus}</p>}
          </div>
        </Card>
      </div>
      <Card style={{ maxWidth: 800 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14, display: "flex", gap: 8, alignItems: "center", color: C.text }}>
          <TrendingUp size={16} color={C.accent} /> AI Executive Sales Report
        </h3>
        <p style={{ fontSize: 13, color: C.muted, marginBottom: 14, lineHeight: 1.6 }}>
          Generate a deeply analyzed HTML report with live charts covering revenue trends, product performance, regional distribution, and pricing strategy.
        </p>
        <Btn onClick={generateReport} disabled={reportLoading} icon={Zap}>
          {reportLoading ? <><Spinner size={13} /> Generating (may take ~20s)…</> : "Generate Report"}
        </Btn>
        {reportHtml && (
          <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", gap: 8 }}>
              <Btn icon={Download} onClick={() => {
                const blob = new Blob([reportHtml], { type: 'text/html;charset=utf-8' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = 'Executive_Sales_Report.html';
                document.body.appendChild(a); a.click();
                document.body.removeChild(a); URL.revokeObjectURL(url);
              }}>Download HTML</Btn>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <Input value={emailReport} onChange={e => setEmailReport(e.target.value)} placeholder="Email report to..." style={{ maxWidth: 300 }} />
              <Btn variant="secondary" onClick={emailGeneratedReport} disabled={!emailReport} icon={Mail}>Email Report</Btn>
            </div>
            <details>
              <summary style={{ fontSize: 13, color: C.accent, cursor: "pointer" }}>Preview Report</summary>
              <iframe srcDoc={reportHtml} style={{ width: "100%", height: 600, border: "none", borderRadius: 8, marginTop: 8 }} title="Report Preview" />
            </details>
          </div>
        )}
      </Card>
    </div>
  );
}

// ─── SCHEMA MAPPER TAB ────────────────────────────────────────
function SchemaMapperTab({ onRefresh }) {
  useTheme();
  const [relationships, setRelationships] = useState([]);
  const [isMaximized, setIsMaximized] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [showColumns, setShowColumns] = useState(true);
  const [autoMapping, setAutoMapping] = useState(false);

  useEffect(() => {
    loadRelationships();
  }, []);

  const loadRelationships = async () => {
    try {
      const d = await safeFetch(`${API}/api/schema/relationships`);
      if (d && d.relationships && d.relationships.length > 0) {
        setRelationships(d.relationships);
      } else {
        setAutoMapping(true);
        const autoRes = await safeFetch(`${API}/api/schema/relationships/auto-map`, { method: "POST" });
        if (autoRes && autoRes.relationships) {
          setRelationships(autoRes.relationships);
        }
        setAutoMapping(false);
      }
    } catch {
      setAutoMapping(false);
    }
  };
  const forceAutoMap = async () => {
    setAutoMapping(true);
    setRelationships([]);
    try {
      const autoRes = await safeFetch(`${API}/api/schema/relationships/auto-map`, { method: "POST" });
      if (autoRes && autoRes.relationships) {
        setRelationships(autoRes.relationships);
      }
    } catch { }
    setAutoMapping(false);
    // Notify parent so DataExplorer re-fetches its table list
    if (onRefresh) onRefresh();
  };

  const [mapColumns, setMapColumns] = useState({});

  useEffect(() => {
    const newTables = {};
    relationships.forEach(rel => {
      const sk = `${rel.source_db}.${rel.source_table}`;
      const tk = `${rel.target_db}.${rel.target_table}`;
      if (!newTables[sk]) newTables[sk] = { db: rel.source_db, table: rel.source_table };
      if (!newTables[tk]) newTables[tk] = { db: rel.target_db, table: rel.target_table };
    });

    // Use Promise.all so column fetches run in parallel and errors are properly caught
    Promise.all(
      Object.values(newTables).map(async (t) => {
        const key = `${t.db}.${t.table}`;
        if (!mapColumns[key]) {
          try {
            const d = await safeFetch(`${API}/api/tables/${t.table}/columns?db_filename=${t.db}`);
            if (d && d.columns) {
              setMapColumns(p => ({ ...p, [key]: d.columns }));
            }
          } catch (err) {
            console.error("Failed to fetch columns for", key, err);
            setMapColumns(p => ({ ...p, [key]: [] }));
          }
        }
      })
    ).catch(err => console.error("Schema column fetch error:", err));
  }, [relationships]);

  const allTables = useMemo(() => {
    const result = {};
    relationships.forEach(rel => {
      const sk = `${rel.source_db}.${rel.source_table}`;
      const tk = `${rel.target_db}.${rel.target_table}`;
      if (!result[sk]) result[sk] = { db: rel.source_db, table: rel.source_table, cols: mapColumns[sk] || [] };
      if (!result[tk]) result[tk] = { db: rel.target_db, table: rel.target_table, cols: mapColumns[tk] || [] };
    });
    return result;
  }, [relationships, mapColumns]);

  const { svgW, svgH, positions } = useMemo(() => {
    const keys = Object.keys(allTables);
    if (keys.length === 0) return { svgW: 100, svgH: 100, positions: {} };

    const COL_WIDTH = 220, ROW_H = 24, HEAD_H = 46, GAP_X = 160, GAP_Y = 30;
    const pos = {};

    const srcCounts = {};
    relationships.forEach(r => {
      const k = `${r.source_db}.${r.source_table}`;
      srcCounts[k] = (srcCounts[k] || 0) + 1;
    });
    const factKey = Object.entries(srcCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || keys[0];
    const dimKeys = keys.filter(k => k !== factKey);

    const getH = (key) => HEAD_H + (showColumns ? allTables[key].cols.length * ROW_H : 0);
    const totalDimH = dimKeys.reduce((sum, k) => sum + getH(k) + GAP_Y, 0);
    const factH = getH(factKey);

    const startY = 20;
    const factY = startY + Math.max(0, (totalDimH - factH) / 2);
    pos[factKey] = { x: 30, y: factY };

    let dy = startY;
    dimKeys.forEach(k => {
      pos[k] = { x: 30 + COL_WIDTH + GAP_X, y: dy };
      dy += getH(k) + GAP_Y;
    });

    const maxY = Math.max(factY + factH, dy);
    return {
      svgW: 30 + COL_WIDTH + GAP_X + COL_WIDTH + 40,
      svgH: maxY + 40,
      positions: pos
    };
  }, [allTables, showColumns, relationships]);

  const COL_WIDTH = 220, ROW_H = 24, HEAD_H = 46;
  const tableKeys = Object.keys(allTables);
  const srcCountsRender = {};
  relationships.forEach(r => { const k = `${r.source_db}.${r.source_table}`; srcCountsRender[k] = (srcCountsRender[k] || 0) + 1; });
  const factKeyRender = Object.entries(srcCountsRender).sort((a, b) => b[1] - a[1])[0]?.[0] || tableKeys[0];

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h2 style={{ fontSize: 19, fontWeight: 700, color: C.text, letterSpacing: "-0.02em" }}>Relationship Viewer</h2>
          <p style={{ color: C.muted, fontSize: 12, marginTop: 3 }}>View and define cross-database JOIN relationships...</p>
        </div>
        {!autoMapping && (
          <Btn variant="secondary" onClick={forceAutoMap} icon={RefreshCw}>
            Scan for Changes
          </Btn>
        )}
      </div>

      {relationships.length > 0 && (
        <Card>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14, color: C.text }}>Defined Relationships ({relationships.length})</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {relationships.map((rel, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 10, padding: "10px 14px",
                background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, fontSize: 13
              }}>
                <span style={{ color: C.yellow, fontFamily: "'IBM Plex Mono',monospace" }}>{rel.source_table}.{rel.source_column}</span>
                <ArrowRight size={14} color={C.muted} />
                <span style={{ color: C.green, fontFamily: "'IBM Plex Mono',monospace" }}>{rel.target_table}.{rel.target_column}</span>
                <Badge color={C.purple}>{rel.type}</Badge>
                <span style={{ fontSize: 11, color: C.muted, marginLeft: "auto" }}>{rel.source_db} → {rel.target_db}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {tableKeys.length > 0 && (
        <div style={isMaximized ? {
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.85)', zIndex: 9999, display: 'flex',
          flexDirection: 'column', p: 0, backdropFilter: 'blur(8px)',
          animation: 'slideIn .3s ease'
        } : {}}>
          <Card style={isMaximized ? {
            width: '94%', height: '94vh', margin: '3vh auto', display: 'flex', flexDirection: 'column', overflow: 'hidden'
          } : {}}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <h3 style={{ fontSize: 15, fontWeight: 600, color: C.text, margin: 0 }}>🕸️ Live Star Schema Diagram</h3>
                {isMaximized && (
                  <div style={{ display: 'flex', background: C.surface, borderRadius: 6, border: `1px solid ${C.border}`, padding: '2px 4px', gap: 4 }}>
                    <button onClick={() => setZoom(z => Math.max(.2, z - .1))} style={{ background: 'none', border: 'none', color: C.text, cursor: 'pointer', padding: 4 }}><ZoomOut size={14} /></button>
                    <span style={{ fontSize: 11, color: C.muted, minWidth: 40, textAlign: 'center' }}>{Math.round(zoom * 100)}%</span>
                    <button onClick={() => setZoom(z => Math.min(2, z + .1))} style={{ background: 'none', border: 'none', color: C.text, cursor: 'pointer', padding: 4 }}><ZoomIn size={14} /></button>
                    <button onClick={() => setZoom(1)} style={{ fontSize: 9, background: C.accentDim, border: 'none', color: C.accent, borderRadius: 4, cursor: 'pointer', padding: '0 6px' }}>Reset</button>
                  </div>
                )}
                <button onClick={() => setShowColumns(!showColumns)} style={{
                  background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6,
                  color: C.textSoft, padding: '4px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                  fontSize: 11, fontWeight: 600
                }}>
                  {showColumns ? <><EyeOff size={13} /> Collapse Columns</> : <><Eye size={13} /> Show Columns</>}
                </button>
              </div>
              <button onClick={() => { setIsMaximized(!isMaximized); setZoom(1); }} style={{
                background: C.accentDim, border: `1px solid ${C.accent}40`, borderRadius: 6,
                color: C.accent, padding: '4px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 12, fontWeight: 600
              }}>
                {isMaximized ? <><Minimize2 size={13} /> Close</> : <><Maximize2 size={13} /> Fullscreen</>}
              </button>
            </div>
            <div style={{ overflow: "auto", flex: 1, background: C.surface, borderRadius: 8, padding: 20, display: 'flex', justifyContent: 'center' }}>
              <svg width={svgW} height={svgH} style={{
                display: 'block',
                transform: `scale(${zoom})`,
                transformOrigin: 'top center',
                transition: 'transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)'
              }}>
                {relationships.map((rel, i) => {
                  const sk = `${rel.source_db}.${rel.source_table}`, tk = `${rel.target_db}.${rel.target_table}`;
                  const sp = positions[sk], tp = positions[tk];
                  if (!sp || !tp) return null;
                  const sColIdx = allTables[sk].cols.findIndex(c => c.name === rel.source_column);
                  const tColIdx = allTables[tk].cols.findIndex(c => c.name === rel.target_column);
                  const x1 = sp.x + COL_WIDTH, y1 = sp.y + (showColumns ? HEAD_H + (sColIdx >= 0 ? sColIdx * ROW_H + ROW_H / 2 : HEAD_H / 2) : HEAD_H / 2);
                  const x2 = tp.x, y2 = tp.y + (showColumns ? HEAD_H + (tColIdx >= 0 ? tColIdx * ROW_H + ROW_H / 2 : HEAD_H / 2) : HEAD_H / 2);
                  const mx = (x1 + x2) / 2;
                  return (
                    <path key={i} d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`}
                      stroke={C.accent} strokeWidth={2} fill="none" opacity={0.4} />
                  );
                })}

                {Object.keys(allTables).map(key => {
                  const t = allTables[key], p = positions[key];
                  const h = HEAD_H + (showColumns ? t.cols.length * ROW_H : 0);
                  const isFact = key === factKeyRender;
                  const hdrColor = isFact ? C.yellowDim : C.accentDim;
                  const hdrTextColor = isFact ? C.yellow : C.accent;
                  return (
                    <g key={key}>
                      <rect x={p.x} y={p.y} width={COL_WIDTH} height={h} rx={8} fill={C.cardRaised} stroke={isFact ? C.yellow + '44' : C.border} strokeWidth={isFact ? 1.5 : 1} />
                      <rect x={p.x} y={p.y} width={COL_WIDTH} height={HEAD_H} rx={8} fill={hdrColor} />
                      <rect x={p.x} y={p.y + HEAD_H - 8} width={COL_WIDTH} height={8} fill={hdrColor} />
                      {isFact && <rect x={p.x + COL_WIDTH - 46} y={p.y + 6} width={40} height={14} rx={7} fill={C.yellow + '22'} />}
                      {isFact && <text x={p.x + COL_WIDTH - 26} y={p.y + 16} textAnchor="middle" fontSize={8} fontWeight="700" fill={C.yellow}>⚡ Fact</text>}
                      <text x={p.x + COL_WIDTH / 2} y={p.y + 18} textAnchor="middle" fontSize={12} fontWeight="700" fill={hdrTextColor}>{t.table}</text>
                      <text x={p.x + COL_WIDTH / 2} y={p.y + 32} textAnchor="middle" fontSize={10} fill={C.muted}>{t.db}</text>
                      {showColumns && t.cols.map((col, ci) => (
                        <g key={col.name}>
                          <rect x={p.x} y={p.y + HEAD_H + ci * ROW_H} width={COL_WIDTH} height={ROW_H}
                            fill={ci % 2 === 0 ? C.surface : C.cardRaised} opacity={.8} />
                          <text x={p.x + 12} y={p.y + HEAD_H + ci * ROW_H + 16} fontSize={10} fill={C.text}>
                            {col.name}
                            <tspan fill={C.muted} fontSize={8} dx={6}>{col.type}</tspan>
                          </text>
                        </g>
                      ))}
                    </g>
                  );
                })}

                {relationships.map((rel, i) => {
                  const sk = `${rel.source_db}.${rel.source_table}`, tk = `${rel.target_db}.${rel.target_table}`;
                  const sp = positions[sk], tp = positions[tk];
                  if (!sp || !tp) return null;
                  const sColIdx = allTables[sk].cols.findIndex(c => c.name === rel.source_column);
                  const tColIdx = allTables[tk].cols.findIndex(c => c.name === rel.target_column);
                  const x1 = sp.x + COL_WIDTH, y1 = sp.y + (showColumns ? HEAD_H + (sColIdx >= 0 ? sColIdx * ROW_H + ROW_H / 2 : HEAD_H / 2) : HEAD_H / 2);
                  const x2 = tp.x, y2 = tp.y + (showColumns ? HEAD_H + (tColIdx >= 0 ? tColIdx * ROW_H + ROW_H / 2 : HEAD_H / 2) : HEAD_H / 2);
                  const gapMidX = (x1 + x2) / 2;
                  const gapMidY = (y1 + y2) / 2;
                  return (
                    <g key={`badge-${i}`}>
                      <circle cx={x1} cy={y1} r={4.5} fill={C.yellow} stroke={C.bg} strokeWidth={1.5} />
                      <circle cx={x2} cy={y2} r={4.5} fill={C.green} stroke={C.bg} strokeWidth={1.5} />
                      <g transform={`translate(${gapMidX}, ${gapMidY})`}>
                        <rect x={-42} y={-11} width={84} height={22} rx={11}
                          fill={C.bg} stroke={C.accent} strokeWidth={1.5}
                          style={{ filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.5))' }} />
                        <text textAnchor="middle" y={5} fontSize={9} fontWeight="700" fill={C.accent}>{rel.type}</text>
                      </g>
                    </g>
                  );
                })}
              </svg>
            </div>
          </Card>
        </div>
      )}

      {relationships.length === 0 && (
        <div style={{ textAlign: "center", padding: 60, color: C.muted }}>
          {autoMapping ? (
            <>
              <Spinner size={32} color={C.accent} style={{ display: "block", margin: "0 auto 16px" }} />
              <p style={{ fontSize: 16, fontWeight: 600, color: C.accent }}>✨ AI is mapping your database schema...</p>
              <p style={{ fontSize: 13, marginTop: 8 }}>Securely analyzing exact table footprints to build the Star Schema.</p>
            </>
          ) : (
            <>
              <GitFork size={40} style={{ margin: "0 auto 16px", display: "block", opacity: .3 }} />
              <p style={{ fontSize: 15 }}>No relationships available.</p>
              <p style={{ fontSize: 13, marginTop: 6 }}>The AI agent automatically maps relationships when tables are queried.</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}


const TABS = [
  { id: "chat", label: "AI Assistant", icon: MessageSquare },
  { id: "data", label: "Data Explorer", icon: Database },
  { id: "reports", label: "AI Reports", icon: FileText },
  { id: "schema", label: "Relationship Viewer", icon: GitFork },
  { id: "settings", label: "Settings", icon: Settings },
];

// ─── USER PILL (topbar) ───────────────────────────────────
function UserPill({ sessionUser, onSignOut }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef();
  React.useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const initial = (sessionUser.name || sessionUser.email || "U")[0].toUpperCase();

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "5px 10px 5px 5px",
          borderRadius: 40, border: `1px solid ${C.border}`,
          background: C.cardRaised, cursor: "pointer",
          transition: "all .15s",
          boxShadow: open ? `0 0 0 3px ${C.accentGlow}` : "none",
        }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = C.accent; e.currentTarget.style.boxShadow = `0 0 0 3px ${C.accentGlow}`; }}
        onMouseLeave={e => { if (!open) { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.boxShadow = "none"; } }}
      >
        {/* Avatar circle */}
        <div style={{
          width: 28, height: 28, borderRadius: "50%",
          background: `linear-gradient(135deg, ${C.accent}, ${C.purple})`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 12, fontWeight: 700, color: "#fff", flexShrink: 0,
        }}>{initial}</div>
        <span style={{ fontSize: 12, fontWeight: 600, color: C.text, whiteSpace: "nowrap" }}>
          {sessionUser.name || "User"}
        </span>
        <span style={{ fontSize: 10, color: C.muted, marginLeft: 2 }}>{open ? "▲" : "▾"}</span>
      </button>

      {/* Dropdown */}
      {open && (
        <div style={{
          position: "absolute", top: "calc(100% + 8px)", right: 0, zIndex: 999,
          background: C.surface, border: `1px solid ${C.border}`,
          borderRadius: 12, padding: 6, minWidth: 200,
          boxShadow: "0 8px 32px rgba(0,0,0,0.14)",
          animation: "slideIn .15s ease",
        }}>
          {/* User info */}
          <div style={{
            padding: "10px 12px 10px",
            borderBottom: `1px solid ${C.borderSoft}`, marginBottom: 4,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: "50%",
                background: `linear-gradient(135deg, ${C.accent}, ${C.purple})`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 15, fontWeight: 700, color: "#fff", flexShrink: 0,
              }}>{initial}</div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: C.text }}>{sessionUser.name || "User"}</div>
                <div style={{ fontSize: 11, color: C.muted, fontFamily: "'IBM Plex Mono',monospace", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {sessionUser.email || ""}
                </div>
              </div>
            </div>
          </div>
          {/* Sign out */}
          <button onClick={onSignOut} style={{
            display: "flex", alignItems: "center", gap: 8, width: "100%",
            padding: "8px 12px", borderRadius: 8, border: "none",
            background: "transparent", color: C.red, fontSize: 12, fontWeight: 600,
            cursor: "pointer", transition: "background .15s",
          }}
            onMouseEnter={e => { e.currentTarget.style.background = C.redDim; }}
            onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
          >
            <LogOut size={13} /> Sign Out
          </button>
        </div>
      )}
    </div>
  );
}

// ─── PROTECTED ROUTE ──────────────────────────────────────────
function ProtectedRoute({ children }) {
  const session = getAuthSession();
  if (!session) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

// ─── ROUTER ROOT ──────────────────────────────────────────────
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/app" element={<ProtectedRoute><MainApp /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
// ─── MAIN DASHBOARD APP ────────────────────────────────────────
function MainApp() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("chat");
  const [activeDb, setActiveDb] = useState("");
  const [apiOk, setApiOk] = useState(null);
  const [theme, setTheme] = useState("dark");
  const [schemaVersion, setSchemaVersion] = useState(0);
  const session = getAuthSession();
  const sessionUser = session?.user || {};

  window.__theme = theme;
  const toggle = () => setTheme(t => t === "dark" ? "light" : "dark");

  useEffect(() => {
    safeFetch(`${API}/api/health`).then(d => {
      if (d) {
        setApiOk(true);
        safeFetch(`${API}/api/databases`).then(db => { if (db) setActiveDb(db.active || ""); });
      } else {
        setApiOk(false);
      }
    });
  }, []);

  return (
    <ThemeCtx.Provider value={{ theme, toggle }}>
      <style>{makeStyle(theme)}</style>
      <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>

        {/* Sidebar */}
        <div style={{
          width: 240, flexShrink: 0, background: C.sidebarBg,
          borderRight: `1px solid ${C.border}`, display: "flex", flexDirection: "column", position: "relative",
          boxShadow: "4px 0 24px rgba(0,0,0,0.18)"
        }}>
          {/* Top accent line */}
          <div style={{
            position: "absolute", top: 0, left: 0, right: 0, height: 2,
            background: `linear-gradient(90deg,${C.accent},${C.purple},${C.teal})`,
            borderRadius: "0 0 2px 2px"
          }} />

          {/* Logo */}
          <div style={{ padding: "26px 18px 16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 11,
                background: `linear-gradient(135deg,${C.accent},${C.purple})`,
                display: "flex", alignItems: "center", justifyContent: "center",
                boxShadow: `0 4px 16px ${C.accentGlow}`
              }}>
                <Bot size={17} color="#fff" />
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 800, color: C.text, letterSpacing: "-0.03em" }}>DataAnalyst</div>
                <div style={{ fontSize: 9.5, color: C.muted, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", marginTop: 1 }}>Enterprise AI</div>
              </div>
            </div>
          </div>

          <Divider style={{ margin: "0 16px 10px" }} />

          {/* Nav */}
          <nav style={{ flex: 1, padding: "4px 10px", display: "flex", flexDirection: "column", gap: 2, overflowY: "auto" }}>
            {TABS.map(tab => {
              const Icon = tab.icon, active = activeTab === tab.id;
              return (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  style={{
                    display: "flex", alignItems: "center", gap: 10, padding: "9px 12px", borderRadius: 10,
                    border: "none",
                    background: active ? C.accentDim : "transparent",
                    color: active ? C.accent : C.textSoft,
                    fontSize: 13, fontWeight: active ? 700 : 500,
                    cursor: "pointer", textAlign: "left", transition: "all .15s",
                    boxShadow: active ? `inset 0 0 0 1px ${C.accent}35` : "none", position: "relative"
                  }}
                  onMouseEnter={e => { if (!active) { e.currentTarget.style.background = C.hover; e.currentTarget.style.color = C.text; } }}
                  onMouseLeave={e => { if (!active) { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = C.textSoft; } }}>
                  {active && <div style={{
                    position: "absolute", left: 0, top: "20%", bottom: "20%", width: 3,
                    background: `linear-gradient(180deg,${C.accent},${C.purple})`, borderRadius: "0 3px 3px 0"
                  }} />}
                  <Icon size={15} style={{ flexShrink: 0 }} />{tab.label}
                </button>
              );
            })}
          </nav>

          {/* Footer */}
          <div style={{ padding: "14px 16px", borderTop: `1px solid ${C.borderSoft}` }}>
            {/* Theme Toggle */}
            <button onClick={toggle}
              style={{
                display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "7px 10px",
                borderRadius: 8, border: `1px solid ${C.border}`, background: C.surface,
                color: C.textSoft, fontSize: 12, fontWeight: 500, cursor: "pointer",
                marginBottom: 8, transition: "all .15s"
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = C.accent; e.currentTarget.style.color = C.text; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.color = C.textSoft; }}>
              {theme === "dark"
                ? <Sun size={13} color={C.yellow} />
                : <Moon size={13} color={C.purple} />}
              {theme === "dark" ? "Light mode" : "Dark mode"}
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <span style={{
                width: 7, height: 7, borderRadius: "50%", flexShrink: 0,
                background: apiOk === null ? C.muted : apiOk ? C.green : C.red,
                boxShadow: apiOk ? `0 0 6px ${C.green}` : "none"
              }} />
              <span style={{ fontSize: 11, color: C.textSoft }}>
                {apiOk === null ? "Connecting…" : apiOk ? "API Connected" : "API Offline"}
              </span>
            </div>
            <div style={{ fontSize: 10, color: C.muted, fontFamily: "'IBM Plex Mono',monospace", letterSpacing: "0.02em" }}>
              Gemini · LangGraph · ChromaDB
            </div>
          </div>
        </div>

        {/* Main */}
        <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column", background: C.bg }}>

          {/* Top bar */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "0 24px", height: 56, flexShrink: 0,
            background: C.surface,
            borderBottom: `1px solid ${C.border}`,
            boxShadow: `0 1px 12px rgba(0,0,0,0.15)`,
          }}>
            {/* Left — current tab label */}
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: C.text, letterSpacing: "-0.01em" }}>
                {TABS.find(t => t.id === activeTab)?.label || "Dashboard"}
              </span>
              {apiOk === false && (
                <div style={{
                  display: "flex", alignItems: "center", gap: 5,
                  background: `${C.red}14`, border: `1px solid ${C.red}30`,
                  borderRadius: 6, padding: "3px 10px",
                }}>
                  <AlertCircle size={11} color={C.red} />
                  <span style={{ fontSize: 11, color: C.red, fontFamily: "'IBM Plex Mono',monospace" }}>
                    API offline
                  </span>
                </div>
              )}
            </div>

            {/* Right — user account pill */}
            <UserPill sessionUser={sessionUser} onSignOut={() => { clearAuthSession(); navigate("/login"); }} />
          </div>

          {/* Tab panels */}
          <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
            <div style={{ display: activeTab === "chat" ? "flex" : "none", height: "100%", flexDirection: "column" }}><ChatTab /></div>
            <div style={{ display: activeTab === "data" ? "block" : "none", height: "100%" }}><DataExplorerTab activeDb={activeDb} schemaVersion={schemaVersion} /></div>
            <div style={{ display: activeTab === "reports" ? "block" : "none", height: "100%" }}><ReportsTab /></div>
            <div style={{ display: activeTab === "schema" ? "block" : "none", height: "100%" }}><SchemaMapperTab onRefresh={() => setSchemaVersion(v => v + 1)} /></div>
            <div style={{ display: activeTab === "settings" ? "block" : "none", height: "100%" }}><SettingsTab activeDb={activeDb} setActiveDb={setActiveDb} /></div>
          </div>
        </div>
      </div>
    </ThemeCtx.Provider>
  );
}
