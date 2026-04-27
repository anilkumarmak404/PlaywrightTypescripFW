import { test as baseTest } from '@playwright/test';
import { Loginpage } from '../pages/Loginpage';
import { Dashboardpage } from '../pages/Dashboardpage';
import { Userpage } from '../pages/Userpage';
import { LeftNavigationpage } from '../pages/LeftNavigationpage';
import { Pimpage } from '../pages/Pimpage';

type pomFixtureType = {
    loginPage: Loginpage;
    dashboardPage: Dashboardpage;
    userPage: Userpage;
    leftNavigationPage: LeftNavigationpage;
    pimPage: Pimpage;
}

export const test = baseTest.extend<pomFixtureType>({
    loginPage: async ({ page }, use) => {
        use(new Loginpage(page));
    },
    dashboardPage: async ({ page }, use) => {
        use(new Dashboardpage(page));
    },
    userPage: async ({ page }, use) => {
        use(new Userpage(page));
    },
    leftNavigationPage: async ({ page }, use) => {
        use(new LeftNavigationpage(page));
    },
    pimPage: async ({ page }, use) => {
        use(new Pimpage(page));
    }

});


