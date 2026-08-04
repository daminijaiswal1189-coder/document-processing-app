import axios from 'axios'
import { API_BASE_URL } from '../utils/constants'

const api = axios.create({
    baseURL: API_BASE_URL,
})

export async function uploadDocument(file) {
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await api.post('/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    })

    return data
}