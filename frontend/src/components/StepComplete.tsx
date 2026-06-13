import { useEffect, useState } from 'react';
import type { JobRequest, JobSummary } from '../types';
import { useMonitorJob } from '../hooks/useMonitorJob';

interface StepCompleteProps {
  jobId: string;
  jobRequest: JobRequest;
  siteCount: number;
  onAddAnother: () => void;
}

export function StepComplete({
  jobId,
  jobRequest,
  siteCount,
  onAddAnother,
}: StepCompleteProps) {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const { fetchJobs, deleteJob } = useMonitorJob();

  useEffect(() => {
    setJobsLoading(true);
    fetchJobs()
      .then(setJobs)
      .catch(() => setJobs([]))
      .finally(() => setJobsLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm('このジョブを削除しますか？')) return;
    setDeletingId(id);
    try {
      await deleteJob(id);
      setJobs((prev) => prev.filter((j) => j.id !== id));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div>
      {/* Success banner */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 mb-5 text-center">
        <div className="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-4">
          <svg className="w-7 h-7 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-slate-900 mb-1">登録が完了しました</h2>
        <p className="text-slate-500 text-sm">スケジュールが有効になりました</p>
      </div>

      {/* Job details */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 mb-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">登録内容</h3>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
          <div>
            <dt className="text-xs text-slate-400">ジョブID</dt>
            <dd className="font-mono text-slate-900 text-sm mt-0.5">{jobId}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-400">監視サイト数</dt>
            <dd className="text-slate-900 text-sm mt-0.5">{siteCount}件</dd>
          </div>
          <div className="col-span-2">
            <dt className="text-xs text-slate-400">調査内容</dt>
            <dd className="text-slate-900 text-sm mt-0.5">{jobRequest.query}</dd>
          </div>
          <div className="col-span-2">
            <dt className="text-xs text-slate-400">頻度</dt>
            <dd className="text-slate-900 text-sm mt-0.5">{jobRequest.schedule_label}</dd>
          </div>
        </dl>
      </div>

      {/* Next steps */}
      <div className="bg-indigo-50 border border-indigo-100 rounded-2xl px-5 py-4 mb-5">
        <h3 className="text-xs font-semibold text-indigo-800 uppercase tracking-wide mb-2">次のステップ</h3>
        <ul className="space-y-1.5 text-sm text-indigo-700">
          <li>初回の調査は <span className="font-semibold">{jobRequest.schedule_label}</span> に自動で実行されます</li>
          <li>GitHub Actions のワークフロータブから手動実行も可能です</li>
          <li>結果は <span className="font-semibold">{jobRequest.email}</span> にメール送信されます</li>
        </ul>
      </div>

      {/* Jobs list */}
      <div className="mb-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-700">登録済みジョブ一覧</h3>
          {jobsLoading && (
            <span className="w-4 h-4 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin" />
          )}
        </div>
        {!jobsLoading && jobs.length === 0 && (
          <p className="text-slate-400 text-xs">ジョブがありません</p>
        )}
        <div className="space-y-2">
          {jobs.map((job) => (
            <div key={job.id} className="bg-white rounded-xl border border-slate-100 shadow-sm px-4 py-3 flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">{job.query}</p>
                <p className="text-xs text-slate-400 mt-0.5">{job.schedule_label} · {job.site_count}サイト</p>
              </div>
              <span className="font-mono text-xs text-slate-400 shrink-0">{job.id8}</span>
              <button
                type="button"
                onClick={() => handleDelete(job.id)}
                disabled={deletingId === job.id}
                title="削除"
                className="shrink-0 w-7 h-7 rounded-lg bg-slate-100 hover:bg-red-50 hover:text-red-500 text-slate-400 flex items-center justify-center transition-colors disabled:opacity-50"
              >
                {deletingId === job.id ? (
                  <span className="w-3 h-3 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                )}
              </button>
            </div>
          ))}
        </div>
      </div>

      <button
        type="button"
        onClick={onAddAnother}
        className="w-full border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold px-6 py-3 rounded-xl transition-colors"
      >
        別のジョブを追加する
      </button>
    </div>
  );
}
