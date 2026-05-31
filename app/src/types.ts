export interface Event {
  id: string;
  name: string;
  date_start: string | null;
  date_end: string | null;
  location: string | null;
  description: string | null;
  tags: string[] | null;
  color: string | null;
  created_at: string;
  people_count: number;
  met_count: number;
}

export interface TalkingPoint {
  text: string;
  source: string;
  priority: number;
}

export interface OpenRole {
  title: string;
  dept: string | null;
  location: string | null;
  url: string | null;
}

export interface ReconSource {
  posts_found?: number;
  repos_found?: number;
  summary: string;
}

export interface ReconSources {
  linkedin?: ReconSource;
  twitter?: ReconSource;
  github?: ReconSource;
  reddit?: ReconSource;
  instagram?: ReconSource;
  company?: ReconSource;
  web?: ReconSource;
  [key: string]: ReconSource | undefined;
}

export interface AttendancePerson {
  attendance_id: string;
  person_id: string;
  name: string;
  company: string | null;
  role: string | null;
  location: string | null;
  photo_url: string | null;
  linkedin_url: string | null;
  twitter_handle: string | null;
  github_handle: string | null;
  bio_snapshot: string | null;
  talking_points: TalkingPoint[] | null;
  recon_sources: ReconSources | null;
  agent_ran_at: string | null;
  open_roles: OpenRole[] | null;
  met: boolean;
  met_at: string | null;
  met_notes: string | null;
  outreach_sent: boolean;
  outreach_channel: string | null;
  outreach_draft: string | null;
  outreach_sent_at: string | null;
}
