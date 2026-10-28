/**
 * NOTES-001 r9 UI 负例回归（T-04/T-09/T-15 r9，对应复审 F-R9-01/F-R9-02 与
 * F-R8-01 的掩盖检查）。
 *
 * R9-1（F-R9-01）：pin 失败必须是 HTTP 200 结构化结果信封，而不是 ?Note 的
 *       None→HTTP 404 异常——合成 trigger 拒绝 pinned UPDATE，点击 Pin 必须真实
 *       发出 PATCH、收到 200+ok:false、显示对应当前动作的错误横幅
 *       （action_error='pin'），全程无页面错误；移除 trigger 后同按钮成功。
 *       旧实现 404 直接抛异常，错误分支永远不执行——以「请求确实发出 +
 *       无 pageerror + 横幅对应」区分。
 * R9-2（F-R9-02，TagAdded）：dirty 正文 flush 成功后标签被拒绝——正文已落库
 *       （rev2），UI dirty=false 且 draft_revision 已在 flush 成功块同步；
 *       解除拒绝后再次保存不得携带旧 revision 自我冲突，新标题落地。
 * R9-3（F-R9-02，TagRemoved）：同 R9-2 的删除标签入口。
 * R9-4（F-R9-01 掩盖检查）：删除失败残留的 conflict 不得吞掉后续 pin——旧实现
 *       的 if .conflict == false 门禁让 pin 根本不发出（横幅沿用删除失败的，
 *       断言假绿）；本用例断言 pin 点击后确实发出新 PATCH 且横幅对应 pin。
 * R9-5（成功对照）：编辑→加标签→再编辑→保存的正常序列——flush 成功块同步
 *       revision 后，标签成功与后续保存都落地（rev2→rev3）。
 *
 * 需要 NOTES_TEST_MODE 实例（经 /api/v1/test/setup 切到本用例自管隔离目录）；
 * 实例未开测试模式时显式跳过。
 */
import { test, expect, type Page } from '@playwright/test'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

const TITLE = 'input[placeholder="Untitled"]'
const rows = (page: Page) => page.locator('button.note-row')
const BANNER = 'Action failed: change not saved'

type Call = { method: string; url: string; status?: number; ok?: boolean }

async function openApp(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'New note' }).waitFor({ timeout: 10000 })
  await page.waitForTimeout(700)
}

async function storeState(page: Page) {
  return page.evaluate(async () => {
    const s = (await import('/src/stores/useNotesStore.ts')).useNotesStore()
    const o: Record<string, unknown> = {}
    for (const k of ['draft_id', 'draft_revision', 'draft_title', 'dirty', 'conflict', 'action_error']) {
      o[k] = s[k].value
    }
    return o as {
      draft_id: number
      draft_revision: number
      draft_title: string
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

/** 记录动作请求（PUT/PATCH/POST /api/notes/*，不含 /api/v1/*）与响应状态。 */
function trackCalls(page: Page, calls: Call[]) {
  page.on('request', (r) => {
    if (['PUT', 'PATCH', 'POST'].includes(r.method()) && r.url().includes('/api/notes/')) {
      calls.push({ method: r.method(), url: r.url() })
    }
  })
  page.on('response', (r) => {
    if (['PUT', 'PATCH', 'POST'].includes(r.request().method()) && r.url().includes('/api/notes/')) {
      const hit = calls.filter((c) => c.url === r.url() && c.status === undefined)
      if (hit.length > 0) {
        hit[0].status = r.status()
        r.json().then((b) => (hit[0].ok = (b as { ok?: boolean }).ok === true)).catch(() => {})
      }
    }
  })
}

const isPin = (c: Call) => c.method === 'PATCH' && c.url.endsWith('/pin/result')
const isTags = (c: Call) => c.method === 'POST' && c.url.endsWith('/tags/result')
const isFlush = (c: Call) => c.method === 'PUT' && /\/result$/.test(c.url)

type Iso = { dir: string; trig: (field: string) => void; untrig: () => void; restore: () => Promise<void> }

/** 隔离目录 + 触发器脚手架（R8-2 惯例）；测试模式未开时跳过用例。 */
async function isolate(page: Page): Promise<Iso | null> {
  const statusRaw = await api(page, 'GET', '/api/v1/status')
  const orig = (typeof statusRaw === 'string' ? JSON.parse(statusRaw) : statusRaw).data_dir as string
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'notes-r9-')).replace(/\\/g, '/')
  const gate = await page.evaluate(
    async (d) => {
      const r = await fetch('/api/v1/test/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data_dir: d, legacy_file: d + '/nope.json' }),
      })
      return r.json()
    },
    dir,
  )
  if (gate === 'test-mode-disabled') {
    test.skip(true, 'dev server not in NOTES_TEST_MODE; R9 needs /api/v1/test/setup')
    return null
  }
  expect(gate).toBe('ok')
  const dbPath = path.join(dir, 'inbox.db')
  const { DatabaseSync } = await import('node:sqlite')
  const trig = (field: string) => {
    const db = new DatabaseSync(dbPath)
    db.exec(`CREATE TRIGGER reject_r9 BEFORE UPDATE OF ${field} ON notes BEGIN SELECT RAISE(ABORT,'independent metadata rejection'); END`)
    db.close()
  }
  const untrig = () => {
    const db = new DatabaseSync(dbPath)
    db.exec('DROP TRIGGER reject_r9')
    db.close()
  }
  const restore = async () => {
    await page.evaluate(
      async ({ d }) => {
        await fetch('/api/v1/test/setup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ data_dir: d, legacy_file: d + '/nope.json' }),
        })
      },
      { d: orig },
    )
    await page.reload()
    await page.waitForTimeout(500)
  }
  return { dir, trig, untrig, restore }
}

