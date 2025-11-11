import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'lucide:shield-check',
      order: 1,
      title: '协议合规与安全性分析',
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
          title: '协议代码提取',
        },
      },
      {
        name: 'ProtocolComplianceStatic',
        path: '/protocol-compliance/static',
        component: () => import('#/views/protocol-compliance/static/index.vue'),
        meta: {
          title: '协议代码提取',
        },
      },
      {
        name: 'ProtocolComplianceAssert',
        path: '/protocol-compliance/assert',
        component: () =>
          import('#/views/protocol-compliance/assert/index.vue'),
        meta: {
          title: '合规断言生成',
        },
      },
      {
        name: 'ProtocolComplianceFuzz',
        path: '/protocol-compliance/fuzz',
        component: () =>
          import('#/views/protocol-compliance/fuzz/index.vue'),
        meta: {
          title: '协议模糊测试',
        },
      },
    ],
  },
];

export default routes;
