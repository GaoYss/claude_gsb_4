import { createResourceApi } from './client'
import http from './client'

export const waterSourceApi = {
  ...createResourceApi('water-sources'),
  /** 下拉选项：仅返回未停用水源点 */
  options: (params) => http.get('/water-sources/options', { params }),
  summary: (params) => http.get('/water-sources/summary', { params }),
}
