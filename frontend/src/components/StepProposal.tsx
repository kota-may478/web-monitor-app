import { useState } from 'react';
import type { AgentResponse, JobDefinition, JobRequest, SiteProposal } from '../types';
import { useMonitorJob } from '../hooks/useMonitorJob';

interface StepProposalProps {
  agentResponse: AgentResponse;
  jobRequest: JobRequest;
  onConfirm: (jobId: string) => void;
  onBack: () => void;
}

export function StepProposal({
  agentResponse,
  jobRequest,
  onConfirm,
  onBack,
}: StepProposalProps) {
  const [sites, setSites] = useState<SiteProposal[]>(agentResponse.sites);
  const [subjectTemplate, setSubjectTemplate] = useState(agentResponse.email_format.subject_template);
  const [bodyTemplate, setBodyTemplate] = useState(agentResponse.email_format.body_template);
  const [emailOpen, setEmailOpen] = useState(false);
  const { confirmJob, loading, error } = useMonitorJob();

  const removeSite = (index: number) => {
    setSites((prev) => prev.filter((_, i) => i !== index));
  };

  const handleConfirm = async () => {
    const job: JobDefinition = {
      id: crypto.randomUUID(),
      query: jobRequest.query,
      email: jobRequest.email,
      schedule_cron: jobRequest.schedule_cron,
      schedule_label: jobRequest.schedule_label,
      sites,
      email_format: { subject_template: subjectTemplate, body_template: bodyTemplate },
      created_at: new Date().toISOString(),
      active: true,
    };
    const result = await confirmJob(job);
    onConfirm(result.id8);
  };

  const fieldClass =
    'w-full border border-slate-200 rounded-lg px-3 py-2 text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white';

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight mb-1">提案内容を確認する</h2>
        <p className="text-slate-500 text-sm">不要なサイトを除外してから登録できます</p>
      </div>

      {/* Agent message */}
      <div className="flex gap-3 bg-indigo-50 border border-indigo-100 rounded-2xl px-4 py-3.5 mb-5">
        <svg className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        <p className="text-indigo-800 text-sm leading-relaxed">{agentResponse.agent_message}</p>
      </div>

      {/* Site cards */}
      <section className="mb-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-700">監視サイト候補</h3>
          <span className="text-xs text-slate-400">{sites.length}件</span>
        </div>
        <div className="space-y-3">
          {sites.map((site, index) => (
            <div
              key={`${site.url}-${index}`}
              className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 flex gap-4"
            >
              <div className="flex-1 min-w-0">
                <h4 className="font-semibold text-slate-900 text-sm truncate">{site.name}</h4>
                <a
                  href={site.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-600 text-xs hover:text-indigo-800 hover:underline block truncate mt-0.5"
                >
                  {site.url}
                </a>
                <p className="text-slate-500 text-xs mt-1.5 leading-relaxed">{site.description}</p>
                <div className="flex flex-wrap gap-1 mt-2">
                  {site.target_keywords.map((kw) => (
                    <span
                      key={kw}
                      className="bg-indigo-50 text-indigo-700 text-xs px-2 py-0.5 rounded-full font-medium"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
              <button
                type="button"
                onClick={() => removeSite(index)}
                title="このサイトを除外する"
                className="shrink-0 w-7 h-7 rounded-lg bg-slate-100 hover:bg-red-50 hover:text-red-500 text-slate-400 flex items-center justify-center transition-colors"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
          {sites.length === 0 && (
            <div className="text-center py-8 text-slate-400 text-sm">
              監視サイトがありません。やり直してください。
            </div>
          )}
        </div>
      </section>

      {/* Email config (collapsible) */}
      <section className="mb-5">
        <button
          type="button"
          onClick={() => setEmailOpen((v) => !v)}
          className="w-full flex items-center justify-between bg-white rounded-2xl border border-slate-100 shadow-sm px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
        >
          <span>メール設定を編集する</span>
          <svg
            className={`w-4 h-4 text-slate-400 transition-transform ${emailOpen ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {emailOpen && (
          <div className="bg-white border border-slate-100 border-t-0 rounded-b-2xl shadow-sm px-4 pb-4 pt-3 space-y-3">
            <div>
              <label htmlFor="subject" className="block text-xs font-semibold text-slate-600 mb-1.5">
                件名テンプレート
              </label>
              <input
                id="subject"
                type="text"
                value={subjectTemplate}
                onChange={(e) => setSubjectTemplate(e.target.value)}
                className={fieldClass}
              />
            </div>
            <div>
              <label htmlFor="body" className="block text-xs font-semibold text-slate-600 mb-1.5">
                本文テンプレート
              </label>
              <textarea
                id="body"
                rows={7}
                value={bodyTemplate}
                onChange={(e) => setBodyTemplate(e.target.value)}
                className={`${fieldClass} font-mono text-xs`}
              />
            </div>
          </div>
        )}
      </section>

      {error && (
        <div className="flex items-start gap-2 bg-red-50 border border-red-100 text-red-700 rounded-xl px-4 py-3 text-sm mb-4">
          <svg className="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M12 3a9 9 0 100 18A9 9 0 0012 3z" />
          </svg>
          {error}
        </div>
      )}

      <div className="flex gap-3">
        <button
          type="button"
          onClick={handleConfirm}
          disabled={loading || sites.length === 0}
          className="flex-1 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-semibold px-6 py-3 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              GitHubに登録中...
            </>
          ) : (
            'この内容でスケジュールを登録する'
          )}
        </button>
        <button
          type="button"
          onClick={onBack}
          disabled={loading}
          className="px-4 py-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-sm font-medium transition-colors disabled:opacity-50"
        >
          やり直す
        </button>
      </div>
    </div>
  );
}
