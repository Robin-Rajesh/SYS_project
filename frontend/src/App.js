import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import LandingPage from "./LandingPage";
import LoginPage from "./LoginPage";
import {
  MessageSquare, Database, BarChart2, BookOpen, Settings,
  Send, Trash2, RefreshCw, Download, Mail, Upload,
  Zap, Activity, Filter, SortAsc, SortDesc, ArrowRight, Bot, User,
  GitFork, Link, Unlink, CheckCircle, AlertCircle, TrendingUp, Plus, Sun, Moon,
  Maximize2, Minimize2, ZoomIn, ZoomOut, Eye, EyeOff
} from "lucide-react";
import Plot from "react-plotly.js";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API = "http://localhost:8000";

// ─── THEME PALETTES ───────────────────────────────────────────
const DARK = {
  bg: "#07090f", surface: "#0d1117", card: "#0d1117", cardRaised: "#131920",
  border: "#1e2733", borderSoft: "#16202b", accent: "#4f9eff",
  accentGlow: "rgba(79,158,255,0.12)", accentDim: "#172336",
  green: "#2ea87e", greenDim: "#0d2e21", yellow: "#c9921a", yellowDim: "#2a1f08",
  red: "#e5534b", redDim: "#2a0f0e", purple: "#a371f7", purpleDim: "#1e1040",
  teal: "#2dd4bf", text: "#cdd9e5", textSoft: "#8b949e", muted: "#545d68",
  hover: "#131920", sidebarBg: "#090d13",
};
const LIGHT = {
  bg: "#f4f6fa", surface: "#ffffff", card: "#ffffff", cardRaised: "#f9fafb",
  border: "#dde3ec", borderSoft: "#e8edf4", accent: "#2563eb",
  accentGlow: "rgba(37,99,235,0.10)", accentDim: "#dbeafe",
  green: "#059669", greenDim: "#d1fae5", yellow: "#b45309", yellowDim: "#fef3c7",
  red: "#dc2626", redDim: "#fee2e2", purple: "#7c3aed", purpleDim: "#ede9fe",
  teal: "#0d9488", text: "#111827", textSoft: "#4b5563", muted: "#9ca3af",
  hover: "#f3f4f6", sidebarBg: "#eef1f7",
};

// Proxy — reads window.__theme at access time so all components always get live colors
const C = new Proxy({}, { get(_, k) { return (window.__theme === "light" ? LIGHT : DARK)[k]; } });

const ThemeCtx = React.createContext({ theme: "dark", toggle: () => { } });
function useTheme() { return React.useContext(ThemeCtx); }

function makeStyle(theme) {
  const t = theme === "light" ? LIGHT : DARK;
  return `
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    html,body,#root{height:100%;background:${t.bg};color:${t.text};font-family:'Plus Jakarta Sans',sans-serif}
    ::-webkit-scrollbar{width:4px;height:4px}
    ::-webkit-scrollbar-track{background:transparent}
    ::-webkit-scrollbar-thumb{background:${t.border};border-radius:4px}
    input,select,textarea,button{font-family:inherit}
    a{color:${t.accent};text-decoration:none}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
    @keyframes slideIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
    @keyframes spin{to{transform:rotate(360deg)}}
    .markdown-body ul, .markdown-body ol{padding-left:1.5em;margin:0.8em 0}
    .markdown-body li{margin-bottom:0.4em}
    .markdown-body p{margin-bottom:0.8em}
    .markdown-body h1, .markdown-body h2, .markdown-body h3{margin:1em 0 0.5em}
    .markdown-body pre{background:${t.surface};padding:10px;border-radius:6px;border:1px solid ${t.border};font-family:'IBM Plex Mono',monospace;margin:0.8em 0;overflow-x:auto}
    .markdown-body code{background:${t.surface};padding:2px 4px;border-radius:4px;font-family:'IBM Plex Mono',monospace;font-size:0.9em}
  `;
}

// ─── SHARED COMPONENTS ────────────────────────────────────────
const Spinner = ({ size = 16 }) => (
  <span style={{
    display: "inline-block", width: size, height: size, border: `1.5px solid ${C.border}`,
    borderTopColor: C.accent, borderRadius: "50%", animation: "spin .65s linear infinite", flexShrink: 0
  }} />
);

const Badge = ({ children, color = C.accent }) => (
  <span style={{
    display: "inline-flex", alignItems: "center", gap: 4, padding: "3px 9px", borderRadius: 20,
    background: `${color}18`, color, fontSize: 10, fontWeight: 700, border: `1px solid ${color}30`,
    fontFamily: "'IBM Plex Mono',monospace", letterSpacing: "0.04em", textTransform: "uppercase"
  }}>
    {children}
  </span>
);

