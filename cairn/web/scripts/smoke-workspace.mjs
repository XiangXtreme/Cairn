import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';

const chrome = process.env.CAIRN_SMOKE_CHROME || '/usr/bin/chromium';
const base = process.env.CAIRN_SMOKE_BASE || 'http://127.0.0.1:8000';
const tmpRoot = mkdtempSync(join(tmpdir(), 'cairn-smoke-'));

function dumpDom(url, targetName) {
  const profileDir = join(tmpRoot, targetName);
  const targetFile = join(tmpRoot, `${targetName}.html`);
  const errorFile = join(tmpRoot, `${targetName}.err`);
  const result = spawnSync(
    chrome,
    [
      '--headless=new',
      '--disable-gpu',
      '--no-sandbox',
      `--user-data-dir=${profileDir}`,
      '--virtual-time-budget=7000',
      '--dump-dom',
      url,
    ],
    { encoding: 'utf-8' },
  );
  writeFileSync(targetFile, result.stdout);
  writeFileSync(errorFile, result.stderr);
  if (result.status !== 0) {
    throw new Error(`chromium failed for ${url}\n${result.stderr}`);
  }
  return readFileSync(targetFile, 'utf-8');
}

function assertIncludes(dom, values, label) {
  const missing = values.filter((value) => !dom.includes(value));
  if (missing.length > 0) {
    throw new Error(`${label} missing markers: ${missing.join(', ')}`);
  }
}

try {
  const homeDom = dumpDom(`${base}/#/`, 'home');
  assertIncludes(homeDom, ['Cairn Workspace', '项目列表'], 'home');

  const projectList = spawnSync('curl', ['-s', `${base}/projects`], { encoding: 'utf-8' });
  const projects = JSON.parse(projectList.stdout || '[]');
  const projectId = projects[0]?.id;
  if (!projectId) {
    throw new Error('no projects available for detail smoke test');
  }

  const detailDom = dumpDom(`${base}/#/projects/${projectId}`, 'detail');
  assertIncludes(detailDom, ['Replay', 'Graph', 'Facts', 'Intents', projectId], 'detail');

  console.log(
    JSON.stringify(
      {
        ok: true,
        projectId,
        checked: ['home', 'detail'],
      },
      null,
      2,
    ),
  );
} finally {
  rmSync(tmpRoot, { recursive: true, force: true });
}
