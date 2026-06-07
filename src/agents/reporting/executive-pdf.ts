import fs from 'fs-extra';
import path from 'path';
import { pathToFileURL } from 'url';
import { readJson } from '../shared/state-store';

export async function generateExecutivePdf() {
  const history = await readJson<any[]>('test-history.json', []);

  const latestRunId = history.at(-1)?.runId;
  const latestResults = history.filter((r) => r.runId === latestRunId);

  const total = latestResults.length;
  const passed = latestResults.filter((r) => r.status === 'passed').length;
  const failed = latestResults.filter((r) => r.status === 'failed').length;
  const passRate = total === 0 ? 0 : (passed / total) * 100;

  const reportDir = await resolveReportDir();
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const htmlPath = path.join(reportDir, `weekly-quality-scorecard-${timestamp}.html`);
  const pdfPath = path.join(reportDir, `weekly-quality-scorecard-${timestamp}.pdf`);
  const latestHtmlPath = path.join(reportDir, 'weekly-quality-scorecard.html');
  const latestPdfPath = path.join(reportDir, 'weekly-quality-scorecard.pdf');

  const html = `
    <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; padding: 32px; }
          h1 { color: #222; }
          .card { border: 1px solid #ddd; padding: 16px; margin: 12px 0; }
          .big { font-size: 32px; font-weight: bold; }
        </style>
      </head>
      <body>
        <h1>Weekly Quality Scorecard</h1>
        <p>Generated: ${new Date().toISOString()}</p>

        <div class="card">
          <h2>Pass Rate</h2>
          <div class="big">${passRate.toFixed(2)}%</div>
        </div>

        <div class="card">
          <h2>Execution Summary</h2>
          <p>Total: ${total}</p>
          <p>Passed: ${passed}</p>
          <p>Failed: ${failed}</p>
        </div>
      </body>
    </html>
  `;

  await fs.writeFile(htmlPath, html);

  const { default: puppeteer } = await import('puppeteer');

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });

  try {
    const page = await browser.newPage();

    await page.goto(pathToFileURL(htmlPath).toString(), {
      waitUntil: 'networkidle2'
    });

    await page.pdf({
      path: pdfPath,
      format: 'A4',
      printBackground: true
    });
  } finally {
    await browser.close();
  }

  await copyLatestIfPossible(htmlPath, latestHtmlPath);
  await copyLatestIfPossible(pdfPath, latestPdfPath);

  console.log(`PDF generated at ${pdfPath}`);
}

async function resolveReportDir() {
  const preferredDir = path.resolve('reports/executive');
  const fallbackDir = path.resolve('agent-state/executive-report');

  for (const dir of [preferredDir, fallbackDir]) {
    try {
      await fs.ensureDir(dir);
      const probePath = path.join(dir, `.write-check-${process.pid}.tmp`);
      await fs.writeFile(probePath, '');
      await fs.remove(probePath);
      return dir;
    } catch {
      // Try the next output directory.
    }
  }

  throw new Error('No writable directory found for executive report output.');
}

async function copyLatestIfPossible(sourcePath: string, destinationPath: string) {
  try {
    await fs.copy(sourcePath, destinationPath, { overwrite: true });
  } catch (error) {
    console.warn(
      `Could not update latest report ${destinationPath}. The timestamped report was still generated.`,
      error
    );
  }
}

generateExecutivePdf().catch((error) => {
  console.error(error);
  process.exit(1);
});
