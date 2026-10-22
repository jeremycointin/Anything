// Renders index.html frame-by-frame in headless Chromium and pipes JPEG frames into ffmpeg.
// Usage: node render.mjs [out.mp4] [--frames 0,450,900] (stills mode writes PNGs to ./stills)
// Run `bash prep.sh` first to extract the narration video frames.
import { createRequire } from 'module';
import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const require = createRequire(import.meta.url);
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(here); // serve the repo so ../sizzle-reel assets resolve
const FPS = 30;
const args = process.argv.slice(2);
const out = args.find(a => a.endsWith('.mp4')) || 'jeremy-for-brightter.mp4';
const fi = args.indexOf('--frames');
const stills = fi >= 0 ? args[fi + 1].split(',').map(Number) : null;

const types = { '.html': 'text/html', '.png': 'image/png', '.jpg': 'image/jpeg', '.wav': 'audio/wav' };
const server = http.createServer((req, res) => {
  const f = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  if (!f.startsWith(root) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(0);
const port = server.address().port;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(`http://127.0.0.1:${port}/${path.basename(here)}/index.html?render`);
await page.evaluate(() => window.ready);
const duration = await page.evaluate(() => window.DURATION);

const grab = (frames, type, q) => page.evaluate(async ([frames, fps, type, q]) => {
  const outs = [];
  for (const f of frames) { await window.prepare(f / fps); window.draw(f / fps); outs.push(document.getElementById('c').toDataURL(type, q).split(',')[1]); }
  return outs;
}, [frames, FPS, type, q]);

if (stills) {
  fs.mkdirSync(path.join(here, 'stills'), { recursive: true });
  const imgs = await grab(stills, 'image/png');
  imgs.forEach((b, i) => fs.writeFileSync(path.join(here, 'stills', `f${String(stills[i]).padStart(5, '0')}.png`), Buffer.from(b, 'base64')));
} else {
  const total = Math.round(duration * FPS);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-i', path.join(here, 'soundtrack.wav'), '-map', '0:v', '-map', '1:a',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
    '-shortest', '-movflags', '+faststart', path.join(here, out)], { stdio: ['pipe', 'inherit', 'inherit'] });
  const write = buf => new Promise(r => ff.stdin.write(buf) ? r() : ff.stdin.once('drain', r));
  for (let f = 0; f < total; f += 15) {
    const batch = Array.from({ length: Math.min(15, total - f) }, (_, i) => f + i);
    for (const b of await grab(batch, 'image/jpeg', 0.93)) await write(Buffer.from(b, 'base64'));
    if (f % 300 === 0) console.log(`frame ${f}/${total}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  console.log('wrote', out);
}
await browser.close();
server.close();
