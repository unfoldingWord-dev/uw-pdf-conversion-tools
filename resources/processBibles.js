import path from 'path-extra';
import fs from 'fs-extra';
import Updater from './tc-source-content-updater'
import yaml from 'js-yaml';

let updater = null;

/**
 * Returns an array of versions found in the path that start with [vV]\d
 * @param {String} resourcePath - base path to search for versions
 * @return {Array} - array of versions, e.g. ['v1', 'v10', 'v1.1']
 */
function getVersionsInPath(resourcePath) {
  if (!resourcePath || !fs.pathExistsSync(resourcePath)) {
    return null;
  }
  const isVersionDirectory = (name) => {
    const fullPath = path.join(resourcePath, name);
    return fs.lstatSync(fullPath).isDirectory() && name.match(/^v\d/i);
  };
  return sortVersions(fs.readdirSync(resourcePath).filter(isVersionDirectory));
}

/**
 * Returns a sorted an array of versions so that numeric parts are properly ordered (e.g. v10a < v100)
 * @param {Array} versions - array of versions unsorted: ['v05.5.2', 'v5.5.1', 'V6.21.0', 'v4.22.0', 'v6.1.0', 'v6.1a.0', 'v5.1.0', 'V4.5.0']
 * @return {Array} - array of versions sorted:  ["V4.5.0", "v4.22.0", "v5.1.0", "v5.5.1", "v05.5.2", "v6.1.0", "v6.1a.0", "V6.21.0"]
 */
function sortVersions(versions) {
  // Don't sort if null, empty or not an array
  if (!versions || !Array.isArray(versions)) {
    return versions;
  }
  // Only sort of all items are strings
  for (let i = 0; i < versions.length; ++i) {
    if (typeof versions[i] !== 'string') {
      return versions;
    }
  }
  versions.sort((a, b) => String(a).localeCompare(b, undefined, {numeric: true}));
  return versions;
}

/**
 * Return the full path to the highest version folder in resource path
 * @param {String} resourcePath - base path to search for versions
 * @return {String} - path to highest version
 */
function getLatestVersionInPath(resourcePath) {
  const versions = sortVersions(getVersionsInPath(resourcePath));
  if (versions && versions.length) {
    return path.join(resourcePath, versions[versions.length - 1]);
  }
  return null; // return illegal path
}

const processOLBible = (resource) => {
  const repo = resource.languageId + '_' + resource.resourceId;
  const repoPath = path.join(workingDir, repo);
  const manifest = yaml.safeLoad(fs.readFileSync(path.join(repoPath, 'manifest.yaml'), 'utf8'));
  const version = manifest['dublin_core']['version'];
  const biblePath = path.join(resourcesPath, resource.languageId, 'bibles', resource.resourceId, 'v' + version);
  console.log("BIBLE " + resource.resourceId + ": " + biblePath + ", repoPath: " + repoPath)
  updater.parseBiblePackage(resource, repoPath, biblePath);
  const twGroupDataPath = path.join(resourcesPath, resource.languageId, 'translationHelps', 'translationWords', 'v' + version);
  console.log("TW " + resource.resourceId + ": " + twGroupDataPath);
  updater.generateTwGroupDataFromAlignedBible(resource, biblePath, twGroupDataPath);
};

const processUWBible = (resource) => {
  const repo = resource.languageId + '_' + resource.resourceId;
  const repoPath = path.join(workingDir, repo);
  const manifest = yaml.safeLoad(fs.readFileSync(path.join(repoPath, 'manifest.yaml'), 'utf8'));
  const version = manifest['dublin_core']['version'];
  const biblePath = path.join(resourcesPath, resource.languageId, 'bibles', resource.resourceId, 'v' + version);
  console.log("BIBLE " + resource.resourceId + ": " + biblePath)
  updater.parseBiblePackage(resource, repoPath, biblePath);
};

const processTA = (resource) => {
  const taRepo = resource.languageId + '_ta';
  const taRepoPath = path.join(workingDir, taRepo);
  const taManifest = yaml.safeLoad(fs.readFileSync(path.join(taRepoPath, 'manifest.yaml'), 'utf8'));
  const taVersion = taManifest['dublin_core']['version'];
  const taGroupDataPath = path.join(resourcesPath, resource.languageId, 'translationHelps', 'translationAcademy', 'v' + taVersion);
  console.log("TA " + resource.resourceId + ": " + taGroupDataPath);
  updater.processTranslationAcademy(resource, taRepoPath, taGroupDataPath);
};

