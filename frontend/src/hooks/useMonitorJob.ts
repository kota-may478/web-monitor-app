import { useState } from 'react';
import axios from 'axios';
import type {
  AgentResponse,
  ConfirmJobResponse,
  JobDefinition,
  JobDetail,
  JobRequest,
  JobSummary,
  UpdateJobRequest,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_KEY = (import.meta.env.VITE_API_KEY || '').trim();
const AUTH_HEADERS = API_KEY ? { 'X-Api-Key': API_KEY } : {};

function formatApiError(detail: unknown, status?: number): string {
  const message = typeof detail === 'string' ? detail : 'リクエストに失敗しました';
  if (status === 401) {
    if (!API_KEY) {
      return 'API認証エラー: フロントエンドにAPIキーが埋め込まれていません。Renderの Static Site で VITE_API_KEY を設定し、再デプロイしてください。';
    }
    return 'API認証エラー: APIキーが一致しません。Renderの API_KEY と VITE_API_KEY が同じ値か確認してください。';
  }
  return message;
}

export function useMonitorJob() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const propose = async (request: JobRequest): Promise<AgentResponse> => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post<AgentResponse>(
        `${API_BASE_URL}/api/agent/propose`,
        request,
        { headers: AUTH_HEADERS }
      );
      return response.data;
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? formatApiError(err.response?.data?.detail, err.response?.status)
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
        { job },
        { headers: AUTH_HEADERS }
      );
      return { job_id: response.data.job_id, id8: response.data.id8 };
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? formatApiError(err.response?.data?.detail, err.response?.status)
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
      const response = await axios.get<JobSummary[]>(`${API_BASE_URL}/api/jobs`, { headers: AUTH_HEADERS });
      return response.data;
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? formatApiError(err.response?.data?.detail, err.response?.status)
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
        `${API_BASE_URL}/api/jobs/${jobId}`,
        { headers: AUTH_HEADERS }
      );
      return response.data.success;
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? formatApiError(err.response?.data?.detail, err.response?.status)
        : 'ジョブ削除に失敗しました';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  const fetchJob = async (jobId: string): Promise<JobDetail> => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get<JobDetail>(
        `${API_BASE_URL}/api/jobs/${jobId}`,
        { headers: AUTH_HEADERS }
      );
      return response.data;
    } catch (err) {
      const isLegacy = axios.isAxiosError(err) && err.response?.status === 404;
      const message = isLegacy
        ? 'このジョブは旧形式のため編集できません。削除して再登録してください。'
        : axios.isAxiosError(err)
        ? formatApiError(err.response?.data?.detail, err.response?.status)
        : 'ジョブ詳細の取得に失敗しました';
      setError(message);
      throw Object.assign(new Error(message), { isLegacy });
    } finally {
      setLoading(false);
    }
  };

  const updateJob = async (jobId: string, data: UpdateJobRequest): Promise<{ id8: string }> => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.put<{ success: boolean; job_id: string; id8: string }>(
        `${API_BASE_URL}/api/jobs/${jobId}`,
        data,
        { headers: AUTH_HEADERS }
      );
      return { id8: response.data.id8 };
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? formatApiError(err.response?.data?.detail, err.response?.status)
        : 'ジョブ更新に失敗しました';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  return { propose, confirmJob, fetchJobs, fetchJob, updateJob, deleteJob, loading, error };
}