async function makeProbe(page: Page, rid: string, title: string) {
  const created = await api(page, 'POST', '/api/v1/notes', { request_id: rid, title, body: 'base', folder: '' })
  const nid = created.doc.note_id as string
  await page.reload()
  await page.waitForTimeout(700)
  await rows(page).filter({ hasText: title }).click()
  await page.waitForTimeout(650)
  return nid
}

async function addTag(page: Page, tag: string) {
  await page.getByRole('button', { name: 'Tag', exact: true }).click()
  await page.locator('input[placeholder="tag name"]').fill(tag)
  await page.keyboard.press('Enter')
  await page.waitForTimeout(700)
}

/** 标签胶囊：内含标签文本的行内 × 按钮（AutoUI row→div，icon 按钮）。 */
async function removeTagChip(page: Page, tag: string) {
  const chip = page.locator('div').filter({ has: page.getByText(tag, { exact: true }) }).last()
  await chip.locator('button').click()
  await page.waitForTimeout(700)
}

test('R9-1: pin failure arrives as a 200 result envelope, banner matches action (F-R9-01)', async ({ page }) => {
  test.setTimeout(60_000)
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  const calls: Call[] = []
  trackCalls(page, calls)
  await openApp(page)
  const iso = await isolate(page)
  if (!iso) return
  try {
    const nid = await makeProbe(page, 'r9-pin', 'R9PinProbe')
    iso.trig('pinned')
    await page.getByRole('button', { name: 'Pin note', exact: true }).click()
    await page.waitForTimeout(700)

    const pins = calls.filter(isPin)
    expect(pins.length).toBe(1)
    expect(pins[0].status).toBe(200)
    expect(pins[0].ok).toBe(false)
    expect(errors).toEqual([])
    await expect(page.getByText(BANNER)).toBeVisible()
    const st = await storeState(page)
    expect(st.conflict).toBe(true)
    expect(st.action_error).toBe('pin')
    const server1 = await api(page, 'GET', `/api/v1/notes/${nid}`)
    expect(server1.doc.pinned).toBe(false)

    iso.untrig()
    await page.getByRole('button', { name: 'Pin note', exact: true }).click()
    await page.waitForTimeout(700)

    const pins2 = calls.filter(isPin)
    expect(pins2.length).toBe(2)
    expect(pins2[1].ok).toBe(true)
    expect(errors).toEqual([])
    await expect(page.getByText(BANNER)).toHaveCount(0)
    const st2 = await storeState(page)
    expect(st2.action_error).toBe('')
    const server2 = await api(page, 'GET', `/api/v1/notes/${nid}`)
    expect(server2.doc.pinned).toBe(true)
  } finally {
    await iso.restore()
  }
})

