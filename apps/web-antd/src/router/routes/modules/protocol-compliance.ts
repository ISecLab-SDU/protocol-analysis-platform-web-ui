import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    name: 'ProtocolComplianceWorkbench',
    path: '/protocol-compliance/workbench',
    component: () =>
      import('#/views/protocol-compliance/workbench/index.vue'),
    meta: {
      title: '协议合规分析工作台',
      icon: 'mdi:shield-check',
    },
  },
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
];

export default routes;
