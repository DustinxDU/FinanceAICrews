# Frontend（Next.js）开发规范

> **Scope**：本文件适用于 `frontend/`（Next.js App Router）。目标：让任何 Agent 快速做出一致、可维护、可扩展的前端改动。

## TL;DR（必须遵守）

1. **App Router 为准**：页面放 `frontend/app/*`，布局用 `layout.tsx`，共享 UI 放 `frontend/components/*`。
2. **能不写 `use client` 就不写**：默认 Server Component；只有需要交互（state/effect/context/window/localStorage）才标记 Client Component。
3. **鉴权是客户端态**：Token 存在 `localStorage`（见 `frontend/lib/auth.ts`），服务端拿不到；需要用户态数据的页面/组件必须走 Client + `useAuth()`。
4. **API 调用优先走统一封装**：优先使用 `frontend/lib/api.ts`；若必须直接 `fetch`，用 `frontend/lib/apiClient.ts` 的 `buildApiUrl()` + `frontend/lib/utils.ts` 的 `authFetch()`。
5. **不要硬编码后端地址**：使用环境变量（见“环境变量”）；保持请求路径以 `/api/...` 开头以便本地 rewrite/生产网关接管。
6. **状态分层**：Context 只放全局"会话态/偏好"（Auth/LLM）；服务端数据不要塞 Context，优先放在 feature hooks（SWR/自定义 hook/必要时 React Query）。
7. **i18n 统一入口**：用 `useTranslations('namespace').t(key)` 或 `getTranslations('namespace')`；新增文案必须进 `frontend/messages/*.json`，不要散落硬编码。
8. **WebSocket 必须可清理**：组件卸载时关闭连接；断线重连要有退避/上限；消息解析失败要容错。
9. **样式与组件复用**：Tailwind + CSS 变量（`frontend/app/globals.css`）；基础组件优先用 `frontend/components/ui/*`（shadcn）。
10. **保持类型严格**：TS `strict: true`；避免 `any`，用 `unknown`/类型守卫/集中 types（`frontend/lib/types.ts`）。

## 关键入口（先看这些文件）

- `frontend/app/layout.tsx`：全局布局与 Provider（Auth/I18n/LLM）
- `frontend/app/globals.css`：全局样式与设计 token（CSS variables）
- `frontend/components/layout/AppLayout.tsx`：登录后主框架
- `frontend/components/layout/PublicLayout.tsx`：公开页布局
- `frontend/lib/api.ts`：主 API Client（带 Token/错误处理/超时）
- `frontend/lib/apiClient.ts`：`buildApiUrl()`（区分浏览器/SSR 的 base URL）
- `frontend/lib/auth.ts`：Token/用户信息存取
- `frontend/contexts/AuthContext.tsx`：登录/注册/登出与 `withAuth()`
- `frontend/hooks/*`：领域数据 Hook（Cockpit、Crew Builder、LLM…）

## 目录与职责

```
frontend/
├── app/            # 路由与页面（App Router）
├── components/     # 复用组件（ui/ 为 shadcn 基础组件）
├── contexts/       # 全局会话态/偏好（Auth/LLM）
├── hooks/          # 领域 hooks（页面逻辑复用）
├── lib/            # API 客户端、types、工具函数
├── messages/       # i18n 文案 JSON
└── public/         # 静态资源
```

## 页面与组件（App Router）

- **Server vs Client**：
  - 只要用到 `useState/useEffect/useAuth/window/localStorage` 等，就必须是 Client Component。
  - 不要为了“方便”把整页都改成 Client；优先把交互/状态下沉到小组件。
- **受保护页面**：
  - 页面级别优先用 `withAuth()`（见 `frontend/contexts/AuthContext.tsx`）。
  - 鉴权失败（401）由 `frontend/lib/api.ts` 与 `frontend/lib/utils.ts` 统一处理（清 token + 跳转登录）。

## API 调用与缓存

- **统一规则**：
  - 业务接口优先用 `frontend/lib/api.ts`（返回值类型集中在 `frontend/lib/types.ts`）。
  - 若要直接 `fetch`（例如 SWR fetcher/少量临时代码），必须使用：
    - URL：`buildApiUrl("/api/v1/...")`
    - 鉴权：`authFetch(url, options)`
- **错误处理**：
  - 对用户显示：使用友好文案（必要时 toast）。
  - 对开发调试：`console.error` 可保留，但不要把后端原始异常/堆栈直接展示在 UI。
- **不要引入第二套 API 基建**：避免再新增一个“新的 apiClient / fetch wrapper / token 存储方案”，先复用现有 `lib/*`。

## Auth（本项目约束）

- Token/用户信息存 `localStorage`（`financeai_token` / `financeai_user`）。
- 因为 Token 不在 Cookie：**SSR 无法代表用户调用需要鉴权的后端接口**。需要用户数据的页面请用 Client 组件 + `useAuth()`，并在 client side 触发请求。

