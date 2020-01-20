'use strict';
import path from 'path-extra';
const fsActual = require.requireActual('fs-extra'); // for copying test files into mock
const fs = jest.genMockFromModule('fs-extra');
let mockFS = Object.create(null);

/** @deprecated */
function __setMockFS(newMockFS) {
  mockFS = newMockFS;
}

/**
 *  @description - clear out mock file system
 */
function __resetMockFS() {
  mockFS = Object.create(null);
}

/**
 * This is a custom function that our tests can use during setup to specify
 * what the files on the "mock" filesystem should look like when any of the
 * `fs` APIs are used.
 * @param {Array} newMockFiles
 */
function __setMockDirectories(newMockFiles) {
  mockFS = Object.create(null);
  for (const file in newMockFiles) {
    const dir = path.dirname(file);

    if (!mockFS[dir]) {
      mockFS[dir] = [];
    }
    mockFS[dir].push(path.basename(file));
  }
}

/**
 * A custom version of `readdirSync` that reads from the special mocked out
 * file list set via __setMockDirectories
 * @param {String} directoryPath - Directory path
 * @return {Array} Contents of the given path
 */
function readdirSync(directoryPath) {
  if (statSync(directoryPath).isDirectory()) {
    return mockFS[directoryPath];
  }
  return [];
}

function writeFileSync(filePath, data) {
  addFileToParentDirectory(filePath);
  mockFS[filePath] = data;
}

function readFileSync(filePath) {
  if (typeof filePath !== 'string') throw 'fail';
  return mockFS[filePath];
}

function outputFileSync(filePath, data) {
  addFileToParentDirectory(filePath);
  mockFS[filePath] = data;
}

function __dumpMockFS() {
  const fsList = JSON.stringify(mockFS, null, 2);
  console.log('mock FS:\n' + fsList);
}

/**
 * @description Call this to list out a directory's content of the mockFS.
 * Can be recursive to list all files and directories under the directoryPath
 * @param {String} directoryPath The root path to list
 * @param {Boolean} recursive If this is to be recursive or not
 */
function __listMockFS(directoryPath, recursive = true) {
  if (!directoryPath) {
    directoryPath = path.parse(process.cwd()).root; // '/' for Unix, C:\ for Windows
    recursive = true;
  }
  if (mockFS[directoryPath] === undefined) {
    console.log('mockFS - Does not exist: ' + directoryPath);
  } else if (statSync(directoryPath).isFile()) {
    console.log('mockFS - ls:\n', directoryPath);
  } else {
    console.log(__getListMockFS(directoryPath, recursive));
  }
}

/**
 * @description The recursive function for getting a mocked directory listing
 * @param {String} directoryPath The root path to list
 * @param {Boolean} recursive If this is to be recursive or not
 * @return {String} The list of files
 */
function __getListMockFS(directoryPath, recursive = true) {
  let ls = directoryPath + ':\n';
  if (!mockFS[directoryPath] || !mockFS[directoryPath].length) {
    return '\t<empty>\n';
  }
  const content = mockFS[directoryPath].sort();
  content.forEach((item) => {
    const fullPath = path.join(directoryPath, item);
    const isDir = statSync(path.join(fullPath)).isDirectory();
    if (isDir) {
      item += '/';
    }
    if (mockFS[fullPath])
      item += '\t' + mockFS[fullPath].length;
    ls += '\t' + item + '\n';
  });
  if (recursive) {
    content.forEach((item) => {
      const fullPath = path.join(directoryPath, item);
      const isDir = statSync(path.join(fullPath)).isDirectory();
      if (isDir && mockFS[fullPath] && mockFS[fullPath].length) {
        ls += __getListMockFS(fullPath, recursive);
      }
    });
  }
  return ls;
}

function __catMockFS(folder) {
  return JSON.stringify(mockFS[folder], null, 2);
  // return JSON.stringify(mockFS, null, 2);
}

/**
 * create subdirs and add file name to them
 * @param {String} filePath Fie path
 */
