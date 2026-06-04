import fs from 'fs-extra';
import { readJson } from '../shared/state-store';

export async function generateExecutivePdf() {
  const history = await readJson<any[]>('test-history.json', []);

  const latestRunId = history.at(-1)?.runId;
  const latestResults = history.filter((r) => r.runId === latestRunId);

  const total = latestResults.length;
  const passed = latestResults.filter((r) => r.status === 'passed').length;
  const failed = latestResults.filter((r) => r.status === 'failed').length;
  const passRate = total === 0 ? 0 : (passed / total) * 100;

  await fs.ensureDir('reports/executive');

  const htmlPath = 'reports/executive/weekly-quality-scorecard.html';
  const pdfPath = 'reports/executive/weekly-quality-scorecard.pdf';

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
    headless: true
  });

  const page = await browser.newPage();

  await page.goto(`file://${process.cwd()}/${htmlPath}`, {
    waitUntil: 'networkidle2'
  });

  await page.pdf({
    path: pdfPath,
    format: 'A4',
    printBackground: true
  });

  await browser.close();

  console.log(`PDF generated at ${pdfPath}`);
}

generateExecutivePdf().catch((error) => {
  console.error(error);
  process.exit(1);
});
