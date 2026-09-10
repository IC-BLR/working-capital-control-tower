import React, { useState, useRef, useEffect } from 'react';
import { AR_API_BASE } from '../config';
// ─── Suggestion chips ─────────────────────────────────────────────────────────
const SUGGESTION_CHIPS = [
  'What will be the forecast after 60 days?',
  'Show 90 day forecast in recession scenario',
  'Show high risk partners',
  'What is the total outstanding amount?',
];

function formatTimestamp(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Streams text into a state setter character by character
function streamText(fullText, setter, onDone) {
  let i = 0;
  setter('');
  const interval = setInterval(() => {
    i++;
    setter(fullText.slice(0, i));
    if (i >= fullText.length) {
      clearInterval(interval);
      if (onDone) onDone();
    }
  }, 18);
  return interval;
}

// Converts **bold** markdown to <strong> elements
function renderMarkdown(text) {
  if (!text) return null;
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

// ─── Single metric card ───────────────────────────────────────────────────────
function MetricCard({ label, value, highlight }) {
  return (
    <div className="glass-card p-4 flex flex-col gap-1 flex-1 min-w-[150px]">
      <p className="stat-label">{label}</p>
      <p
        className="stat-value mt-1"
        style={{ color: highlight ? '#dc2626' : undefined }}
      >
        {value}
      </p>
    </div>
  );
}

// ─── Bot message ──────────────────────────────────────────────────────────────
function BotMessage({ msg, isStreaming }) {
  const d = msg.analysisData;
  const hasMetrics =
    d &&
    (d.projectedBalance !== undefined ||
      d.overdueAmount !== undefined ||
      d.outstandingAmount !== undefined);

  const renderText = (text) =>
    text.split('\n').map((line, i, arr) => (
      <span key={i}>
        {renderMarkdown(line)}
        {i < arr.length - 1 && <br />}
      </span>
    ));

  return (
    <div className="flex flex-col gap-3 max-w-4xl w-full">
      {/* Question echo */}
      {msg.question && (
        <p className="text-sm text-slate-700">
          <span className="font-semibold text-slate-500">Question: </span>
          {msg.question}
        </p>
      )}

      {/* Metric cards */}
      {hasMetrics && (
        <div className="glass-card p-4">
          <div className="flex flex-wrap gap-3">
            {d.projectedBalance !== undefined && (
              <MetricCard
                label={`Projected Balance (${d.days || 60} days)`}
                value={d.projectedBalance}
              />
            )}
            {d.overdueAmount !== undefined && (
              <MetricCard label="Overdue Amount" value={d.overdueAmount} highlight />
            )}
            {d.outstandingAmount !== undefined && (
              <MetricCard label="Outstanding Amount" value={d.outstandingAmount} />
            )}
            {d.whatIfDelta !== undefined && (
              <MetricCard label="What-if Delta vs Baseline" value={d.whatIfDelta} />
            )}
            {d.dominantAgingBucket !== undefined && (
              <MetricCard label="Dominant Aging Bucket" value={d.dominantAgingBucket} />
            )}
            {d.collectionRate !== undefined && (
              <MetricCard label="Collection Rate" value={d.collectionRate} />
            )}
          </div>
        </div>
      )}

      {/* Text response */}
      <div
        className={
          hasMetrics
            ? 'text-sm text-slate-700 leading-relaxed'
            : 'glass-card p-4 text-sm text-slate-700 leading-relaxed'
        }
      >
        {renderText(msg.text)}
        {/* Blinking cursor while this message is streaming */}
        {isStreaming && (
          <span
            style={{
              display: 'inline-block',
              width: 2,
              height: '1em',
              background: '#047857',
              marginLeft: 2,
              verticalAlign: 'text-bottom',
              animation: 'cursor-blink 0.7s steps(1) infinite',
            }}
          />
        )}
      </div>

      <span className="text-xs text-slate-400">{formatTimestamp(msg.timestamp)}</span>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function AIAssistant() {
  const [messages, setMessages]       = useState([]);
  const [input, setInput]             = useState('');
  const [loading, setLoading]         = useState(false);
  const [isStreaming, setIsStreaming]  = useState(false);
  const [streamingId, setStreamingId] = useState(null);
  const messagesEndRef                 = useRef(null);
  const textareaRef                    = useRef(null);
  const streamRef                      = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Clean up stream interval on unmount
  useEffect(() => {
    return () => { if (streamRef.current) clearInterval(streamRef.current); };
  }, []);

  const autoResize = (el) => {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 140) + 'px';
  };

  const sendQuery = async (queryText) => {
    if (!queryText.trim() || loading || isStreaming) return;

    const userMsg = {
      id: Date.now(),
      type: 'user',
      text: queryText,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    setLoading(true);

    try {
      const res = await fetch(`${AR_API_BASE}/chatbot/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: queryText,
          conversationHistory: messages.map((m) => ({
            role: m.type === 'user' ? 'user' : 'assistant',
            content: m.text,
          })),
        }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();

      const fullText = data.response || 'No response received';
      const botMsgId = Date.now() + 1;
      const botMsg = {
        id: botMsgId,
        type: 'bot',
        question: queryText,
        text: '',
        analysisData: data.analysisData || null,
        timestamp: new Date(),
      };

    setTimeout(() => {
      setMessages((prev) => [...prev, { ...botMsg, text: fullText }]);
      setLoading(false);
    }, 600); // 600ms minimum dot display time
        } catch (err) {
          setLoading(false);
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now() + 2,
              type: 'bot',
              text: `Unable to reach the server. Please check the backend and API configuration.\n\nError: ${err.message}`,
              timestamp: new Date(),
            },
          ]);
        }
      };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendQuery(input);
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="space-y-6" data-testid="ai-assistant-page">

      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">AI Assistant</h1>
          <p className="text-slate-500 mt-1">
            Natural-language forecasting assistant powered by existing Forecast logic
          </p>
        </div>
      </div>

      {/* ── Info notice ── */}
      <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-100 rounded-full text-xs font-medium text-blue-700">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
        </svg>
        Uses the same Forecast API, calculations, and portfolio data already used by the Forecast tab
      </div>

      {/* ── Suggestion chips ── */}
      <div className="flex flex-wrap gap-2">
        {SUGGESTION_CHIPS.map((chip) => (
          <button
            key={chip}
            onClick={() => sendQuery(chip)}
            className="px-3 py-1.5 rounded-full border border-slate-200 bg-white text-slate-500 text-xs font-medium hover:border-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 transition-colors cursor-pointer"
          >
            {chip}
          </button>
        ))}
      </div>

      {/* ── Chat panel ── */}
      <div className="glass-card flex flex-col" style={{ height: '62vh', minHeight: '480px' }}>

        {/* Messages scroll area */}
        <div
          className="flex-1 overflow-y-auto p-6 flex flex-col gap-6"
          style={{ scrollbarWidth: 'thin', scrollbarColor: '#e2e8f0 transparent' }}
        >
          {/* Empty state */}
          {isEmpty && (
            <div className="flex-1 flex flex-col items-center justify-center gap-4 py-16 text-center">
              <div className="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#047857" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
              </div>
              <div>
                <p className="font-semibold text-slate-800 text-base">Ask the AI Assistant</p>
                <p className="text-slate-500 text-sm mt-1 max-w-xs">
                  Pick a suggestion above or type your own forecasting question below
                </p>
              </div>
            </div>
          )}

          {/* Message list */}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.type === 'user' ? (
                <div className="flex flex-col items-end gap-1 max-w-xl">
                  <div className="px-4 py-2.5 rounded-2xl rounded-tr-sm bg-emerald-700 text-white text-sm leading-relaxed whitespace-pre-wrap break-words">
                    {msg.text}
                  </div>
                  <span className="text-xs text-slate-400 pr-1">
                    {formatTimestamp(msg.timestamp)}
                  </span>
                </div>
              ) : (
                <BotMessage
                  msg={msg}
                  isStreaming={isStreaming && streamingId === msg.id}
                />
              )}
            </div>
          ))}

          {/* Typing indicator — dots while waiting for API */}
          {loading && (
            <div className="flex items-center gap-2">
              <div className="glass-card px-4 py-3 flex gap-1.5 items-center">
                {[0, 160, 320].map((delay) => (
                  <span
                    key={delay}
                    style={{
                      width: 7, height: 7, borderRadius: '50%',
                      background: '#047857', display: 'inline-block',
                      animation: 'ai-bounce 1.3s infinite ease-in-out',
                      animationDelay: `${delay}ms`,
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* ── Input bar ── */}
        <div className="border-t border-slate-100 p-4">
          <div className="input-glass flex items-end gap-3 rounded-xl px-4 py-3 focus-within:ring-2 focus-within:ring-emerald-500 focus-within:ring-offset-1 transition-shadow">
            <textarea
              ref={textareaRef}
              value={input}
              rows={1}
              disabled={loading || isStreaming}
              placeholder="Ask about forecasts, partners, cashflow… (Enter to send)"
              onChange={(e) => { setInput(e.target.value); autoResize(e.target); }}
              onKeyDown={handleKeyDown}
              className="flex-1 resize-none border-none outline-none bg-transparent text-sm text-slate-800 placeholder-slate-400 leading-relaxed disabled:opacity-60"
              style={{ maxHeight: 140, overflowY: 'auto' }}
            />
            <button
              onClick={() => sendQuery(input)}
              disabled={loading || isStreaming || !input.trim()}
              aria-label="Send message"
              className="flex items-center justify-center w-9 h-9 rounded-full bg-emerald-700 text-white flex-shrink-0 hover:bg-emerald-800 active:scale-95 disabled:bg-slate-300 disabled:cursor-not-allowed transition-all"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
          <p className="text-xs text-slate-400 mt-2 ml-1">
            Press <kbd className="px-1 py-0.5 bg-slate-100 border border-slate-200 rounded text-[10px] font-mono">Enter</kbd> to send
            &nbsp;·&nbsp;
            <kbd className="px-1 py-0.5 bg-slate-100 border border-slate-200 rounded text-[10px] font-mono">Shift+Enter</kbd> for new line
          </p>
        </div>
      </div>

      <style>{`
        @keyframes ai-bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40% { transform: translateY(-5px); opacity: 1; }
        }
        @keyframes cursor-blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}