const Card = ({ children, style = {} }) => (
  <div style={{
    background: C.cardRaised, border: `1px solid ${C.border}`, borderRadius: 14, padding: 20,
    boxShadow: `inset 0 1px 0 rgba(255,255,255,0.03)`, ...style
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
  const pad = size === "sm" ? "5px 12px" : "8px 16px";
  const fs = size === "sm" ? 12 : 13;
  const V = {
    primary: { background: `linear-gradient(135deg,${C.accent},#3b8dff)`, color: C.bg === "dark" ? "#000" : "#fff", boxShadow: `0 2px 8px ${C.accentGlow}` },
    secondary: { background: C.surface, color: C.text, border: `1px solid ${C.border}` },
    danger: { background: C.redDim, color: C.red, border: `1px solid ${C.red}30` },
    ghost: { background: "transparent", color: C.textSoft },
    success: { background: C.greenDim, color: C.green, border: `1px solid ${C.green}30` },
  };
  return (
    <button onClick={onClick} disabled={disabled} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6, padding: pad, borderRadius: 8, fontSize: fs,
        fontWeight: 600, border: "none", transition: "all .15s", cursor: disabled ? "not-allowed" : "pointer",
        letterSpacing: "0.01em", opacity: disabled ? .45 : hov ? .82 : 1,
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
  const [messages, setMessages] = useState([{
    role: "assistant",
    content: "Welcome! I am your Enterprise Data Analyst AI. Ask me anything about your sales data.", ts: new Date()
  }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState([]);
  const bottomRef = useRef();

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, steps]);

  const sendMessage = useCallback(async () => {
    if (!input.trim() || loading) return;
    const userMsg = { role: "user", content: input.trim(), ts: new Date() };
    setMessages(p => [...p, userMsg]);
    setInput(""); setLoading(true); setSteps([]);

    const res = await fetch(`${API}/api/chat/stream`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMsg.content })
    });

    const reader = res.body.getReader();
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
            const sql = pendingSql;
            setMessages(p => [...p, {
              role: "assistant", content: evt.content,
              plotlyJson: evt.plotly_json, sqlQuery: sql || null, ts: new Date()
            }]);
            pendingSql = null; setSteps([]); setLoading(false);
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
    await fetch(`${API}/api/chat/clear`, { method: "POST" });
    setMessages([{ role: "assistant", content: "Memory cleared. Starting fresh.", ts: new Date() }]);
    setSteps([]);
  };

  // Smart Suggestions: shown after last AI message
  const DYNAMIC_SUGGESTIONS = [
    ["Which product category has the highest profit margin?", "Show me discount vs profit as a scatter chart", "Who are the top 5 customers by revenue?"],
    ["What is the month-over-month revenue trend?", "Compare regional sales as a bar chart", "What is the average order value?"],
    ["Show all cross-database relationships in the data", "Which customers have purchased the most products?", "What percentage of orders have discounts over 20%?"],
    ["Show me top-selling sub-categories", "Which region has the lowest profit margin?", "Plot monthly revenue for the last year"],
  ];

  const getSuggestions = (msgCount) => DYNAMIC_SUGGESTIONS[msgCount % DYNAMIC_SUGGESTIONS.length];

  const suggestions = [
    "Show me total sales by region as a bar chart",
    "Plot revenue over time as a line chart",
    "What are the top 5 products by profit?",
    "Are there any policy violations with 25% discounts?",
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "16px 24px", borderBottom: `1px solid ${C.borderSoft}`, background: C.sidebarBg, flexShrink: 0
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: `linear-gradient(135deg,${C.purpleDim},${C.accentDim})`,
            border: `1px solid ${C.purple}40`, display: "flex", alignItems: "center", justifyContent: "center"
          }}>
            <Bot size={16} color={C.purple} />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: C.text }}>AI Assistant</div>
            <div style={{ fontSize: 11, color: C.green, display: "flex", alignItems: "center", gap: 4, marginTop: 1 }}>
              <span style={{
                width: 5, height: 5, borderRadius: "50%", background: C.green,
                boxShadow: `0 0 4px ${C.green}`, display: "inline-block"
              }} />
              Live · Gemini 2.5 Flash
            </div>
          </div>
        </div>
        <Btn variant="ghost" onClick={clearChat} icon={Trash2} size="sm">Clear</Btn>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{
            display: "flex", gap: 10, alignItems: "flex-start",
            flexDirection: msg.role === "user" ? "row-reverse" : "row", animation: "slideIn .2s ease"
          }}>
            <div style={{
              width: 30, height: 30, borderRadius: 8, flexShrink: 0, display: "flex",
              alignItems: "center", justifyContent: "center",
              background: msg.role === "user"
                ? `linear-gradient(135deg,${C.accentDim},${C.purpleDim})`
                : `linear-gradient(135deg,${C.purpleDim},${C.accentDim})`,
              border: `1px solid ${msg.role === "user" ? C.accent : C.purple}30`
            }}>
              {msg.role === "user" ? <User size={13} color={C.accent} /> : <Bot size={13} color={C.purple} />}
            </div>
            <div style={{ maxWidth: "76%", display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{
                background: msg.role === 'user' ? C.accentDim : C.cardRaised,
                border: `1px solid ${msg.error ? C.red : msg.role === 'user' ? C.accent + '30' : C.border}`,
                borderRadius: msg.role === 'user' ? '14px 4px 14px 14px' : '4px 14px 14px 14px',
                padding: '11px 15px', fontSize: 13.5, lineHeight: 1.6,
                wordBreak: 'break-word', color: C.text
              }}>
                <div className="markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
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

              <span style={{
                fontSize: 10, color: C.muted,
                alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                fontFamily: "'IBM Plex Mono',monospace", marginTop: 4
              }}>
                {msg.ts?.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
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
              justifyContent: "center", background: C.purpleDim, border: `1px solid ${C.purple}30`
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
        <div style={{ padding: "0 24px 10px", display: "flex", gap: 6, flexWrap: "wrap", animation: "slideIn .25s ease" }}>
          <span style={{ fontSize: 10, color: C.muted, width: '100%', marginBottom: 2, fontFamily: "'IBM Plex Mono',monospace" }}>Suggested questions:</span>
          {getSuggestions(messages.length).map((s, i) => (
            <button key={i} onClick={() => { setInput(s); }}
              style={{
                padding: "5px 12px", borderRadius: 20, background: C.surface,
                border: `1px solid ${C.border}`, color: C.textSoft, fontSize: 11, cursor: "pointer",
                transition: "all .15s", fontFamily: "'Plus Jakarta Sans',sans-serif"
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = C.accent; e.currentTarget.style.color = C.text; e.currentTarget.style.background = C.accentDim; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.color = C.textSoft; e.currentTarget.style.background = C.surface; }}>
              ✦ {s}
            </button>
          ))}
        </div>
      )}

      {messages.length <= 1 && (
        <div style={{ padding: "0 24px 12px", display: "flex", gap: 6, flexWrap: "wrap" }}>
          {suggestions.map((s, i) => (
            <button key={i} onClick={() => setInput(s)}
              style={{
                padding: "5px 12px", borderRadius: 20, background: C.cardRaised,
                border: `1px solid ${C.border}`, color: C.textSoft, fontSize: 11.5, cursor: "pointer",
                transition: "all .15s", fontFamily: "'Plus Jakarta Sans',sans-serif"
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = C.accent; e.currentTarget.style.color = C.text; e.currentTarget.style.background = C.accentDim; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.color = C.textSoft; e.currentTarget.style.background = C.cardRaised; }}>
              {s}
            </button>
          ))}
        </div>
      )}

      <div style={{
        padding: "14px 24px 18px", borderTop: `1px solid ${C.borderSoft}`,
        background: C.sidebarBg, display: "flex", gap: 10, alignItems: "flex-end"
      }}>
        <textarea value={input} onChange={e => setInput(e.target.value)}
          placeholder="Ask anything about your data…" rows={2}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
          style={{
            flex: 1, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10,
            padding: "10px 14px", color: C.text, fontSize: 13.5, outline: "none", resize: "none",
            fontFamily: "'Plus Jakarta Sans',sans-serif", lineHeight: 1.55, transition: "border .15s,box-shadow .15s"
          }}
          onFocus={e => { e.target.style.borderColor = C.accent; e.target.style.boxShadow = `0 0 0 3px ${C.accentGlow}`; }}
          onBlur={e => { e.target.style.borderColor = C.border; e.target.style.boxShadow = "none"; }} />
        <Btn onClick={sendMessage} disabled={!input.trim() || loading} icon={Send}
          style={{ height: 42, paddingLeft: 18, paddingRight: 18 }}>
          {loading ? <Spinner size={13} /> : "Send"}
        </Btn>
      </div>
    </div>
  );
}

