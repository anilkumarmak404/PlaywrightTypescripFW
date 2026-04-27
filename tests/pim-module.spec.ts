import { test, expect } from '../fixtures/hooks-fixture';
import pimData from '../data/pim-module.data.json';

test('[PIM] verify new employee created under PIM module', {
    tag: ['@UAT, @REGRESSION', '@UI', '@SMOKE'],
    annotation: {
        type: "Testcasid-89079",
        description: "Verify new employee created under PIM module",
    }
}, async ({ gotourl, leftNavigationPage, pimPage, logout }) => {
    await test.step('Navigate to PIM Module', async () => {
        await leftNavigationPage.openPimModule();
    });
    await test.step('Add new employee and verify employee created successfully', async () => {
        await pimPage.addNewEmployee(pimData.first_name, pimData.middle_name, pimData.last_name);
        await expect(pimPage.newEmployeeNameHeading).toHaveText(`${pimData.first_name} ${pimData.last_name}`);
    });
})
