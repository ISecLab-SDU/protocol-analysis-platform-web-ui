import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    name: 'ProtocolComplianceWorkbench',
    path: '/protocol-compliance/workbench',
    component: () => import('#/views/protocol-compliance/workbench/index.vue'),
    meta: {
      title: '协议合规分析工作台',
      icon: 'mdi:shield-check',
    },
  },
];

export default routes;
