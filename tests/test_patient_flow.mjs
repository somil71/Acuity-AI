import { chromium } from 'playwright';

(async () => {
  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('Navigating to login...');
  await page.goto('http://localhost:3000/');

  // Fill login
  await page.fill('input[type="text"]', 'PAT_1');
  await page.fill('input[type="password"]', 'pat');
  await page.click('button[type="submit"]');

  console.log('Logged in. Waiting for patient dashboard...');
  await page.waitForURL('http://localhost:3000/patient');
  
  console.log('Waiting for SWR fetch to complete...');
  await page.waitForSelector('text=Welcome Back', { timeout: 10000 });
  
  console.log('Checking if Book an Appointment form is visible...');
  const formVisible = await page.isVisible('text=Book an Appointment');
  
  if (formVisible) {
      console.log('Form is visible. Filling it out...');
      
      // The form has selects: Department, Doctor, Visit Type, and datetime-local
      // Department is Cardiology by default. Let's change to Orthopedics.
      await page.selectOption('select:has(option[value="Cardiology"])', 'Orthopedics');
      
      // Wait a tick for React state to update the doctor dropdown
      await page.waitForTimeout(500);
      
      // Click book!
      console.log('Clicking book now...');
      await page.click('button[type="submit"]');
      
      console.log('Waiting for Live Status to appear...');
      // The word 'Expected Consultation Window' should appear if successful
      await page.waitForSelector('text=Expected Consultation Window', { timeout: 10000 });
      console.log('SUCCESS! Live prediction appeared!');
      
      const arrival = await page.locator('text=Recommended Arrival').textContent();
      console.log(`UI shows: ${arrival}`);
  } else {
      console.log('Booking form not visible. Possibly already booked.');
      const isLive = await page.isVisible('text=Expected Consultation Window');
      if (isLive) {
          console.log('Live prediction is already active!');
          const arrival = await page.locator('text=Recommended Arrival').textContent();
          console.log(`UI shows: ${arrival}`);
      } else {
          console.log('ERROR: Neither form nor live prediction is visible.');
      }
  }

  await page.screenshot({ path: 'patient_flow.png' });
  console.log('Screenshot saved to patient_flow.png');
  await browser.close();
})();
