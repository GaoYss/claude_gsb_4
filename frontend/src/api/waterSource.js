import { createResourceApi } from './client'
import http from './client'

export const waterSourceApi = {
  ...createResourceApi('water-sources'),
  options: (params) => http.get('/water-sources/options', { params }),
}