## i18n（本项目约束）

- 使用 next-intl：
  - Server Component: `import {getTranslations} from 'next-intl/server'`
  - Client Component: `import {useTranslations} from 'next-intl'`
  - 文案：`t('namespace.key')`
  - 语言切换：通过 URL 前缀（如 `/en/`, `/zh-CN/`）由 middleware 处理
- 支持语言（16种）：`en`, `zh-CN`, `zh-TW`, `ja`, `ko`, `ms`, `id`, `vi`, `th`, `es`, `fr`, `de`, `ru`, `ar`, `hi`, `pt`
- 新增语言：
  1. 创建 `frontend/messages/<locale>.json`
  2. 添加 locale 到 `frontend/middleware.ts` 的 locales 数组
  3. 添加 locale 到 `frontend/i18n/routing.ts` 的 locales 数组
- 不要同时引入其他 i18n 库的运行时

## WebSocket / 流式接口

- WebSocket 基础 URL：`NEXT_PUBLIC_WS_URL`（默认 `ws://localhost:8000`），路径使用后端推荐路由（如 `/api/v1/realtime/ws/price`）。
- 必须做到：
  - `onclose` 清理状态 + 有界重连
  - `try/catch` 解析消息
  - `useEffect` cleanup 中关闭连接（避免泄漏）

## UI 与样式

- Tailwind 为主；复用 `cn()`（`frontend/lib/utils.ts`）合并 class。
- 设计 token 走 CSS 变量（`frontend/app/globals.css`），避免硬编码颜色值。
- 基础组件优先复用 `frontend/components/ui/*`；业务组件放对应 domain 目录（如 `components/crew-builder/*`）。

## 环境变量（不要硬编码）

- `NEXT_PUBLIC_API_URL`：浏览器侧 API 基址（留空时走同域 `/api/...`，本地用 `frontend/next.config.js` rewrites 代理到后端）
- `INTERNAL_API_URL`：SSR/Server Actions 可用的内网后端地址（可选，仅在需要时设置）
- `NEXT_PUBLIC_WS_URL`：WebSocket 基址（可选）

## E2E 测试（Playwright）

### 测试文件位置
- E2E 测试放在 `frontend/tests/e2e/*.spec.ts`
- 配置文件：`frontend/playwright.config.ts`

### 最佳实践

1. **避免外部 CDN 依赖**
   - Playwright 的 `setContent` 方法在处理外部 CDN 脚本时不可靠
   - 优先使用内联脚本或本地资源
   - 如必须使用 CDN，添加重试配置：`test.describe.configure({ retries: 2 })`

2. **隔离关注点**
   - 将逻辑测试与渲染测试分离
   - 响应式布局逻辑可以用纯 HTML/CSS/JS 测试，不需要依赖图表库
   ```typescript
   // ❌ 不好：响应式测试依赖 ECharts CDN
   await page.setContent(createChartPage(chartScript), { waitUntil: 'networkidle' });

   // ✅ 好：响应式测试使用纯 HTML
   await page.setContent(htmlWithResponsiveLogic, { waitUntil: 'domcontentloaded' });
   ```

3. **选择正确的 waitUntil 策略**
   - `domcontentloaded`：纯 HTML/内联脚本（最快）
   - `load`：需要等待图片/样式加载
   - `networkidle`：需要等待所有网络请求完成（最慢，容易超时）

4. **合理设置超时**
   ```typescript
   test.setTimeout(120_000);  // 测试级别超时
   await page.waitForFunction(() => condition, { timeout: 30000 });  // 单个等待超时
   ```

5. **截图用于调试**
   - 失败时自动截图（playwright.config.ts 已配置）
   - 关键步骤可手动截图：`await page.screenshot({ path: "test-results/step-name.png" })`

### 运行测试
```bash
# 运行所有 E2E 测试
npx playwright test

# 运行特定测试文件
npx playwright test tests/e2e/chart-components-visual.spec.ts

# 运行特定测试（按名称匹配）
npx playwright test -g "Chart height adapts"

# 查看测试报告
npx playwright show-report
```

## 提交前 Checklist

- [ ] 新增页面/组件没有滥用 `use client`（只把需要交互的部分变成 Client）
- [ ] API 调用复用 `frontend/lib/api.ts` 或 `buildApiUrl + authFetch`
- [ ] 文案已加入 `frontend/messages/*.json` 并使用 `useTranslations`/`getTranslations`
- [ ] WebSocket/定时器在 cleanup 中正确释放
- [ ] `npm run lint` 与 `npm run build` 能通过（至少本地自测一次）
- [ ] E2E 测试通过：`npx playwright test`

## 相关文档

- `AGENTS.md`（根目录总纲）
- `backend/AGENTS.md`（API 设计与错误规范）
- `docs/FINAL_ARCHITECTURE_DESIGN.md`（架构与数据层）

---

**最后更新**: 2025-01-10
**维护者**: Frontend Team
