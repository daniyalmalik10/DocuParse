export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
}

export interface UploadResponse {
  document_id: string;
  job_id: string;
  status: JobStatus;
}

export interface DocumentSummary {
  document_id: string;
  filename: string;
  content_type: string;
  size: number;
  uploaded_at: string;
  status: JobStatus;
}

export interface DocumentListResponse {
  items: DocumentSummary[];
}

export interface WorkExperience {
  company: string;
  title: string;
  start: string;
  end: string | null;
  bullets: string[];
}

export interface Education {
  institution: string;
  degree: string;
  year: string | null;
}

export interface ResumeExtraction {
  full_name: string;
  email: string | null;
  phone: string | null;
  location: string | null;
  summary: string | null;
  skills: string[];
  experience: WorkExperience[];
  education: Education[];
}

export interface DocumentDetail {
  document_id: string;
  filename: string;
  content_type: string;
  size: number;
  uploaded_at: string;
  status: JobStatus;
  error_message: string | null;
  extraction: ResumeExtraction | null;
}
