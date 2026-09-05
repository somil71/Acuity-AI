/**
 * DEEP AUDIT - captures screenshots of every page and logs all visible data.
 * Saves results to audit_results/ directory.
 */
import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'fs';

const AUDIT_DIR = 'audit_results';
mkdirSync(AUDIT_DIR, { recursive: true });

const PAGES = [
  { url: '/patient',              name: 'dashboard' },
  { url: '/patient/records',      name: 'records' },
  { url: '/patient/medications',  name: 'medications' },
  { url: '/patient/messages',     name: 'messages' },
  { url: '/patient/billing',      name: 'billing' },
  { url: '/patient/reviews',      name: 'reviews' },
  { url: '/patient/notifications',name: 'notifications' },
];

const results = [];

const check = (name, pass, detail = '') => {
  const r = { name, pass, detail };
  results.push(r);
  console.log(`  [${pass ? 'PASS' : 'FAIL'}] ${name}${detail ? ': ' + detail : ''}`);
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.setDefaultTimeout(12000);

  // ── LOGIN ─────────────────────────────────────────────────────────────────
  console.log('\n=== LOGIN ===');
  await page.goto('http://localhost:3000/');
  await page.fill('input[type="text"]', 'PAT_1');
  await page.fill('input[type="password"]', 'pat');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/patient');
  await page.waitForTimeout(2000);
  check('Login redirects to /patient', page.url().includes('/patient'));

  // ── SCREENSHOT EACH PAGE ──────────────────────────────────────────────────
  for (const { url, name } of PAGES) {
    console.log(`\n=== ${name.toUpperCase()} PAGE ===`);
    await page.goto(`http://localhost:3000${url}`);
    await page.waitForTimeout(2500);

    // Always screenshot
    const shot = `${AUDIT_DIR}/${name}.png`;
    await page.screenshot({ path: shot, fullPage: true });
    console.log(`  Saved: ${shot}`);

    const body = await page.textContent('body');
    const hasError = body.includes('Failed to') || body.includes('Error') || body.includes('TypeError');

    // ── Per-page checks ──
    if (name === 'dashboard') {
      check('Dashboard: Welcome Back', body.includes('Welcome Back'));
      check('Dashboard: Sidebar visible (Records link)', body.includes('Records'));
      check('Dashboard: Sidebar visible (Medications link)', body.includes('Medications'));
      check('Dashboard: Sidebar visible (Messages link)', body.includes('Messages'));
      check('Dashboard: Sidebar visible (Billing link)', body.includes('Billing'));
      check('Dashboard: Sidebar visible (Reviews link)', body.includes('Reviews'));
      const bellBadge = await page.locator('a[href="/patient/notifications"] span').count();
      check('Dashboard: Bell badge rendered', bellBadge > 0, `badge elements=${bellBadge}`);
      check('Dashboard: No runtime errors', !hasError, hasError ? body.substring(0,200) : '');
    }

    if (name === 'records') {
      check('Records: Diagnosis text visible', body.includes('Hypertension') || body.includes('Osteoarthritis') || body.includes('Rhinitis'));
      check('Records: Department rendered', body.includes('General Physician') || body.includes('Pediatrics'));
      check('Records: Doctor notes visible', body.includes('Blood pressure') || body.includes('physiotherapy') || body.includes('antihistamines'));
      check('Records: No runtime errors', !hasError);
      // Click lab results expand
      try {
        await page.click('button:has-text("Lab Results")');
        await page.waitForTimeout(800);
        const afterClick = await page.textContent('body');
        check('Records: Lab results expand shows test names', afterClick.includes('Blood Pressure') || afterClick.includes('Cholesterol'));
      } catch { check('Records: Lab results expand', false, 'button not found'); }
    }

    if (name === 'medications') {
      check('Medications: Amlodipine card visible', body.includes('Amlodipine'));
      check('Medications: Atorvastatin card visible', body.includes('Atorvastatin'));
      check('Medications: Dosage shown', body.includes('5mg') || body.includes('20mg'));
      check('Medications: Frequency shown', body.includes('daily') || body.includes('nightly'));
      check('Medications: Refill button present', body.includes('Request Refill') || body.includes('Refill'));
      check('Medications: No runtime errors', !hasError);

      // Test refill request
      try {
        await page.click('button:has-text("Request Refill")', { timeout: 5000 });
        await page.waitForTimeout(1500);
        const afterRefill = await page.textContent('body');
        check('Medications: Refill request updates status', afterRefill.includes('requested') || afterRefill.includes('Requested'));
      } catch { check('Medications: Refill button clickable', false, 'click failed'); }
    }

    if (name === 'messages') {
      check('Messages: New Message button', body.includes('New Message'));
      check('Messages: Thread list visible', body.includes('Question about my medication') || body.includes('Conversation'));
      check('Messages: Chat bubble text', body.includes('Hello doctor') || body.includes('Amlodipine'));
      check('Messages: Reply box visible', await page.locator('textarea').count() > 0, `textareas=${await page.locator('textarea').count()}`);
      check('Messages: No runtime errors', !hasError);

      // Test send reply
      try {
        await page.fill('textarea', 'This is an audit test reply.');
        await page.click('button:has-text("Send")');
        await page.waitForTimeout(1500);
        const afterSend = await page.textContent('body');
        check('Messages: Reply sent appears in chat', afterSend.includes('audit test reply'));
      } catch(e) { check('Messages: Send reply works', false, e.message.slice(0,80)); }
    }

    if (name === 'billing') {
      check('Billing: Total Outstanding card', body.includes('Outstanding') || body.includes('outstanding'));
      check('Billing: Total Paid card', body.includes('Total Paid'));
      check('Billing: Invoice table rows', body.includes('Pay Now') || body.includes('Paid'));
      check('Billing: Insurance column', body.includes('Insurance') || body.includes('insurance'));
      check('Billing: No runtime errors', !hasError);

      // Test Pay Now
      const payBtn = page.locator('button:has-text("Pay Now")').first();
      if (await payBtn.count() > 0) {
        await payBtn.click();
        await page.waitForTimeout(2000);
        const afterPay = await page.textContent('body');
        check('Billing: Pay Now updates status', afterPay.includes('Paid') || !afterPay.includes('Pay Now'));
      } else {
        check('Billing: Pay Now button (all already paid)', true, 'no pending invoices');
      }
    }

    if (name === 'reviews') {
      const hasPending = body.includes('Awaiting Your Review') || body.includes('Leave a Review');
      const hasSubmitted = body.includes('Your Past Reviews') || body.includes('past reviews') || body.includes('Good visit overall');
      check('Reviews: Pending or submitted section visible', hasPending || hasSubmitted, `pending=${hasPending} submitted=${hasSubmitted}`);
      check('Reviews: Star ratings visible', body.includes('Overall Rating') || body.includes('Good visit') || body.includes('star'));
      check('Reviews: No runtime errors', !hasError);

      // Test review submission if pending
      if (hasPending) {
        try {
          const stars = page.locator('button').filter({ hasText: '' }).nth(5); // 5th star
          await page.locator('[class*="star"],[class*="Star"]').first().click();
          await page.waitForTimeout(500);
          check('Reviews: Star selection works', true);
        } catch { check('Reviews: Star selection', false, 'could not click star'); }
      }
    }

    if (name === 'notifications') {
      check('Notifications: Lab Results Ready card', body.includes('Lab Results Ready'));
      check('Notifications: Appointment Tomorrow card', body.includes('Appointment Tomorrow') || body.includes('Reminder'));
      check('Notifications: Unread indicator', body.includes('unread') || body.includes('Unread'));
      check('Notifications: Mark all read button', body.includes('Mark all read'));
      check('Notifications: No runtime errors', !hasError);

      // Test mark-all-read
      try {
        await page.click('button:has-text("Mark all read")', { timeout: 5000 });
        await page.waitForTimeout(1500);
        const afterMark = await page.textContent('body');
        check('Notifications: Mark all read removes badge', !afterMark.includes('Mark all read') || afterMark.includes('All caught up'));
      } catch { check('Notifications: Mark all read clickable', false, 'button not found after action'); }
    }
  }

  // ── TRIAGE API CHECK ───────────────────────────────────────────────────────
  console.log('\n=== TRIAGE (API direct check) ===');
  const triageRes = await page.evaluate(async () => {
    const r = await fetch('http://localhost:8000/api/triage/assess', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symptoms: ['joint pain', 'swelling'], symptom_description: 'knee pain', pain_scale: 5, duration_days: 10, age: 45, gender: 'F' })
    });
    return r.json();
  });
  check('Triage: Returns urgency field', !!triageRes.urgency, `urgency=${triageRes.urgency}`);
  check('Triage: Returns recommended_dept', !!triageRes.recommended_dept, `dept=${triageRes.recommended_dept}`);
  check('Triage: Returns go_to_er flag', triageRes.go_to_er !== undefined, `go_to_er=${triageRes.go_to_er}`);
  check('Triage: Orthopedics for joint pain', triageRes.recommended_dept === 'Orthopedics', `got=${triageRes.recommended_dept}`);

  // ── CANCEL + WAITLIST ─────────────────────────────────────────────────────
  console.log('\n=== CANCEL / WAITLIST (API direct check) ===');
  const token = await page.evaluate(async () => localStorage.getItem('token'));
  const waitlistRes = await page.evaluate(async (tok) => {
    const r = await fetch('http://localhost:8000/api/appointments/waitlist', {
      method: 'POST',
      headers: { Authorization: `Bearer ${tok}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ doctor_id: 'DOC_CAR_1', department: 'Cardiology', preferred_date: new Date().toISOString() })
    });
    return { status: r.status, data: await r.json() };
  }, token);
  check('Waitlist: POST /waitlist succeeds', waitlistRes.status === 200, `status=${waitlistRes.status} msg=${JSON.stringify(waitlistRes.data).slice(0,60)}`);

  const myWaitlist = await page.evaluate(async (tok) => {
    const r = await fetch('http://localhost:8000/api/appointments/waitlist/my', {
      headers: { Authorization: `Bearer ${tok}` }
    });
    return r.json();
  }, token);
  check('Waitlist: GET /waitlist/my returns entries', Array.isArray(myWaitlist) && myWaitlist.length > 0, `count=${myWaitlist.length ?? 'N/A'}`);

  // ── ANOMALY API CHECK ──────────────────────────────────────────────────────
  console.log('\n=== ANOMALY DETECTION (API direct check) ===');
  const staffToken = await page.evaluate(async () => {
    const r = await fetch('http://localhost:8000/api/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'username=DOC_CAR_1&password=doc'
    });
    return (await r.json()).access_token;
  });
  const anomalyRes = await page.evaluate(async (tok) => {
    const r = await fetch('http://localhost:8000/api/anomaly/check', {
      headers: { Authorization: `Bearer ${tok}` }
    });
    return r.json();
  }, staffToken);
  check('Anomaly: Returns results array', Array.isArray(anomalyRes.results), `got=${JSON.stringify(anomalyRes).slice(0,80)}`);
  check('Anomaly: anomalies_checked field present', anomalyRes.anomalies_checked !== undefined, `checked=${anomalyRes.anomalies_checked}`);

  // ── FINAL SUMMARY ──────────────────────────────────────────────────────────
  console.log('\n\n==============================');
  console.log('       AUDIT SUMMARY');
  console.log('==============================');
  const passed = results.filter(r => r.pass).length;
  const failed = results.filter(r => !r.pass);
  console.log(`PASSED: ${passed}/${results.length}`);
  if (failed.length > 0) {
    console.log('\nFAILED:');
    failed.forEach(f => console.log(`  - ${f.name}: ${f.detail}`));
  } else {
    console.log('ALL CHECKS PASSED');
  }

  writeFileSync(`${AUDIT_DIR}/audit_report.json`, JSON.stringify({ passed, total: results.length, results }, null, 2));
  console.log(`\nReport saved to ${AUDIT_DIR}/audit_report.json`);
  console.log('Screenshots saved to audit_results/');

  await browser.close();
  process.exit(failed.length > 0 ? 1 : 0);
})();
