import { useState } from 'react';
import type { AgentResponse, JobRequest } from './types';
import { StepInput } from './components/StepInput';
import { StepProposal } from './components/StepProposal';
import { StepComplete } from './components/StepComplete';

type Step = 'input' | 'proposal' | 'complete';

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
    <div className="min-h-screen bg-gray-50">
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
    </div>
  );
}