const processTW = (resource) => {
  const twRepo = resource.languageId + '_tw';
  const twRepoPath = path.join(workingDir, twRepo);
  const twManifest = yaml.safeLoad(fs.readFileSync(path.join(twRepoPath, 'manifest.yaml'), 'utf8'));
  const twVersion = twManifest['dublin_core']['version'];
  const twGroupDataPath = path.join(resourcesPath, resource.languageId, 'translationHelps', 'translationWords', 'v' + twVersion);
  console.log("TW " + resource.resourceId + ": " + twGroupDataPath);
  updater.processTranslationWords(resource, twRepoPath, twGroupDataPath);
};

const processTN = (resource) => {
  const tnRepo = resource.languageId + '_tn';
  const tnRepoPath = path.join(workingDir, tnRepo);
  const tnManifest = yaml.safeLoad(fs.readFileSync(path.join(tnRepoPath, 'manifest.yaml'), 'utf8'));
  const tnVersion = tnManifest['dublin_core']['version'];
  const tnGroupDataPath = path.join(resourcesPath, resource.languageId, 'translationHelps', 'translationNotes', 'v' + tnVersion);
  console.log("TN: " + tnGroupDataPath);
  updater.processTranslationNotes(resource, tnRepoPath, tnGroupDataPath, resourcesPath);
};

const processSN = (resource) => {
  const snRepo = resource.languageId + '_sn';
  const snRepoPath = path.join(workingDir, snRepo);
  const snManifest = yaml.safeLoad(fs.readFileSync(path.join(snRepoPath, 'manifest.yaml'), 'utf8'));
  const snVersion = snManifest['dublin_core']['version'];
  const snGroupDataPath = path.join(resourcesPath, resource.languageId, 'translationHelps', 'studyNotes', 'v' + snVersion);
  console.log("SN: " + snGroupDataPath);
  updater.processTranslationNotes(resource, snRepoPath, snGroupDataPath, resourcesPath);
};

const processBibles = (langId, workingDir, resourcesPath, book, ultId, ustId) => {
  updater = new Updater();
  fs.mkdirSync(resourcesPath, {recursive: true});
  processOLBible({
    book: book,
    languageId: 'hbo',
    resourceId: 'uhb',
    downloadUrl: 'https://test.com'
  });
  processOLBible({
    book: book,
    languageId: 'el-x-koine',
    resourceId: 'ugnt',
    downloadUrl: 'https://test.com'
  });
  processUWBible({
    book: book,
    languageId: langId,
    resourceId: ultId,
    downloadUrl: 'https://test.com'
  });
  processUWBible({
    book: book,
    languageId: langId,
    resourceId: ustId,
    downloadUrl: 'https://test.com'
  });
  processTA({
    languageId: langId,
    resourceId: 'ta',
    downloadUrl: 'https://test.com'
  });
  processTW({
    languageId: langId,
    resourceId: 'tw',
    downloadUrl: 'https://test.com'
  });
  processTN({
    book: book,
    languageId: langId,
    resourceId: 'tn',
    downloadUrl: 'https://test.com'
  });
  // processSN({
  //   languageId: langId,
  //   resourceId: 'sn',
  //   downloadUrl: 'https://test.com'
  // });
};

if (process.argv.length < 4) {
  throw Error('Syntax: node processBibles.js <lang> <working_dir> [book] [ult_id] [ust_id]');
}
const lang = process.argv[2];
const resourcesPath = process.argv[3];
const workingDir = path.dirname(resourcesPath)
let ultId = 'ult';
let ustId = 'ust';
let book = null;
if (process.argv.length > 4) {
  book = process.argv[4];
  if (book == 'all')
    book = null;
}
if (process.argv.length > 5) {
  ultId = process.argv[5];
}
if (process.argv.length > 6) {
  ustId = process.argv[6];
}
if (!fs.existsSync(workingDir)) {
  throw Error('Parent of resources path does not exist: ' + workingDir);
}
processBibles(lang, workingDir, resourcesPath, book, ultId, ustId);
// processTnData(lang, workingDir, ultId,ustId);

