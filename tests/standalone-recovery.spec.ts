/**
 * NOTES-004 N-04（Vue profile）：正常/强杀退出后的重开与下一次真实编辑保存。
 *
 * 由 tests/basic/verify_standalone.py 编排：
 *   STAGE=before — 真实 UI 建笔记（中文/引号/换行正文）→ Save → API 断言落库
 *   （python 侧随后强杀后端 → 同数据目录重启 → 再进本规格）
 *   STAGE=after  — 真实 UI 重开 → 正文/标题逐字保真 → 追加编辑 → Save →
 *                  API 断言 revision 推进、正文更新（下一次保存成功）
 *
 * 前置条件：隔离后端 + vite dev 已就绪（NOTES_URL）。
 */
import { test, expect, type Page } from '@playwright/test'

const TITLE = 'input[placeholder="Untitled"]'
const BODY = 'textarea[placeholder="Start writing..."]'
const rows = (page: Page) => page.locator('button.note-row')
const saveBtn = (page: Page) => page.getByRole('button', { name: 'Save' })

const NOTE_TITLE = process.env.N04_TITLE || 'N04-恢复探针'
// 中文 + 双引号 + 单引号 + 换行：编辑器内容与磁盘保真的区分性输入
const BODY_BEFORE = `第一行：恢复探针正文
第二行 "双引号" 与 '单引号' 混排
第三行：强杀前落库`

async function findNote(page: Page, title: string) {
  const res = await page.request.get('/api/notes')
  const notes = (await res.json()) as Array<Record<string, any>>
  return notes.find((n) => (n.title || '') === title)
}

test('N-04 before: 新建+中文正文+保存落库', async ({ page }) => {
  if (process.env.STAGE !== 'before') test.skip(true, 'before 阶段专用')
  await page.goto('/')
  await page.getByRole('button', { name: 'New note' }).waitFor({ timeout: 10000 })
  await page.waitForTimeout(800) // 等 store.Init 的 API 调用 + 渲染
  await page.getByRole('button', { name: 'New note' }).click()
  await page.waitForTimeout(800)
  await page.locator(TITLE).fill(NOTE_TITLE)
  await page.locator(BODY).fill(BODY_BEFORE)
  await page.waitForTimeout(300)
  await expect(saveBtn(page)).toBeVisible()
  await saveBtn(page).click()
  await page.waitForTimeout(1500)
  const note = await findNote(page, NOTE_TITLE)
  expect(note, '保存后 API 可见').toBeTruthy()
  expect(note!.body).toBe(BODY_BEFORE) // 磁盘逐字保真（引号/换行）
  expect(Number(note!.revision)).toBeGreaterThanOrEqual(1)
})

test('N-04 after: 强杀重启后正文保真+下一次保存推进 revision', async ({ page }) => {
  if (process.env.STAGE !== 'after') test.skip(true, 'after 阶段专用')
  await page.goto('/')
  await page.getByRole('button', { name: 'New note' }).waitFor({ timeout: 10000 })
  await page.waitForTimeout(800)
  // 重开：真实 UI 导航到目标笔记（列表里按标题点击）
  await rows(page).filter({ hasText: NOTE_TITLE }).first().click()
  await page.waitForTimeout(800)
  await expect(page.locator(TITLE)).toHaveValue(NOTE_TITLE)
  // 正文逐字保真（重启后）
  const bodyValue = await page.locator(BODY).inputValue()
  expect(bodyValue).toBe(BODY_BEFORE)

  // 下一次真实编辑必须成功：追加一行后保存
  const appended = BODY_BEFORE + '\n第四行：重启后追加（下一次保存）'
  await page.locator(BODY).fill(appended)
  await page.waitForTimeout(300)
  await expect(saveBtn(page)).toBeVisible()
  await saveBtn(page).click()
  await page.waitForTimeout(1500)

  const note = await findNote(page, NOTE_TITLE)
  expect(note, '下一次保存后 API 可见').toBeTruthy()
  expect(note!.body).toBe(appended)
  const beforeRev = Number(process.env.N04_REV_BEFORE || '1')
  expect(Number(note!.revision)).toBeGreaterThan(beforeRev) // revision 推进
  // UI 无冲突横幅（保存成功分支）
  await expect(page.getByText('Action failed: change not saved')).toHaveCount(0)
})
