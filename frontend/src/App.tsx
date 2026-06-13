import { useState } from 'react';
import type { AgentResponse, JobRequest } from './types';
import { StepInput } from './components/StepInput';
import { StepProposal } from './components/StepProposal';
import { StepComplete } from './components/StepComplete';

type Step = 'input' | 'proposal' | 'complete';

const STEP_LABELS = ['入力', '確認', '完了'] as const;
const STEP_KEYS: Step[] = ['input', 'proposal', 'complete'];

function StepIndicator({ current }: { current: Step }) {
  const currentIndex = STEP_KEYS.indexOf(current);
  return (
    <div className="flex items-center justify-center gap-1 pt-8 pb-6">
      {STEP_LABELS.map((label, i) => (
        <div key={label} className="flex items-center gap-1">
          <div className="flex flex-col items-center gap-1">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
                i < currentIndex
                  ? 'bg-indigo-600 text-white'
                  : i === currentIndex
                  ? 'bg-indigo-600 text-white ring-4 ring-indigo-100'
                  : 'bg-slate-200 text-slate-400'
              }`}
            >
              {i < currentIndex ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                i + 1
              )}
            </div>
            <span className={`text-xs font-medium ${i === currentIndex ? 'text-indigo-700' : 'text-slate-400'}`}>
              {label}
            </span>
          </div>
          {i < STEP_LABELS.length - 1 && (
            <div className={`w-12 h-px mb-5 transition-colors ${i < currentIndex ? 'bg-indigo-400' : 'bg-slate-200'}`} />
          )}
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [step, setStep] = useState<Step>('input');
  const [agentResponse, setAgentResponse] = useState<AgentResponse | null>(null);
  const [jobRequest, setJobRequest] = useState<JobRequest | null>(null);
  const [completedJobId, setCompletedJobId] = useState<string | null>(null);

  const handleProposeComplete = (request: JobRequest, response: AgentResponse) => {
    setJobRequest(request);
    setAgentResponse(response);
    setStep('proposal');
  };

  const handleConfirmComplete = (jobId: string) => {
    setCompletedJobId(jobId);
    setStep('complete');
  };

  const handleReset = () => {
    setStep('input');
    setAgentResponse(null);
    setJobRequest(null);
    setCompletedJobId(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/40">
      <header className="border-b border-slate-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-6 py-3 flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <span className="font-semibold text-slate-800 text-sm tracking-tight">Web Monitor</span>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-6 pb-16">
        <StepIndicator current={step} />

        {step === 'input' && (
          <StepInput onComplete={handleProposeComplete} />
        )}
        {step === 'proposal' && agentResponse && jobRequest && (
          <StepProposal
            agentResponse={agentResponse}
            jobRequest={jobRequest}
            onConfirm={handleConfirmComplete}
            onBack={handleReset}
          />
        )}
        {step === 'complete' && jobRequest && completedJobId && (
          <StepComplete
            jobId={completedJobId}
            jobRequest={jobRequest}
            siteCount={agentResponse?.sites.length ?? 0}
            onAddAnother={handleReset}
          />
        )}
      </main>
    </div>
  );
}
