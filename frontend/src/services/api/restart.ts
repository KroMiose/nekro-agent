import axios from './axios'

export interface RestartResponse {
    code: number
    msg: string
    data?: any
}

export const restartApi = {
    /**
     * 重启系统
     */
    restartSystem: async (): Promise<RestartResponse> => {
        const response = await axios.post<RestartResponse>('/restart')
        return response.data
    },
}
