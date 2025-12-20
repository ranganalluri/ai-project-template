// Shared API model types and enums for UI projects

// Example: User model

export interface User {
  user_id: string;
  name: string;
  email: string;
}


// Example: Enum for user roles
export enum UserRole {
  Admin = 'admin',
  Editor = 'editor',
  Viewer = 'viewer',
}

// Example: API response wrapper
type ApiResponseStatus = 'success' | 'error';

export interface ApiResponse<T> {
  status: ApiResponseStatus;
  data: T;
  message?: string;
}

// Add more models/enums as needed for your REST API
