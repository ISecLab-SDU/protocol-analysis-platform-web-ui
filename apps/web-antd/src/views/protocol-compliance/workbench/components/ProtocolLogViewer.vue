<template>
  <div class="protocol-log-viewer">
    <!-- 协议特定的日志展示容器 -->
    <div 
      :id="`log-viewer-${protocol}`"
      class="log-container bg-light-gray rounded-lg border border-dark/10 h-80 overflow-hidden font-mono text-xs relative"
    >
      <!-- 实时滚动日志容器 -->
      <div 
        ref="scrollContainer"
        class="h-full overflow-y-auto scrollbar-thin p-3"
      >
        <!-- 日志项 -->
        <div 
          v-for="(log, index) in displayLogs" 
          :key="`${protocol}-log-${log.id || index}`"
          class="log-item mb-1 leading-relaxed text-dark/80"
          :class="getLogItemClass(log)"
          v-html="formatLogContent(log)"
        >
        </div>
        
        <!-- 空状态提示 -->
        <div v-if="logs.length === 0" class="text-center text-dark/50 py-8">
          <div class="mb-2">
            <i class="fa fa-play-circle text-2xl text-primary/30"></i>
          </div>
          <div>测试未开始，等待日志输出...</div>
        </div>
      </div>
      
    </div>
    
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';

// Props
interface Props {
  protocol: 'SNMP' | 'RTSP' | 'MQTT';
  logs: Array<{
    id?: string;
    timestamp: string;
    type: 'INFO' | 'ERROR' | 'WARNING' | 'SUCCESS';
    content: string;
    [key: string]: any;
  }>;
  isActive: boolean;
  formatLogContent?: (log: any) => string;
}

const props = withDefaults(defineProps<Props>(), {
  formatLogContent: (log) => `[${log.timestamp}] ${log.content}`
});

// 组件引用
const scrollContainer = ref<HTMLElement>();

// 状态管理
const maxDisplayLogs = 1000; // 最多显示1000条日志，避免性能问题

// 显示的日志（限制数量以保证性能）
const displayLogs = computed(() => {
  if (!props.isActive) return [];
  
  // 如果日志数量超过限制，只显示最新的日志
  if (props.logs.length > maxDisplayLogs) {
    return props.logs.slice(-maxDisplayLogs);
  }
  
  return props.logs;
});

// 滚动到底部
function scrollToBottom() {
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight;
  }
}

// 自动滚动到底部
function autoScrollToBottom() {
  nextTick(() => {
    scrollToBottom();
  });
}

// 获取日志项样式
function getLogItemClass(log: any) {
  const baseClass = 'transition-colors duration-200';
  switch (log.type) {
    case 'ERROR':
      return `${baseClass} text-red-600 bg-red-50`;
    case 'WARNING':
      return `${baseClass} text-orange-600 bg-orange-50`;
    case 'SUCCESS':
      return `${baseClass} text-green-600 bg-green-50`;
    default:
      return `${baseClass} text-dark/80`;
  }
}

// 监听日志变化，自动滚动到底部
watch(() => props.logs.length, (newLength, oldLength) => {
  if (newLength > oldLength) {
    autoScrollToBottom();
  }
});

// 监听协议激活状态
watch(() => props.isActive, (isActive) => {
  if (isActive && props.logs.length > 0) {
    nextTick(() => {
      scrollToBottom();
    });
  }
});

// 组件挂载时初始化
onMounted(() => {
  // 如果有日志且是激活状态，滚动到底部
  if (props.logs.length > 0 && props.isActive) {
    nextTick(() => {
      scrollToBottom();
    });
  }
});
</script>

<style scoped>
.log-item {
  word-break: break-all;
  line-height: 1.4;
}

.protocol-log-viewer {
  position: relative;
}

/* 自定义滚动条 */
.scrollbar-thin::-webkit-scrollbar {
  width: 6px;
}

.scrollbar-thin::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 过渡动画 */
.transition-colors {
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}
</style>
