/// <reference types="vite/client" />
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
console.log("API URL:", import.meta.env.VITE_API_URL);
export class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  async get<T>(endpoint: string): Promise<T> {
    console.log(`GET Request to: ${this.baseUrl}${endpoint}`);
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`)
    }

    return response.json() as Promise<T>
  }

  async post<T>(endpoint: string, data: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`)
    }

    return response.json() as Promise<T>
  }
}

export const apiClient = new ApiClient()