test('R9-2: tag-add rejection after body flush keeps revision synced (F-R9-02)', async ({ page }) => {
  test.setTimeout(60_000)
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  const calls: Call[] = []
  trackCalls(page, calls)
  await openApp(page)
  const iso = await isolate(page)
  if (!iso) return
  try {
    const nid = await makeProbe(page, 'r9-tagadd', 'R9TagAddProbe')
    iso.trig('tags_json')
    await page.locator(TITLE).fill('R9-tag-one')
    await addTag(page, 'new-tag')

    // 正文 flush 已确认（PUT 落地 rev2），标签请求被 200 信封拒绝。
    const flushes = calls.filter(isFlush)
    expect(flushes.length).toBe(1)
    expect(flushes[0].ok).toBe(true)
    const tags = calls.filter(isTags)
    expect(tags.length).toBe(1)
    expect(tags[0].status).toBe(200)
    expect(tags[0].ok).toBe(false)
    expect(errors).toEqual([])
    const server1 = await api(page, 'GET', `/api/v1/notes/${nid}`)
    expect(server1.doc.title).toBe('R9-tag-one')
    expect(server1.doc.revision).toBe(2)
    await expect(page.getByText(BANNER)).toBeVisible()
    const st1 = await storeState(page)
    expect(st1.dirty).toBe(false)
    expect(st1.conflict).toBe(true)
    expect(st1.action_error).toBe('tags')
    // 核心断言：flush 成功块已同步 revision，草稿不再停留 rev1。
    expect(st1.draft_revision).toBe(2)

    iso.untrig()
    await page.locator(TITLE).fill('R9-tag-two')
    await page.getByRole('button', { name: 'Save', exact: true }).click()
    await page.waitForTimeout(900)

    const st2 = await storeState(page)
    expect(st2.dirty).toBe(false)
    expect(st2.action_error).toBe('')
    const server2 = await api(page, 'GET', `/api/v1/notes/${nid}`)
    expect(server2.doc.title).toBe('R9-tag-two')
    expect(server2.doc.revision).toBe(3)
    expect(st2.draft_revision).toBe(3)
    expect(errors).toEqual([])
  } finally {
    await iso.restore()
  }
})

test('R9-3: tag-remove rejection after body flush keeps revision synced (F-R9-02)', async ({ page }) => {
  test.setTimeout(60_000)
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  const calls: Call[] = []
  trackCalls(page, calls)
  await openApp(page)
  const iso = await isolate(page)
  if (!iso) return
  try {
    const nid = await makeProbe(page, 'r9-tagrm', 'R9TagRemoveProbe')
    await addTag(page, 'keep-tag')
    const seeded = await api(page, 'GET', `/api/v1/notes/${nid}`)
    expect(seeded.doc.tags).toEqual(['keep-tag'])

    iso.trig('tags_json')
    await page.locator(TITLE).fill('R9-rm-one')
    const beforeRemove = calls.length
    await removeTagChip(page, 'keep-tag')

    // 只统计移除动作片段（前置 addTag 的成功 POST 不在断言范围）。
    const flushes = calls.slice(beforeRemove).filter(isFlush)
    expect(flushes.length).toBe(1)
    expect(flushes[0].ok).toBe(true)
    const tags = calls.slice(beforeRemove).filter(isTags)
    expect(tags.length).toBe(1)
    expect(tags[0].ok).toBe(false)
    expect(errors).toEqual([])
    const server1 = await api(page, 'GET', `/api/v1/notes/${nid}`)
    expect(server1.doc.title).toBe('R9-rm-one')
    expect(server1.doc.revision).toBe(2)
    await expect(page.getByText(BANNER)).toBeVisible()
    const st1 = await storeState(page)
    expect(st1.dirty).toBe(false)
    expect(st1.action_error).toBe('tags')
    expect(st1.draft_revision).toBe(2)

    iso.untrig()
    await page.locator(TITLE).fill('R9-rm-two')
    await page.getByRole('button', { name: 'Save', exact: true }).click()
    await page.waitForTimeout(900)

    const st2 = await storeState(page)
    expect(st2.dirty).toBe(false)
    const server2 = await api(page, 'GET', `/api/v1/notes/${nid}`)
    expect(server2.doc.title).toBe('R9-rm-two')
    expect(server2.doc.revision).toBe(3)
    expect(errors).toEqual([])
  } finally {
    await iso.restore()
  }
})

