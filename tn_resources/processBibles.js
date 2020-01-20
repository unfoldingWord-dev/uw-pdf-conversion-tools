require("babel-polyfill"); // required for async/await
import  path from 'path-extra';
import fs  from 'fs-extra';
import * as parseHelpers from  'tc-source-content-updater/src/helpers/packageParseHelpers';
import * as dataHelpers from  'tc-source-content-updater/src/helpers/translationHelps/twGroupDataHelpers';

const processBibles = (langId, workingDir, ultId, ustId) => {
  const resources = [
    {
      languageId: 'hbo',
      resourceId: 'uhb',
      downloadUrl: 'https://test.com'
    },
    {
      languageId: 'el-x-koine',
      resourceId: 'ugnt',
      downloadUrl: 'https://test.com'
    },
    {
      languageId: langId,
      resourceId: ultId,
      downloadUrl: 'https://test.com'
    },
    {
      languageId: langId,
      resourceId: ustId,
      downloadUrl: 'https://test.com'
    }
  ];
  resources.forEach((resource) => {
    const repo = resource.languageId + '_' + resource.resourceId;
    const repoPath = path.join(workingDir, repo);
    const packagePath = path.join(workingDir, repo + '_master_package');
    const twGroupDataPath = path.join(packagePath + '_tw_group_data');
    if (resource.languageId === 'hbo' || resource.languageId === 'el-x-koine') {
      if (! fs.pathExists(packagePath)) {
        if (!fs.existsSync(packagePath)) {
          fs.mkdirSync(packagePath);
        }
        parseHelpers.parseBiblePackage(resource, repoPath, packagePath);
      }
      if (! fs.pathExists(twGroupDataPath)) {
        dataHelpers.generateTwGroupDataFromAlignedBible(resource, packagePath, twGroupDataPath);
      }
    } else {
      if (!fs.existsSync(packagePath)) {
        fs.mkdirSync(packagePath);
      }
      parseHelpers.parseBiblePackage(resource, repoPath, packagePath);
    }
  });
};

if (process.argv.length < 4) {
    console.error('Syntax: node processBibles.js <lang> <working_dir> [ult_id] [ust_id]');
}
else {
  const lang = process.argv[2];
  const workingDir = process.argv[3];
  let ultId = 'ult';
  let ustId = 'ust';
  if (process.argv.length > 4) {
    ultId = process.argv[4];
  }
  if (process.argv.length > 5) {
    ustId = process.argv[5];
  }
  if (! fs.existsSync(workingDir)) {
    console.error('Working Directory does not exist: ' + workingDir);
  }
  else {
    processBibles(lang, workingDir, ultId, ustId);
  }
}
