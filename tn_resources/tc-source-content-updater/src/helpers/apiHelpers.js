const request = require('request');
const DCS_API = 'https://api.door43.org';
const PIVOTED_CATALOG_PATH = '/v3/subjects/pivoted.json';
/**
 * Performs a get request on the specified url.
 * This function trys to parse the body but if it fails
 * will return the body by itself.
 *
 * @param {string} url - Url of the get request to make
 * @return {Promise} - parsed body from the response
 */
function makeRequest(url) {
  return new Promise((resolve, reject) => {
    request(url, function(error, response, body) {
      if (error)
        reject(error);
      else if (response.statusCode === 200) {
        let result = body;
        try {
          result = JSON.parse(body);
        } catch (e) {
          reject(e);
        }
        resolve(result);
      }
    });
  });
}

/**
 * Request the catalog.json from DCS API
 * @return {Object} - Catalog from the DCS API
 */
export function getCatalog() {
  return makeRequest(DCS_API + PIVOTED_CATALOG_PATH);
}
