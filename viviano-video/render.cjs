// Render index.html to MP4 frame-by-frame.
// Usage: NODE_PATH=$(npm root -g) node render.cjs [out.mp4] [--stills 3,10,20]
// Pipeline: render.cjs (silent video) -> soundtrack.py (music) -> mix.py (voice + music + mux)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');

const FPS = 30, DURATION = 90;
const args = process.argv.slice(2);
const stillsIdx = args.indexOf('--stills');
const out = args.find(a => a.endsWith('.mp4')) || path.join(__dirname, 'viviano-promo-silent.mp4');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + path.join(__dirname, 'index.html') + '?capture=1');
  await page.evaluate(() => window.ready);

  if (stillsIdx >= 0) {
    const dir = args[stillsIdx + 2] || __dirname;
    for (const t of args[stillsIdx + 1].split(',').map(Number)) {
      await page.evaluate(t => window.renderAt(t), t);
      await page.screenshot({ path: path.join(dir, `still-${t}.png`) });
    }
    await browser.close();
    return;
  }

  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  const total = FPS * DURATION;
  for (let f = 0; f < total; f++) {
    await page.evaluate(t => window.renderAt(t), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (f % 300 === 0) console.log(`frame ${f}/${total}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  console.log('wrote', out);
})();
