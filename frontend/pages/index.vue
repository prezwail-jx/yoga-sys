<template>
  <main class="page-shell">
    <section class="hero">
      <p class="eyebrow">Yoga Studio Management</p>
      <h1>Yoga Sys</h1>
      <p class="summary">
        会员、卡项、交易和核销流程的管理系统骨架已经启动。当前前端先提供最小首页，
        后续可以继续补业务页面。
      </p>

      <div class="status-grid" aria-label="Project status">
        <div class="status-item">
          <span class="label">Frontend</span>
          <strong>Nuxt 3 running</strong>
        </div>
        <div class="status-item">
          <span class="label">Backend</span>
          <strong>FastAPI ready</strong>
        </div>
        <div class="status-item">
          <span class="label">Stage</span>
          <strong>Skeleton</strong>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.page-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
  color: #17211d;
  background:
    linear-gradient(135deg, rgba(221, 235, 225, 0.92), rgba(247, 249, 242, 0.86)),
    repeating-linear-gradient(90deg, rgba(23, 33, 29, 0.06) 0 1px, transparent 1px 56px);
  font-family: ui-serif, Georgia, "Times New Roman", serif;
}

.hero {
  width: min(920px, 100%);
  padding: 48px;
  border: 1px solid rgba(23, 33, 29, 0.14);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.68);
  box-shadow: 0 24px 70px rgba(23, 33, 29, 0.12);
}

.eyebrow {
  margin: 0 0 12px;
  color: #6a7b3f;
  font: 700 13px/1.2 ui-sans-serif, system-ui, sans-serif;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: clamp(48px, 8vw, 96px);
  line-height: 0.96;
  letter-spacing: 0;
}

.summary {
  max-width: 680px;
  margin: 24px 0 0;
  color: #445149;
  font: 18px/1.7 ui-sans-serif, system-ui, sans-serif;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 36px;
}

.status-item {
  padding: 18px;
  border: 1px solid rgba(23, 33, 29, 0.12);
  border-radius: 6px;
  background: rgba(247, 249, 242, 0.78);
}

.label {
  display: block;
  margin-bottom: 8px;
  color: #6b756f;
  font: 12px/1.2 ui-sans-serif, system-ui, sans-serif;
}

strong {
  font: 700 16px/1.3 ui-sans-serif, system-ui, sans-serif;
}

@media (max-width: 720px) {
  .page-shell {
    padding: 18px;
    place-items: stretch;
  }

  .hero {
    padding: 28px;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