test('R9-4: prior delete failure must not mask a pin click (F-R9-01 stale state)', async ({ page }) => {
  test.setTimeout(60_000)
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  const calls: Call[] = []
  trackCalls(page, calls)
  await openApp(page)
  const iso = await isolate(page)
  if (!iso) return
  try {
    const nid = await makeProbe(page, 'r9-mask', 'R9MaskProbe')
    iso.trig('state')
    await page.getByRole('button', { name: 'Delete', exact: true }).click()
    await page.waitForTimeout(300)
    await page.getByRole('button', { name: 'Delete', exact: true }).click()
    await page.waitForTimeout(700)
    await expect(page.getByText(BANNER)).toBeVisible()
    const stDel = await storeState(page)
    expect(stDel.action_error).toBe('delete')
    const server0 = await api(page, 'GET', `/api/v1/notes/${nid}`)
    expect(server0.doc.state).toBe('active')

    // 掩盖检查核心：删除失败后点击 pin，必须真的发出新 PATCH（旧实现被
    // if .conflict == false 门禁跳过，0 请求，横幅沿用删除失败——假绿）。
    iso.untrig()
    iso.trig('pinned')
    const before = calls.length
    await page.getByRole('button', { name: 'Pin note', exact: true }).click()
    await page.waitForTimeout(700)

    const newPins = calls.slice(before).filter(isPin)
    expect(newPins.length).toBe(1)
    expect(newPins[0].ok).toBe(false)
    const stPin = await storeState(page)
    expect(stPin.action_error).toBe('pin')
    const server1 = await api(page, 'GET', `/api/v1/notes/${nid}`)
    expect(server1.doc.pinned).toBe(false)

    iso.untrig()
    await page.getByRole('button', { name: 'Pin note', exact: true }).click()
    await page.waitForTimeout(700)
    const server2 = await api(page, 'GET', `/api/v1/notes/${nid}`)
    expect(server2.doc.pinned).toBe(true)
    expect(errors).toEqual([])
  } finally {
    await iso.restore()
  }
})

test('R9-5: normal edit-tag-save control lands with synced revision', async ({ page }) => {
  test.setTimeout(60_000)
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  const calls: Call[] = []
  trackCalls(page, calls)
  await openApp(page)
  const iso = await isolate(page)
  if (!iso) return
  try {
    const nid = await makeProbe(page, 'r9-ctl', 'R9CtlProbe')
    await page.locator(TITLE).fill('R9-ctl-one')
    await addTag(page, 'good-tag')

    const tags = calls.filter(isTags)
    expect(tags.length).toBe(1)
    expect(tags[0].ok).toBe(true)
    const server1 = await api(page, 'GET', `/api/v1/notes/${nid}`)
    expect(server1.doc.title).toBe('R9-ctl-one')
    expect(server1.doc.revision).toBe(2)
    expect(server1.doc.tags).toEqual(['good-tag'])
    const st1 = await storeState(page)
    expect(st1.dirty).toBe(false)
    expect(st1.action_error).toBe('')
    expect(st1.draft_revision).toBe(2)

    await page.locator(TITLE).fill('R9-ctl-two')
    await page.getByRole('button', { name: 'Save', exact: true }).click()
    await page.waitForTimeout(900)

    const server2 = await api(page, 'GET', `/api/v1/notes/${nid}`)
    expect(server2.doc.title).toBe('R9-ctl-two')
    expect(server2.doc.revision).toBe(3)
    expect(server2.doc.tags).toEqual(['good-tag'])
    const st2 = await storeState(page)
    expect(st2.dirty).toBe(false)
    expect(st2.draft_revision).toBe(3)
    expect(errors).toEqual([])
  } finally {
    await iso.restore()
  }
})
