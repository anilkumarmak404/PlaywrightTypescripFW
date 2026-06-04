import { test, expect } from '../../fixtures/hooks-fixture';
import leaveData from '../../data/ui-data/leave-module.data.json';

test.setTimeout(120000);

test.describe('[Leave] Leave Module Scenarios', {
    tag: ['@Leave']
}, () => {
    test('@id:LEAVE-001 @feature:leave-management @owner:qa-hr @jira:HRM-LEAVE-001 [Leave] User can open leave module dashboard', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ leavePage }) => {
        await test.step('Open Leave module and verify module header', async () => {
            await leavePage.openLeaveModule();
            await expect(leavePage.page).toHaveURL(/\/leave\/(viewLeaveModule|viewLeaveList)/);
            await expect(leavePage.page.getByRole('link', { name: 'Apply' })).toBeVisible();
        });
    });

    test('@id:LEAVE-002 @feature:leave-management @owner:qa-hr @jira:HRM-LEAVE-002 [Leave] User can open leave list page', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ leavePage }) => {
        await test.step('Open Leave List and verify search filters', async () => {
            await leavePage.openLeaveList();
            await expect(leavePage.page).toHaveURL(/\/leave\/viewLeaveList/);
            await expect(leavePage.searchButton).toBeVisible();
        });
    });

    test('@id:LEAVE-003 @feature:leave-management @owner:qa-hr @jira:HRM-LEAVE-003 [Leave] User can search leave list by date range', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ leavePage }) => {
        await test.step('Search Leave List using configured date range', async () => {
            await leavePage.openLeaveList();
            await leavePage.searchLeaveListByDateRange(leaveData.from_date, leaveData.to_date);
            await expect(leavePage.page).toHaveURL(/\/leave\/viewLeaveList/);
            await expect(leavePage.searchButton).toBeVisible();
        });
    });

    test('@id:LEAVE-004 @feature:leave-management @owner:qa-hr @jira:HRM-LEAVE-004 [Leave] User can reset leave list filters', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ leavePage }) => {
        await test.step('Reset Leave List filters after entering date range', async () => {
            await leavePage.openLeaveList();
            await leavePage.searchLeaveListByDateRange(leaveData.from_date, leaveData.to_date);
            await leavePage.resetButton.click();
            await expect(leavePage.page).toHaveURL(/\/leave\/viewLeaveList/);
            await expect(leavePage.searchButton).toBeVisible();
        });
    });

    test('@id:LEAVE-005 @feature:leave-management @owner:qa-hr @jira:HRM-LEAVE-005 [Leave] User can open my leave page', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ leavePage }) => {
        await test.step('Open My Leave page and verify filters', async () => {
            await leavePage.openMyLeave();
            await expect(leavePage.page).toHaveURL(/\/leave\/viewMyLeaveList/);
            await expect(leavePage.searchButton).toBeVisible();
        });
    });

    test('@id:LEAVE-006 @feature:leave-management @owner:qa-hr @jira:HRM-LEAVE-006 [Leave] User can search my leave by date range', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ leavePage }) => {
        await test.step('Search My Leave using configured date range', async () => {
            await leavePage.openMyLeave();
            await leavePage.searchLeaveListByDateRange(leaveData.from_date, leaveData.to_date);
            await expect(leavePage.page).toHaveURL(/\/leave\/viewMyLeaveList/);
            await expect(leavePage.searchButton).toBeVisible();
        });
    });

    test('@id:LEAVE-007 @feature:leave-management @owner:qa-hr @jira:HRM-LEAVE-007 [Leave] User can open apply leave form', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ leavePage }) => {
        await test.step('Open Apply Leave and verify form fields', async () => {
            await leavePage.openApplyLeave();
            await expect(leavePage.page).toHaveURL(/\/leave\/applyLeave/);
            await expect(leavePage.applyLeaveHeading).toBeVisible();

            if (await leavePage.commentsTextArea.count()) {
                await expect(leavePage.leaveTypeDropdown).toBeVisible();
                await expect(leavePage.commentsTextArea).toBeVisible();
            } else {
                await expect(leavePage.noLeaveBalanceMessage).toBeVisible();
            }
        });
    });

    test('@id:LEAVE-008 @feature:leave-management @owner:qa-hr @jira:HRM-LEAVE-008 [Leave] Apply leave form accepts comments', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ leavePage }) => {
        await test.step('Enter comments on Apply Leave form without submitting', async () => {
            await leavePage.openApplyLeave();
            await expect(leavePage.applyLeaveHeading).toBeVisible();

            if (await leavePage.commentsTextArea.count()) {
                await leavePage.commentsTextArea.fill(leaveData.comments);
                await expect(leavePage.commentsTextArea).toHaveValue(leaveData.comments);
            } else {
                await expect(leavePage.noLeaveBalanceMessage).toBeVisible();
            }
        });
    });

    test('@id:LEAVE-009 @feature:leave-management @owner:qa-hr @jira:HRM-LEAVE-009 [Leave] User can open assign leave form', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ leavePage }) => {
        await test.step('Open Assign Leave and verify form fields', async () => {
            await leavePage.openAssignLeave();
            await expect(leavePage.page).toHaveURL(/\/leave\/assignLeave/);
            await expect(leavePage.employeeNameInput).toBeVisible();
            await expect(leavePage.leaveTypeDropdown).toBeVisible();
        });
    });

    test('@id:LEAVE-010 @feature:leave-management @owner:qa-hr @jira:HRM-LEAVE-010 [Leave] Assign leave form accepts employee search text', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ leavePage }) => {
        await test.step('Enter employee search text on Assign Leave form without submitting', async () => {
            await leavePage.openAssignLeave();
            await leavePage.employeeNameInput.fill(leaveData.employee_name);
            await expect(leavePage.employeeNameInput).toHaveValue(leaveData.employee_name);
        });
    });
});
