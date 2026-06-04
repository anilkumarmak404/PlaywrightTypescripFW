import { expect, test } from '../../fixtures/hooks-fixture';
import apiPathData from '../../data/api-data/api-path-data.json';
import restfulApiData from '../../data/api-data/restful-booker-api-module.data.json';

// to run the APi's npm run test_demo_api

test("@id:BOOKER-API-001 @feature:restful-booker-api @owner:qa-api @jira:API-BOOKER-001 Get Booking ID's from api call", async ({ request }) => {
    const bookingIds = await request.get("booking");
    console.log(await bookingIds.json());

})
test("@id:BOOKER-API-002 @feature:restful-booker-api @owner:qa-api @jira:API-BOOKER-002 Get the booking details", async ({ request }) => {
    const bookingDetails = await request.get('booking/6');
    console.log(await bookingDetails.json());

});
test('@id:BOOKER-API-003 @feature:restful-booker-api @owner:qa-api @jira:API-BOOKER-003 TC1 :create new booking and verify the booking details', {
    tag: ['@API', '@UAT'],
}, async ({ request }) => {
    const bookingIdRes = await request.get(apiPathData.Booking_path);
    const bookingIdResJson = await bookingIdRes.json();
    console.log(bookingIdResJson);
    expect(bookingIdRes.status()).toBe(200);
    expect(bookingIdRes.statusText()).toBe('OK')
    expect(bookingIdRes.ok()).toBeTruthy();
    expect(bookingIdResJson).not.toBeNull();
    expect(bookingIdRes.headers()['content-type']).toBe(restfulApiData['content-type']);

});

test('@id:BOOKER-API-004 @feature:restful-booker-api @owner:qa-api @jira:API-BOOKER-004 Tc-9 rest-booker GET api booking details and verify the valid response', {
    tag: ['@API', '@UAT'],
}, async ({ request }) => {
    const bookingResp = await request.get(`${apiPathData.Booking_path}/${restfulApiData.booking_id}`);
    const bookingRespJson = await bookingResp.json();
    console.log(bookingRespJson);
    expect(bookingResp.status()).toBe(200);
    expect(bookingResp.statusText()).toBe('OK');
    expect(bookingResp.ok()).toBeTruthy();
    expect(bookingRespJson).not.toBeNull();
    // expect(bookingRespJson.lastname).toEqual(restfulApiData.lastname);
    // expect(bookingRespJson.totalprice).toEqual(restfulApiData.totalprice);
});
test('@id:BOOKER-API-005 @feature:restful-booker-api @owner:qa-api @jira:API-BOOKER-005 TEST-10:adding booking details to an api and get the response', {
    tag: ['@API', '@UAT'],
}, async ({ request }) => {
    const bookingDetailsRes = await request.post(apiPathData.Booking_path, {
        data: restfulApiData.update_booking
    });
    const bookingDetailsResjson = await bookingDetailsRes.json();
    console.log(bookingDetailsResjson);
    expect(bookingDetailsRes.status()).toBe(200);
    expect(bookingDetailsRes.statusText()).toBe("OK");
    expect(bookingDetailsResjson).not.toBeNull();
    expect(bookingDetailsResjson.booking.firstname).toEqual(restfulApiData.update_booking.firstname);
    expect(bookingDetailsResjson.booking.totalprice).toEqual(restfulApiData.update_booking.totalprice);
    expect(bookingDetailsResjson.booking).toMatchObject(restfulApiData.update_booking);

})
test('@id:BOOKER-API-006 @feature:restful-booker-api @owner:qa-api @jira:API-BOOKER-006 TEST-11:adding booking details to an api and get the response using basic auth method', {
    tag: ['@API', '@UAT'],
}, async ({ request, commonApiUtils }) => {
    const tokenValue = await commonApiUtils.createToken();
    const bookingDetailsRes = await request.post(apiPathData.Booking_path, {
        headers: {
            cookie: `token = ${tokenValue}`
        },
        data: restfulApiData.update_booking

    }
    );
    const bookingDetailsResjson = await bookingDetailsRes.json();
    console.log(bookingDetailsResjson);
    expect(bookingDetailsRes.status()).toBe(200);
    expect(bookingDetailsRes.statusText()).toBe("OK");
    expect(bookingDetailsResjson).not.toBeNull();
    expect(bookingDetailsResjson.booking.firstname).toEqual(restfulApiData.update_booking.firstname);
    expect(bookingDetailsResjson.booking.totalprice).toEqual(restfulApiData.update_booking.totalprice);
    expect(bookingDetailsResjson.booking).toMatchObject(restfulApiData.update_booking);

})
