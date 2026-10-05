/**
 * NOTES-001 r4 UI 负例回归（T-15/T-16，对应复审 F-R4-03/04）。
 *
 * R4-1：双客户端冲突后，B 加标签不得清掉未保存草稿（F-R4-04 主诉）。
 * R4-2：COMMIT 后丢 HTTP 响应 → 同意图（同 rid 同内容）原样重试即恢复。
 * R4-3：flush 成功后切换筛选再回来，显示的是已保存正文（刷新后 LoadDraft）。
 *
 * 前置：dev server + 后端 API 已就绪（NOTES_TEST_MODE 实例均可；只读+常规 CRUD）。
 */
import { test, expect, type Page } from '@playwright/test'

const TITLE = 'input[placeholder="Untitled"]'
const rows = (page: Page) => page.locator('button.note-row')

async function openApp(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'New note' }).waitFor({ timeout: 10000 })
  await page.waitForTimeout(700)
}

test('R4-1: 双客户端冲突后，B 加标签不清草稿', async ({ browser }) => {
  const ctxA = await browser.newContext()
  const pa = await ctxA.newPage()
  const ctxB = await browser.newContext()
  const pb = await ctxB.newPage()
  await openApp(pa)
  await openApp(pb)

  await rows(pa).first().click()
  await pa.waitForTimeout(500)
  await rows(pb).first().click()
  await pb.waitForTimeout(500)
  const original = await pa.locator(TITLE).inputValue()
  expect(original.length).toBeGreaterThan(0)

  // A 正常保存（revision +1）
  await pa.locator(TITLE).fill(original + ' [A]')
  await pa.waitForTimeout(300)
  await pa.getByRole('button', { name: 'Save' }).click()
  await pa.waitForTimeout(1200)

  // B 携陈旧 revision 保存 → 冲突，草稿保留
  await pb.locator(TITLE).fill(original + ' [B-draft]')
  await pb.waitForTimeout(300)
  await pb.getByRole('button', { name: 'Save' }).click()
  await pb.waitForTimeout(800)
  await expect(pb.locator(TITLE)).toHaveValue(original + ' [B-draft]')

  // B 加标签（复审主诉：TagAdded 路径曾清掉草稿并显示 Saved）
  await pb.getByRole('button', { name: 'Tag', exact: true }).click()
  await pb.locator('input[placeholder="tag name"]').fill('r4tag')
  await pb.keyboard.press('Enter')
  await pb.waitForTimeout(1200)

  await expect(pb.locator(TITLE)).toHaveValue(original + ' [B-draft]')
  await expect(pb.getByRole('button', { name: 'Save' })).toBeVisible()

  await ctxA.close()
  await ctxB.close()
})

test('R4-2: COMMIT 后丢响应，同意图重试恢复', async ({ page }) => {
  await openApp(page)
  await rows(page).first().click()
  await page.waitForTimeout(500)
  const t = page.locator(TITLE)
  const original = await t.inputValue()

  let dropped = false
  await page.route('**/api/notes/*', async route => {
    if (route.request().method() === 'PUT' && dropped === false) {
      dropped = true
      await route.fetch() // 服务端已提交
      route.abort() // 响应丢弃：UI 视角 = 网络失败
    } else {
      await route.continue()
    }
  })

  await t.fill(original + ' [LOST]')
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForTimeout(1000)
  // 服务端已提交但 UI 视为失败 → Save 仍在（dirty 保持、rid 未变）
  await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()

  // 原样重试 = 同一意图 → 服务端按意图重放返回成功
  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForTimeout(1500)
  await expect(page.getByText('Saved')).toBeVisible()
})

test('R4-3: flush 后切换筛选再回来，显示已保存正文', async ({ page }) => {
  await openApp(page)
  await rows(page).first().click()
  await page.waitForTimeout(500)
  const t = page.locator(TITLE)
  const original = await t.inputValue()
  const suffix = ` [R43-${Date.now()}]`

  await t.fill(original + suffix)
  await page.waitForTimeout(300)
  // 通过文件夹筛选触发 flush（成功路径）
  await page.getByRole('button', { name: 'personal' }).click()
  await page.waitForTimeout(800)
  await page.getByRole('button', { name: 'All', exact: true }).click()
  await page.waitForTimeout(800)
  await rows(page).filter({ hasText: original.slice(0, 12) }).first().click()
  await page.waitForTimeout(600)
  await expect(t).toHaveValue(original + suffix)

  // 清理：改回原标题并保存
  await t.fill(original)
  await page.waitForTimeout(200)
  await page.getByRole('button', { name: 'Save' }).click()
  await page.waitForTimeout(1000)
})
