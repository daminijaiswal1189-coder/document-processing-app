/**
 * Shared axios instance — baseURL resolved at request time (desktop runtime config).
 */
import axios from 'axios'
import { getApiBaseUrl } from '../utils/apiConfig'

const api = axios.create()

api.interceptors.request.use((config) => {
  config.baseURL = getApiBaseUrl()
  return config
})

export default api
