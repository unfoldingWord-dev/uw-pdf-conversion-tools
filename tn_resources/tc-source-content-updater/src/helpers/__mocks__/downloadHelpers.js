import url from 'url';
import fs from 'fs-extra';
import path from 'path-extra';

/**
 * @description Downloads a url to a file.
 * @param {String} uri the uri to download
 * @param {String} dest the file to download the uri to
 * @param {Function} progressCallback receives progress updates
 * @return {Promise.<{}|Error>} the status code or an error
 */
export function download(uri, dest, progressCallback) {
  return new Promise((resolve, reject) => {
    if (uri === 'a/url/that/should/fail') {
      return reject({
        uri,
        dest,
        status: 400,
      });
    }
    progressCallback = progressCallback || function() {};
    const parsedUrl = url.parse(uri, false, true);
    const filePath = path.join(__dirname, '../../../__tests__/fixtures', parsedUrl.host, parsedUrl.path);
    const content = fs.__actual.readFileSync(filePath);
    fs.writeFileSync(dest, content);
    resolve({
      uri,
      dest,
      status: 200,
    });
  });
}
