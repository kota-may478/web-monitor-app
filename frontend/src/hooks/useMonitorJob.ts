import { useState } from 'react';
import axios from 'axios';
import type {
  AgentResponse,
  ConfirmJobResponse,
  JobDefinition,
  JobRequest,
  JobSummary,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Web監視ジョブのAPI操作カスタムフック
 */
export function useMonitorJob() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const propose = async (request: JobRequest): Promise<AgentResponse> => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post<AgentResponse>(
        `${API_BASE_URL}/api/agent/propose`,
        request
      );
      return response.data;
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : '提案の取得に失敗しました';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  const confirmJob = async (job: JobDefinition): Promise<{ job_id: string; id8: string }> => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post<ConfirmJobResponse>(
        `${API_BASE_URL}/api/jobs/confirm`,
        { job }
      );
      return { job_id: response.data.job_id, id8: response.data.id8 };
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : 'ジョブ登録に失敗しました';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  const fetchJobs = async (): Promise<JobSummary[]> => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get<JobSummary[]>(`${API_BASE_URL}/api/jobs`);
      return response.data;
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : 'ジョブ一覧の取得に失敗しました';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  const deleteJob = async (jobId: string): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.delete<{ success: boolean }>(
        `${API_BASE_URL}/api/jobs/${jobId}`
      );
      return response.data.success;
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : 'ジョブ削除に失敗しました';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  return { propose, confirmJob, fetchJobs, deleteJob, loading, error };
}
