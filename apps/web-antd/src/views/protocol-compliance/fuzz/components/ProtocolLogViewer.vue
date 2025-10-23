<template>
  <div class="protocol-log-viewer">
    <!-- 协议特定的日志展示容器 -->
    <div 
      :id="`log-viewer-${protocol}`"
      class="log-container bg-light-gray rounded-lg border border-dark/10 h-80 overflow-hidden font-mono text-xs"
    >
      <!-- 虚拟滚动容器 -->
      <div 
        ref="scrollContainer"
        class="virtual-scroll-container h-full overflow-y-auto scrollbar-thin"
        @scroll="handleScroll"
      >
        <!-- 上方占位符 -->
        <div :style="{ height: `${topPlaceholderHeight}px` }"></div>
        
        <!-- 可见区域的日志项 -->
        <div 
          v-for="(log, index) in visibleLogs" 
          :key="`${protocol}-log-${log.id || startIndex + index}`"
          class="log-item mb-1 leading-relaxed text-dark/80 px-3 py-1"
          :class="getLogItemClass(log)"
          v-html="formatLogContent(log)"
        >
        </div>
        
        <!-- 下方占位符 -->
        <div :style="{ height: `${bottomPlaceholderHeight}px` }"></div>
      </div>
      
      <!-- 实时状态指示器 -->
      <div 
        v-if="isRealTime && logs.length > 0"
        class="absolute top-2 right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full flex items-center"
      >
        <div class="w-2 h-2 bg-white rounded-full mr-1 animate-pulse"></div>
        实时更新
      </div>
    </div>
    
    <!-- 分页控制器 -->
    <div class="pagination-controls mt-4 flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <span class="text-sm text-dark/70">
          显示 {{ startIndex + 1 }}-{{ Math.min(startIndex + pageSize, totalLogs) }} 
          / 共 {{ totalLogs }} 条
        </span>
        
        <!-- 页面大小选择 -->
        <select 
          v-model="pageSize" 
          @change="updateVisibleLogs"
          class="text-sm border border-dark/20 rounded px-2 py-1"
        >
          <option :value="50">50条/页</option>
          <option :value="100">100条/页</option>
          <option :value="200">200条/页</option>
          <option :value="500">500条/页</option>
        </select>
      </div>
      
      <div class="flex items-center space-x-2">
        <!-- 跳转到最新 -->
        <button 
          v-if="!isAtBottom"
          @click="scrollToBottom"
          class="text-sm bg-primary text-white px-3 py-1 rounded hover:bg-primary/90"
        >
          跳转到最新
        </button>
        
        <!-- 暂停/恢复实时更新 -->
        <button 
          @click="toggleRealTime"
          class="text-sm px-3 py-1 rounded border"
          :class="isRealTime ? 'bg-orange-500 text-white' : 'bg-gray-500 text-white'"
        >
          {{ isRealTime ? '暂停实时' : '恢复实时' }}
        </button>
        
        <!-- 清空日志 -->
        <button 
          @click="clearLogs"
          class="text-sm bg-red-500 text-white px-3 py-1 rounded hover:bg-red-600"
        >
          清空日志
        </button>
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

// 虚拟滚动配置
const itemHeight = 24; // 每个日志项的高度（px）
const pageSize = ref(100); // 每页显示的日志数量
const scrollContainer = ref<HTMLElement>();

// 滚动状态
const scrollTop = ref(0);
const containerHeight = ref(320); // 容器高度
const isRealTime = ref(true);
const isAtBottom = ref(true);

// 计算可见区域
const visibleCount = computed(() => Math.ceil(containerHeight.value / itemHeight) + 5); // 多渲染5个缓冲
const startIndex = computed(() => Math.max(0, Math.floor(scrollTop.value / itemHeight) - 2));
const endIndex = computed(() => Math.min(props.logs.length, startIndex.value + visibleCount.value));

// 可见的日志项
const visibleLogs = computed(() => {
  if (!props.isActive) return [];
  return props.logs.slice(startIndex.value, endIndex.value);
});

// 占位符高度
const topPlaceholderHeight = computed(() => startIndex.value * itemHeight);
const bottomPlaceholderHeight = computed(() => 
  Math.max(0, (props.logs.length - endIndex.value) * itemHeight)
);

// 总日志数
const totalLogs = computed(() => props.logs.length);

// 滚动处理
function handleScroll(event: Event) {
  const target = event.target as HTMLElement;
  scrollTop.value = target.scrollTop;
  
  // 检查是否在底部
  const isNearBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - 50;
  isAtBottom.value = isNearBottom;
  
  // 如果不在底部，暂停实时更新
  if (!isNearBottom && isRealTime.value) {
    // 可以选择暂停实时更新，或者继续更新但不自动滚动
  }
}

// 滚动到底部
function scrollToBottom() {
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight;
    isAtBottom.value = true;
  }
}

// 更新可见日志
function updateVisibleLogs() {
  nextTick(() => {
    if (isAtBottom.value) {
      scrollToBottom();
    }
  });
}

// 切换实时更新
function toggleRealTime() {
  isRealTime.value = !isRealTime.value;
  if (isRealTime.value) {
    scrollToBottom();
  }
}

// 清空日志
function clearLogs() {
  // 发送清空事件给父组件
  emit('clear-logs');
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
  if (newLength > oldLength && isRealTime.value && isAtBottom.value) {
    nextTick(() => {
      scrollToBottom();
    });
  }
});

// 监听协议激活状态
watch(() => props.isActive, (isActive) => {
  if (isActive) {
    nextTick(() => {
      updateVisibleLogs();
    });
  }
});

// 组件挂载时初始化
onMounted(() => {
  if (scrollContainer.value) {
    containerHeight.value = scrollContainer.value.clientHeight;
  }
  
  // 如果有日志且是激活状态，滚动到底部
  if (props.logs.length > 0 && props.isActive) {
    nextTick(() => {
      scrollToBottom();
    });
  }
});

// 事件发射
const emit = defineEmits<{
  'clear-logs': [];
}>();
</script>

<style scoped>
.virtual-scroll-container {
  position: relative;
}

.log-item {
  min-height: 24px;
  word-break: break-all;
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
</style>
