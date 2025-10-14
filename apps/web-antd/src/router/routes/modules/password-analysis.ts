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
          title: '密码算法误用分析',
        },
        name: 'PasswordStrengthAssessment',
        path: '/password-analysis/strength',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
      },
      {
        meta: {
          title: '协议设计形式化验证',
        },
        name: 'PasswordDictionaryManagement',
        path: '/password-analysis/dictionaries',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
      },
    ],
  },
];

export default routes;
