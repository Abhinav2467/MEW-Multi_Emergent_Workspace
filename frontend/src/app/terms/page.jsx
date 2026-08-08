import Link from "next/link";

export const metadata = {
  title: "Terms of Service - MEW-Multi Emergent Workspace",
  description: "Terms of Service for MEW-Multi Emergent Workspace",
};

export default function TermsOfService() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-10 shadow-2xl space-y-8">
        <div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-sky-400 mb-2">Terms of Service</h1>
          <p className="text-sm text-slate-400">MEW-Multi Emergent Workspace • Last Updated: August 8, 2026</p>
        </div>

        <div className="h-px bg-slate-800 w-full" />

        {/* 1. Acceptance of Terms */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">1. Acceptance of Terms</h2>
          <p className="text-slate-300 leading-relaxed">
            By accessing or using <strong>MEW-Multi Emergent Workspace</strong> ("Service", "Application", "we", "us"), you agree to be bound by these Terms of Service ("Terms"). If you do not agree to all of these Terms, you may not access or use the Service.
          </p>
        </section>

        {/* 2. Description of Service */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">2. Description of Service</h2>
          <p className="text-slate-300 leading-relaxed">
            MEW-Multi Emergent Workspace provides autonomous job matching, candidate profile management, and recruiter outreach drafting tools to streamline career outreach workflows.
          </p>
        </section>

        {/* 3. User Responsibilities */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">3. User Responsibilities</h2>
          <ul className="list-disc list-inside space-y-2 text-slate-300 pl-2">
            <li>Provide accurate resume and career information.</li>
            <li>Users are responsible for reviewing generated outreach before sending.</li>
            <li>Maintain security over connected accounts and credentials.</li>
          </ul>
        </section>

        {/* 4. Google OAuth and Gmail Usage */}
        <section className="space-y-3 p-6 bg-slate-950/70 rounded-xl border border-sky-500/30">
          <h2 className="text-xl font-bold text-sky-400">4. Google OAuth and Gmail Usage</h2>
          <p className="text-slate-300 leading-relaxed">
            Google OAuth/Gmail permissions (<code className="font-mono text-xs text-sky-300">gmail.compose</code> and <code className="font-mono text-xs text-sky-300">gmail.send</code>) are used only for draft creation and user-approved sending of recruiter outreach emails.
          </p>
          <ul className="list-disc list-inside space-y-1 text-slate-300 pt-2">
            <li>We do not read your inbox for unrelated purposes.</li>
            <li>We do not sell user data and we do not use Google user data for advertising.</li>
            <li>Users can revoke access at any time via <a href="https://myaccount.google.com/permissions" target="_blank" rel="noopener noreferrer" className="text-sky-400 underline">https://myaccount.google.com/permissions</a>.</li>
          </ul>
        </section>

        {/* 5. Prohibited Use */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">5. Prohibited Use</h2>
          <p className="text-slate-300 leading-relaxed">
            Users must not use the app for spam, harassment, fraud, or unauthorized outreach to recruiters, employers, or third parties.
          </p>
        </section>

        {/* 6. No Guarantee of Job Outcomes */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">6. No Guarantee of Job Outcomes</h2>
          <p className="text-slate-300 leading-relaxed">
            The app does not guarantee jobs, interviews, offers, recruiter replies, or application outcomes. Employment decisions remain solely between candidates and employers.
          </p>
        </section>

        {/* 7. Account and Access */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">7. Account and Access</h2>
          <p className="text-slate-300 leading-relaxed">
            We reserve the right to suspend or terminate accounts violating these terms.
          </p>
        </section>

        {/* 8. Termination */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">8. Termination</h2>
          <p className="text-slate-300 leading-relaxed">
            You may stop using the Service at any time and request account and data deletion by emailing <a href="mailto:akamutala9@gmail.com" className="text-sky-400 underline">akamutala9@gmail.com</a>.
          </p>
        </section>

        {/* 9. Disclaimer */}
        <section className="space-y-3">
          <h2 className="text-xl font-bold text-slate-200">9. Disclaimer</h2>
          <p className="text-slate-300 leading-relaxed">
            THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS OR IMPLIED.
          </p>
        </section>

        {/* 10. Contact Information */}
        <section className="space-y-3 pt-4 border-t border-slate-800">
          <h2 className="text-xl font-bold text-slate-200">10. Contact Information</h2>
          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-sm">
            <p className="font-bold text-slate-100">MEW-Multi Emergent Workspace Support</p>
            <p className="text-slate-400">Email: <a href="mailto:akamutala9@gmail.com" className="text-sky-400 underline">akamutala9@gmail.com</a></p>
          </div>
        </section>

        <div className="pt-6 border-t border-slate-800 flex gap-6 text-sm text-slate-400">
          <Link href="/terms" className="text-sky-400 font-bold">Terms of Service</Link>
          <Link href="/privacy" className="hover:text-sky-400 transition-colors">Privacy Policy</Link>
        </div>
      </div>
    </div>
  );
}
