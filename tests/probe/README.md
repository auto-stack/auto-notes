# T-00 持久化能力探针（NOTES-001）

目的、结论与跨仓缺口见 [CAPABILITY-REPORT.md](CAPABILITY-REPORT.md)。
本目录保存探针源码与原始证据；探针模块**不在 src/back**（采证已完成，
避免混入产品代码；复现时按下述步骤临时放回）。

## 文件

- `probe.at` — 探针实现体（`probe_cap_body`/`probe_json_body` 两个 pub fn）
- `evidence/*.json` — 原始 HTTP 采证（双路径 + 崩溃重启）

## 复现步骤（worktree 根执行）

1. 把 `probe.at` 复制回 `src/back/probe.at`。
2. 在 `src/back/api.at` 的 `use db` 后加：

   ```at
   /// T-00 能力电池
   #[api(method = "GET", path = "/api/probe/cap")]
   pub fn probe_cap() str {
       return db.probe_cap()
   }

   /// T-00 json 模块面探针
   #[api(method = "GET", path = "/api/probe/json")]
   pub fn probe_json() str {
       return db.probe_json()
   }
   ```

3. 在 `src/back/db.at` 的 `use api: Note` 后加：

   ```at
   use probe

   pub fn probe_cap() str {
       return probe.probe_cap_body()
   }

   pub fn probe_json() str {
       return probe.probe_json_body()
   }
   ```

   （生成器约束：api.at 端点必须在 db.at 有同名函数，否则拒绝生成。）

4. `auto run -r vm`（或 `auto run`；后端为同一 a2r 生成物）后：

   ```sh
   curl http://localhost:17819/api/probe/cap > cap.json
   curl http://localhost:17819/api/probe/json > json.json
   # 崩溃重启：taskkill /F /PID <17819监听PID>，重启后再取一次 cap.json，
   # restart.marker.previous 应等于上次 restart.marker.write 的值。
   ```

5. 采证完成移除探针布线，保持 `src/back` 干净。
