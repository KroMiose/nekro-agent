import axios from './axios'

export const healthApi = {
  check: async () => {
    const response = await axios.get<{ msg: string }>('/health')
    return response.data
  },
}
