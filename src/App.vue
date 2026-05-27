<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import Page1 from './pages/Page1.vue'
import Page2 from './pages/Page2.vue'
import Page3 from './pages/Page3.vue'
import Page4 from './pages/Page4.vue'

const pages = [
  { id: 'page1', label: '全国总览', eyebrow: 'Page 01', component: Page1 },
  { id: 'page2', label: '房价变化', eyebrow: 'Page 02', component: Page2 },
  { id: 'page3', label: '人口流动', eyebrow: 'Page 03', component: Page3 },
  { id: 'page4', label: '耦合关系', eyebrow: 'Page 04', component: Page4 }
]

const currentPage = ref('page1')
let observer

function scrollToPage(pageId) {
  currentPage.value = pageId
  document.getElementById(pageId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
      if (visible?.target?.id) {
        currentPage.value = visible.target.id
      }
    },
    {
      rootMargin: '-18% 0px -58% 0px',
      threshold: [0.08, 0.2, 0.45]
    }
  )

  pages.forEach((page) => {
    const section = document.getElementById(page.id)
    if (section) observer.observe(section)
  })
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<template>
  <div class="app-frame">
    <nav class="app-nav" aria-label="页面导航">
      <div class="app-brand">
        <span>中国房价与人口流动</span>
      </div>
      <div class="app-tabs" role="tablist">
        <button
          v-for="page in pages"
          :key="page.id"
          type="button"
          :class="{ active: currentPage === page.id }"
          @click="scrollToPage(page.id)"
        >
          <small>{{ page.eyebrow }}</small>
          <span>{{ page.label }}</span>
        </button>
      </div>
    </nav>
    <section v-for="page in pages" :id="page.id" :key="page.id" class="app-section">
      <component :is="page.component" />
    </section>
  </div>
</template>

<style>
:root {
  color: #172033;
  background: #f5f7fa;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(245, 247, 250, 0.95)),
    #f5f7fa;
  scroll-behavior: smooth;
}

button,
select,
input {
  font: inherit;
}

button {
  cursor: pointer;
}

.app-frame {
  min-height: 100vh;
}

.app-section {
  min-height: calc(100vh - 72px);
  scroll-margin-top: 74px;
}

.app-section + .app-section {
  border-top: 1px solid rgba(214, 221, 232, 0.72);
}

.app-nav {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px max(16px, calc((100vw - 1440px) / 2 + 16px));
  border-bottom: 1px solid rgba(214, 221, 232, 0.9);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(16px);
}

.app-brand {
  color: #172033;
  font-size: 14px;
  font-weight: 800;
  white-space: nowrap;
}

.app-tabs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
}

.app-tabs button {
  display: grid;
  min-width: 112px;
  min-height: 46px;
  padding: 7px 12px;
  border: 1px solid #d6dde8;
  border-radius: 8px;
  background: #ffffff;
  color: #475569;
  text-align: left;
}

.app-tabs button small {
  color: #7b8798;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.app-tabs button span {
  font-size: 14px;
  font-weight: 800;
}

.app-tabs button.active {
  border-color: #15616d;
  background: #15616d;
  color: #ffffff;
}

.app-tabs button.active small {
  color: rgba(255, 255, 255, 0.72);
}

@media (max-width: 760px) {
  .app-nav {
    align-items: stretch;
    flex-direction: column;
  }

  .app-brand {
    white-space: normal;
  }

  .app-tabs button {
    flex: 1 1 calc(50% - 4px);
    min-width: 0;
  }

  .app-tabs {
    flex-wrap: wrap;
    overflow-x: visible;
  }
}
</style>
