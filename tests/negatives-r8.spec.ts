/**
 * NOTES-001 r8 UI 负例回归（T-09/T-15/T-31 r8，对应复审 F-R8-01/F-R8-03）。
 *
 * R8-1：筛选导航后的稳定动作目标与后续保存（F-R8-03）——A 改名移出过滤
 *       结果后点击 B：导航 flush 刷新/重排后必须仍按目标 id 定位。旧实现
 *       被尾部旧下标覆盖（active_id 越界/错行），第一次保存后草稿
 *       revision 不刷新，第二次保存被自己的旧 revision 拒绝。断言：最终
 *       下标合法且身份正确、保存后 draft_revision 与服务器一致、连续两
 *       次保存都落地、全程无页面错误。
 * R8-2：删除/置顶动作失败的 UI 接收（F-R8-01）——合成 trigger 拒绝存储
 *       写入，UI 必须显示 "Action failed" 且不得刷新成假成功（行仍在/
 *       状态不变）；移除 trigger 后正常控制成功。需要 NOTES_TEST_MODE
 *       实例（经 /api/v1/test/setup 切到本用例自管隔离目录）；实例未开
 *       测试模式时显式跳过。
 */
import { test, expect, type Page } from '@playwright/test'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

const TITLE = 'input[placeholder="Untitled"]'
const rows = (page: Page) => page.locator('button.note-row')

async function openApp(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'New note' }).waitFor({ timeout: 10000 })
  await page.waitForTimeout(700)
}

async function storeState(page: Page) {
  return page.evaluate(async () => {
    const s = (await import('/src/stores/useNotesStore.ts')).useNotesStore()
    const o: Record<string, unknown> = {}
    for (const k of ['notes', 'active_id', 'draft_id', 'draft_title', 'draft_revision', 'dirty', 'conflict', 'action_error']) {
      o[k] = s[k].value
    }
    return o as {
      notes: Array<{ id: number }>
      active_id: number
      draft_id: number
      draft_title: string
      draft_revision: number
      dirty: boolean
      conflict: boolean
      action_error: string
    }
  })
}

async function api(page: Page, method: string, url: string, data?: unknown) {
  return page.evaluate(
    async ({ method, url, data }) => {
      const r = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: data === undefined ? undefined : JSON.stringify(data),
      })
      return r.json()
    },
    { method, url, data },
  )
}

/** 定位探针笔记（note_id → 数字 id / revision）。 */
async function findProbe(page: Page, noteId: string) {
  const list = await api(page, 'GET', '/api/v1/notes')
  const hit = list.find((n: { note_id: string }) => n.note_id === noteId)
  if (!hit) throw new Error('probe not found: ' + noteId)
  return hit
}

test('R8-1: filtered navigation keeps identity, revision and repeat saves (F-R8-03)', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await openApp(page)
  const b = await api(page, 'POST', '/api/v1/notes', { request_id: 'nav-B', title: 'NavProbe-B', body: 'base', folder: '' })
  await api(page, 'POST', '/api/v1/notes', { request_id: 'nav-A', title: 'NavProbe-A', body: 'base', folder: '' })
  const bNid = b.doc.note_id as string
  await page.reload()
  await page.waitForTimeout(700)

  await page.locator('input[placeholder="Search notes"]').fill('NavProbe')
  await page.waitForTimeout(650)
  await rows(page).filter({ hasText: 'NavProbe-A' }).click()
  await page.waitForTimeout(650)
  await page.locator(TITLE).fill('Removed-A')
  await page.waitForTimeout(300)

  // 点击 B：导航 flush 把 A 改名保存（A 移出过滤结果），工作集收缩为 [B]。
  await rows(page).filter({ hasText: 'NavProbe-B' }).click()
  await page.waitForTimeout(650)
  const afterNav = await storeState(page)
  expect(errors).toEqual([])
  expect(afterNav.notes.length).toBe(1)
  expect(afterNav.active_id).toBeLessThan(afterNav.notes.length)
  expect(afterNav.active_id).toBeGreaterThanOrEqual(0)
  expect(afterNav.notes[afterNav.active_id].id).toBe(afterNav.draft_id)
  expect(afterNav.draft_title).toBe('NavProbe-B')

  // 第一次保存：draft_revision 必须刷新到服务器 rev2（旧实现草稿停留 rev1）。
  await page.locator(TITLE).fill('NavProbe-B-one')
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  await page.waitForTimeout(900)
  const afterFirst = await storeState(page)
  const serverFirst = await findProbe(page, bNid)
  expect(errors).toEqual([])
  expect(afterFirst.dirty).toBe(false)
  expect(afterFirst.draft_revision).toBe(serverFirst.revision)
  expect(serverFirst.revision).toBe(2)
  expect(afterFirst.active_id).toBeLessThan(afterFirst.notes.length)
  expect(afterFirst.notes[afterFirst.active_id].id).toBe(afterFirst.draft_id)

  // 第二次保存：不得被自己的旧 revision 拒绝（F-R8-03 的核心反例）。
  await page.locator(TITLE).fill('NavProbe-B-two')
  await page.getByRole('button', { name: 'Save', exact: true }).click()
  await page.waitForTimeout(900)
  const afterSecond = await storeState(page)
  const serverSecond = await findProbe(page, bNid)
  expect(errors).toEqual([])
  expect(afterSecond.dirty).toBe(false)
  expect(serverSecond.title).toBe('NavProbe-B-two')
  expect(serverSecond.revision).toBe(3)
  expect(afterSecond.draft_revision).toBe(serverSecond.revision)

  // 清理：两个探针进回收站（不进活动列表，不污染后续 spec 基线）。
  await page.locator('input[placeholder="Search notes"]').fill('')
  await page.waitForTimeout(650)
  for (const t of ['Removed-A', 'NavProbe-B-two']) {
    await rows(page).filter({ hasText: t }).first().click()
    await page.waitForTimeout(400)
    await page.getByRole('button', { name: 'Delete' }).click()
    await page.waitForTimeout(300)
    await page.getByRole('button', { name: 'Delete' }).click()
    await page.waitForTimeout(700)
  }
  await expect(rows(page).filter({ hasText: 'NavProbe' })).toHaveCount(0)
})

