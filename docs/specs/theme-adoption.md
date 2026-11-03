# 主题采纳合同（theme-adoption）

> 来源：auto-os/PLAN-056（2026-11-03 work 候选 T-02；本仓候选见 git log
> plan-056 提交）。宿主主合同：auto-os `docs/specs/shell/host-theme-policy-and-delivery.md`；
> 本批登记页：auto-os `docs/specs/apps/product-theme-batch-056.md`。

## 消费形态

- **固定快照**：`vendor/themes` = UI 管理渠道发布的官方主题包快照
  （`themes` 0.2.0，内容 digest
  `9fa07742dc68aa5377ae06cb2d966386002063f184c515b6c5dddf8a6bef838e`，
  per-file sha256 与源包校验同律）。快照不可二次编辑、非第二权威源；
  升级 = UI 发新快照替换 + 本仓重验。
- **pac 声明**：`dep themes { path: "vendor/themes" }`；`theme` 键保持
  缺省 = **follow 宿主**（宿主策略完整快照 > 本 design 默认 > legacy 回退；
  显式值会以 pac 优先级压过跟随——本仓原有显式 theme 键已按此退役/保持缺省）。
- **源内导入**：`use themes.themes: Auto`——缺此行包主题不入收集链，
  design/follow 候选按 C-11 未注册整帧拒绝（031 合同）。
- **design 默认**：dark_mode 位派生（默认 true=暗色，与退役 pac `theme:"dark"` 语义等价）；
  `dark_mode` 模型位语义沿 458 机制（family 链激活时由已提交策略派生 mode
  驱动，被拒候选的 legacy 翻转不得污染）。

## 豁免与不变量

- 外观面板四色板（indigo/coral/ocean/sage，`bg-indigo-500` 等固定类）与顶栏 icon_btn/primary_btn 既有配方为 App 命名空间豁免；store `dark_mode`/`accent_color` 业务语义原样。
- 原完整适用业务门在采纳前后保持：desktop_mcp 11 passed/2 failed/1 skipped（2 fail=种子计数与快照标签，A/B 基线逐项同现=非本包回归；T5 主题字段全过）+ 015-notes.autotest **19/19**（含 T11 Light/Dark 真实切换、T12 主题色初始值）+ standalone follow probe **5/5**（像素级）

## 验证与测试设施（os-056 冻结工具链：auto.exe 5858593b + auto-ui-tool 3493e746）

- desktop_mcp 启动等待 30→420s + AUTOUI_MCP_PORT 钉定；autotest URL env 化 + 就绪 180→420s（工具链代次每 boot 再生成 107–348s 实测；检查不变量未动）
- NOTES_DATA_DIR 隔离与 AutoDown 准备门原样；2 fail 需在 final review 复核是否列入产品自身待办（非 056 义务）。
