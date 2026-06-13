import { useEffect, useState } from 'react';
import type { JobSummary } from '../types';
import { useMonitorJob } from '../hooks/useMonitorJob';
import { JobEditPage } from './JobEditPage';

interface JobManagePageProps {
  onNewJob: () => void;
}

export function JobManagePage({ onNewJob }: JobManagePageProps) {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingJobId, setEditingJobId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const { fetchJobs, deleteJob } = useMonitorJob();

  const loadJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJobs();
      setJobs(data);
    } catch {
      setError('ジョブ一覧の取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDelete = async (job: JobSummary) => {
    if (!confirm(`「${job.query}」を削除しますか？`)) return;
    try {
      await deleteJob(job.id);
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
      setSuccessMessage('ジョブを削除しました');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch {
      setError('削除に失敗しました');
    }
  };

  const handleEditSaved = () => {
    setEditingJobId(null);
    setSuccessMessage('ジョブを更新しました');
    setTimeout(() => setSuccessMessage(null), 3000);
    loadJobs();
  };

  if (editingJobId) {
    return (
      <JobEditPage
        jobId={editingJobId}
        onBack={() => setEditingJobId(null)}
        onSaved={handleEditSaved}
        onDeleted={() => {
          setEditingJobId(null);
          loadJobs();
        }}
      />
    );
  }

  return (
    <div className="pt-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">ジョブ管理</h1>
          <p className="text-slate-500 text-sm mt-0.5">登録済みの監視ジョブを確認・編集できます</p>
        </div>
        <button
          type="button"
          onClick={onNewJob}
          className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2 rounded-xl transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          新規登録
        </button>
      </div>

      {successMessage && (
        <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-100 text-emerald-700 rounded-xl px-4 py-3 text-sm mb-4">
          <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          {successMessage}
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 bg-red-50 border border-red-100 text-red-700 rounded-xl px-4 py-3 text-sm mb-4">
          <svg className="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M12 3a9 9 0 100 18A9 9 0 0012 3z" />
          </svg>
          {error}
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-12">
          <span className="w-6 h-6 border-2 border-slate-300 border-t-indigo-600 rounded-full animate-spin" />
        </div>
      )}

      {!loading && jobs.length === 0 && !error && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center">
          <p className="text-slate-400 text-sm mb-4">登録済みのジョブがありません</p>
          <button
            type="button"
            onClick={onNewJob}
            className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
          >
            最初のジョブを登録する →
          </button>
        </div>
      )}

      <div className="space-y-3">
        {jobs.map((job) => (
          <div
            key={job.id}
            className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 flex items-center gap-3"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-slate-900 truncate">{job.query}</p>
              <p className="text-xs text-slate-400 mt-0.5">
                {job.schedule_label} · {job.site_count}サイト · {job.created_at.slice(0, 10)}
              </p>
            </div>
            <span className="font-mono text-xs text-slate-400 shrink-0 hidden sm:block">{job.id8}</span>
            <button
              type="button"
              onClick={() => setEditingJobId(job.id)}
              className="shrink-0 flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-indigo-700 bg-slate-100 hover:bg-indigo-50 px-3 py-1.5 rounded-lg transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              編集
            </button>
            <button
              type="button"
              onClick={() => handleDelete(job)}
              title="削除"
              className="shrink-0 w-7 h-7 rounded-lg bg-slate-100 hover:bg-red-50 hover:text-red-500 text-slate-400 flex items-center justify-center transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
