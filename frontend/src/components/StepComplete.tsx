import type { JobRequest } from '../types';

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
  return (
    <div className="max-w-2xl mx-auto p-6 text-center">
      <div className="text-6xl mb-4">✅</div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">スケジュールが登録されました</h2>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-left mb-6">
        <dl className="space-y-3">
          <div>
            <dt className="text-sm text-gray-500">ジョブID</dt>
            <dd className="font-mono text-gray-900">{jobId}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">調査内容</dt>
            <dd className="text-gray-900">{jobRequest.query}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">頻度</dt>
            <dd className="text-gray-900">{jobRequest.schedule_label}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-500">監視サイト数</dt>
            <dd className="text-gray-900">{siteCount}件</dd>
          </div>
        </dl>
      </div>

      <p className="text-gray-600 text-sm mb-6">
        初回の調査は次回のスケジュール実行時（{jobRequest.schedule_label}）に行われます。
        GitHub Actionsのワークフロータブから手動実行することも可能です。
      </p>

      <button
        type="button"
        onClick={onAddAnother}
        className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg"
      >
        + 別のジョブを追加する
      </button>
    </div>
  );
}