test('R8-2: storage rejection surfaces in UI, no false success (F-R8-01)', async ({ page }) => {
  await openApp(page)
  // 记录服务器当前数据目录，用例结束必须还原——串行套件共享同一后端，
  // 留在临时目录会让后续 spec 看到空库。注意 /api/v1/status 返回的是
  // 双重编码 JSON 字符串。
  const statusRaw = await api(page, 'GET', '/api/v1/status')
  const orig = (typeof statusRaw === 'string' ? JSON.parse(statusRaw) : statusRaw).data_dir as string
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'notes-r8-')).replace(/\\/g, '/')
  try {
  const gate = await page.evaluate(
    async (dir) => {
      const r = await fetch('/api/v1/test/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data_dir: dir, legacy_file: dir + '/nope.json' }),
      })
      return r.json()
    },
    tmp,
  )
  if (gate === 'test-mode-disabled') {
    test.skip(true, 'dev server not in NOTES_TEST_MODE; R8-2 needs /api/v1/test/setup')
    return
  }
  expect(gate).toBe('ok')

  const { DatabaseSync } = await import('node:sqlite')
  const dbPath = path.join(tmp, 'inbox.db')
  const trig = (field: string) => {
    const db = new DatabaseSync(dbPath)
    db.exec(
      `CREATE TRIGGER reject_r8 BEFORE UPDATE OF ${field} ON notes BEGIN SELECT RAISE(ABORT,'independent metadata rejection'); END`,
    )
    db.close()
  }
  const untrig = () => {
    const db = new DatabaseSync(dbPath)
    db.exec('DROP TRIGGER reject_r8')
    db.close()
  }

  await page.reload()
  await page.waitForTimeout(700)
  // 在自管隔离目录里建探针。
  const created = await api(page, 'POST', '/api/v1/notes', {
    request_id: 'r8-base',
    title: 'R8FailProbe',
    body: 'x',
    folder: '',
  })
  const nid = created.doc.note_id as string
  await page.reload()
  await page.waitForTimeout(700)
  await rows(page).filter({ hasText: 'R8FailProbe' }).click()
  await page.waitForTimeout(650)

  // 删除失败：UI 显示 Action failed，行仍在，服务端仍 active。
  trig('state')
  await page.getByRole('button', { name: 'Delete' }).click()
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: 'Delete' }).click()
  await page.waitForTimeout(700)
  await expect(page.getByText('Action failed: change not saved')).toBeVisible()
  await expect(rows(page).filter({ hasText: 'R8FailProbe' })).toHaveCount(1)
  const st = await api(page, 'GET', `/api/v1/notes/${nid}`)
  expect(st.ok).toBe(true)
  expect(st.doc.state).toBe('active')
  untrig()

  // 置顶失败：同样可见且服务端 pinned 不变。
  trig('pinned')
  await page.getByRole('button', { name: 'Pin note' }).click()
  await page.waitForTimeout(700)
  await expect(page.getByText('Action failed: change not saved')).toBeVisible()
  const st2 = await api(page, 'GET', `/api/v1/notes/${nid}`)
  expect(st2.doc.pinned).toBe(false)
  untrig()

  // 正常控制：删除成功，行消失，进入回收站。
  await page.getByRole('button', { name: 'Delete' }).click()
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: 'Delete' }).click()
  await page.waitForTimeout(700)
  await expect(page.getByText('Action failed: change not saved')).toHaveCount(0)
  await expect(rows(page).filter({ hasText: 'R8FailProbe' })).toHaveCount(0)
  const st3 = await api(page, 'GET', `/api/v1/notes/${nid}`)
  expect(st3.ok).toBe(true)
  expect(st3.doc.state).toBe('trashed')
  } finally {
    // 还原共享后端的数据目录（无论断言成败），后续 spec 依赖原目录状态。
    await page.evaluate(
      async ({ dir }) => {
        await fetch('/api/v1/test/setup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ data_dir: dir, legacy_file: dir + '/nope.json' }),
        })
      },
      { dir: orig },
    )
    await page.reload()
    await page.waitForTimeout(500)
  }
})