function addFileToParentDirectory(filePath) {
  const dir = path.dirname(filePath);
  const filename = path.basename(filePath);
  if (filename) {
    if (!mockFS[dir]) {
      mockFS[dir] = [];
      addFileToParentDirectory(dir);
    }
    if (mockFS[dir].indexOf(filename) < 0) {
      mockFS[dir].push(filename);
    }
  }
}

function outputJsonSync(filePath, data) {
  addFileToParentDirectory(filePath);
  // clone data so changes to object do not affect object in file system
  const clonedData = JSON.parse(JSON.stringify(data));
  mockFS[filePath] = clonedData;
}

function readJsonSync(filePath) {
  if (!existsSync(filePath)) {
    throw 'File could not be read: ' + filePath;
  }
  const data = mockFS[filePath];
  // clone data so changes to object do not affect object in file system
  const clonedData = JSON.parse(typeof data === 'string' ? data : JSON.stringify(data));
  return clonedData;
}

function existsSync(path) {
  return mockFS[path] !== '' ? !!mockFS[path] : true;
}

function exists(path, callback) {
  callback(mockFS[path] !== '' ? !!mockFS[path] : true);
}


function removeSync(path) {
  Object.keys(mockFS).forEach((element) => {
    element.includes(path) ? delete mockFS[element] : null;
  });
}

function renameSync(oldPath, newPath) {
  writeFileSync(newPath, readFileSync(oldPath));
  removeSync(oldPath);
}

function copySync(srcPath, destinationPath) {
  mockFS[destinationPath] = mockFS[srcPath];
  addFileToParentDirectory(destinationPath);
  const isDir = statSync(srcPath).isDirectory();
  if (isDir) {
    const files = readdirSync(srcPath);
    for (const f of files) {
      copySync(path.join(srcPath, f), path.join(destinationPath, f));
    }
  }
}

/**
 * @description cause a directory to exist if it does not
 * @param path - path to directory
 */
function ensureDirSync(path) {
  if (!mockFS[path]) mockFS[path] = [];
  addFileToParentDirectory(path);
}

/**
 * @description determine file status
 * @param path - path to file or directory
 * @param exists - expect file to exist
 * @param isDir - expect a directory
 * @return {boolean} - is item a regular file or directory
 */
function Stats(path, exists, isDir) {
  this.path = path;
  this.exists = exists;
  this.isDir = isDir;
  this.atime = 'Not-a-real-date';
  this.isDirectory = () => {
    const isDir = this.exists && this.isDir;
    return isDir;
  };
  this.isFile = () => {
    const isFile = this.exists && !this.isDir;
    return isFile;
  };
}

/**
 * @description ensure this actually contains an array of file names (strings)
 * @param path
 * @return {arg is Array<any>}
 */
function isValidDirectory(path) {
  const dir = mockFS[path];
  let isDir = Array.isArray(dir);
  if (isDir) { // make sure it's an array of paths (strings) and not objects (such as json object stored)
    const failedItem = dir.findIndex((item) => (typeof item !== 'string'));
    isDir = (failedItem < 0); // valid if failed item not found
  }
  return isDir;
}

/**
 * @description only minimal implementation of fs.Stats: isDirectory() and isFile()
 * @param {string} path - file name to stat
 * @return {Object} - Stats Object
 */
function statSync(path) {
  const exists = existsSync(path);
  const isDir = (exists && isValidDirectory(path));
  return new Stats(path, exists, isDir);
}

/**
 * @description convertes linux style separators to OS specific separators
 * @param {string} filePath
 * @return {string} converted path
 */
function __correctSeparatorsFromLinux(filePath) {
  const result = filePath.split('/').join(path.sep);
  return result;
}

/**
 * @description - copies list of files from local file system into mock File system
 * @param {array} copyFiles - array of paths (in linux format) relative to source path
 * @param {string} sourceFolder - source folder fo files to copy (in linux format)
 * @param {string} mockDestinationFolder - destination folder for copied files {string} in mock File system
 */
