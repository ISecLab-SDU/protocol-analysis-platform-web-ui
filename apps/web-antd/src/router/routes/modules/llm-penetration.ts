import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'mdi:robot',
      order: 3,
      title: 'LLM 自动化渗透',
    },
    name: 'LlmAutomation',
    path: '/llm-penetration',
    children: [
      {
        meta: {
          title: '占位符 #1',
        },
        name: 'LlmAttackOrchestration',
        path: '/llm-penetration/orchestration',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
      },
      {
        meta: {
          title: '占位符 #2',
        },
        name: 'LlmPromptTemplates',
        path: '/llm-penetration/prompts',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
      },
      {
        meta: {
          title: '占位符 #3',
        },
        name: 'LlmExecutionLogs',
        path: '/llm-penetration/logs',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
      },
    ],
  },
];

export default routes;
