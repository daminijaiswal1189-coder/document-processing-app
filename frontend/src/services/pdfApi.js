import axios from 'axios'
import { API_BASE_URL } from '../utils/constants'

const api = axios.create({
  baseURL: API_BASE_URL,
})

export async function processPdf(filename) {
  const { data } = await api.post('/process/pdf', { filename })
  return data
}
