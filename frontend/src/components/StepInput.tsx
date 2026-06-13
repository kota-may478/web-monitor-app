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

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">🔍 Web Monitor</h1>
      <p className="text-gray-600 mb-8">
        調査したい情報を登録すると、LLMが自動でウェブを監視してメールでお知らせします
      </p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-1">
            調査したい情報
          </label>
          <textarea
            id="query"
            rows={4}
            required
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="例：ヘリコプター体験搭乗の無料イベント情報（東京近郊）"
            className="w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label htmlFor="schedule" className="block text-sm font-medium text-gray-700 mb-1">
            調査頻度
          </label>
          <select
            id="schedule"
            value={scheduleIndex}
            onChange={(e) => setScheduleIndex(Number(e.target.value))}
            className="w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {SCHEDULE_OPTIONS.map((opt, i) => (
              <option key={opt.cron} value={i}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
            通知先メールアドレス
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Geminiがウェブを調査中...
            </span>
          ) : (
            '🤖 LLMに調査させる'
          )}
        </button>
      </form>
    </div>
  );
}
