/// <reference types="vite/client" />

// 声明 Vue 单文件组件的类型
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/ban-types
  const component: DefineComponent<{}, {}, any>
  export default component
}

// 声明路径别名的类型
declare module '#/*' {
  const value: any
  export default value
}