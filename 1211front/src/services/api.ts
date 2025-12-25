import axios, { type AxiosError, type AxiosResponse } from 'axios'

export interface ApiResponse<T> {
  code: number
  msg: string
  data: T
}

const baseURL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') || 'http://localhost:8000/api'

export const apiClient = axios.create({
  baseURL,
  timeout: 20000,
})

export async function unwrap<T>(promise: Promise<AxiosResponse<ApiResponse<T>>>) {
  try {
    const response = await promise
    if (response.data.code !== 0 && response.data.code !== 200) {
      throw new Error(response.data.msg || 'Request failed')
    }
    return response.data.data
  } catch (err) {
    const error = err as AxiosError<{ detail?: string; msg?: string }>
    const message =
      error.response?.data?.detail ||
      error.response?.data?.msg ||
      error.message ||
      'Network error'
    throw new Error(message)
  }
}
