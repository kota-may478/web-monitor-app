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
  const [subjectTemplate, setSubjectTemplate] = useState(
    agentResponse.email_format.subject_template
  );
  const [bodyTemplate, setBodyTemplate] = useState(
    agentResponse.email_format.body_template
  );
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
      email_format: {
        subject_template: subjectTemplate,
        body_template: bodyTemplate,
      },
      created_at: new Date().toISOString(),
      active: true,
    };

    const result = await confirmJob(job);
    onConfirm(result.id8);
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">提案内容の確認</h2>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <p className="text-blue-800">{agentResponse.agent_message}</p>
      </div>

      <section className="mb-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">監視サイト候補</h3>
        <div className="space-y-3">
          {sites.map((site, index) => (
            <div
              key={`${site.url}-${index}`}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h4 className="font-medium text-gray-900">{site.name}</h4>
                  <a
                    href={site.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 text-sm hover:underline break-all"
                  >
                    {site.url}
                  </a>
                  <p className="text-gray-600 text-sm mt-2">{site.description}</p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {site.target_keywords.map((kw) => (
                      <span
                        key={kw}
                        className="bg-gray-100 text-gray-700 text-xs px-2 py-0.5 rounded"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => removeSite(index)}
                  className="bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1 rounded text-sm ml-2 shrink-0"
                >
                  除外する
                </button>
              </div>
            </div>
          ))}
          {sites.length === 0 && (
            <p className="text-gray-500 text-sm">監視サイトがありません。やり直してください。</p>
          )}
        </div>
      </section>

      <section className="mb-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">メール設定プレビュー</h3>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 space-y-4">
          <div>
            <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-1">
              件名テンプレート
            </label>
            <input
              id="subject"
              type="text"
              value={subjectTemplate}
              onChange={(e) => setSubjectTemplate(e.target.value)}
              className="w-full border border-gray-300 rounded-lg p-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="body" className="block text-sm font-medium text-gray-700 mb-1">
              本文テンプレート
            </label>
            <textarea
              id="body"
              rows={8}
              value={bodyTemplate}
              onChange={(e) => setBodyTemplate(e.target.value)}
              className="w-full border border-gray-300 rounded-lg p-2 text-sm font-mono"
            />
          </div>
        </div>
      </section>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm mb-4">
          {error}
        </div>
      )}

      <div className="flex gap-3">
        <button
          type="button"
          onClick={handleConfirm}
          disabled={loading || sites.length === 0}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'GitHubに登録中...' : '✅ この内容でスケジュールを登録する'}
        </button>
        <button
          type="button"
          onClick={onBack}
          disabled={loading}
          className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg"
        >
          ← やり直す
        </button>
      </div>
    </div>
  );
}
