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
          title: '密码强度评估',
        },
        name: 'PasswordStrengthAssessment',
        path: '/password-analysis/strength',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
      },
      {
        meta: {
          title: '字典库管理',
        },
        name: 'PasswordDictionaryManagement',
        path: '/password-analysis/dictionaries',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
      },
      {
        meta: {
          title: '破解报告',
        },
        name: 'PasswordCrackReports',
        path: '/password-analysis/reports',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
      },
    ],
  },
];

export default routes;
