import { chromium } from 'playwright';
import sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';

(async () => {
    console.log("Setting up fresh appointment in DB...");
    const db = new sqlite3.Database('backend/hospital.db');
    const appt_id = uuidv4();
    const ts = new Date().toISOString();
    await new Promise((resolve) => {
        db.run(`INSERT INTO appointments (appointment_id, patient_id, doctor_id, department, scheduled_time, appointment_type) VALUES ('${appt_id}', 'PAT_1', 'DOC_CAR_1', 'Cardiology', '${ts}', 'new')`, resolve);
    });
    db.close();
    
    console.log("Launching browser to prove Live Polling...");
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    
    // We will listen for polling requests to the status endpoint
    let pollCount = 0;
    page.on('response', async (response) => {
        if (response.url().includes('/status') && response.request().method() === 'GET') {
            pollCount++;
            console.log(`[Network Tab equivalent] - Polling request #${pollCount} completed with status ${response.status()}`);
        }
    });

    console.log("Navigating to Patient Dashboard and logging in...");
    await page.goto('http://localhost:3000');
    
    // Fill in PAT_1 credentials
    await page.fill('input[type="text"]', 'PAT_1');
    await page.fill('input[type="password"]', 'pat');
    await page.click('button[type="submit"]');
    
    // Wait for the live prediction to appear
    try {
        await page.waitForSelector('text=Live Prediction', { timeout: 10000 });
    } catch (e) {
        console.log("Failed to find Live Prediction text. Taking debug screenshot...");
        await page.screenshot({ path: 'debug_error.png' });
        await browser.close();
        process.exit(1);
    }
    
    // Capture the first DOM state & screenshot
    const beforeState = await page.textContent('.text-lg.text-blue-900.font-bold');
    console.log(`\nDOM STATE BEFORE INJECTION (Timestamp: ${new Date().toISOString()}):`);
    console.log(`Visible Wait Time Window: ${beforeState.trim()}`);
    await page.screenshot({ path: 'before_injection.png' });
    
    console.log("\nInjecting a 45-minute emergency directly to the backend...");
    // Inject emergency as staff via direct backend call
    const loginRes = await fetch('http://localhost:8000/api/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'username=DOC_CAR_1&password=doc'
    });
    const token = (await loginRes.json()).access_token;

    // We need to fetch the patient queue to know which doc to inject for
    const statusRes = await fetch('http://localhost:8000/api/patients/PAT_1', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const patData = await statusRes.json();
    const targetDoc = patData.visit_history[0].doctor_id;
    const targetDept = patData.visit_history[0].department;
    
    await fetch('http://localhost:8000/api/appointments/emergency', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ doctor_id: targetDoc, department: targetDept, estimated_duration: 45 })
    });
    
    console.log("\nEmergency Injected! Now waiting 6 seconds for the SWR polling cycle to fetch and React to re-render (without manual page reload)...");
    
    // Wait for polling interval (5 seconds + 1 second buffer)
    await page.waitForTimeout(6000);
    
    // Capture the second DOM state & screenshot
    const afterState = await page.textContent('.text-lg.text-blue-900.font-bold');
    console.log(`\nDOM STATE AFTER POLLING (Timestamp: ${new Date().toISOString()}):`);
    console.log(`Visible Wait Time Window: ${afterState.trim()}`);
    await page.screenshot({ path: 'after_injection.png' });
    
    if (beforeState !== afterState) {
        console.log("\nPROOF SUCCESSFUL: The browser DOM updated purely via the SWR polling background request.");
    } else {
        console.log("\nPROOF FAILED: The DOM state did not change.");
    }
    
    await browser.close();
})();
