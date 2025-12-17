<!--
 * Void System Frontend - AI Message Component
 * -----------------------------
 * AI 消息组件，支持打字机效果和Markdown渲染
-->

<template>
  <div class="ai-message">
    <div class="ai-avatar">
      <i class="el-icon-robot"></i>
    </div>
    <div class="ai-content" v-html="displayContent"></div>
    <div class="ai-loading" v-if="isLoading">
      <i class="el-icon-loading"></i>
      <span>正在思考...</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AIMessage',
  props: {
    /**
     * AI消息内容
     */
    content: {
      type: String,
      default: ''
    },
    /**
     * 是否启用打字机效果
     */
    typewriter: {
      type: Boolean,
      default: true
    },
    /**
     * 打字机效果速度（毫秒/字符）
     */
    typeSpeed: {
      type: Number,
      default: 30
    },
    /**
     * 是否正在加载
     */
    loading: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      /**
       * 显示的内容（用于打字机效果）
       */
      displayContent: '',
      /**
       * 内部加载状态
       */
      isLoading: this.loading,
      /**
       * 打字机定时器
       */
      typewriterTimer: null,
      /**
       * 内容索引（用于打字机效果）
       */
      contentIndex: 0
    };
  },
  watch: {
    /**
     * 监听content变化，重新开始打字机效果
     */
    content: {
      handler(newContent) {
        if (this.typewriter) {
          this.startTypewriter(newContent);
        } else {
          this.displayContent = newContent;
        }
      },
      immediate: true
    },
    /**
     * 监听loading变化
     */
    loading: {
      handler(newLoading) {
        this.isLoading = newLoading;
      },
      immediate: true
    }
  },
  methods: {
    /**
     * 开始打字机效果
     */
    startTypewriter(newContent) {
      // 清除之前的定时器
      if (this.typewriterTimer) {
        clearInterval(this.typewriterTimer);
      }
      
      this.displayContent = '';
      this.contentIndex = 0;
      
      // 如果内容为空，直接结束
      if (!newContent) {
        this.isLoading = false;
        return;
      }
      
      // 开始打字机效果
      this.typewriterTimer = setInterval(() => {
        if (this.contentIndex < newContent.length) {
          this.displayContent += newContent[this.contentIndex];
          this.contentIndex++;
        } else {
          // 结束打字机效果
          clearInterval(this.typewriterTimer);
          this.typewriterTimer = null;
          this.isLoading = false;
        }
      }, this.typeSpeed);
    },
    /**
     * 清除打字机效果
     */
    clearTypewriter() {
      if (this.typewriterTimer) {
        clearInterval(this.typewriterTimer);
        this.typewriterTimer = null;
      }
    }
  },
  beforeUnmount() {
    // 清除定时器
    this.clearTypewriter();
  }
};
</script>

<style scoped>
.ai-message {
  display: flex;
  align-items: flex-start;
  margin-bottom: 16px;
  position: relative;
}

.ai-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #6366f1;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  font-size: 20px;
  flex-shrink: 0;
}

.ai-content {
  flex: 1;
  padding: 12px 16px;
  background-color: #1e293b;
  border-radius: 8px;
  line-height: 1.6;
  word-break: break-word;
  color: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}

/* Markdown样式 */
.ai-content h1,
.ai-content h2,
.ai-content h3,
.ai-content h4,
.ai-content h5,
.ai-content h6 {
  margin: 12px 0;
  font-weight: 600;
  color: #f1f5f9;
}

.ai-content h1 {
  font-size: 1.5rem;
  border-bottom: 1px solid #334155;
  padding-bottom: 4px;
}

.ai-content h2 {
  font-size: 1.25rem;
}

.ai-content h3 {
  font-size: 1.1rem;
}

.ai-content pre {
  background-color: #0f172a;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 12px 0;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.9rem;
}

.ai-content code {
  background-color: #0f172a;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.9rem;
  color: #f472b6;
}

.ai-content ul,
.ai-content ol {
  margin: 12px 0;
  padding-left: 24px;
}

.ai-content li {
  margin-bottom: 4px;
}

.ai-content ul li::marker {
  color: #6366f1;
}

.ai-content ol li::marker {
  color: #6366f1;
  font-weight: 500;
}

.ai-content strong {
  font-weight: 600;
  color: #f1f5f9;
}

.ai-content em {
  font-style: italic;
  color: #cbd5e1;
}

.ai-content a {
  color: #60a5fa;
  text-decoration: none;
  transition: color 0.2s;
}

.ai-content a:hover {
  color: #3b82f6;
  text-decoration: underline;
}

.ai-content blockquote {
  border-left: 4px solid #6366f1;
  padding-left: 12px;
  margin: 12px 0;
  color: #cbd5e1;
  font-style: italic;
}

.ai-content hr {
  border: none;
  border-top: 1px solid #334155;
  margin: 20px 0;
}

.ai-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #cbd5e1;
  font-size: 0.9rem;
  margin-top: 8px;
  margin-left: 52px;
}

.ai-loading i {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
