import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';

interface ThemeContextValue {
  darkMode: boolean;
  setDarkMode: (v: boolean) => void;
}

export const ThemeContext = createContext<ThemeContextValue>({
  darkMode: false,
  setDarkMode: () => {},
});

export const useTheme = () => useContext(ThemeContext);

// ==================== 设计 Token（Phase 4 完整覆盖）====================

/** 浅色模式 Token */
const LIGHT_TOKEN = {
  colorPrimary: '#1890ff',
  colorSuccess: '#52c41a',
  colorWarning: '#faad14',
  colorError: '#ff4d4f',
  colorInfo: '#1890ff',

  borderRadius: 6,

  // 背景
  colorBgContainer: '#ffffff',
  colorBgElevated: '#ffffff',
  colorBgLayout: '#f0f2f5',
  colorBgSpotlight: '#ffffff',

  // 文字
  colorText: '#262626',
  colorTextSecondary: '#8c8c8c',
  colorTextTertiary: '#bfbfbf',
  colorTextQuaternary: '#d9d9d9',

  // 边框
  colorBorder: '#d9d9d9',
  colorBorderSecondary: '#f0f0f0',

  // 分割线
  colorSplit: '#f0f0f0',

  // 表格
  colorTableHeader: '#fafafa',
  colorTableHeaderHover: '#f5f5f5',
  colorTableRowHover: '#fafafa',

  // 卡片
  colorCardBg: '#ffffff',

  // 品牌色
  colorLink: '#1890ff',
  colorLinkHover: '#40a9ff',

  // 滚动条
  colorScrollbar: 'rgba(0,0,0,0.25)',
  colorScrollbarHover: 'rgba(0,0,0,0.45)',
};

/** 深色模式 Token — 完整覆盖 Ant Design 组件 */
const DARK_TOKEN = {
  ...LIGHT_TOKEN,

  colorPrimary: '#177ddc',
  colorSuccess: '#49aa19',
  colorWarning: '#d89614',
  colorError: '#dc4446',
  colorInfo: '#177ddc',

  // 背景
  colorBgContainer: '#1f1f1f',
  colorBgElevated: '#252525',
  colorBgLayout: '#141414',
  colorBgSpotlight: '#303030',

  // 文字
  colorText: '#e8e8e8',
  colorTextSecondary: '#a6a6a6',
  colorTextTertiary: '#747474',
  colorTextQuaternary: '#525252',

  // 边框
  colorBorder: '#434343',
  colorBorderSecondary: '#303030',

  // 分割线
  colorSplit: '#303030',

  // 表格
  colorTableHeader: '#262626',
  colorTableHeaderHover: '#303030',
  colorTableRowHover: '#262626',

  // 卡片
  colorCardBg: '#1f1f1f',

  // 品牌色
  colorLink: '#69b1ff',
  colorLinkHover: '#91caff',

  // 滚动条
  colorScrollbar: 'rgba(255,255,255,0.25)',
  colorScrollbarHover: 'rgba(255,255,255,0.45)',
};

interface Props {
  children: ReactNode;
}

/**
 * 应用主题 Provider
 * P4-2: 扩展 Token 覆盖（光/暗模式完整支持）
 *
 * Token 覆盖说明：
 * - 浅色模式：LIGHT_TOKEN（完整覆盖背景/文字/边框/组件）
 * - 深色模式：DARK_TOKEN（配合 darkAlgorithm 使用）
 * - CSS 变量同步：darkMode 状态同步到 document.documentElement class
 */
export const AppThemeProvider: React.FC<Props> = ({ children }) => {
  const [darkMode, setDarkMode] = useState(false);

  // 同步 darkMode 到 HTML class，供 index.css CSS 变量使用
  useEffect(() => {
    const root = document.documentElement;
    if (darkMode) {
      root.classList.add('dark-mode');
    } else {
      root.classList.remove('dark-mode');
    }
  }, [darkMode]);

  return (
    <ThemeContext.Provider value={{ darkMode, setDarkMode }}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          algorithm: darkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
          token: darkMode ? DARK_TOKEN : LIGHT_TOKEN,
          // 组件级 Token 覆盖（确保关键组件在深色模式下正确渲染）
          components: darkMode ? {
            Table: {
              headerBg: '#262626',
              rowHoverBg: '#303030',
              borderColor: '#434343',
              headerColor: '#e8e8e8',
              colorText: '#e8e8e8',
            },
            Card: {
              colorBgContainer: '#1f1f1f',
            },
            Modal: {
              contentBg: '#1f1f1f',
              headerBg: '#1f1f1f',
            },
            Drawer: {
              colorBgElevated: '#1f1f1f',
            },
            Menu: {
              darkItemBg: '#141414',
              darkSubMenuItemBg: '#141414',
              darkItemSelectedBg: '#177ddc',
            },
            Layout: {
              siderBg: '#141414',
              headerBg: '#141414',
              bodyBg: '#141414',
            },
          } : {},
        }}
      >
        {children}
      </ConfigProvider>
    </ThemeContext.Provider>
  );
};
