import axios from "axios"

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

const api = axios.create({ baseURL: BASE })

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token")
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => Promise.reject(err)
)

export default api

// Auth
export const register = (email: string, password: string, name: string) =>
  api.post("/auth/register", { email, password, name })
export const login = (email: string, password: string) =>
  api.post("/auth/login", { email, password })

// Stores
export const createStore = (data: object) => api.post("/stores", data)
export const listStores = () => api.get("/stores")
export const uploadSales = (storeId: string, file: File) => {
  const fd = new FormData(); fd.append("file", file)
  return api.post(`/stores/${storeId}/sales`, fd)
}
export const uploadCosts = (storeId: string, file: File) => {
  const fd = new FormData(); fd.append("file", file)
  return api.post(`/stores/${storeId}/costs`, fd)
}
export const uploadReviewCsv = (storeId: string, platform: string, file: File) => {
  const fd = new FormData(); fd.append("file", file)
  return api.post(`/stores/${storeId}/reviews/upload?platform=${platform}`, fd)
}
export const addReviewSource = (storeId: string, data: object) =>
  api.post(`/stores/${storeId}/reviews/sources`, data)
export const collectReviews = (storeId: string) =>
  api.post(`/stores/${storeId}/reviews/collect`)

// Agent
export const runDiagnosis = (storeId: string) => api.post(`/stores/${storeId}/diagnose`)
export const getDashboard = (storeId: string) => api.get(`/stores/${storeId}/dashboard`)
export const generateStrategy = (storeId: string) => api.post(`/stores/${storeId}/strategy`)
export const runSimulation = (storeId: string, data: object) =>
  api.post(`/stores/${storeId}/simulate`, data)
export const createReport = (storeId: string) => api.post(`/stores/${storeId}/reports`)
export const getReport = (reportId: string) => api.get(`/stores/reports/${reportId}`)
export const getReviewSignals = (storeId: string) =>
  api.get(`/stores/${storeId}/reviews/signals`)
export const downloadReport = (reportId: string) =>
  `${BASE}/stores/reports/${reportId}/download`
