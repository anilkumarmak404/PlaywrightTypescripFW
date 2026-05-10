import { test as baseTest } from '../fixtures/pom-fixtures';
import CommonApiUtils from '../utils/commonApiUtils';
import CommonUtils from '../utils/commonUtils';

type commonFixtureType = {
    commonUtils: CommonUtils;
    commonApiUtils: CommonApiUtils
}

export const test = baseTest.extend<commonFixtureType>({
    commonUtils: async ({ }, use) => {
        use(new CommonUtils());
    },
    commonApiUtils: async ({ request }, use) => {
        use(new CommonApiUtils(request))
    }


});