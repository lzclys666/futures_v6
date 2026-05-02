/**
 * Axios 客户端封装
 * 统一 baseURL、超时、错误处理
 * @author Lucy
 * @date 2026-04-27
 */

import axios, { AxiosError, AxiosResponse } from 'axios'

const BASE_TIMEOUT = 10000

/** 通用 API 响应包装 */
export interface ApiWrapper<T = unknown> {
  code: number
  message: string
  data: T
}

/**
 * 创建 axios 实例
 * @param baseURL - API 路径前缀，如 '/api/vnpy'
 */
export function createClient(baseURL: string) {
  const client = axios.create({
    baseURL,
    timeout: BASE_TIMEOUT,
    headers: { 'Content-Type': 'application/json' },
  })

  // 响应拦截：解包 data 层 + 统一错误
  client.interceptors.response.use(
    (response: AxiosResponse) => {
      const data = response.data
      // 如果响应包含 code/message/data 包装，解包（兼容 code=0 或 status=success）
      if (data && typeof data === 'object' && 'code' in data) {
        const wrapper = data as ApiWrapper
        if (wrapper.code !== 0) {
          const err = new Error(wrapper.message || `API 错误: ${wrapper.code}`)
          ;(err as unknown as Record<string, unknown>).code = wrapper.code
          return Promise.reject(err)
        }
        // 返回解包后的 data
        return { ...response, data: wrapper.data }
      }
      // 兼容 { status, data, message } 格式（FastAPI 默认格式）
      if (data && typeof data === 'object' && 'status' in data) {
        const wrapper = data as { status: string; data?: unknown; message?: string }
        if (wrapper.status !== 'success') {
          const err = new Error(wrapper.message || `API 错误: ${wrapper.status}`)
          return Promise.reject(err)
        }
        // 两种子格式：
        // 1. { status, data: {...}, message } → 解包 data
        // 2. { status, count, positions, ... } → data 在根级别，整个根对象作为 data
        if ('data' in wrapper && wrapper.data !== undefined) {
          return { ...response, data: wrapper.data }
        } else {
          // data 不存在或为 undefined → 根级别数据（去掉 status 和 message 后其余全部透传）
          const { status: _s, message: _m, ...rootData } = data as Record<string, unknown>
          return { ...response, data: rootData }
        }
      }
      return response
    },
    (error: AxiosError) => {
      if (error.code === 'ECONNABORTED') {
        return Promise.reject(new Error('请求超时，请检查后端服务是否启动'))
      }
      if (error.response?.status === 503) {
        return Promise.reject(new Error('后端服务暂时不可用'))
      }
      if (error.response?.status === 500) {
        const msg = (error.response?.data as Record<string, unknown>)?.message
        return Promise.reject(new Error(`服务器错误: ${msg || error.message}`))
      }
      return Promise.reject(error)
    },
  )

  return client
}

/** 默认 API 客户端（用于无前缀的接口） */
export const defaultClient = createClient('')
