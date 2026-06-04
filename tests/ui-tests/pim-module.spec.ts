import { test, expect } from '../../fixtures/hooks-fixture';
import pimData from '../../data/ui-data/pim-module.data.json';

test.setTimeout(120000);

test('@id:PIM-001 @feature:pim-employee-management @owner:qa-hr @jira:HRM-PIM-001 [PIM] verify new employee created under PIM module', {
    tag: ['@UAT', '@REGRESSION', '@UI'],
}, async ({ pimPage }) => {
    await test.step('Add new employee and verify employee created successfully', async () => {
        await pimPage.addNewEmployee(pimData.first_name, pimData.middle_name, pimData.last_name);
        await expect(pimPage.firstNameTextBox).toHaveValue(pimData.first_name);
        await expect(pimPage.middleNameTextBox).toHaveValue(pimData.middle_name);
        await expect(pimPage.lastNameTextBox).toHaveValue(pimData.last_name);
    });
})