// ─── DATA EXPLORER TAB ────────────────────────────────────────
function DataExplorerTab({ activeDb }) {
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
  const [aiInsight, setAiInsight] = useState("");
  const [scanLoading, setScanLoading] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/tables`).then(r => r.json())
      .then(d => { setTables(d.tables); if (d.tables.length) setSelectedTable(d.tables[0]); })
      .catch(() => { });
  }, [activeDb]);

  useEffect(() => {
    if (!selectedTable) return;
    fetch(`${API}/api/tables/${selectedTable}/columns`).then(r => r.json())
      .then(d => setColumns(d.columns)).catch(() => { });
  }, [selectedTable]);

  const fetchData = useCallback(async (p = page) => {
    if (!selectedTable) return;
    setLoadingData(true);
    const params = new URLSearchParams({ page: p, page_size: 10 });
    // Global search — if set, ignore filterCol/filterVal
    if (globalSearch.trim()) {
      params.append("global_search", globalSearch.trim());
    } else {
      if (filterCol && filterVal) { params.append("filter_col", filterCol); params.append("filter_val", filterVal); }
    }
    if (sortCol) { params.append("sort_col", sortCol); params.append("sort_order", sortOrder); }
    const res = await fetch(`${API}/api/tables/${selectedTable}/data?${params}`);
    const d = await res.json();
    setData(d); setLoadingData(false);
  }, [selectedTable, globalSearch, filterCol, filterVal, sortCol, sortOrder, page]);

  useEffect(() => { fetchData(1); setPage(1); }, [selectedTable]); // eslint-disable-line

  const runScan = async () => {
    setScanLoading(true); setAiInsight("");
    const res = await fetch(`${API}/api/tables/${selectedTable}/ai-scan`, { method: "POST" });
    const d = await res.json(); setAiInsight(d.insight); setScanLoading(false);
  };

  const colNames = columns.map(c => c.name);

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
        {/* Column filter + sort */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 12, marginBottom: 12 }}>
          <div>
            <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>Table</label>
            <Select value={selectedTable} onChange={e => setSelectedTable(e.target.value)}>
              {tables.map(t => <option key={t} value={t}>{t}</option>)}
            </Select>
          </div>
          <div>
            <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>Filter Column</label>
            <Select value={filterCol} onChange={e => setFilterCol(e.target.value)}>
              <option value="">— none —</option>
              {colNames.map(c => <option key={c} value={c}>{c}</option>)}
            </Select>
          </div>
          <div>
            <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>Column Value</label>
            <Input value={filterVal} onChange={e => setFilterVal(e.target.value)}
              placeholder="filter by column…" onKeyDown={e => e.key === "Enter" && fetchData(1)} />
          </div>
          <div>
            <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>Sort</label>
            <div style={{ display: "flex", gap: 6 }}>
              <Select value={sortCol} onChange={e => setSortCol(e.target.value)} style={{ flex: 1 }}>
                <option value="">— none —</option>
                {colNames.map(c => <option key={c} value={c}>{c}</option>)}
              </Select>
              <Btn variant="secondary" onClick={() => setSortOrder(o => o === "ASC" ? "DESC" : "ASC")}
                icon={sortOrder === "ASC" ? SortAsc : SortDesc} />
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn onClick={() => { setPage(1); fetchData(1); }} icon={Filter}>Apply</Btn>
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
                          onClick={() => { setSortCol(col.name); setSortOrder(o => o === "ASC" ? "DESC" : "ASC"); fetchData(1); }}
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
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: C.text }}>🔍 AI Data Quality Scan</h3>
          <Btn onClick={runScan} disabled={scanLoading || !selectedTable} icon={Zap}>
            {scanLoading ? <><Spinner size={13} /> Scanning…</> : "Run Scan"}
          </Btn>
        </div>
        {aiInsight && (
          <div style={{
            background: C.surface, border: `1px solid ${C.yellow}44`,
            borderLeft: `3px solid ${C.yellow}`, borderRadius: 8,
            padding: "12px 16px", fontSize: 13, lineHeight: 1.7, color: C.text
          }}>
            {aiInsight}
          </div>
        )}
      </Card>
    </div>
  );
}

// ─── DASHBOARD TAB ────────────────────────────────────────────
function DashboardTab() {
  useTheme();
  const [tables, setTables] = useState([]);
  const [cols, setCols] = useState([]);
  const [table, setTable] = useState("");
  const [xCol, setXCol] = useState("");
  const [yCol, setYCol] = useState("");
  const [chartType, setChartType] = useState("bar");
  const [agg, setAgg] = useState("None");
  const [limit, setLimit] = useState(50);
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [insight, setInsight] = useState("");
  const [insightLoading, setInsightLoading] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/tables`).then(r => r.json()).then(d => {
      setTables(d.tables); if (d.tables[0]) setTable(d.tables[0]);
    }).catch(() => { });
  }, []);

  useEffect(() => {
    if (!table) return;
    fetch(`${API}/api/tables/${table}/columns`).then(r => r.json()).then(d => {
      setCols(d.columns);
      if (d.columns[0]) setXCol(d.columns[0].name);
      const num = d.columns.find(c => ["INT", "FLOAT", "REAL", "NUMERIC"].some(t => c.type.toUpperCase().startsWith(t)));
      setYCol(num?.name || d.columns[1]?.name || "");
    }).catch(() => { });
  }, [table]);

  const generateChart = async () => {
    if (!table || !xCol || !yCol) return;
    setLoading(true); setChartData(null); setInsight("");
    const params = new URLSearchParams({ table, x_col: xCol, y_col: yCol, chart_type: chartType, aggregation: agg, limit });
    const res = await fetch(`${API}/api/dashboard/chart?${params}`);
    if (res.ok) { const d = await res.json(); setChartData(d); }
    setLoading(false);
  };

  const getInsight = async () => {
    if (!chartData) return;
    setInsightLoading(true);
    const res = await fetch(`${API}/api/dashboard/ai-insight`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rows: chartData.rows })
    });
    const d = await res.json(); setInsight(d.insight); setInsightLoading(false);
  };

  const chartTypes = [
    { id: "bar", label: "Bar", emoji: "📊" }, { id: "line", label: "Line", emoji: "📈" },
    { id: "pie", label: "Pie", emoji: "🥧" }, { id: "scatter", label: "Scatter", emoji: "✦" },
  ];

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      <h2 style={{ fontSize: 19, fontWeight: 700, color: C.text, letterSpacing: "-0.02em" }}>Interactive Dashboard</h2>
      <Card>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 16 }}>
          {[["Table", table, setTable, tables.map(t => ({ v: t, l: t }))],
          ["X Axis", xCol, setXCol, cols.map(c => ({ v: c.name, l: c.name }))],
          ["Y Axis", yCol, setYCol, cols.map(c => ({ v: c.name, l: c.name }))],
          ["Aggregation", agg, setAgg, ["None", "SUM", "AVG", "COUNT", "MAX", "MIN"].map(a => ({ v: a, l: a }))],
          ["Limit", limit, setLimit, [10, 25, 50, 100, 500].map(n => ({ v: n, l: `Top ${n}` }))]
          ].map(([lbl, val, setter, opts]) => (
            <div key={lbl}>
              <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>{lbl}</label>
              <Select value={val} onChange={e => setter(lbl === "Limit" ? Number(e.target.value) : e.target.value)}>
                {opts.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
              </Select>
            </div>
          ))}
        </div>
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 8 }}>Chart Type</label>
          <div style={{ display: "flex", gap: 10 }}>
            {chartTypes.map(ct => (
              <button key={ct.id} onClick={() => setChartType(ct.id)}
                style={{
                  padding: "8px 16px", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer",
                  transition: "all .15s", background: chartType === ct.id ? C.accentDim : C.surface,
                  color: chartType === ct.id ? C.accent : C.textSoft,
                  border: `1px solid ${chartType === ct.id ? C.accent + "40" : C.border}`,
                  boxShadow: chartType === ct.id ? `0 2px 8px ${C.accentGlow}` : "none"
                }}>
                {ct.emoji} {ct.label}
              </button>
            ))}
          </div>
        </div>
        <Btn onClick={generateChart} disabled={loading || !table || !xCol || !yCol} icon={BarChart2}>
          {loading ? <><Spinner size={13} /> Generating…</> : "Generate Chart"}
        </Btn>
      </Card>

      {chartData && (
        <>
          <Card><PlotlyChart plotlyJson={chartData.plotly_json} style={{ height: 420 }} /></Card>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Card style={{ overflow: "auto", maxHeight: 300 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: C.text }}>Raw Data</h3>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead><tr>{chartData.rows[0] && Object.keys(chartData.rows[0]).map(k => (
                  <th key={k} style={{
                    padding: "6px 10px", textAlign: "left", color: C.muted,
                    borderBottom: `1px solid ${C.border}`
                  }}>{k}</th>
                ))}</tr></thead>
                <tbody>{chartData.rows.slice(0, 50).map((row, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}22` }}>
                    {Object.values(row).map((v, j) => (
                      <td key={j} style={{ padding: "5px 10px", color: C.text }}>{String(v)}</td>
                    ))}
                  </tr>
                ))}</tbody>
              </table>
            </Card>
            <Card>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, color: C.text }}>✨ AI Insight</h3>
                <Btn onClick={getInsight} disabled={insightLoading} icon={Zap}>
                  {insightLoading ? <><Spinner size={13} /> Analyzing…</> : "Generate"}
                </Btn>
              </div>
              {insight
                ? <div style={{
                  background: C.surface, borderLeft: `3px solid ${C.purple}`, borderRadius: 8,
                  padding: "12px 16px", fontSize: 13, lineHeight: 1.7, color: C.text
                }}>{insight}</div>
                : <p style={{ color: C.muted, fontSize: 13 }}>Click "Generate" to get AI business insights on the current chart.</p>}
            </Card>
          </div>
        </>
      )}
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
    const res = await fetch(`${API}/api/policy/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: q })
    });
    const d = await res.json();
    setMessages(p => [...p, { role: "assistant", content: d.answer, chunks: d.chunks }]);
    setLoading(false);
  };

  const uploadDoc = async () => {
    if (!uploadFile) return;
    const fd = new FormData(); fd.append("file", uploadFile);
    const res = await fetch(`${API}/api/policy/upload`, { method: "POST", body: fd });
    const d = await res.json();
    setUploadStatus(d.success ? `✅ Uploaded: ${d.filename}` : "❌ Upload failed");
  };

  const rebuildVectorDb = async () => {
    setRebuildLoading(true); setRebuildStatus("");
    const res = await fetch(`${API}/api/policy/rebuild-vectordb`, { method: "POST" });
    const d = await res.json();
    setRebuildStatus(d.success ? "✅ Vector DB rebuilt!" : "❌ Rebuild failed");
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
  const [scheduleTime, setScheduleTime] = useState("09:00");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [schedEnabled, setSchedEnabled] = useState(true);
  const [schedStatus, setSchedStatus] = useState(null);
  const [reportHtml, setReportHtml] = useState("");
  const [reportLoading, setReportLoading] = useState(false);
  const [emailStatus, setEmailStatus] = useState("");
  const [emailReport, setEmailReport] = useState("");
  const [sendNowLoading, setSendNowLoading] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/databases`).then(r => r.json()).then(d => {
      setDatabases(d.databases); setSelectedDb(d.databases[0] || "");
    }).catch(() => { });
    fetch(`${API}/api/scheduler/status`).then(r => r.json()).then(setSchedStatus).catch(() => { });
  }, []);

  const connectDb = async () => {
    const res = await fetch(`${API}/api/databases/connect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ db_filename: selectedDb })
    });
    const d = await res.json(); if (d.success) setActiveDb(d.uri);
  };

  const updateSchedule = async () => {
    await fetch(`${API}/api/scheduler/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ time_str: scheduleTime, recipient_email: recipientEmail, enabled: schedEnabled })
    });
    const d = await fetch(`${API}/api/scheduler/status`).then(r => r.json()); setSchedStatus(d);
  };

  const sendNow = async () => {
    if (!recipientEmail) return; setSendNowLoading(true);
    const fd = new FormData(); fd.append("recipient_email", recipientEmail);
    const res = await fetch(`${API}/api/scheduler/send-now`, { method: "POST", body: fd });
    const d = await res.json();
    setEmailStatus(d.success ? "✅ Report sent!" : `❌ ${d.detail}`); setSendNowLoading(false);
  };

  const generateReport = async () => {
    setReportLoading(true); setReportHtml("");
    const res = await fetch(`${API}/api/report/generate`, { method: "POST" });
    const d = await res.json(); setReportHtml(d.html); setReportLoading(false);
  };

  const emailGeneratedReport = async () => {
    if (!emailReport || !reportHtml) return;
    const res = await fetch(`${API}/api/report/email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recipient_email: emailReport, html_content: reportHtml })
    });
    const d = await res.json();
    setEmailStatus(d.success ? "✅ Report emailed!" : `❌ ${d.detail}`);
  };

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      <h2 style={{ fontSize: 19, fontWeight: 700, color: C.text, letterSpacing: "-0.02em" }}>Settings & Reports</h2>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
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
            <div>
              <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>Daily Time</label>
              <Input type="time" value={scheduleTime} onChange={e => setScheduleTime(e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 6 }}>Recipient Email</label>
              <Input value={recipientEmail} onChange={e => setRecipientEmail(e.target.value)} placeholder="manager@company.com" />
            </div>
            <label style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13, cursor: "pointer", color: C.text }}>
              <input type="checkbox" checked={schedEnabled} onChange={e => setSchedEnabled(e.target.checked)} />
              Enable daily email report
            </label>
            <div style={{ display: "flex", gap: 8 }}>
              <Btn onClick={updateSchedule} icon={RefreshCw}>Update</Btn>
              <Btn variant="secondary" onClick={sendNow} disabled={sendNowLoading || !recipientEmail} icon={Mail}>
                {sendNowLoading ? <><Spinner size={13} /> Sending…</> : "Send Now"}
              </Btn>
            </div>
            {emailStatus && <p style={{ fontSize: 12, color: C.green }}>{emailStatus}</p>}
          </div>
        </Card>
      </div>
      <Card>
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
              <a href={`data:text/html;charset=utf-8,${encodeURIComponent(reportHtml)}`} download="Executive_Sales_Report.html">
                <Btn icon={Download}>Download HTML</Btn>
              </a>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <Input value={emailReport} onChange={e => setEmailReport(e.target.value)}
                placeholder="Email report to..." style={{ maxWidth: 300 }} />
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
function SchemaMapperTab() {
  useTheme();
  const [databases, setDatabases] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [srcDb, setSrcDb] = useState("");
  const [srcTables, setSrcTables] = useState([]);
  const [srcTable, setSrcTable] = useState("");
  const [srcCols, setSrcCols] = useState([]);
  const [srcCol, setSrcCol] = useState("");
  const [tgtDb, setTgtDb] = useState("");
  const [tgtTables, setTgtTables] = useState([]);
  const [tgtTable, setTgtTable] = useState("");
  const [tgtCols, setTgtCols] = useState([]);
  const [tgtCol, setTgtCol] = useState("");
  const [relType, setRelType] = useState("Many-to-One");
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("");
  const [isMaximized, setIsMaximized] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [showColumns, setShowColumns] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/databases`).then(r => r.json()).then(d => {
      setDatabases(d.databases);
      if (d.databases[0]) { setSrcDb(d.databases[0]); setTgtDb(d.databases[0]); }
    }).catch(() => { });
    loadRelationships();
  }, []);

  const loadRelationships = () => {
    fetch(`${API}/api/schema/relationships`).then(r => r.json())
      .then(d => setRelationships(d.relationships || [])).catch(() => { });
  };

  useEffect(() => {
    if (!srcDb) return;
    fetch(`${API}/api/tables?db_filename=${srcDb}`).then(r => r.json()).then(d => {
      setSrcTables(d.tables); if (d.tables[0]) setSrcTable(d.tables[0]);
    }).catch(() => { });
  }, [srcDb]);

  useEffect(() => {
    if (!tgtDb) return;
    fetch(`${API}/api/tables?db_filename=${tgtDb}`).then(r => r.json()).then(d => {
      setTgtTables(d.tables); if (d.tables[0]) setTgtTable(d.tables[0]);
    }).catch(() => { });
  }, [tgtDb]);

  useEffect(() => {
    if (!srcTable) return;
    fetch(`${API}/api/tables/${srcTable}/columns?db_filename=${srcDb}`).then(r => r.json()).then(d => {
      setSrcCols(d.columns); if (d.columns[0]) setSrcCol(d.columns[0].name);
    }).catch(() => { });
  }, [srcTable, srcDb]);

  useEffect(() => {
    if (!tgtTable) return;
    fetch(`${API}/api/tables/${tgtTable}/columns?db_filename=${tgtDb}`).then(r => r.json()).then(d => {
      setTgtCols(d.columns); if (d.columns[0]) setTgtCol(d.columns[0].name);
    }).catch(() => { });
  }, [tgtTable, tgtDb]);

  const addRelationship = async () => {
    if (!srcTable || !srcCol || !tgtTable || !tgtCol) return;
    setSaving(true);
    const res = await fetch(`${API}/api/schema/relationships`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_db: srcDb, source_table: srcTable, source_column: srcCol,
        target_db: tgtDb, target_table: tgtTable, target_column: tgtCol, type: relType
      })
    });
    if (res.ok) { setStatus("✅ Relationship added!"); loadRelationships(); }
    else setStatus("❌ Failed to add relationship.");
    setSaving(false); setTimeout(() => setStatus(""), 3000);
  };

  const clearAll = async () => {
    await fetch(`${API}/api/schema/relationships`, { method: "DELETE" });
    setRelationships([]); setStatus("✅ All cleared."); setTimeout(() => setStatus(""), 3000);
  };

  const deleteRelationship = async (index) => {
    const res = await fetch(`${API}/api/schema/relationships/${index}`, { method: "DELETE" });
    if (res.ok) { loadRelationships(); setStatus("✅ Removed."); setTimeout(() => setStatus(""), 2000); }
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

    Object.values(newTables).forEach(async (t) => {
      const key = `${t.db}.${t.table}`;
      if (!mapColumns[key]) {
        const res = await fetch(`${API}/api/tables/${t.table}/columns?db_filename=${t.db}`);
        const d = await res.json();
        setMapColumns(p => ({ ...p, [key]: d.columns }));
      }
    });
  }, [relationships]);

  const allTables = {};
  relationships.forEach(rel => {
    const sk = `${rel.source_db}.${rel.source_table}`;
    const tk = `${rel.target_db}.${rel.target_table}`;
    if (!allTables[sk]) allTables[sk] = { db: rel.source_db, table: rel.source_table, cols: mapColumns[sk] || [] };
    if (!allTables[tk]) allTables[tk] = { db: rel.target_db, table: rel.target_table, cols: mapColumns[tk] || [] };
  });

  const { svgW, svgH, positions } = useMemo(() => {
    const keys = Object.keys(allTables);
    if (keys.length === 0) return { svgW: 100, svgH: 100, positions: {} };
    
    const COL_WIDTH = 220, ROW_H = 24, HEAD_H = 46, GAP_X = 160, GAP_Y = 30;
    const pos = {};

    // Find the "fact" table (has the most relationships as source)
    const srcCounts = {};
    relationships.forEach(r => {
      const k = `${r.source_db}.${r.source_table}`;
      srcCounts[k] = (srcCounts[k] || 0) + 1;
    });
    const factKey = Object.entries(srcCounts).sort((a,b) => b[1]-a[1])[0]?.[0] || keys[0];
    const dimKeys = keys.filter(k => k !== factKey);

    // Fact table on the left, dimension tables stacked on right
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
  // Re-compute fact key for render (same logic as useMemo)
  const srcCountsRender = {};
  relationships.forEach(r => { const k = `${r.source_db}.${r.source_table}`; srcCountsRender[k] = (srcCountsRender[k]||0)+1; });
  const factKeyRender = Object.entries(srcCountsRender).sort((a,b)=>b[1]-a[1])[0]?.[0] || tableKeys[0];

  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h2 style={{ fontSize: 19, fontWeight: 700, color: C.text, letterSpacing: "-0.02em" }}>Star Schema & Relationship Mapper</h2>
          <p style={{ color: C.muted, fontSize: 12, marginTop: 3 }}>Define FK/PK connections across tables to build your enterprise star schema.</p>
        </div>
        {relationships.length > 0 && (
          <div style={{ display: 'flex', gap: 8 }}>
            <Btn variant="danger" onClick={clearAll} icon={Unlink}>Clear All</Btn>
          </div>
        )}
      </div>

      <Card>
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16, display: "flex", gap: 8, alignItems: "center", color: C.text }}>
          <Link size={15} color={C.accent} /> Define New Relationship
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 16, alignItems: "start" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: C.yellow }}>SOURCE (Foreign Key)</div>
            {[["Database", srcDb, setSrcDb, databases.map(d => ({ v: d, l: d }))],
            ["Table", srcTable, setSrcTable, srcTables.map(t => ({ v: t, l: t }))],
            ["Column (FK)", srcCol, setSrcCol, srcCols.map(c => ({ v: c.name, l: c.name }))]
            ].map(([lbl, val, setter, opts]) => (
              <div key={lbl}>
                <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 4 }}>{lbl}</label>
                <Select value={val} onChange={e => setter(e.target.value)}>
                  {opts.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
                </Select>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, paddingTop: 28 }}>
            <ArrowRight size={24} color={C.accent} />
            <Select value={relType} onChange={e => setRelType(e.target.value)} style={{ width: 140, fontSize: 11 }}>
              {["Many-to-One", "One-to-One", "Many-to-Many"].map(t => <option key={t} value={t}>{t}</option>)}
            </Select>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: C.green }}>TARGET (Primary Key)</div>
            {[["Database", tgtDb, setTgtDb, databases.map(d => ({ v: d, l: d }))],
            ["Table", tgtTable, setTgtTable, tgtTables.map(t => ({ v: t, l: t }))],
            ["Column (PK)", tgtCol, setTgtCol, tgtCols.map(c => ({ v: c.name, l: c.name }))]
            ].map(([lbl, val, setter, opts]) => (
              <div key={lbl}>
                <label style={{ fontSize: 12, color: C.muted, display: "block", marginBottom: 4 }}>{lbl}</label>
                <Select value={val} onChange={e => setter(e.target.value)}>
                  {opts.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
                </Select>
              </div>
            ))}
          </div>
        </div>
        <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 12 }}>
          <Btn onClick={addRelationship} disabled={saving} icon={Plus}>
            {saving ? <><Spinner size={13} /> Adding…</> : "Add Relationship"}
          </Btn>
          {status && <span style={{ fontSize: 13, color: C.green }}>{status}</span>}
        </div>
      </Card>

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
                <button onClick={() => deleteRelationship(i)}
                  title="Remove this relationship"
                  style={{
                    marginLeft: 8, padding: "4px 8px", borderRadius: 6, border: `1px solid ${C.red}30`,
                    background: C.redDim, color: C.red, cursor: "pointer", fontSize: 11, fontWeight: 600,
                    display: "flex", alignItems: "center", gap: 4, flexShrink: 0, transition: "all .15s"
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = C.red; e.currentTarget.style.color = "#fff"; }}
                  onMouseLeave={e => { e.currentTarget.style.background = C.redDim; e.currentTarget.style.color = C.red; }}>
                  <Trash2 size={11} /> Remove
                </button>
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
              {/* LAYER 1: RELATIONSHIP LINES (BOTTOM) */}
              {relationships.map((rel, i) => {
                const sk = `${rel.source_db}.${rel.source_table}`, tk = `${rel.target_db}.${rel.target_table}`;
                const sp = positions[sk], tp = positions[tk];
                if (!sp || !tp) return null;
                const sColIdx = allTables[sk].cols.findIndex(c => c.name === rel.source_column);
                const tColIdx = allTables[tk].cols.findIndex(c => c.name === rel.target_column);
                const x1 = sp.x + COL_WIDTH, y1 = sp.y + (showColumns ? HEAD_H + (sColIdx >= 0 ? sColIdx * ROW_H + ROW_H/2 : HEAD_H/2) : HEAD_H/2);
                const x2 = tp.x, y2 = tp.y + (showColumns ? HEAD_H + (tColIdx >= 0 ? tColIdx * ROW_H + ROW_H/2 : HEAD_H/2) : HEAD_H/2);
                const mx = (x1 + x2) / 2;
                return (
                  <path key={i} d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`}
                    stroke={C.accent} strokeWidth={2} fill="none" opacity={0.4} />
                );
              })}

              {/* LAYER 2: TABLES (MIDDLE) */}
              {Object.keys(allTables).map(key => {
                const t = allTables[key], p = positions[key];
                const h = HEAD_H + (showColumns ? t.cols.length * ROW_H : 0);
                const isFact = key === factKeyRender;
                const hdrColor = isFact ? C.yellowDim : C.accentDim;
                const hdrTextColor = isFact ? C.yellow : C.accent;
                return (
                  <g key={key}>
                    <rect x={p.x} y={p.y} width={COL_WIDTH} height={h} rx={8} fill={C.cardRaised} stroke={isFact ? C.yellow+'44' : C.border} strokeWidth={isFact ? 1.5 : 1} />
                    <rect x={p.x} y={p.y} width={COL_WIDTH} height={HEAD_H} rx={8} fill={hdrColor} />
                    <rect x={p.x} y={p.y + HEAD_H - 8} width={COL_WIDTH} height={8} fill={hdrColor} />
                    {isFact && <rect x={p.x + COL_WIDTH - 46} y={p.y + 6} width={40} height={14} rx={7} fill={C.yellow+'22'} />}
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

              {/* LAYER 3: BADGES & DOTS (TOP) */}
              {relationships.map((rel, i) => {
                const sk = `${rel.source_db}.${rel.source_table}`, tk = `${rel.target_db}.${rel.target_table}`;
                const sp = positions[sk], tp = positions[tk];
                if (!sp || !tp) return null;
                const sColIdx = allTables[sk].cols.findIndex(c => c.name === rel.source_column);
                const tColIdx = allTables[tk].cols.findIndex(c => c.name === rel.target_column);
                const x1 = sp.x + COL_WIDTH, y1 = sp.y + (showColumns ? HEAD_H + (sColIdx >= 0 ? sColIdx * ROW_H + ROW_H/2 : HEAD_H/2) : HEAD_H/2);
                const x2 = tp.x, y2 = tp.y + (showColumns ? HEAD_H + (tColIdx >= 0 ? tColIdx * ROW_H + ROW_H/2 : HEAD_H/2) : HEAD_H/2);
                // Place badge in the horizontal gap center
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
          <GitFork size={40} style={{ margin: "0 auto 16px", display: "block", opacity: .3 }} />
          <p style={{ fontSize: 15 }}>No relationships defined yet.</p>
          <p style={{ fontSize: 13, marginTop: 6 }}>Use the form above to connect tables across your databases.</p>
        </div>
      )}
    </div>
  );
}

// ─── HYBRID SEARCH TAB ────────────────────────────────────────
function HybridSearchTab() {
  useTheme();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [showSql, setShowSql] = useState(false);

  const EXAMPLES = [
    "What are the top 5 customers by revenue?",
    "Show discount policy for orders over $1000",
    "Which products have the highest profit margin?",
    "What is the refund policy for premium customers?",
  ];

  const search = async (q = query) => {
    if (!q.trim()) return;
    setLoading(true); setError(""); setResult(null); setShowSql(false);
    try {
      const res = await fetch(`${API}/api/hybrid-search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const sqlOk   = result?.sql?.success && result?.sql?.rows?.length > 0;
  const ragOk   = result?.rag?.success && result?.rag?.chunks?.length > 0;

  return (
    <div style={{ padding: 28, display: "flex", flexDirection: "column", gap: 20, height: "100%", overflowY: "auto" }}>
      {/* Header */}
      <div>
        <h2 style={{ fontSize: 22, fontWeight: 800, color: C.text, letterSpacing: "-0.03em", marginBottom: 4 }}>
          ⚡ Hybrid Search
        </h2>
        <p style={{ fontSize: 13, color: C.muted }}>
          Simultaneously queries the SQL database <em>and</em> policy documents — results appear side-by-side.
        </p>
      </div>

      {/* Search Bar */}
      <Card style={{ padding: 16 }}>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input
            value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && search()}
            placeholder="Ask anything — e.g. 'top customers by profit'"
            style={{
              flex: 1, padding: "11px 16px", borderRadius: 10,
              background: C.surface, border: `1px solid ${C.border}`,
              color: C.text, fontSize: 14, outline: "none",
              fontFamily: "'Plus Jakarta Sans',sans-serif",
              transition: "border-color .15s",
            }}
            onFocus={e => { e.currentTarget.style.borderColor = C.accent; }}
            onBlur={e => { e.currentTarget.style.borderColor = C.border; }}
          />
          <Btn onClick={() => search()} icon={Activity} disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </Btn>
        </div>
        {/* Example chips */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
          {EXAMPLES.map((ex, i) => (
            <button key={i} onClick={() => { setQuery(ex); search(ex); }}
              style={{
                padding: "4px 12px", borderRadius: 20,
                background: C.surface, border: `1px solid ${C.border}`,
                color: C.textSoft, fontSize: 11.5, cursor: "pointer",
                fontFamily: "'Plus Jakarta Sans',sans-serif", transition: "all .15s",
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = C.accent; e.currentTarget.style.color = C.accent; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.color = C.textSoft; }}
            >
              {ex}
            </button>
          ))}
        </div>
      </Card>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: "center", padding: 60, color: C.muted }}>
          <div style={{
            width: 36, height: 36, margin: "0 auto 14px",
            border: `3px solid ${C.border}`, borderTopColor: C.accent,
            borderRadius: "50%", animation: "spin 0.7s linear infinite"
          }} />
          <p style={{ fontSize: 14 }}>Running SQL query + RAG search in parallel…</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ padding: "12px 16px", background: `${C.red}15`, border: `1px solid ${C.red}30`, borderRadius: 10, color: C.red, fontSize: 13 }}>
          ⚠ {error}
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <>
          {/* AI Synthesis bar */}
          <Card style={{
            padding: "14px 20px",
            background: `linear-gradient(135deg, ${C.accentDim}, ${C.purpleDim || C.accentDim})`,
            border: `1px solid ${C.accent}30`,
          }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
              <span style={{ fontSize: 20, flexShrink: 0 }}>✨</span>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: C.accent, marginBottom: 4, fontFamily: "'IBM Plex Mono',monospace", letterSpacing: "0.08em" }}>AI SYNTHESIS</div>
                <p style={{ fontSize: 13.5, color: C.text, lineHeight: 1.65, margin: 0 }}>{result.synthesis}</p>
              </div>
            </div>
          </Card>

          {/* Two-panel layout */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, alignItems: "start" }}>

            {/* SQL Panel */}
            <Card style={{ padding: 0, overflow: "hidden" }}>
              <div style={{
                padding: "12px 16px", borderBottom: `1px solid ${C.border}`,
                display: "flex", alignItems: "center", justifyContent: "space-between",
                background: `${C.accentDim}`,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Database size={14} color={C.accent} />
                  <span style={{ fontSize: 13, fontWeight: 700, color: C.accent }}>SQL Records</span>
                  {sqlOk && (
                    <span style={{
                      fontSize: 10, background: C.accent + "22", color: C.accent,
                      border: `1px solid ${C.accent}40`, borderRadius: 20, padding: "2px 8px", fontWeight: 700
                    }}>
                      {result.sql.total_rows} rows
                    </span>
                  )}
                </div>
                {result.sql.sql && (
                  <button onClick={() => setShowSql(s => !s)} style={{
                    background: "none", border: `1px solid ${C.border}`, borderRadius: 6,
                    color: C.muted, cursor: "pointer", padding: "3px 8px", fontSize: 10,
                    fontFamily: "'IBM Plex Mono',monospace",
                  }}>
                    {showSql ? "Hide SQL" : "Show SQL"}
                  </button>
                )}
              </div>

              {showSql && result.sql.sql && (
                <div style={{
                  padding: "10px 16px", background: C.bg,
                  borderBottom: `1px solid ${C.border}`,
                  fontFamily: "'IBM Plex Mono',monospace", fontSize: 11.5,
                  color: C.accent, lineHeight: 1.7, overflowX: "auto",
                }}>
                  {result.sql.sql}
                </div>
              )}

              {result.sql.error && (
                <div style={{ padding: 16, color: C.red, fontSize: 12 }}>⚠ {result.sql.error}</div>
              )}

              {sqlOk ? (
                <div style={{ overflowX: "auto", maxHeight: 420 }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                    <thead>
                      <tr style={{ background: C.surface, position: "sticky", top: 0 }}>
                        {result.sql.columns.map(col => (
                          <th key={col} style={{
                            padding: "8px 12px", textAlign: "left",
                            color: C.muted, fontWeight: 600, fontSize: 11,
                            borderBottom: `1px solid ${C.border}`,
                            fontFamily: "'IBM Plex Mono',monospace",
                            letterSpacing: "0.04em", whiteSpace: "nowrap",
                          }}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.sql.rows.map((row, ri) => (
                        <tr key={ri} style={{ borderBottom: `1px solid ${C.borderSoft}` }}
                          onMouseEnter={e => e.currentTarget.style.background = C.hover}
                          onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                        >
                          {result.sql.columns.map(col => (
                            <td key={col} style={{
                              padding: "7px 12px", color: C.text, whiteSpace: "nowrap",
                            }}>
                              {typeof row[col] === "number"
                                ? (Number.isInteger(row[col]) ? row[col].toLocaleString() : row[col].toFixed(2))
                                : String(row[col] ?? "")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : !result.sql.error && (
                <div style={{ padding: 32, textAlign: "center", color: C.muted, fontSize: 13 }}>
                  No matching database records found.
                </div>
              )}
            </Card>

            {/* RAG Panel */}
            <Card style={{ padding: 0, overflow: "hidden" }}>
              <div style={{
                padding: "12px 16px", borderBottom: `1px solid ${C.border}`,
                display: "flex", alignItems: "center", gap: 8,
                background: `${C.yellowDim || C.accentDim}`,
              }}>
                <BookOpen size={14} color={C.yellow || C.accent} />
                <span style={{ fontSize: 13, fontWeight: 700, color: C.yellow || C.accent }}>Document Context</span>
                {ragOk && (
                  <span style={{
                    fontSize: 10, background: (C.yellow || C.accent) + "22",
                    color: C.yellow || C.accent, border: `1px solid ${(C.yellow || C.accent)}40`,
                    borderRadius: 20, padding: "2px 8px", fontWeight: 700
                  }}>
                    {result.rag.chunks.length} chunks
                  </span>
                )}
              </div>

              {result.rag.error && (
                <div style={{ padding: 16, color: C.red, fontSize: 12 }}>⚠ {result.rag.error}</div>
              )}

              {ragOk ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 0, maxHeight: 460, overflowY: "auto" }}>
                  {result.rag.chunks.map((chunk, i) => (
                    <div key={i} style={{
                      padding: "12px 16px",
                      borderBottom: `1px solid ${C.borderSoft}`,
                      transition: "background .15s",
                    }}
                      onMouseEnter={e => e.currentTarget.style.background = C.hover}
                      onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                    >
                      <div style={{
                        display: "inline-block", fontSize: 9, fontWeight: 700,
                        color: C.yellow || C.accent, background: (C.yellow || C.accent) + "12",
                        border: `1px solid ${(C.yellow || C.accent)}30`,
                        borderRadius: 6, padding: "2px 8px", marginBottom: 6,
                        fontFamily: "'IBM Plex Mono',monospace", letterSpacing: "0.06em",
                      }}>
                        📄 {chunk.source}
                      </div>
                      <p style={{ fontSize: 12.5, color: C.text, lineHeight: 1.7, margin: 0 }}>
                        {chunk.content}
                      </p>
                    </div>
                  ))}
                </div>
              ) : !result.rag.error && (
                <div style={{ padding: 32, textAlign: "center", color: C.muted, fontSize: 13 }}>
                  No relevant policy documents found.
                </div>
              )}
            </Card>

          </div>
        </>
      )}

      {/* Empty state */}
      {!result && !loading && !error && (
        <div style={{ textAlign: "center", padding: 80, color: C.muted }}>
          <Activity size={44} style={{ margin: "0 auto 16px", display: "block", opacity: .25 }} />
          <p style={{ fontSize: 15, fontWeight: 600 }}>Hybrid Search ready</p>
          <p style={{ fontSize: 13, marginTop: 6 }}>Type a question above to query both the database and your documents simultaneously.</p>
        </div>
      )}
    </div>
  );
}

const TABS = [
  { id: "chat",      label: "AI Assistant",  icon: MessageSquare },
  { id: "hybrid",    label: "Hybrid Search", icon: Activity },
  { id: "data",      label: "Data Explorer", icon: Database },
  { id: "dashboard", label: "Dashboard",     icon: BarChart2 },
  { id: "policy",    label: "Policy Hub",    icon: BookOpen },
  { id: "schema",    label: "Schema Mapper", icon: GitFork },
  { id: "settings",  label: "Settings",      icon: Settings },
];

// ─── ROUTER ROOT ──────────────────────────────────────────────
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/app" element={<MainApp />} />
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

  window.__theme = theme;
  const toggle = () => setTheme(t => t === "dark" ? "light" : "dark");

  useEffect(() => {
    fetch(`${API}/api/health`).then(r => r.json()).then(() => {
      setApiOk(true);
      fetch(`${API}/api/databases`).then(r => r.json()).then(db => setActiveDb(db.active || "")).catch(() => { });
    }).catch(() => setApiOk(false));
  }, []);

  return (
    <ThemeCtx.Provider value={{ theme, toggle }}>
      <style>{makeStyle(theme)}</style>
      <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>

        {/* Sidebar */}
        <div style={{
          width: 230, flexShrink: 0, background: C.sidebarBg,
          borderRight: `1px solid ${C.borderSoft}`, display: "flex", flexDirection: "column", position: "relative"
        }}>
          <div style={{
            position: "absolute", top: 0, left: 0, right: 0, height: 1,
            background: `linear-gradient(90deg,transparent 10%,${C.accent}60,transparent 90%)`
          }} />

          {/* Logo */}
          <div style={{ padding: "22px 18px 18px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{
                  width: 34, height: 34, borderRadius: 10,
                  background: `linear-gradient(135deg,${C.accent},${C.purple})`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  boxShadow: `0 4px 12px ${C.accentGlow}`
                }}>
                  <Bot size={16} color="#fff" />
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 800, color: C.text, letterSpacing: "-0.02em" }}>DataAnalyst</div>
                  <div style={{ fontSize: 9, color: C.muted, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", marginTop: 1 }}>Enterprise AI</div>
                </div>
              </div>
              {/* Home button */}
              <button onClick={() => navigate("/")} title="Back to Home"
                style={{
                  background: "none", border: `1px solid ${C.border}`, borderRadius: 7,
                  color: C.muted, cursor: "pointer", padding: "4px 8px", fontSize: 11,
                  fontFamily: "'Plus Jakarta Sans',sans-serif", transition: "all .15s",
                  display: "flex", alignItems: "center", gap: 4,
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = C.accent; e.currentTarget.style.color = C.accent; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.color = C.muted; }}
              >
                ← Home
              </button>
            </div>
          </div>

          <Divider style={{ margin: "0 18px 10px" }} />

          {/* Nav */}
          <nav style={{ flex: 1, padding: "4px 10px", display: "flex", flexDirection: "column", gap: 2, overflowY: "auto" }}>
            {TABS.map(tab => {
              const Icon = tab.icon, active = activeTab === tab.id;
              return (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                  style={{
                    display: "flex", alignItems: "center", gap: 10, padding: "9px 12px", borderRadius: 9,
                    border: "none", background: active ? C.accentDim : "transparent",
                    color: active ? C.accent : C.textSoft, fontSize: 13, fontWeight: active ? 600 : 500,
                    cursor: "pointer", textAlign: "left", transition: "all .15s",
                    fontFamily: "'Plus Jakarta Sans',sans-serif",
                    boxShadow: active ? `inset 0 0 0 1px ${C.accent}30` : "none", position: "relative"
                  }}
                  onMouseEnter={e => { if (!active) { e.currentTarget.style.background = C.hover; e.currentTarget.style.color = C.text; } }}
                  onMouseLeave={e => { if (!active) { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = C.textSoft; } }}>
                  {active && <div style={{
                    position: "absolute", left: 0, top: "25%", bottom: "25%", width: 2,
                    background: C.accent, borderRadius: "0 2px 2px 0"
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
                marginBottom: 10, transition: "all .15s"
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
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", background: C.bg }}>
          {apiOk === false && (
            <div style={{
              background: `${C.red}18`, borderBottom: `1px solid ${C.red}30`,
              padding: "10px 20px", display: "flex", alignItems: "center", gap: 10, flexShrink: 0
            }}>
              <AlertCircle size={14} color={C.red} />
              <span style={{ fontSize: 12, color: C.red }}>
                API offline — run: <code style={{
                  marginLeft: 8, fontFamily: "'IBM Plex Mono',monospace",
                  background: C.redDim, padding: "2px 8px", borderRadius: 4, fontSize: 11
                }}>
                  uvicorn api:app --reload --port 8000
                </code>
              </span>
            </div>
          )}
          {activeTab === "chat"     && <ChatTab />}
          {activeTab === "hybrid"   && <HybridSearchTab />}
          {activeTab === "data"     && <DataExplorerTab activeDb={activeDb} />}
          {activeTab === "dashboard"&& <DashboardTab />}
          {activeTab === "policy"   && <PolicyTab />}
          {activeTab === "schema"   && <SchemaMapperTab />}
          {activeTab === "settings" && <SettingsTab activeDb={activeDb} setActiveDb={setActiveDb} />}
        </div>
      </div>
    </ThemeCtx.Provider>
  );
}