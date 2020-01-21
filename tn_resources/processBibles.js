require("babel-polyfill"); // required for async/await
const path = require('path-extra');
const fs = require('fs-extra');
const sourceContentUpdater = require('tc-source-content-updater').default;

const processBibles = (langId, workingDir, ultId, ustId) => {
  const SourceContentUpdater = new sourceContentUpdater();
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
    if (fs.pathExistsSync(packagePath))
      fs.mkdirSync(packagePath);
    SourceContentUpdater.parseBiblePackage(resource, repoPath, packagePath);
    if (resource.languageId === 'hbo' || resource.languageId === 'el-x-koine') {
      if (fs.pathExistsSync(twGroupDataPath))
        fs.mkdirSync(twGroupDataPath);
      SourceContentUpdater.generateTwGroupDataFromAlignedBible(resource, packagePath, twGroupDataPath);
    }
  });
};

// run as main
if(require.main === module) {
  if (process.argv.length < 4) {
    console.error('Syntax: node processBibles.js <lang> <working_dir> [ult_id] [ust_id]');
    return 1;
  }
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
  if (!fs.existsSync(workingDir)) {
    console.error('Working Directory does not exist: ' + workingDir);
    return 1;
  }
  processBibles(lang, workingDir, ultId, ustId);
}
