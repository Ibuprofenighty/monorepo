import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { ResourcesPage } from "./pages/ResourcesPage";

export function App() {
  return (
    <div data-testid="app-root">
      <BrowserRouter>
        <nav style={{ padding: 12, borderBottom: "1px solid #eee", display: "flex", gap: 16 }}>
          <Link to="/" style={{ fontWeight: 700 }}>Project</Link>
          <Link to="/resources">Resources</Link>
        </nav>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/resources" element={<ResourcesPage />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}
