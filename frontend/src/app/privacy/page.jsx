import Link from "next/link";

export const metadata = {
  title: "Privacy Policy - MEW-Multi Emergent Workspace",
  description: "Privacy Policy and Google OAuth Data Disclosure for MEW-Multi Emergent Workspace",
};

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-10 shadow-2xl space-y-8">
        <div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-sky-400 mb-2">Privacy Policy</h1>
          <p className="text-sm text-slate-400">MEW-Multi Emergent Workspace • Last Updated: August 8, 2026</p>
        </div>

        <div className="h-px bg-slate-800 w-full" />

        {/* 1. Introduction */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">1. Introduction</h2>
          <p className="text-slate-300 leading-relaxed">
            Welcome to <strong>MEW-Multi Emergent Workspace</strong> ("we", "our", "us"). MEW-Multi Emergent Workspace is an autonomous job search and recruiter outreach application designed to streamline job applications, candidate profile management, and career outreach.
          </p>
          <p className="text-slate-300 leading-relaxed">
            We respect your privacy and are committed to protecting your personal data and Google user data. This Privacy Policy explains how we collect, use, store, share, and protect your information when you access or use our web application.
          </p>
        </section>

        {/* 2. Information We Collect */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">2. Information We Collect</h2>
          <ul className="list-disc list-inside space-y-2 text-slate-300 pl-2">
            <li><strong>Account Information:</strong> Name, email address, and profile details provided via Google OAuth authentication.</li>
            <li><strong>Application & Candidate Data:</strong> Resumes, career history, skills, job application logs, and recruiter messages.</li>
            <li><strong>Technical Data:</strong> IP address, browser type, device information, and authentication tokens required for system operation.</li>
          </ul>
        </section>

        {/* 3. Google User Data and Gmail Permissions */}
        <section className="space-y-3 p-6 bg-slate-950/70 rounded-xl border border-sky-500/30">
          <h2 className="text-xl font-bold text-sky-400">3. Google User Data and Gmail Permissions</h2>
          <p className="text-slate-300 leading-relaxed">
            MEW-Multi Emergent Workspace uses Google OAuth to authenticate users and enable recruiter email outreach capabilities. Specifically, our application requests the following Gmail API OAuth scopes:
          </p>
          <ul className="list-disc list-inside space-y-1 font-mono text-xs text-sky-300 bg-slate-900 p-3 rounded-lg border border-slate-800">
            <li>https://www.googleapis.com/auth/gmail.compose</li>
            <li>https://www.googleapis.com/auth/gmail.send</li>
          </ul>
          <div className="space-y-2 pt-2 text-slate-300">
            <p><strong>Strictly Scoped Usage:</strong></p>
            <ul className="list-disc list-inside space-y-1 pl-2 text-slate-300">
              <li>We only use Gmail access for draft creation and sending user-approved outreach emails.</li>
              <li>We use these permissions solely to create recruiter outreach email drafts in the user's Gmail account, and to send recruiter outreach emails only when the user explicitly initiates the send action.</li>
              <li><strong>We do not read the user's inbox</strong> unless a future explicitly listed feature requires it.</li>
              <li><strong>We do not sell user data.</strong></li>
              <li><strong>We do not use Gmail data for advertising.</strong></li>
            </ul>
          </div>
        </section>

        {/* 4. How We Use Information */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">4. How We Use Information</h2>
          <p className="text-slate-300 leading-relaxed">
            We use your data to process job matches, create outreach drafts in your connected Gmail account, dispatch user-approved outreach emails, and support workspace functionality.
          </p>
        </section>

        {/* 5. How We Store and Protect Information */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">5. How We Store and Protect Information</h2>
          <p className="text-slate-300 leading-relaxed">
            We utilize robust industry-standard encryption protocols (TLS/SSL in transit, AES encryption at rest) to safeguard your personal information and OAuth tokens.
          </p>
        </section>

        {/* 6. Data Sharing */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">6. Data Sharing</h2>
          <p className="text-slate-300 leading-relaxed">
            <strong>We do not sell user data.</strong> We do not use Gmail data for advertising. Your information is never sold, rented, or commercialized to third parties.
          </p>
        </section>

        {/* 7. Data Retention and Deletion */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">7. Data Retention and Deletion</h2>
          <p className="text-slate-300 leading-relaxed">
            Users can request complete deletion of their account data at any time by contacting us directly at <a href="mailto:akamutala9@gmail.com" className="text-sky-400 underline">akamutala9@gmail.com</a>. Account deletion requests are processed within 30 days.
          </p>
        </section>

        {/* 8. User Controls and Revoking Access */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">8. User Controls and Revoking Access</h2>
          <p className="text-slate-300 leading-relaxed">
            Users can revoke Google OAuth permissions at any time via Google Account settings:
          </p>
          <p className="pt-1">
            <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener noreferrer" className="inline-flex items-center px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold rounded-lg transition-colors">
              Revoke Access at Google Permissions &rarr;
            </a>
          </p>
        </section>

        {/* 9. Contact Information */}
        <section className="space-y-3 pt-4 border-t border-slate-800">
          <h2 className="text-xl font-bold text-slate-200">9. Contact Information</h2>
          <p className="text-slate-300">
            For questions regarding this policy or data privacy, contact:
          </p>
          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-sm">
            <p className="font-bold text-slate-100">MEW-Multi Emergent Workspace</p>
            <p className="text-slate-400">Email: <a href="mailto:akamutala9@gmail.com" className="text-sky-400 underline">akamutala9@gmail.com</a></p>
          </div>
        </section>

        <div className="pt-6 border-t border-slate-800 flex gap-6 text-sm text-slate-400">
          <Link href="/terms" className="hover:text-sky-400 transition-colors">Terms of Service</Link>
          <Link href="/privacy" className="text-sky-400 font-bold">Privacy Policy</Link>
        </div>
      </div>
    </div>
  );
}
