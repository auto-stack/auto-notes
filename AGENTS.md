# AGENTS.md — auto-notes 仓工作纪律

## 构建纪律：debug/dev 是默认，release 仅限性能测试与交付门

**平时开发一律用 debug（dev profile）。release 只允许出现在性能测试和最终交付验证。**

### 为什么专门写这条

`auto service` / `auto run` / `auto build` 的 Rust 后端服务路径**硬编码 `--release`**
（auto-man `crates/auto-man-runtime/src/http_service.rs` 的
`cargo run --release`；`automan.rs` 同款），无开关、无提示。产物静默落到
`auto-lang/target/generated-consumers/<hash>/release/`，而 release profile 下
cargo 增量编译默认关闭——**一行改动也要近全量 codegen + 链接，单轮 3–15 分钟**。
NOTES-002（2026-11-12/13）曾因此把每轮迭代拖到 15 分钟量级。

### 开发期正确姿势（dev profile；PLAN-1003 受管策略=行号表、依赖无调试信息、增量保留）

```bash
# 构建（必须在 rust-workspace/ 目录内执行——cargo 从 CWD 发现 .cargo/config.toml
# 的 target-dir 重定向；热增量下全后端 ~7s）
cd rust-workspace && cargo build -p auto-notes-30db9907-back

# 运行（直接执行 debug exe；生成 main 原生支持 AUTO_HTTP_PORT，无需服务 JSON）
D:/autostack/auto-lang/target/generated-consumers/<hash>/debug/auto-notes-30db9907-back.exe
#   env: AUTO_HTTP_PORT=<port>  NOTES_DATA_DIR=<隔离目录>  NOTES_TEST_MODE=1
#        AUTO_ALLOW_PARTIAL_DB=1   # NOTES-002 T-01 起必需（UploadRequest 端点装配检查）
```

- `generated-consumers/<hash>/debug/` 是**热增量缓存**（含 incremental/），不要随手清理；
  `release/` 可随时删除（本仓 2026-11-13 清理过一次，1.6G）。
- 辨别自己是否踩了 release：看服务日志里的 cargo 产物路径含 `release` 即是。
- 前端/UI 迭代同理优先快环（VM/`auto run` 前端热重载），避免每步都触发后端重建。

## 本仓关键操作事实

- 端口：前端 17818 / 后端 17819（`pac.at`）；测试电池自管端口时逐实例递增并
  只回收自有 PID 树（`taskkill /T /F /PID`）。
- 永久验证入口：`tests/basic/verify_standalone.py`（独立准备/启动门）、
  `verify_featurepack_service.py`（FP 服务面）、`verify_featurepack_editor.py
  --profile vue|vm`（双端编辑器面）、`verify_quick_card_assets.py
  --profile service|vue|vm`（NOTES-002 附件/快速卡片面）。
- 电池需要 `AUTO_ALLOW_PARTIAL_DB=1`（见上；已在脚本内 setdefault）。
- 后端 .at 改动会触发生成后端重建；`use api:` 类型改动同时影响 TS 客户端生成。
- 双轨语义差异（写作时警惕）：a2r 轨 `len()`=字节数、`sub()`=字符切片、
  裸表达式语句发射丢分号、跨模块 async 不发射 `.await`——非 ASCII 字符串
  一律避免索引数学（NOTES-002 §9 有 12 项实测清单）。
