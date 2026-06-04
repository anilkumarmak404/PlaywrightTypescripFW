import { expect, test } from '@playwright/test';
import AddPlace from '../../data/api-data/google-api-data.json'
test('@id:GOOGLE-API-001 @feature:google-place-api @owner:qa-api @jira:API-GOOGLE-001 Google API test', async ({ request }) => {
    let placeId;
    let newAddress = "6-813/44A Munnekolal,Bang IND";
    const addplaceResponse = await request.post('https://rahulshettyacademy.com/maps/api/place/add/json', {
        params: AddPlace.queryParam,
        data: AddPlace.addPlaceBody
    })
    const addplaceResponseBody = await addplaceResponse.json();
    console.log(addplaceResponseBody);
    expect(addplaceResponse.status()).toBe(200);
    placeId = addplaceResponseBody.place_id;
    console.log(placeId);

    //update the API details
    const UpdateApiResponse = await request.put("https://rahulshettyacademy.com/maps/api/place/update/json", {
        params: AddPlace.queryParam,
        data:
        {
            "place_id": placeId,
            "address": newAddress,
            "key": "qaclick123"
        }


    })
    const UpdateApiResponseJson = await UpdateApiResponse.json();
    console.log(UpdateApiResponseJson);
    expect(UpdateApiResponse.status()).toBe(200);
    expect(UpdateApiResponseJson.msg).toEqual("Address successfully updated");

    //GET place
    const getapiResponse = await request.get("https://rahulshettyacademy.com/maps/api/place/get/json", {
        params: {
            key: "qaclick123",
            place_id: placeId
        }
    })
    const getapiResponseJson = await getapiResponse.json();
    console.log(getapiResponse);
    expect(getapiResponse.status()).toBe(200);
    expect(getapiResponseJson.address).toEqual(newAddress);



});
