/* eslint-disable spaced-comment */
/// <reference types="vite/client" />
/* eslint-enable spaced-comment */

// 声明 Vue 单文件组件的类型
declare module '*.vue' {
  import type { DefineComponent } from 'vue';

  const component: DefineComponent<object, object, unknown>;
  export default component;
}

// 声明路径别名的类型
declare module '#/*' {
  const value: any;
  export default value;
}
