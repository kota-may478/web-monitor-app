import { useState } from 'react';
import type { AgentResponse, JobRequest } from '../types';
import { useMonitorJob } from '../hooks/useMonitorJob';

interface ScheduleOption {
  label: string;
  cron: string;
}

const SCHEDULE_OPTIONS: ScheduleOption[] = [
  { label: '毎週土曜日 9:00 JST', cron: '0 0 * * 6' },
  { label: '毎週月曜日 8:00 JST', cron: '0 23 * * 0' },
  { label: '毎日 8:00 JST', cron: '0 23 * * *' },
  { label: '毎月1日 8:00 JST', cron: '0 23 1 * *' },
];

interface StepInputProps {
  onComplete: (request: JobRequest, response: AgentResponse) => void;
}

export function StepInput({ onComplete }: StepInputProps) {
  const [query, setQuery] = useState('');
  const [scheduleIndex, setScheduleIndex] = useState(0);
  const [email, setEmail] = useState('');
  const { propose, loading, error } = useMonitorJob();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const schedule = SCHEDULE_OPTIONS[scheduleIndex];
    const request: JobRequest = {
      query,
      schedule_cron: schedule.cron,
      schedule_label: schedule.label,
      email,
    };
    const response = await propose(request);
    onComplete(request, response);
  };

  const fieldClass =
    'w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-900 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-shadow bg-white';

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight mb-1">
          監視内容を登録する
        </h1>
        <p className="text-slate-500 text-sm">
          調査テーマを入力すると、AIが最適な監視サイトを提案します
        </p>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="query" className="block text-sm font-semibold text-slate-700 mb-2">
              調査したい情報
            </label>
            <textarea
              id="query"
              rows={4}
              required
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="例：ヘリコプター体験搭乗の無料イベント情報（東京近郊）"
              className={fieldClass}
            />
            <p className="mt-1.5 text-xs text-slate-400">できるだけ具体的に書くと、より的確な提案が得られます</p>
          </div>

          <div>
            <label htmlFor="schedule" className="block text-sm font-semibold text-slate-700 mb-2">
              調査頻度
            </label>
            <select
              id="schedule"
              value={scheduleIndex}
              onChange={(e) => setScheduleIndex(Number(e.target.value))}
              className={fieldClass}
            >
              {SCHEDULE_OPTIONS.map((opt, i) => (
                <option key={opt.cron} value={i}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-semibold text-slate-700 mb-2">
              通知先メールアドレス
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className={fieldClass}
            />
          </div>

          {error && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-100 text-red-700 rounded-xl px-4 py-3 text-sm">
              <svg className="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M12 3a9 9 0 100 18A9 9 0 0012 3z" />
              </svg>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-semibold px-6 py-3 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                AIがウェブを調査中...
              </>
            ) : (
              'AIにサイトを提案させる'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
