import { createResourceApi } from './client'
import http from './client'

export const irrigationRecordApi = {
  ...createResourceApi('irrigation-records'),
  summary: (params) => http.get('/irrigation-records/summary', { params }),
}
