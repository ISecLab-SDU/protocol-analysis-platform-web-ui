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
        name: 'ProtocolComplianceExtract',
        path: '/protocol-compliance/extract',
        component: () =>
          import('#/views/protocol-compliance/extract/index.vue'),
        meta: {
          title: '协议规则提取',
        },
      },
      {
        name: 'ProtocolComplianceStatic',
        path: '/protocol-compliance/static',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
        meta: {
          title: '静态分析',
        },
      },
      {
        name: 'ProtocolComplianceFuzz',
        path: '/protocol-compliance/fuzz',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
        meta: {
          title: '协议模糊测试',
        },
      },
    ],
  },
];

export default routes;
