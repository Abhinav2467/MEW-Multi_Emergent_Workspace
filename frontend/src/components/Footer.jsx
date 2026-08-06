export default function Footer() {
  return (
    <footer className="w-full bg-surface-gray py-margin-desktop border-t border-outline-variant/30">
      <div className="max-w-container-max mx-auto px-margin-desktop flex flex-col md:flex-row justify-between items-center gap-gutter">
        <div className="flex items-center gap-2">
          <img
            alt="Mew Logo"
            className="h-6 w-auto opacity-50 grayscale"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuA7lY6S7Y9HVG8JsmUlr_g0Ba4MyFUja5ttCtDfCdTXZonDaxJTt4DyuFy2-0sSnK-oInhJ-4C-9bbLuHrTAsoa225ABaix7flyiEFflUm9ZnNXli5OJp8kU1PAZYTVXGmHlW-l-ng7f5SDz71cg-b4a_8aM7pwIgIdsTGAVMmFSNH__lBljE7uIft8n4SoUJDfzfREQrA8wP4GIGiaDHC1ftocy2_dIZ2a3ice1lqrEu9gXNTI0cC0NA"
            onError={(e) => { e.target.style.display = "none"; }}
          />
          <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-widest">
            Powered by Mew AI
          </span>
        </div>
        <div className="flex gap-gutter">
          <a className="font-label-md text-label-md text-on-surface-variant hover:text-primary uppercase transition-colors" href="#">Terms</a>
          <a className="font-label-md text-label-md text-on-surface-variant hover:text-primary uppercase transition-colors" href="#">Privacy</a>
          <a className="font-label-md text-label-md text-on-surface-variant hover:text-primary uppercase transition-colors" href="#">Support</a>
        </div>
        <div className="font-label-md text-label-md text-on-surface-variant">
          © 2024 MEW AI CORP.
        </div>
      </div>
    </footer>
  );
}
