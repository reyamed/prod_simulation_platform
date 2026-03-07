const { test, expect } = require('@playwright/test');

test.describe('Elastic Simulator Authentication and Game Flow', () => {
    test.beforeEach(async ({ page }) => {
        // Go to our frontend
        await page.goto('http://localhost:5173');
    });

    test('should register a new user, log in, start game and skip to next stage', async ({ page }) => {
        // Wait for page to load and confirm we are on the login form
        await expect(page.locator('h1')).toHaveText('Elastic Simulator');
        await expect(page.locator('h2')).toHaveText('Player Login');

        // Switch to registration context
        await page.getByText('Need an account? Register here.').click();
        await expect(page.locator('h2')).toHaveText('Register Account');

        // Generate a random email/username for the session to avoid unique conflicts in live db
        const randId = Date.now();
        const randEmail = `test_${randId}@example.com`;
        const randUser = `E2E_${randId}`;

        // Fill out registration form
        await page.getByPlaceholder('Username').fill(randUser);
        await page.getByPlaceholder('Email Address').fill(randEmail);
        await page.getByPlaceholder('Password').fill('securetest123');

        // Submit form
        await page.getByRole('button', { name: 'Sign Up' }).click();

        // After successful registration, it automatically attempts a login via our React hook 
        // We should eventually see the Welcome message on the dashboard panel
        await expect(page.getByText('Welcome to the active simulation floor.')).toBeVisible({ timeout: 10000 });

        // Ensure "Incident Board" title is present
        await expect(page.getByText('Incident Board')).toBeVisible();

        // Ensure that Stage 1 Ticket is mounted and listed.
        await expect(page.getByText('Billing logs are missing!').first()).toBeVisible();

        // Assert we see the skip button
        const skipBtn = page.getByRole('button', { name: 'Skip Stage ⏭️' });
        await expect(skipBtn).toBeVisible();

        // Perform Skip Stage to unlock Stage 2.
        // Wait, window.confirm intercepts Playwright executions! We must intercept the dialog.
        page.on('dialog', dialog => dialog.accept());

        await skipBtn.click();

        // Now assert the Toast message comes up globally
        await expect(page.getByText('Stage skipped. Next scenario unlocked!')).toBeVisible({ timeout: 6000 });

        // The "To Do" column should now mount "Cluster Health is Yellow - Unassigned Shards!"
        await expect(page.getByText('Cluster Health is Yellow - Unassigned Shards!').first()).toBeVisible();
    });
});
