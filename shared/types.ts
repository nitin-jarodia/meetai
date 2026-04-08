/**
 * Optional shared TypeScript shapes aligned with backend Pydantic schemas.
 * Extend as you add features (search, action items, etc.).
 */

export type UUID = string;

export interface UserDTO {
  id: UUID;
  email: string;
  full_name: string | null;
  created_at: string;
}

export interface MeetingDTO {
  id: UUID;
  title: string;
  description: string | null;
  host_id: UUID;
  created_at: string;
}
