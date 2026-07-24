import { useState } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const AGENT_META = {
  planner: { emoji: "🧭", color: "#6366f1" },
  researcher: { emoji: "🔎", color: "#0891b2" },
  writer: { emoji: "✍️", color: "#ca8a04" },
  reviewer: { emoji: "🧐", color: "#dc2626" },
};

export default function App() {
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!topic.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.page}>
     <header style={styles.header}>
     <h1 style={styles.h1}>🤖 AgentCrew</h1>
       <p style={styles.subtitle}>
          A planner, researcher, writer, and reviewer agent collaborate to research your topic.
       </p>
     </header>

     <section style={styles.workflowSection}>
     <h2 style={styles.h2}>📖 How to Use</h2>

     <div style={styles.workflowGrid}>
      {[
      {
        icon: "📝",
        title: "Enter a Topic",
        desc: "Type the topic you want to research.",
      },
      {
        icon: "🚀",
        title: "Run Crew",
        desc: "Click the Run Crew button.",
      },
      {
        icon: "🧭",
        title: "Planner",
        desc: "Creates a research plan.",
      },
      {
        icon: "🔍",
        title: "Researcher",
        desc: "Collects relevant information.",
      },
      {
        icon: "✍️",
        title: "Writer",
        desc: "Generates the report.",
      },
      {
        icon: "🧐",
        title: "Reviewer",
        desc: "Improves the output.",
      },
      {
        icon: "📄",
        title: "Final Report",
        desc: "Displays the completed report.",
      },
      ].map((step, index) => (
          <div
            key={index}
            className="workflowCard"
            style={styles.workflowCard}
          >
          <div style={styles.workflowIcon}>{step.icon}</div>
          <h3 style={styles.workflowTitle}>{step.title}</h3>
          <p style={styles.workflowDesc}>{step.desc}</p>
          </div>
      ))}
    </div>
    </section>

    <form onSubmit={handleSubmit} style={styles.form}>
        <input
          style={styles.input}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. The environmental impact of lithium-ion batteries"
          disabled={loading}
        />
        <button style={styles.button} type="submit" disabled={loading}>
          {loading ? "Running crew..." : "Run Crew"}
        </button>
      </form>

      {error && <div style={styles.error}>⚠️ {error}</div>}

      {result && (
        <div style={styles.results}>
          <section>
            <h2 style={styles.h2}>Agent Trace</h2>
            <div style={styles.trace}>
              {result.steps.map((step, i) => {
                const meta = AGENT_META[step.agent] || { emoji: "🤖", color: "#555" };
                return (
                  <details key={i} style={{ ...styles.step, borderColor: meta.color }}>
                    <summary style={styles.stepSummary}>
                      <span style={{ marginRight: 8 }}>{meta.emoji}</span>
                      <strong style={{ color: meta.color }}>{step.agent}</strong>
                      <span style={styles.stepLabel}> — {step.label}</span>
                    </summary>
                    <pre style={styles.stepContent}>{step.content}</pre>
                  </details>
                );
              })}
            </div>
            
          </section>

          <section>
            <h2 style={styles.h2}>
              Final Report {result.revised && <span style={styles.badge}>revised after review</span>}
            </h2>
            <div style={styles.report}>
              <pre style={styles.reportText}>{result.report}</pre>
            </div>
          </section>
        </div>
      )}
      <footer style={styles.footer}>
        <div style={styles.footerLogo}>🤖 AgentCrew</div>
        <div style={styles.footerLinks}>
          <a href="https://github.com/your-repo" style={styles.footerLink}>GitHub</a>
          <span style={styles.footerDot}>·</span>
          <a href="https://github.com/your-repo/blob/main/LICENSE" style={styles.footerLink}>MIT License</a>
          <span style={styles.footerDot}>·</span>
          <a href="https://github.com/your-repo/graphs/contributors" style={styles.footerLink}>Contributors</a>
        </div>
        <p style={styles.footerBuilt}>Built with React · FastAPI · LangGraph · Gemini</p>
      </footer>
    </div>
  );
}

const styles = {
  page: {
    maxWidth: 820,
    margin: "0 auto",
    padding: "2rem 1.25rem 4rem",
    fontFamily: "Inter, system-ui, sans-serif",
    color: "#1e1e1e",
  },
  header: { marginBottom: "1.5rem" },
  h1: { fontSize: "1.8rem", marginBottom: "0.25rem" },
  subtitle: { color: "#555", margin: 0 },
  form: { display: "flex", gap: "0.5rem", marginBottom: "1.5rem" },
  input: {
    flex: 1,
    padding: "0.65rem 0.9rem",
    borderRadius: 8,
    border: "1px solid #ccc",
    fontSize: "1rem",
  },
  button: {
    padding: "0.65rem 1.2rem",
    borderRadius: 8,
    border: "none",
    background: "#111827",
    color: "white",
    fontWeight: 600,
    cursor: "pointer",
  },
  error: {
    background: "#fee2e2",
    color: "#991b1b",
    padding: "0.75rem 1rem",
    borderRadius: 8,
    marginBottom: "1rem",
  },
  results: { display: "flex", flexDirection: "column", gap: "2rem" },
  h2: { fontSize: "1.2rem", marginBottom: "0.75rem" },
  trace: { display: "flex", flexDirection: "column", gap: "0.6rem" },
  step: {
    border: "1px solid",
    borderRadius: 8,
    padding: "0.6rem 0.9rem",
    background: "#fafafa",
  },
  stepSummary: { cursor: "pointer", listStyle: "none" },
  stepLabel: { color: "#444" },
  stepContent: {
    whiteSpace: "pre-wrap",
    fontFamily: "inherit",
    fontSize: "0.9rem",
    marginTop: "0.6rem",
    color: "#333",
  },
  badge: {
    fontSize: "0.7rem",
    background: "#fef3c7",
    color: "#92400e",
    padding: "0.15rem 0.5rem",
    borderRadius: 6,
    marginLeft: "0.5rem",
    verticalAlign: "middle",
  },
  report: { background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, padding: "1rem" },
  reportText: { whiteSpace: "pre-wrap", fontFamily: "inherit", lineHeight: 1.6, margin: 0 },
  workflowSection: {marginBottom: "2rem",},
  workflowCard: { border: "1px solid #e5e7eb", borderRadius: "12px", padding: "1rem", background: "#ffffff", textAlign: "center", boxShadow: "0 2px 8px rgba(0,0,0,0.06)",transition: "transform 0.25s ease, box-shadow 0.25s ease",},
  workflowGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem", },
  workflowIcon: { fontSize: "2rem", marginBottom: "0.5rem",},
  workflowTitle: { margin: "0.5rem 0", fontSize: "1rem", fontWeight: "600", },
  workflowDesc: { fontSize: "0.9rem", color: "#555", margin: 0, },
  footer: { marginTop: "3rem", paddingTop: "1.5rem", borderTop: "1px solid #e2e8f0", textAlign: "center", color: "#888", fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.5rem" },
  footerLogo: { fontWeight: 700, fontSize: "1rem", color: "#1e1e1e" },
  footerLinks: { display: "flex", justifyContent: "center", gap: "0.5rem", alignItems: "center" },
  footerLink: { color: "#6366f1", textDecoration: "none" },
  footerDot: { color: "#ccc" },
  footerBuilt: { margin: 0, color: "#aaa" },
};
