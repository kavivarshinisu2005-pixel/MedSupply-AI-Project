
import React, { useEffect, useState, useCallback, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  CartesianGrid,
} from "recharts";
import "./style.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [inventory, setInventory] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [activePage, setActivePage] = useState("Dashboard");

  const refresh = useCallback(async () => {
    setLoading(true);
    setMessage("");

    try {
      const [dashboardRes, analysisRes, inventoryRes] =
        await Promise.all([
          fetch(`${API}/api/dashboard`),
          fetch(`${API}/api/analysis`),
          fetch(`${API}/api/inventory`),
        ]);

      if (!dashboardRes.ok || !analysisRes.ok || !inventoryRes.ok) {
        throw new Error("Backend API request failed. Check FastAPI server.");
      }

      const [dashboardData, analysisData, inventoryData] =
        await Promise.all([
          dashboardRes.json(),
          analysisRes.json(),
          inventoryRes.json(),
        ]);

      setDashboard(dashboardData);
      setAnalysis(analysisData);
      setInventory(Array.isArray(inventoryData) ? inventoryData : []);
    } catch (error) {
      setMessage(`Backend connection error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function upload(endpoint, file) {
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    setMessage(`Uploading ${file.name}...`);

    try {
      const response = await fetch(`${API}/api/upload/${endpoint}`, {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Upload failed");
      }

      setMessage(result.message || "Upload successful");
      await refresh();
    } catch (error) {
      setMessage(`Upload error: ${error.message}`);
    }
  }

  const navItems = [
    { name: "Dashboard", icon: "▦", description: "Overview" },
    { name: "Inventory Analysis", icon: "▤", description: "Stock intelligence" },
    { name: "Supplier Comparison", icon: "♧", description: "Supplier insights" },
    { name: "Purchase Planning", icon: "✧", description: "Purchase decisions" },
  ];

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo">✚</span>
          <div>
            <b>MedSupply AI</b>
            <small>Procurement intelligence</small>
          </div>
        </div>

        <div className="sidebar-label">WORKSPACE</div>

        <nav>
          {navItems.map((item) => (
            <div
              key={item.name}
              className={`nav ${activePage === item.name ? "active" : ""}`}
              onClick={() => setActivePage(item.name)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-copy">
                <b>{item.name}</b>
                <small>{item.description}</small>
              </span>
              {activePage === item.name && <span className="nav-indicator" />}
            </div>
          ))}
        </nav>

        <div className="sidebar-status">
          <span className="online-dot" />
          AI services enabled
        </div>

        <div className="sidebar-note">
          <span>✦ AI-assisted decisions</span>
          <small>Human approval required</small>
        </div>
      </aside>

      <main>
        <header className="top-header">
          <div>
            <p className="eyebrow">HOSPITAL OPERATIONS / PROCUREMENT</p>
            <h1>
              {activePage === "Dashboard"
                ? "Procurement Dashboard"
                : activePage}
            </h1>
            <p className="muted">
              Monitor stock levels and plan essential medical purchases.
            </p>
          </div>

          <div className="header-actions">
            <span className="system-status">
              <span className="online-dot" /> System online
            </span>
            <button className="refresh-button" onClick={refresh} disabled={loading}>
              {loading ? "Loading..." : "↻ Refresh"}
            </button>
          </div>
        </header>

        {message && (
          <div className="notice">
            <span>ℹ</span> {message}
            <button className="notice-close" onClick={() => setMessage("")}>×</button>
          </div>
        )}

        {loading && !dashboard && (
          <section className="panel loading-panel">
            <div className="loader" />
            Loading MedSupply AI data...
          </section>
        )}

        {activePage === "Dashboard" && (
          <Dashboard
            dashboard={dashboard}
            analysis={analysis}
            upload={upload}
          />
        )}

        {activePage === "Inventory Analysis" && (
          <InventoryAnalysis
            inventory={inventory}
            dashboard={dashboard}
            analysis={analysis}
          />
        )}

        {activePage === "Supplier Comparison" && (
          <SupplierComparison analysis={analysis} />
        )}

        {activePage === "Purchase Planning" && (
          <PurchasePlanning analysis={analysis} />
        )}

        <footer>
          MedSupply AI · Intelligent Medical Procurement · Human approval required
        </footer>
      </main>

      <Chatbot />
    </div>
  );
}

// DASHBOARD

function Dashboard({ dashboard, analysis, upload }) {
  const shortages = dashboard?.shortages || [];

  return (
    <div className="page-content">
      <section className="welcome-banner">
        <div>
          <span className="banner-label">SMART PROCUREMENT PLATFORM</span>
          <h2>Smarter decisions for better healthcare.</h2>
          <p>
            AI-powered inventory monitoring, supplier intelligence and
            procurement planning in one place.
          </p>
        </div>
        <div className="banner-art">
          <div className="banner-orbit orbit-one" />
          <div className="banner-orbit orbit-two" />
          <div className="banner-cross">✚</div>
          <span className="floating-symbol symbol-one">✦</span>
          <span className="floating-symbol symbol-two">＋</span>
        </div>
      </section>

      <section className="stats">
        <Stat
          label="Inventory items"
          value={dashboard?.total_items ?? "—"}
          icon="▦"
          color="mint"
          hint="Items monitored"
        />
        <Stat
          label="Shortage alerts"
          value={dashboard?.shortage_items ?? "—"}
          icon="⚠"
          color="orange"
          hint="Need attention"
        />
        <Stat
          label="Suppliers"
          value={dashboard?.total_suppliers ?? "—"}
          icon="♧"
          color="purple"
          hint="Available suppliers"
        />
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <span className="section-kicker">DOCUMENT CENTER</span>
            <h2>Upload procurement documents</h2>
            <p className="muted">
              Upload inventory, supplier quotations and procurement guidelines.
            </p>
          </div>
          <span className="panel-icon">⇧</span>
        </div>

        <div className="uploads">
          <Upload
            label="Inventory CSV"
            description="Stock and daily usage data"
            accept=".csv"
            onChange={(file) => upload("inventory", file)}
            icon="▤"
          />
          <Upload
            label="Supplier quotations CSV"
            description="Supplier prices and delivery"
            accept=".csv"
            onChange={(file) => upload("quotations", file)}
            icon="♧"
          />
          <Upload
            label="Procurement guidelines"
            description="TXT or Markdown documents"
            accept=".txt,.md"
            onChange={(file) => upload("guidelines", file)}
            icon="▧"
          />
        </div>
      </section>

      <section className="grid">
        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="section-kicker">INVENTORY MONITORING</span>
              <h2>Inventory shortage alerts</h2>
              <p className="muted">Items below minimum stock level</p>
            </div>
            <span className="tag">{dashboard?.shortage_items ?? 0} alerts</span>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Available</th>
                  <th>Minimum</th>
                  <th>Days left</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {shortages.map((item, index) => (
                  <tr key={item.item || index}>
                    <td><b>{item.item}</b></td>
                    <td>{item.current_stock}</td>
                    <td>{item.minimum_stock}</td>
                    <td>{item.estimated_days_remaining}</td>
                    <td><Status value={item.status} /></td>
                  </tr>
                ))}
                {!shortages.length && (
                  <tr><td colSpan="5">No shortage detected.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <span className="section-kicker">STOCK INTELLIGENCE</span>
              <h2>Stock overview</h2>
              <p className="muted">Current stock vs minimum threshold</p>
            </div>
            <span className="chart-icon">▥</span>
          </div>

          <div className="chart-area">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={shortages} barGap={7}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eaf0ed" />
                <XAxis dataKey="item" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} />
                <Tooltip />
                <Legend />
                <Bar dataKey="current_stock" name="Current stock" fill="#159b7b" radius={[6, 6, 0, 0]} />
                <Bar dataKey="minimum_stock" name="Minimum stock" fill="#e9ad45" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <Recommendations analysis={analysis} />
      <Guidelines analysis={analysis} />
    </div>
  );
}

// INVENTORY ANALYSIS

function InventoryAnalysis({ inventory, dashboard, analysis }) {
  const shortages = analysis?.shortages || dashboard?.shortages || [];

  return (
    <section className="panel page-content">
      <SectionHeading
        kicker="STOCK INTELLIGENCE"
        title="Inventory Analysis"
        subtitle="Stock monitoring, shortage detection and AI recommendations."
      />

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th>Current Stock</th>
              <th>Minimum Stock</th>
              <th>Shortage</th>
              <th>Days Remaining</th>
              <th>Status</th>
              <th>AI Priority</th>
            </tr>
          </thead>
          <tbody>
            {shortages.map((item, index) => (
              <tr key={item.item || index}>
                <td><b>{item.item}</b></td>
                <td>{item.current_stock}</td>
                <td>{item.minimum_stock}</td>
                <td>{item.shortage_quantity}</td>
                <td>{item.estimated_days_remaining}</td>
                <td><Status value={item.status} /></td>
                <td><Status value={item.ai_priority || "Not available"} /></td>
              </tr>
            ))}
            {!shortages.length && (
              <tr><td colSpan="7">No shortage data available.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <h2 className="subheading">AI Inventory Recommendations</h2>

      {shortages.map((item, index) => (
        <div className="recommendation-card" key={item.item || index}>
          <div className="recommendation-symbol">✦</div>
          <div>
            <h3>{item.item}</h3>
            <p><b>AI Priority:</b> {item.ai_priority || "Not available"}</p>
            <p><b>AI Reason:</b> {item.ai_reason || "No AI reason available."}</p>
            <p><b>Recommendation:</b> {item.ai_recommendation || "No recommendation available."}</p>
          </div>
        </div>
      ))}
    </section>
  );
}

// SUPPLIER COMPARISON

function SupplierComparison({ analysis }) {
  const items = analysis?.supplier_comparison || [];

  return (
    <section className="panel page-content">
      <SectionHeading
        kicker="SUPPLIER INTELLIGENCE"
        title="Supplier Comparison"
        subtitle="Compare supplier quotations, pricing and delivery speed."
      />

      {items.map((item, index) => (
        <div className="supplier-card" key={item.item || index}>
          <div className="supplier-card-heading">
            <div>
              <span className="section-kicker">PRODUCT COMPARISON</span>
              <h3>{item.item}</h3>
            </div>
            <span className="supplier-badge">AI evaluated</span>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Supplier</th>
                  <th>Unit Price</th>
                  <th>Delivery Days</th>
                  <th>Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {(item.suppliers || []).map((supplier, supplierIndex) => (
                  <tr key={supplier.supplier || supplierIndex}>
                    <td><b>{supplier.supplier}</b></td>
                    <td>₹{Number(supplier.unit_price).toFixed(2)}</td>
                    <td>{supplier.delivery_days} days</td>
                    <td>
                      {supplier.supplier === item.recommended_supplier
                        ? <span className="status recommended">Recommended</span>
                        : "—"}
                    </td>
                  </tr>
                ))}
                {!item.suppliers?.length && (
                  <tr><td colSpan="4">No supplier quotations available.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="recommendation-card compact">
            <div className="recommendation-symbol">✦</div>
            <div>
              <p><b>Recommended Supplier:</b> {item.recommended_supplier || "Quotation required"}</p>
              {item.ai_reason && <p><b>AI Reason:</b> {item.ai_reason}</p>}
            </div>
          </div>
        </div>
      ))}

      {!items.length && <p>No supplier comparison data available.</p>}
    </section>
  );
}

// PURCHASE PLANNING

function PurchasePlanning({ analysis }) {
  const plans = analysis?.purchase_plan || [];

  return (
    <section className="panel page-content">
      <SectionHeading
        kicker="PURCHASE INTELLIGENCE"
        title="Purchase Planning"
        subtitle="AI-assisted draft purchase recommendations."
      />

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th>Suggested Quantity</th>
              <th>Recommended Supplier</th>
              <th>Unit Price</th>
              <th>Estimated Cost</th>
              <th>Approval</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((item, index) => (
              <tr key={item.item || index}>
                <td><b>{item.item}</b></td>
                <td>{item.suggested_quantity}</td>
                <td>{item.supplier}</td>
                <td>
                  {item.unit_price == null
                    ? "—"
                    : `₹${Number(item.unit_price).toFixed(2)}`}
                </td>
                <td>
                  {item.estimated_cost == null
                    ? "Quotation required"
                    : `₹${Number(item.estimated_cost).toLocaleString("en-IN")}`}
                </td>
                <td>
                  <span className="status pending">
                    {item.approval_required ? "Pending approval" : "Review required"}
                  </span>
                </td>
              </tr>
            ))}
            {!plans.length && (
              <tr><td colSpan="6">No purchase plan available.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {plans.map((item, index) => (
        <div className="recommendation-card" key={item.item || index}>
          <div className="recommendation-symbol">✦</div>
          <div>
            <h3>{item.item}</h3>
            <p><b>AI Recommendation:</b> {item.ai_recommendation || item.note || "No recommendation available."}</p>
            {item.approval_required && (
              <p><b>Approval:</b> Authorized hospital approval is required.</p>
            )}
          </div>
        </div>
      ))}

      <p className="disclaimer">
        ⚠ These are draft recommendations, not purchase orders. Verify product
        specifications, supplier credentials, expiry dates and obtain authorized
        approval before procurement.
      </p>
    </section>
  );
}

// AI PURCHASE RECOMMENDATIONS

function Recommendations({ analysis }) {
  const plans = analysis?.purchase_plan || [];

  return (
    <section className="panel">
      <SectionHeading
        kicker="AI RECOMMENDATIONS"
        title="AI Purchase Recommendations"
        subtitle="Draft purchase plan generated from inventory shortages and quotations."
      />

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th>Suggested Quantity</th>
              <th>Supplier</th>
              <th>Estimated Cost</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((item, index) => (
              <tr key={item.item || index}>
                <td><b>{item.item}</b></td>
                <td>{item.suggested_quantity}</td>
                <td>{item.supplier}</td>
                <td>
                  {item.estimated_cost == null
                    ? "Quotation needed"
                    : `₹${Number(item.estimated_cost).toLocaleString("en-IN")}`}
                </td>
              </tr>
            ))}
            {!plans.length && (
              <tr><td colSpan="4">No purchase recommendation available.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="disclaimer">
        Recommendations are drafts. Human approval is required before procurement.
      </p>
    </section>
  );
}

// RAG GUIDELINES

function Guidelines({ analysis }) {
  const matches = analysis?.guideline_matches || [];

  return (
    <section className="panel">
      <SectionHeading
        kicker="KNOWLEDGE RETRIEVAL"
        title="RAG - Procurement Guideline Knowledge"
        subtitle="Relevant guideline passages retrieved for this analysis."
      />

      {matches.map((guideline, index) => (
        <div className="guideline" key={index}>
          <p>{guideline.content}</p>
          <div className="guideline-meta">
            {guideline.similarity != null && (
              <span>Similarity: {Number(guideline.similarity).toFixed(3)}</span>
            )}
            {guideline.matched_terms != null && (
              <span>Matched terms: {guideline.matched_terms}</span>
            )}
          </div>
        </div>
      ))}

      {!matches.length && <p>No guideline passages retrieved.</p>}
    </section>
  );
}

// CHATBOT

function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hello! I'm MedSupply AI Assistant. 👋\n\nI can help you understand procurement guidelines, stock management, supplier evaluation and purchase approvals.\n\nWhat would you like to know?",
      sources: [],
    },
  ]);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending, isOpen]);

  async function sendMessage(text = question) {
    const userQuestion = text.trim();

    if (!userQuestion || sending) return;

    setChatError("");
    setQuestion("");

    setMessages((previous) => [
      ...previous,
      { role: "user", text: userQuestion, sources: [] },
    ]);

    setSending(true);

    try {
      const response = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: userQuestion }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to get an AI response.");
      }

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          text: result.answer || "No answer was returned.",
          sources: result.sources || [],
          retrievalMethod: result.retrieval_method || "",
        },
      ]);
    } catch (error) {
      setChatError(error.message);
      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          text: "Sorry, I couldn't process that question. Please check that the backend is running and try again.",
          sources: [],
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  const suggestions = [
    "What are the procurement approval rules?",
    "How should critical stock be managed?",
    "How do we evaluate suppliers?",
  ];

  return (
    <>
      {isOpen && (
        <section className="chat-window">
          <div className="chat-header">
            <div className="chat-avatar">✚</div>
            <div className="chat-header-copy">
              <b>MedSupply AI Assistant</b>
              <small><span className="online-dot" /> AI procurement support</small>
            </div>
            <button
              className="chat-close"
              onClick={() => setIsOpen(false)}
              aria-label="Close chatbot"
            >
              ×
            </button>
          </div>

          <div className="chat-security">
            ✦ Answers are based on your procurement guidelines.
          </div>

          <div className="chat-messages">
            {messages.map((item, index) => (
              <div className={`chat-message ${item.role}`} key={index}>
                {item.role === "assistant" && (
                  <div className="message-avatar">✚</div>
                )}

                <div className="message-content">
                  <div className="message-bubble">
                    {item.text}
                  </div>

                  {item.sources?.length > 0 && (
                    <div className="chat-sources">
                      <b>📚 Retrieved guideline sources</b>
                      {item.sources.slice(0, 3).map((source, sourceIndex) => (
                        <div className="chat-source" key={sourceIndex}>
                          <p>{source.content}</p>
                          {source.similarity != null && (
                            <small>
                              Similarity: {Number(source.similarity).toFixed(3)}
                            </small>
                          )}
                        </div>
                      ))}
                      {item.retrievalMethod && (
                        <small className="retrieval-label">
                          Retrieval: {item.retrievalMethod}
                        </small>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {sending && (
              <div className="chat-message assistant">
                <div className="message-avatar">✚</div>
                <div className="message-bubble typing-bubble">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {messages.length <= 1 && (
            <div className="chat-suggestions">
              <small>TRY ASKING</small>
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => sendMessage(suggestion)}
                  disabled={sending}
                >
                  {suggestion} <span>↗</span>
                </button>
              ))}
            </div>
          )}

          {chatError && <div className="chat-error">{chatError}</div>}

          <form
            className="chat-input-area"
            onSubmit={(event) => {
              event.preventDefault();
              sendMessage();
            }}
          >
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about procurement..."
              maxLength={1000}
              disabled={sending}
            />
            <button
              type="submit"
              disabled={!question.trim() || sending}
              aria-label="Send message"
            >
              ➤
            </button>
          </form>

          <div className="chat-footer">
            AI-generated guidance · Verify before procurement decisions
          </div>
        </section>
      )}

      <button
        className={`chat-launcher ${isOpen ? "chat-launcher-open" : ""}`}
        onClick={() => setIsOpen((value) => !value)}
        aria-label={isOpen ? "Close AI assistant" : "Open AI assistant"}
      >
        {isOpen ? "×" : <><span className="launcher-sparkle">✦</span> AI</>}
        {!isOpen && <span className="launcher-pulse" />}
      </button>
    </>
  );
}

// COMMON COMPONENTS

function SectionHeading({ kicker, title, subtitle }) {
  return (
    <div className="section-heading">
      <span className="section-kicker">{kicker}</span>
      <h2>{title}</h2>
      <p className="muted">{subtitle}</p>
    </div>
  );
}

function Stat({ label, value, icon, color, hint }) {
  return (
    <div className={`stat stat-${color}`}>
      <span className="stat-icon">{icon}</span>
      <div className="stat-copy">
        <p>{label}</p>
        <strong>{value}</strong>
        <small>{hint}</small>
      </div>
      <span className="stat-decoration" />
    </div>
  );
}

function Status({ value }) {
  const status = String(value || "Unknown");
  const normalized = status.toLowerCase();

  let className = "status";
  if (normalized.includes("critical")) className += " critical";
  else if (normalized.includes("low") || normalized.includes("high")) className += " low";
  else className += " neutral";

  return <span className={className}>{status}</span>;
}

function Upload({ label, description, accept, onChange, icon }) {
  return (
    <label className="upload">
      <span className="upload-icon">{icon || "＋"}</span>
      <b>{label}</b>
      <small>{description}</small>
      <span className="upload-action">Choose file ↗</span>
      <input
        type="file"
        accept={accept}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onChange(file);
          event.target.value = "";
        }}
      />
    </label>
  );
}

createRoot(document.getElementById("root")).render(<App />);
