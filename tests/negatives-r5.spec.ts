/**
 * NOTES-001 r5 UI 负例回归（T-19，对应复审 F-R5-03 / SD-14）。
 *
 * R5-1：Recover 不得自我覆盖——当前 dirty 草稿入另一槽，两份内容都可恢复
 *       （旧实现 Recover 先 StashDraft 把正要装载的暂存内容覆盖掉）。
 * R5-2：Discard = 显式取最新服务器版本（旧实现只 LoadDraft 陈旧工作集）。
 * R5-3：COMMIT 后丢响应 → 继续编辑再保存：新意图（新 rid）+ 未确认提交
 *       裁决（服务器内容 = 旧意图 ⇒ 采用其 revision 重试），新草稿可保存。
 *
 * 自包含：各自建探针笔记并在结尾两步删除（回收站不进活动列表，不污染
 * 后续 smoke 的净库基线断言）。
 */
import { test, expect, type Page } from '@playwright/test'

const TITLE = 'input[placeholder="Untitled"]'
const rows = (page: Page) => page.locator('button.note-row')

async function openApp(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'New note' }).waitFor({ timeout: 10000 })
  await page.waitForTimeout(700)
}

/** 新建探针笔记并落库（New note → 标题 → Save），返回标题。 */
async function createProbe(page: Page, name: string): Promise<string> {
  const title = `${name} ${Date.now()}`
  await page.getByRole('button', { name: 'New note' }).click()
  await page.waitForTimeout(700)
  await page.locator(TITLE).fill(title)
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForTimeout(900)
  await expect(page.getByText('Saved')).toBeVisible()
  return title
}

