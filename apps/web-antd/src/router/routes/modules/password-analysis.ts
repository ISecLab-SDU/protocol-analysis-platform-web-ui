import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'mdi:key-outline',
      keepAlive: true,
      order: 2,
      title: '密码分析',
    },
    name: 'PasswordAnalysis',
    path: '/password-analysis',
    children: [
      {
        meta: {
          title: '密码算法安全分析',
        },
        name: 'CryptographicMisuseAnalysis',
        path: '/password-analysis/misuse',
        component: () => import('#/views/cryptographic-misuse/index.vue'),
      },
      {
        meta: {
          title: '协议设计形式化验证', // 保持原标题（或根据需要修改）
        },
        name: 'CryptographicFormalVerification', // 保持原路由名称（如需保持历史路由兼容性）
        path: '/password-analysis/verification', // 保持原访问路径
        component: () => import('#/views/formalGPT/ekev2/index.vue'), // 替换为你的组件路径
      },
    ],
  },
];

export default routes;
