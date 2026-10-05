// README screenshots from the local dev environment (sample data only).
// Start ../scripts/dev.sh first, then: npm run screenshots
import { mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

const BASE = process.env.TASKWEB_URL ?? 'http://localhost:5173'
const DEV_PASSWORD = 'taskweb-dev' // dev.sh's throwaway password; never a real one
const OUT = fileURLToPath(new URL('../../docs/screenshots/', import.meta.url))

const DESKTOP = { width: 1280, height: 800, deviceScaleFactor: 2 }
const PHONE = { width: 390, height: 844, deviceScaleFactor: 3, isMobile: true, hasTouch: true }

const browser = await puppeteer.launch({ channel: 'chrome', headless: true })
const page = await browser.newPage()
await mkdir(OUT, { recursive: true })

async function open(path, viewport, scheme) {
  await page.setViewport(viewport)
  await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: scheme }])
  await page.goto(BASE + path, { waitUntil: 'networkidle0' })
  await page.waitForSelector('.row')
  await page.addStyleTag({ content: '.toasts { display: none !important }' })
}

async function uidOf(title) {
  return page.evaluate(async (t) => {
    const { tasks } = await fetch('/api/tasks').then((r) => r.json())
    return tasks.find((x) => x.title.startsWith(t)).uid
  }, title)
}

async function shot(name) {
  await new Promise((r) => setTimeout(r, 400)) // let transitions settle
  await page.screenshot({ path: OUT + name })
  console.log('wrote docs/screenshots/' + name)
}

await page.goto(BASE + '/', { waitUntil: 'networkidle0' })
const ok = await page.evaluate(async (pw) => {
  const r = await fetch('/api/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'taskweb' },
    body: JSON.stringify({ password: pw }),
  })
  return r.ok
}, DEV_PASSWORD)
if (!ok) throw new Error('Login failed. Is ./scripts/dev.sh running?')

await open('/list/pending', DESKTOP, 'light')
await shot('desktop-list.png')

const water = await uidOf('Water the backyard')
await open(`/list/pending?task=${water}`, DESKTOP, 'dark')
await page.waitForSelector('.editor')
await shot('desktop-editor-dark.png')

await open('/list/saved-mup167dc', DESKTOP, 'light').catch(() => open('/list/pending', DESKTOP, 'light'))
await page.click('.filter-btn')
await page.waitForSelector('.filters')
await shot('desktop-filters.png')

await open('/list/pending', PHONE, 'light')
await shot('phone-list.png')

const build = await uidOf('Build the 3')
await open(`/list/pending?task=${build}`, PHONE, 'dark')
await page.waitForSelector('.editor')
await shot('phone-editor-dark.png')

await browser.close()
