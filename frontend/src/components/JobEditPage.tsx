import { useEffect, useState } from 'react';
import type { JobRequest, SiteProposal } from '../types';
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

const EMPTY_SITE: NewSiteForm = { url: '', name: '', description: '', keywords: '', css_selector: '' };

interface NewSiteForm {
  url: string;
  name: string;
  description: string;
  keywords: string;
  css_selector: string;
}

interface JobEditPageProps {
  jobId: string;
  onBack: () => void;
  onSaved: () => void;
  onDeleted: () => void;
}

export function JobEditPage({ jobId, onBack, onSaved, onDeleted }: JobEditPageProps) {
  const [loadState, setLoadState] = useState<'loading' | 'legacy' | 'error' | 'ready'>('loading');
  const [query, setQuery] = useState('');
  const [scheduleIndex, setScheduleIndex] = useState(0);
  const [email, setEmail] = useState('');
  const [sites, setSites] = useState<SiteProposal[]>([]);
  const [subjectTemplate, setSubjectTemplate] = useState('');
  const [bodyTemplate, setBodyTemplate] = useState('');
  const [active, setActive] = useState(true);
  const [emailOpen, setEmailOpen] = useState(false);
  const [addSiteOpen, setAddSiteOpen] = useState(false);
  const [newSite, setNewSite] = useState<NewSiteForm>(EMPTY_SITE);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [reProposing, setReProposing] = useState(false);

  const { fetchJob, updateJob, deleteJob, propose } = useMonitorJob();

  useEffect(() => {
    fetchJob(jobId)
      .then((job) => {
        setQuery(job.query);
        const idx = SCHEDULE_OPTIONS.findIndex((o) => o.cron === job.schedule_cron);
        setScheduleIndex(idx >= 0 ? idx : 0);
        setSites(job.sites);
        setSubjectTemplate(job.email_format.subject_template);
        setBodyTemplate(job.email_format.body_template);
        setActive(job.active);
        setLoadState('ready');
      })
      .catch((err) => {
        if (err && (err as { isLegacy?: boolean }).isLegacy) {
          setLoadState('legacy');
        } else {
          setLoadState('error');
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    const schedule = SCHEDULE_OPTIONS[scheduleIndex];
    try {
      await updateJob(jobId, {
        query,
        schedule_cron: schedule.cron,
        schedule_label: schedule.label,
        sites,
        email_format: { subject_template: subjectTemplate, body_template: bodyTemplate },
        email,
        active,
      });
      onSaved();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'ジョブ更新に失敗しました');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('このジョブを削除しますか？この操作は取り消せません。')) return;
    setDeleting(true);
    try {
      await deleteJob(jobId);
      onDeleted();
    } catch {
      setSaveError('削除に失敗しました');
      setDeleting(false);
    }
  };

  const handleAddSite = () => {
    if (!newSite.url || !newSite.name) return;
    const keywords = newSite.keywords
      .split(',')
      .map((k) => k.trim())
      .filter(Boolean);
    const site: SiteProposal = {
      url: newSite.url,
      name: newSite.name,
      description: newSite.description,
      target_keywords: keywords,
      css_selector: newSite.css_selector || null,
    };
    setSites((prev) => [...prev, site]);
    setNewSite(EMPTY_SITE);
    setAddSiteOpen(false);
  };

  const handleRePropose = async () => {
    if (!email) {
      setSaveError('「AIに再提案」を使うには、先にメールアドレスを入力してください。');
      return;
    }
    setReProposing(true);
    setSaveError(null);
    const schedule = SCHEDULE_OPTIONS[scheduleIndex];
    const request: JobRequest = {
      query,
      schedule_cron: schedule.cron,
      schedule_label: schedule.label,
      email,
    };
    try {
      const response = await propose(request);
      setSites(response.sites);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'AIの再提案に失敗しました');
    } finally {
      setReProposing(false);
    }
  };

  const fieldClass =
    'w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-900 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-shadow bg-white';
  const smallFieldClass =
    'w-full border border-slate-200 rounded-lg px-3 py-2 text-slate-900 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white';

  if (loadState === 'loading') {
    return (
      <div className="pt-6 flex justify-center py-12">
        <span className="w-6 h-6 border-2 border-slate-300 border-t-indigo-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (loadState === 'legacy') {
    return (
      <div className="pt-6">
        <button type="button" onClick={onBack} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 mb-6">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          一覧に戻る
        </button>
        <div className="bg-amber-50 border border-amber-100 rounded-2xl p-6 text-center">
          <p className="text-amber-800 font-semibold mb-2">旧形式のジョブのため編集できません</p>
          <p className="text-amber-700 text-sm mb-5">
            このジョブはメタファイルなしで登録されています。<br />
            削除して新規登録することで編集可能になります。
          </p>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="bg-red-600 hover:bg-red-700 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition-colors disabled:opacity-50"
          >
            {deleting ? '削除中...' : 'このジョブを削除する'}
          </button>
        </div>
      </div>
    );
  }

  if (loadState === 'error') {
    return (
      <div className="pt-6">
        <button type="button" onClick={onBack} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 mb-6">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          一覧に戻る
        </button>
        <div className="bg-red-50 border border-red-100 rounded-2xl p-6 text-center">
          <p className="text-red-700 text-sm">ジョブ詳細の取得に失敗しました。しばらく待ってから再度お試しください。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="pt-6">
      <button type="button" onClick={onBack} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 mb-6">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        一覧に戻る
      </button>

      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">ジョブを編集する</h2>
        <p className="text-slate-500 text-sm mt-0.5">変更後、「保存する」で反映されます</p>
      </div>

      <form onSubmit={handleSave} className="space-y-4">
        {/* Query */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
          <label htmlFor="edit-query" className="block text-sm font-semibold text-slate-700 mb-2">
            調査したい情報
          </label>
          <textarea
            id="edit-query"
            rows={3}
            required
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className={fieldClass}
          />
        </div>

        {/* Schedule */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
          <label htmlFor="edit-schedule" className="block text-sm font-semibold text-slate-700 mb-2">
            調査頻度
          </label>
          <select
            id="edit-schedule"
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

        {/* Email */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
          <label htmlFor="edit-email" className="block text-sm font-semibold text-slate-700 mb-2">
            通知先メールアドレス
          </label>
          <input
            id="edit-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className={fieldClass}
          />
          <p className="mt-1.5 text-xs text-amber-600">
            メールアドレスはプライバシー保護のため非公開です。毎回入力が必要です。
          </p>
        </div>

        {/* Sites */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-700">監視サイト</h3>
            <span className="text-xs text-slate-400">{sites.length}件</span>
          </div>
          <div className="space-y-3 mb-3">
            {sites.map((site, index) => (
              <div
                key={`${site.url}-${index}`}
                className="rounded-xl border border-slate-100 p-3 flex gap-3 bg-slate-50"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-slate-900 text-sm truncate">{site.name}</p>
                  <a
                    href={site.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 text-xs hover:underline block truncate mt-0.5"
                  >
                    {site.url}
                  </a>
                  {site.description && (
                    <p className="text-slate-500 text-xs mt-1 leading-relaxed">{site.description}</p>
                  )}
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {site.target_keywords.map((kw) => (
                      <span key={kw} className="bg-indigo-50 text-indigo-700 text-xs px-2 py-0.5 rounded-full font-medium">
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSites((prev) => prev.filter((_, i) => i !== index))}
                  title="このサイトを除外する"
                  className="shrink-0 w-7 h-7 rounded-lg bg-white border border-slate-200 hover:bg-red-50 hover:text-red-500 text-slate-400 flex items-center justify-center transition-colors"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
            {sites.length === 0 && (
              <p className="text-slate-400 text-xs text-center py-4">監視サイトがありません</p>
            )}
          </div>

          {/* Add site / re-propose buttons */}
          <div className="flex gap-2 flex-wrap">
            <button
              type="button"
              onClick={() => setAddSiteOpen((v) => !v)}
              className="flex items-center gap-1.5 text-xs font-medium text-slate-600 hover:text-indigo-700 bg-slate-100 hover:bg-indigo-50 px-3 py-1.5 rounded-lg transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              サイトを追加
            </button>
            <button
              type="button"
              onClick={handleRePropose}
              disabled={reProposing}
              className="flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >
              {reProposing ? (
                <>
                  <span className="w-3 h-3 border-2 border-indigo-300 border-t-indigo-600 rounded-full animate-spin" />
                  AIが調査中...
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  AIに再提案
                </>
              )}
            </button>
          </div>

          {/* Inline add site form */}
          {addSiteOpen && (
            <div className="mt-3 border border-dashed border-slate-300 rounded-xl p-4 space-y-3 bg-slate-50">
              <p className="text-xs font-semibold text-slate-600">サイトを追加</p>
              <div>
                <label className="block text-xs text-slate-500 mb-1">URL <span className="text-red-500">*</span></label>
                <input
                  type="url"
                  placeholder="https://example.com"
                  value={newSite.url}
                  onChange={(e) => setNewSite((s) => ({ ...s, url: e.target.value }))}
                  className={smallFieldClass}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">サイト名 <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  placeholder="例：農林水産省イベント"
                  value={newSite.name}
                  onChange={(e) => setNewSite((s) => ({ ...s, name: e.target.value }))}
                  className={smallFieldClass}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">説明</label>
                <input
                  type="text"
                  value={newSite.description}
                  onChange={(e) => setNewSite((s) => ({ ...s, description: e.target.value }))}
                  className={smallFieldClass}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">キーワード（カンマ区切り）</label>
                <input
                  type="text"
                  placeholder="例：無料,体験,イベント"
                  value={newSite.keywords}
                  onChange={(e) => setNewSite((s) => ({ ...s, keywords: e.target.value }))}
                  className={smallFieldClass}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">CSSセレクター（省略可）</label>
                <input
                  type="text"
                  placeholder="例：#main .event-list"
                  value={newSite.css_selector}
                  onChange={(e) => setNewSite((s) => ({ ...s, css_selector: e.target.value }))}
                  className={smallFieldClass}
                />
              </div>
              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  onClick={handleAddSite}
                  disabled={!newSite.url || !newSite.name}
                  className="text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-1.5 rounded-lg transition-colors disabled:opacity-50"
                >
                  追加
                </button>
                <button
                  type="button"
                  onClick={() => { setAddSiteOpen(false); setNewSite(EMPTY_SITE); }}
                  className="text-xs font-medium text-slate-500 hover:text-slate-700 px-4 py-1.5 rounded-lg border border-slate-200 bg-white transition-colors"
                >
                  キャンセル
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Email format (collapsible) */}
        <div>
          <button
            type="button"
            onClick={() => setEmailOpen((v) => !v)}
            className="w-full flex items-center justify-between bg-white rounded-2xl border border-slate-100 shadow-sm px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
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
            <div className="bg-white border border-slate-100 border-t-0 rounded-b-2xl shadow-sm px-5 pb-5 pt-4 space-y-3">
              <div>
                <label htmlFor="edit-subject" className="block text-xs font-semibold text-slate-600 mb-1.5">
                  件名テンプレート
                </label>
                <input
                  id="edit-subject"
                  type="text"
                  value={subjectTemplate}
                  onChange={(e) => setSubjectTemplate(e.target.value)}
                  className={smallFieldClass}
                />
              </div>
              <div>
                <label htmlFor="edit-body" className="block text-xs font-semibold text-slate-600 mb-1.5">
                  本文テンプレート
                </label>
                <textarea
                  id="edit-body"
                  rows={7}
                  value={bodyTemplate}
                  onChange={(e) => setBodyTemplate(e.target.value)}
                  className={`${smallFieldClass} font-mono text-xs`}
                />
              </div>
            </div>
          )}
        </div>

        {saveError && (
          <div className="flex items-start gap-2 bg-red-50 border border-red-100 text-red-700 rounded-xl px-4 py-3 text-sm">
            <svg className="w-4 h-4 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M12 3a9 9 0 100 18A9 9 0 0012 3z" />
            </svg>
            {saveError}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={saving || sites.length === 0}
            className="flex-1 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-semibold px-6 py-3 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {saving ? (
              <>
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                保存中...
              </>
            ) : (
              '保存する'
            )}
          </button>
          <button
            type="button"
            onClick={onBack}
            disabled={saving}
            className="px-4 py-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-sm font-medium transition-colors disabled:opacity-50"
          >
            キャンセル
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={saving || deleting}
            className="px-4 py-3 rounded-xl border border-red-200 bg-white hover:bg-red-50 text-red-600 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {deleting ? '削除中...' : '削除'}
          </button>
        </div>
      </form>
    </div>
  );
}
