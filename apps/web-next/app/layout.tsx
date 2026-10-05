import type { Metadata } from "next";

export const metadata: Metadata = { title: "Project" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui", margin: 0 }}>
        <nav style={{ padding: 12, borderBottom: "1px solid #eee", display: "flex", gap: 16 }}>
          <a href="/" style={{ fontWeight: 700 }}>Project</a>
          <a href="/resources">Resources</a>
        </nav>
        {children}
      </body>
    </html>
  );
}