/** 外部写者推进指定笔记的 revision（按标题前缀定位）。 */
async function externalBump(page: Page, titlePrefix: string, newTitle: string) {
  await page.evaluate(async ({ titlePrefix, newTitle }) => {
    const res = await fetch('/api/notes')
    const notes = (await res.json()) as Array<{ id: number; revision: number; title: string }>
    const target = notes.find(n => n.title.startsWith(titlePrefix))
    if (!target) throw new Error('probe note not found: ' + titlePrefix)
    const res2 = await fetch(`/api/notes/${target.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        expected_revision: target.revision,
        title: newTitle,
        body: 'external writer',
        request_id: `r5-ext-${Date.now()}-${Math.random()}`,
      }),
    })
    if (!res2.ok) throw new Error('external bump failed: ' + res2.status)
  }, { titlePrefix, newTitle })
}

/** 两步删除当前选中的探针笔记（回收站不进活动列表）。 */
async function deleteCurrent(page: Page) {
  await page.getByRole('button', { name: 'Delete' }).click()
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: 'Delete' }).click()
  await page.waitForTimeout(700)
}

test('R5-1: Recover 保全两份草稿（当前 dirty 入另一槽）', async ({ page }) => {
  await openApp(page)
  const titleA = await createProbe(page, 'R5A')
  const titleB = await createProbe(page, 'R5B')
  const t = page.locator(TITLE)

  // 在 A 上制造冲突草稿：本地陈旧 revision + 外部写者推进
  await rows(page).filter({ hasText: titleA }).first().click()
  await page.waitForTimeout(500)
  await t.fill(titleA + ' [precious]')
  await page.waitForTimeout(300)
  await externalBump(page, 'R5A', titleA + ' [server-ext]')
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForTimeout(900)
  await expect(page.getByRole('button', { name: 'Save' })).toBeVisible() // 冲突保持

  // 冲突下导航到 B：A 草稿入恢复槽
  await rows(page).filter({ hasText: titleB }).first().click()
  await page.waitForTimeout(700)
  await expect(page.getByText('Unsaved draft kept aside', { exact: true })).toBeVisible()

  // B 上继续输入（dirty）→ Recover：必须显示 A 草稿，B 草稿入第二槽不丢
  await t.fill(titleB + ' [shopping]')
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: 'Recover' }).click()
  await page.waitForTimeout(700)
  await expect(t).toHaveValue(titleA + ' [precious]')
  await expect(page.getByText('Unsaved draft kept aside (2nd)')).toBeVisible()

  // 再恢复第二槽：B 草稿回来（A 草稿此刻入另一槽，仍不丢失）
  await page.getByRole('button', { name: 'Recover' }).click()
  await page.waitForTimeout(700)
  await expect(t).toHaveValue(titleB + ' [shopping]')
  await expect(page.getByText('Unsaved draft kept aside', { exact: true })).toBeVisible()

  // 清理：放弃 B 草稿 → 删除 A、B 探针
  await page.getByRole('button', { name: 'Discard' }).click()
  await page.waitForTimeout(800)
  await rows(page).filter({ hasText: titleA }).first().click()
  await page.waitForTimeout(500)
  await deleteCurrent(page)
  await rows(page).filter({ hasText: titleB }).first().click()
  await page.waitForTimeout(500)
  await deleteCurrent(page)
})

test('R5-2: Discard 显示最新服务器版本（非陈旧缓存）', async ({ page }) => {
  await openApp(page)
  const titleC = await createProbe(page, 'R5C')
  const t = page.locator(TITLE)
  const serverTitle = `${titleC} [server-truth]`

  await rows(page).filter({ hasText: titleC }).first().click()
  await page.waitForTimeout(500)
  // 本地陈旧草稿 → 外部写者推进 → 本地保存必冲突
  await t.fill(titleC + ' [stale-local]')
  await page.waitForTimeout(300)
  await externalBump(page, 'R5C', serverTitle)
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForTimeout(900)
  await expect(page.getByRole('button', { name: 'Discard' })).toBeVisible()

  // Discard = 显式选择服务器版本：显示外部写者的最新内容并 Saved
  await page.getByRole('button', { name: 'Discard' }).click()
  await page.waitForTimeout(900)
  await expect(t).toHaveValue(serverTitle)
  await expect(page.getByText('Saved')).toBeVisible()

  await deleteCurrent(page)
})

test('R5-3: COMMIT 丢响应后继续编辑，新意图可保存', async ({ page }) => {
  await openApp(page)
  const titleD = await createProbe(page, 'R5D')
  const t = page.locator(TITLE)

  await rows(page).filter({ hasText: titleD }).first().click()
  await page.waitForTimeout(500)

  let dropped = false
  // 保存走 /api/notes/:id/result（SD-14）；只拦首个 PUT（C1），其余放行
  await page.route('**/api/notes/*/result', async route => {
    if (route.request().method() === 'PUT' && dropped === false) {
      dropped = true
      await route.fetch() // 服务端已提交 C1
      route.abort() // 响应丢弃：UI 视角 = 网络失败
    } else {
      await route.continue()
    }
  })

  // C1 保存：服务端提交但 UI 视为失败（handler 中断，rid+意图已绑定）
  await t.fill(titleD + ' [c1-unconfirmed]')
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForTimeout(1000)
  await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()

  // 继续编辑为 C2 → 保存：轮换新意图 → revision 冲突 → 裁决（服务器=C1
  // 的内容）→ 采用服务器 revision 重试新意图 → 成功
  await t.fill(titleD + ' [c2-final]')
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForTimeout(1800)
  await expect(page.getByText('Saved')).toBeVisible()
  await expect(t).toHaveValue(titleD + ' [c2-final]')

  // 服务器终态 = C2（旧提交 C1 被裁决吸收，新意图落地，无内容丢失）
  const server = await page.evaluate(async (prefix) => {
    const res = await fetch('/api/notes')
    const notes = (await res.json()) as Array<{ title: string }>
    const target = notes.find(n => n.title.startsWith(prefix))
    return target ? target.title : 'NOT-FOUND'
  }, 'R5D')
  expect(server).toBe(titleD + ' [c2-final]')

  await deleteCurrent(page)
})
