import { test, expect } from '../../fixtures/hooks-fixture';
import pimData from '../../data/ui-data/pim-module.data.json';

test.setTimeout(120000);

test.describe('[PIM] Employee Management Scenarios', {
    tag: ['@PIM']
}, () => {
    test('@id:PIM-001 @feature:pim-employee-management @owner:qa-hr @jira:SCRUM-53 [PIM] User can view employee list', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ pimPage }) => {
        await test.step('Open Employee List and verify search grid is available', async () => {
            await pimPage.openEmployeeList();
            await expect(pimPage.page).toHaveURL(/\/pim\/viewEmployeeList/);
            await expect(pimPage.searchButton).toBeVisible();
            await expect(pimPage.employeeTable).toBeVisible();
        });
    });

    test('@id:PIM-002 @feature:pim-employee-management @owner:qa-hr @jira:SCRUM-54 [PIM] User can search employee by name', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ pimPage }) => {
        await test.step('Create an employee and search using employee name', async () => {
            const employee = await pimPage.addNewEmployee(pimData.first_name, pimData.middle_name, pimData.last_name);
            await pimPage.searchEmployeeByName(employee.firstName);
            await expect(pimPage.searchButton).toBeVisible();
            await expect(pimPage.employeeTable).toBeVisible();
        });
    });

    test('@id:PIM-003 @feature:pim-employee-management @owner:qa-hr @jira:SCRUM-55 [PIM] User can search employee by employee ID', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ pimPage }) => {
        await test.step('Create an employee and search using employee ID', async () => {
            const employee = await pimPage.addNewEmployee(pimData.first_name, pimData.middle_name, pimData.last_name);
            await pimPage.searchEmployeeById(employee.employeeId);
            await expect(pimPage.page.getByText(employee.employeeId).first()).toBeVisible();
        });
    });

    test('@id:PIM-004 @feature:pim-employee-management @owner:qa-hr @jira:SCRUM-56 [PIM] User can reset employee search filters', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ pimPage }) => {
        await test.step('Enter employee ID filter and reset the search form', async () => {
            await pimPage.resetEmployeeFilters('12345');
            await expect(pimPage.employeeIdSearchInput).toHaveValue('');
            await expect(pimPage.searchButton).toBeVisible();
        });
    });

    test('@id:PIM-005 @feature:pim-employee-management @owner:qa-hr @jira:SCRUM-57 [PIM] User can add new employee with required details', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ pimPage }) => {
        await test.step('Add new employee and verify employee created successfully', async () => {
            await pimPage.addNewEmployee(pimData.first_name, pimData.middle_name, pimData.last_name);
            await expect(pimPage.firstNameTextBox).toHaveValue(pimData.first_name);
            await expect(pimPage.middleNameTextBox).toHaveValue(pimData.middle_name);
            await expect(pimPage.lastNameTextBox).toHaveValue(pimData.last_name);
        });
    });

    test('@id:PIM-006 @feature:pim-employee-management @owner:qa-hr @jira:SCRUM-58 [PIM] Add employee validates required fields', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ pimPage }) => {
        await test.step('Submit Add Employee form without required name fields', async () => {
            await pimPage.openAddEmployee();
            await pimPage.saveButton1.click();
            await expect(pimPage.requiredValidation.first()).toBeVisible();
            await expect(pimPage.page).toHaveURL(/\/pim\/addEmployee/);
        });
    });

    test('@id:PIM-007 @feature:pim-employee-management @owner:qa-hr @jira:SCRUM-59 [PIM] User can edit employee personal details', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ pimPage }) => {
        await test.step('Create employee and update middle name on personal details page', async () => {
            await pimPage.addNewEmployee(pimData.first_name, pimData.middle_name, pimData.last_name);
            await pimPage.middleNameTextBox.fill(pimData.updated_middle_name);
            await expect(pimPage.middleNameTextBox).toHaveValue(pimData.updated_middle_name);
            await pimPage.savePersonalDetails();
            await expect(pimPage.successToast).toBeVisible();
        });
    });

    test('@id:PIM-008 @feature:pim-employee-management @owner:qa-hr @jira:SCRUM-60 [PIM] User can delete employee record', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ pimPage }) => {
        await test.step('Create an employee and delete the employee from list', async () => {
            const employee = await pimPage.addNewEmployee(pimData.first_name, pimData.middle_name, pimData.last_name);
            await pimPage.deleteEmployeeById(employee.employeeId);
            await expect(pimPage.successToast).toBeVisible();
        });
    });

    test('@id:PIM-009 @feature:pim-employee-management @owner:qa-hr @jira:SCRUM-61 [PIM] User can cancel employee deletion', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ pimPage }) => {
        await test.step('Create an employee and cancel delete confirmation', async () => {
            const employee = await pimPage.addNewEmployee(pimData.first_name, pimData.middle_name, pimData.last_name);
            await pimPage.deleteEmployeeById(employee.employeeId, false);
            await expect(pimPage.page.getByText(employee.employeeId).first()).toBeVisible();
        });
    });

    test('@id:PIM-010 @feature:pim-employee-management @owner:qa-hr @jira:SCRUM-62 [PIM] User can add employee with login details enabled', {
        tag: ['@UAT', '@REGRESSION', '@UI'],
    }, async ({ pimPage }) => {
        await test.step('Enable Create Login Details while adding employee', async () => {
            await pimPage.addNewEmployee(pimData.first_name, pimData.middle_name, pimData.last_name, {
                withLogin: true
            });
            await expect(pimPage.firstNameTextBox).toHaveValue(pimData.first_name);
            await expect(pimPage.lastNameTextBox).toHaveValue(pimData.last_name);
        });
    });
});
