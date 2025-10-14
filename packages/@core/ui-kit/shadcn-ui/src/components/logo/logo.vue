<script setup lang="ts">
interface Props {
  /**
   * @zh_CN 是否收起文本
   */
  collapsed?: boolean;
  /**
   * @zh_CN Logo 跳转地址
   */
  href?: string;
  /**
   * @zh_CN Logo 文本
   */
  text: string;
  /**
   * @zh_CN Logo 主题
   */
  theme?: string;
}

defineOptions({
  name: 'VbenLogo',
});

withDefaults(defineProps<Props>(), {
  collapsed: false,
  href: 'javascript:void 0',
  theme: 'light',
});
</script>

<template>
  <div :class="theme" class="flex h-full items-center justify-center text-lg">
    <a
      :class="$attrs.class"
      :href="href"
      class="flex h-full items-center justify-center overflow-hidden px-3 text-lg leading-normal transition-all duration-500"
    >
      <template v-if="!collapsed">
        <slot name="text">
          <span
            class="text-foreground truncate text-nowrap text-center font-semibold"
          >
            {{ text }}
          </span>
        </slot>
      </template>
    </a>
  </div>
</template>
