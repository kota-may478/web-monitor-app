export interface SiteProposal {
  url: string;
  name: string;
  description: string;
  target_keywords: string[];
  css_selector: string | null;
}

export interface EmailFormat {
  subject_template: string;
  body_template: string;
}

export interface AgentResponse {
  sites: SiteProposal[];
  email_format: EmailFormat;
  agent_message: string;
}

export interface JobRequest {
  query: string;
  schedule_cron: string;
  schedule_label: string;
  email: string;
}

export interface JobDefinition {
  id: string;
  query: string;
  email: string;
  schedule_cron: string;
  schedule_label: string;
  sites: SiteProposal[];
  email_format: EmailFormat;
  created_at: string;
  active: boolean;
}

export interface ConfirmJobRequest {
  job: JobDefinition;
}

export interface JobSummary {
  id: string;
  id8: string;
  query: string;
  schedule_label: string;
  site_count: number;
  created_at: string;
  active: boolean;
}

export interface ConfirmJobResponse {
  success: boolean;
  job_id: string;
  id8: string;
}

export interface JobDetail {
  id: string;
  query: string;
  schedule_cron: string;
  schedule_label: string;
  sites: SiteProposal[];
  email_format: EmailFormat;
  created_at: string;
  active: boolean;
  email_hidden: boolean;
}

export interface UpdateJobRequest {
  query: string;
  schedule_cron: string;
  schedule_label: string;
  sites: SiteProposal[];
  email_format: EmailFormat;
  email: string;
  active: boolean;
}
