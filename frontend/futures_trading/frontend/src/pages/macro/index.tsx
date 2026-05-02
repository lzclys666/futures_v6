/**
 * 宏观打分页面入口
 * @author Lucy (UI Designer)
 * @date 2026-04-20
 */

import React from 'react'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import MacroDashboard from '../../components/macro/MacroDashboard'

const MacroPage: React.FC = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <MacroDashboard />
    </ConfigProvider>
  )
}

export default MacroPage
