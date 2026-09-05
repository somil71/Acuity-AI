import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const results = [];

  const test = async (name, fn) => {
    try { await fn(); results.push(`[PASS] ${name}`); }
    catch(e) { results.push(`[FAIL] ${name}: ${e.message?.slice(0,100)}`); }
  };

  // Login
  await page.goto('http://localhost:3000/');
  await page.fill('input[type="text"]', 'PAT_1');
  await page.fill('input[type="password"]', 'pat');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/patient');
  await page.waitForTimeout(1500);

  // Dashboard
  await test('Dashboard: Welcome Back visible', async () => {
    await page.waitForSelector('text=Welcome Back', { timeout: 5000 });
  });

  await test('Sidebar: Navigation links present', async () => {
    await page.waitForSelector('text=Records', { timeout: 3000 });
    await page.waitForSelector('text=Medications', { timeout: 3000 });
    await page.waitForSelector('text=Messages', { timeout: 3000 });
    await page.waitForSelector('text=Billing', { timeout: 3000 });
    await page.waitForSelector('text=Reviews', { timeout: 3000 });
  });

  await test('Navbar: Notification bell visible', async () => {
    const bell = await page.locator('a[href="/patient/notifications"]').first();
    await bell.waitFor({ timeout: 3000 });
  });

  // Records page
  await page.click('text=Records');
  await page.waitForTimeout(1500);
  await test('Records: Health record cards visible', async () => {
    await page.waitForSelector('text=Hypertension', { timeout: 5000 });
  });
  await test('Records: Lab results expandable', async () => {
    await page.click('button:has-text("Lab Results")', { timeout: 3000 });
    await page.waitForSelector('text=Blood Pressure Systolic', { timeout: 3000 });
  });

  // Medications page
  await page.click('text=Medications');
  await page.waitForTimeout(1500);
  await test('Medications: Drug cards visible', async () => {
    await page.waitForSelector('text=Amlodipine', { timeout: 5000 });
    await page.waitForSelector('text=Atorvastatin', { timeout: 5000 });
  });
  await test('Medications: Refill button present', async () => {
    await page.waitForSelector('button:has-text("Request Refill")', { timeout: 3000 });
  });

  // Messages page
  await page.click('text=Messages');
  await page.waitForTimeout(1500);
  await test('Messages: New Message button present', async () => {
    await page.waitForSelector('button:has-text("New Message")', { timeout: 5000 });
  });
  await test('Messages: Existing thread visible', async () => {
    await page.waitForSelector('text=Question about my medication', { timeout: 5000 });
  });
  await test('Messages: Chat bubbles visible', async () => {
    await page.waitForSelector('text=Hello doctor', { timeout: 5000 });
  });

  // Billing page
  await page.click('text=Billing');
  await page.waitForTimeout(1500);
  await test('Billing: Outstanding and Paid cards visible', async () => {
    await page.waitForSelector('text=Total Outstanding', { timeout: 5000 });
    await page.waitForSelector('text=Total Paid', { timeout: 5000 });
  });
  await test('Billing: Invoice table rows present', async () => {
    await page.waitForSelector('text=Pay Now', { timeout: 5000 });
  });

  // Reviews page
  await page.click('text=Reviews');
  await page.waitForTimeout(1500);
  await test('Reviews: Pending and submitted sections visible', async () => {
    const hasPending = await page.isVisible('text=Awaiting Your Review');
    const hasSubmitted = await page.isVisible('text=Your Past Reviews');
    if (!hasPending && !hasSubmitted) throw new Error('Neither section visible');
  });

  // Notifications page
  await page.goto('http://localhost:3000/patient/notifications');
  await page.waitForTimeout(1500);
  await test('Notifications: Cards with title+body visible', async () => {
    await page.waitForSelector('text=Lab Results Ready', { timeout: 5000 });
    await page.waitForSelector('text=Appointment Tomorrow', { timeout: 5000 });
  });
  await test('Notifications: Mark all read button present', async () => {
    await page.waitForSelector('button:has-text("Mark all read")', { timeout: 3000 });
  });

  // Final screenshot
  await page.goto('http://localhost:3000/patient/records');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: 'e2e_final.png', fullPage: true });

  console.log('\n=== RESULTS ===');
  results.forEach(r => console.log(r));
  const passed = results.filter(r => r.startsWith('[PASS]')).length;
  console.log(`\n${passed}/${results.length} tests passed`);

  await browser.close();
})();
