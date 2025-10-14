import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'lucide:shield-check',
      order: 1,
      title: '协议合规性分析',
    },
    name: 'ProtocolCompliance',
    path: '/protocol-compliance',
    children: [
      {
        name: 'ProtocolComplianceOverview',
        path: '/protocol-compliance/overview',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
        meta: {
          title: '合规性概览',
        },
      },
      {
        name: 'ProtocolComplianceMonitoring',
        path: '/protocol-compliance/monitoring',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
        meta: {
          title: '协议监控',
        },
      },
      {
        name: 'ProtocolComplianceReports',
        path: '/protocol-compliance/reports',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
        meta: {
          title: '风险报告',
        },
      },
    ],
  },
];

export default routes;
