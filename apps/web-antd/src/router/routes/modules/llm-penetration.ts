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
        name: 'UndefinedRoute1',
        path: '/llm-penetration/undefined1',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
      },
      {
        meta: {
          title: '占位符 #2',
        },
        name: 'LlmPromptTemplates',
        path: '/llm-penetration/undefined2',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
      },
      {
        meta: {
          title: '占位符 #3',
        },
        name: 'LlmExecutionLogs',
        path: '/llm-penetration/undefined3',
        component: () => import('#/views/placeholders/menu-placeholder.vue'),
      },
    ],
  },
];

export default routes;