function __loadFilesIntoMockFs(copyFiles, sourceFolder, mockDestinationFolder) {
  const mockDestinationFolder_ =
    __correctSeparatorsFromLinux(mockDestinationFolder);
  const sourceFolder_ = __correctSeparatorsFromLinux(sourceFolder);
  for (const copyFile of copyFiles) {
    const filePath2 = path.join(sourceFolder_,
      __correctSeparatorsFromLinux(copyFile));
    let fileData = null;
    const isDir = fsActual.statSync(filePath2).isDirectory();
    if (!isDir) {
      fileData = fsActual.readFileSync(filePath2).toString();
    }
    let dirPath = mockDestinationFolder_;
    fs.ensureDirSync(dirPath);
    const parts = copyFile.split('/');
    const endCount = parts.length - 1;
    for (let i = 0; i < endCount; i++) {
      const part = parts[i];
      dirPath = path.join(dirPath, part);
      fs.ensureDirSync(dirPath);
    }
    if (!isDir) {
      const filePath = path.join(mockDestinationFolder_, parts.join(path.sep));
      // console.log("Copying File: " + filePath);
      fs.writeFileSync(filePath, fileData);
    } else {
      __loadDirIntoMockFs(
        filePath2, path.join(mockDestinationFolder, copyFile));
    }
  }
}

/**
 * @description - recursively copies folder from local file system into mock File system
 * @param {string} sourceFolder - source folder fo files to copy (in linux format)
 * @param {string} mockDestinationFolder - destination folder for copied files {string} in mock File system
 */
function __loadDirIntoMockFs(sourceFolder, mockDestinationFolder) {
  const mockDestinationFolder_ =
    __correctSeparatorsFromLinux(mockDestinationFolder);
  fs.ensureDirSync(mockDestinationFolder_);
  const sourceFolder_ = __correctSeparatorsFromLinux(sourceFolder);
  // console.log("Copying Directory: " + sourceFolder_);
  const files = fsActual.readdirSync(sourceFolder_);
  for (const file of files) {
    const sourceFilePath = path.join(sourceFolder, file);
    const mockFilePath = path.join(mockDestinationFolder_, file);
    const isDir = fsActual.statSync(sourceFilePath).isDirectory();
    if (!isDir) {
      const fileData = fsActual.readFileSync(sourceFilePath).toString();
      // console.log("Copying Subfile: " + mockFilePath);
      fs.writeFileSync(mockFilePath, fileData);
    } else {
      // console.log("Entering Subdir: " + mockFilePath);
      __loadDirIntoMockFs(sourceFilePath, mockFilePath);
    }
  }
}

function moveSync(source, destination) {
  copySync(source, destination);
  removeSync(source);
}

const stream = require('stream');
/**
 * Mock write stream
 * @param {string} path the path to create the write stream
 * @return {Function}
 */
function createWriteStream(path) {
  const writable = new stream.Writable({
    write: function(chunk, encoding, next) {
      fs.writeFileSync(path, chunk);
      next();
    },
  });
  return writable;
}

fs.createWriteStream = createWriteStream;
fs.__files = () => {
  return mockFS;
};
fs.__dumpMockFS = __dumpMockFS;
fs.__listMockFS = __listMockFS;
fs.__catMockFS = __catMockFS;
fs.__setMockDirectories = __setMockDirectories;
fs.__setMockFS = __setMockFS;
fs.__resetMockFS = __resetMockFS;
fs.__actual = fsActual; // to access actual file system
fs.__loadFilesIntoMockFs = __loadFilesIntoMockFs;
fs.__correctSeparatorsFromLinux = __correctSeparatorsFromLinux;
fs.__loadDirIntoMockFs = __loadDirIntoMockFs;
fs.readdirSync = readdirSync;
fs.writeFileSync = writeFileSync;
fs.readFileSync = readFileSync;
fs.writeJsonSync = outputJsonSync;
fs.writeJSONSync = outputJsonSync;
fs.outputJsonSync = outputJsonSync;
fs.readJsonSync = readJsonSync;
fs.readJSONSync = readJsonSync;
fs.existsSync = existsSync;
fs.exists = exists;
fs.pathExistsSync = existsSync;
fs.outputFileSync = outputFileSync;
fs.removeSync = removeSync;
fs.copySync = copySync;
fs.renameSync = renameSync;
fs.ensureDirSync = ensureDirSync;
fs.statSync = statSync;
fs.fstatSync = statSync;
fs.lstatSync = statSync;
fs.moveSync = moveSync;

module.exports = fs;
