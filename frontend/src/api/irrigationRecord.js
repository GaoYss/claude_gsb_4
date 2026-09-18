import { createResourceApi } from './client'
import http from './client'

export const irrigationRecordApi = {
  ...createResourceApi('irrigation-records'),
  summary: (params) => http.get('/irrigation-records/summary', { params }),
  /** 按行政区与月份汇总用水量，异常偏高的单次用水随组返回 */
  monthlySummary: (params) => http.get('/irrigation-records/monthly-summary', { params }),
}
