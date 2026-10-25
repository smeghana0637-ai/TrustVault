
import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

export default function App() {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(
    localStorage.getItem("trustvault_token") || ""
  );
  const [message, setMessage] = useState("");
  const [documents, setDocuments] = useState([]);
  const [busy, setBusy] = useState(false);

  async function submitAuth(e) {
    e.preventDefault();
    setMessage("");
    setBusy(true);

    try {
      const endpoint = mode === "login" ? "/login" : "/register";
      const body =
        mode === "login"
          ? { email, password }
          : { username, email, password };

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Request failed");

      if (mode === "login") {
        localStorage.setItem("trustvault_token", data.access_token);
        setToken(data.access_token);
        setMessage("Login successful!");
        await loadDocuments(data.access_token);
      } else {
        setMessage("Registration successful. Please log in.");
        setMode("login");
      }
    } catch (error) {
      setMessage(error.message || "Could not connect to the backend.");
    } finally {
      setBusy(false);
    }
  }

  async function loadDocuments(authToken = token) {
    try {
      const response = await fetch(`${API_URL}/documents`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load documents");
      setDocuments(data);
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function uploadDocument(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    setMessage("");
    setBusy(true);

    try {
      const response = await fetch(`${API_URL}/documents/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Upload failed");

      setMessage("Document uploaded successfully!");
      await loadDocuments();
    } catch (error) {
      setMessage(error.message || "Upload failed.");
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  function logout() {
    localStorage.removeItem("trustvault_token");
    setToken("");
    setDocuments([]);
    setMessage("You have logged out.");
  }

  if (token) {
    return (
      <main className="page">
        <header className="topbar">
          <div className="brand"><span className="brand-icon">T</span> TrustVault</div>
          <button className="secondary" onClick={logout}>Log out</button>
        </header>

        <section className="dashboard">
          <p className="eyebrow">YOUR SECURE WORKSPACE</p>
          <h1>Welcome to TrustVault</h1>
          <p className="muted">Manage your private documents securely.</p>

          <div className="panel">
            <h2>Upload a document</h2>
            <p className="muted">Choose a file to store it in your vault.</p>
            <label className="upload-button">
              {busy ? "Please wait..." : "Choose document"}
              <input type="file" onChange={uploadDocument} disabled={busy} />
            </label>
          </div>

          <div className="panel">
            <div className="list-heading">
              <h2>My documents</h2>
              <button className="secondary" onClick={() => loadDocuments()}>
                Refresh
              </button>
            </div>
            {documents.length === 0 ? (
              <p className="muted">No documents found. Upload your first file.</p>
            ) : (
              <ul className="document-list">
                {documents.map((doc) => (
                  <li key={doc.id}>
                    <span>📄 {doc.filename}</span>
                    <button
                      className="secondary"
                      onClick={async () => {
                        const response = await fetch(
                          `${API_URL}/documents/${doc.id}/download`,
                          { headers: { Authorization: `Bearer ${token}` } }
                        );
                        if (!response.ok) {
                          setMessage("Download failed.");
                          return;
                        }
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement("a");
                        link.href = url;
                        link.download = doc.filename;
                        link.click();
                        URL.revokeObjectURL(url);
                      }}
                    >
                      Download
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {message && <p className="message" role="status">{message}</p>}
        </section>
      </main>
    );
  }

  return (
    <main className="page auth-page">
      <header className="brand"><span className="brand-icon">T</span> TrustVault</header>

      <section className="auth-card">
        <p className="eyebrow">PRIVATE DOCUMENT MANAGEMENT</p>
        <h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1>
        <p className="muted">
          {mode === "login"
            ? "Sign in to access your secure vault."
            : "Register to create your secure vault account."}
        </p>

        <form onSubmit={submitAuth}>
          {mode === "register" && (
            <label>
              Username
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                minLength={3}
                required
                autoComplete="username"
              />
            </label>
          )}

          <label>
            Email address
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </label>

          <button className="primary" type="submit" disabled={busy}>
            {busy ? "Please wait..." : mode === "login" ? "Sign in" : "Register"}
          </button>
        </form>

        {message && <p className="message" role="status">{message}</p>}

        <p className="switch-mode">
          {mode === "login" ? "New to TrustVault?" : "Already have an account?"}{" "}
          <button
            className="text-button"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setMessage("");
            }}
          >
            {mode === "login" ? "Create account" : "Sign in"}
          </button>
        </p>
      </section>
      <p className="footer-note">Your documents. Your access. Your control.</p>
    </main>
  );
}
