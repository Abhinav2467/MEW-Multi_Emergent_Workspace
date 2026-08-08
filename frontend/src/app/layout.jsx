import "./globals.css";

export const metadata = {
  title: "MEW-Multi Emergent Workspace",
  description: "MEW-Multi Emergent Workspace - Autonomous job search, candidate profile management, and recruiter outreach workspace.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased selection:bg-sky-500 selection:text-slate-900">
        <div className="fixed inset-0 pointer-events-none z-0">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl" />
        </div>
        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}
