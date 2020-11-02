import fs from 'fs-extra';
import path from 'path-extra';
import { getGroupName } from './helpers/resourcesHelpers';

/**
 * make sure this groupId is in a category
 * @param {String} groupId
 * @param {String} groupName - localized group name
 * @param {Object} categorizedGroupsIndex
 * @param {String} categoryName - category that should contain this groupId
 */
const addGroupToCategory = (groupId, groupName, categorizedGroupsIndex, categoryName) => {
  const groupIndexItem = getGroupIndex(groupId, groupName);

  // Only add the groupIndexItem if it isn't already in the category's groups index.
  if (!categorizedGroupsIndex[categoryName].some(e => e.id === groupIndexItem.id)) {
    categorizedGroupsIndex[categoryName].push(groupIndexItem); // adding group Index Item
  }
};

export const generateGroupsIndex = (tnCategoriesPath, taCategoriesPath) => {
  const categorizedGroupsIndex = {
    discourse: [],
    numbers: [],
    figures: [],
    culture: [],
    grammar: [],
    other: [],
  };
  const errors = [];

  const isDirectory = item => fs.lstatSync(path.join(tnCategoriesPath, item)).isDirectory();
  const categories = fs.readdirSync(tnCategoriesPath).filter(isDirectory);

  categories.forEach(categoryName => {
    const booksPath = path.join(tnCategoriesPath, categoryName, 'groups');
    const books = fs.readdirSync(booksPath).filter(item => item !== '.DS_Store');

    books.forEach(bookid => {
      const groupDataPath = path.join(booksPath, bookid);
      const groupDataFiles = fs.readdirSync(groupDataPath).filter(filename => path.extname(filename) === '.json');
      let taArticleCategory;
      let groupName;

      groupDataFiles.forEach(groupDataFile => {
        try {
          const filePath = path.join(groupDataPath, groupDataFile);
          const groupId = groupDataFile.replace('.json', '');
          const groupData = fs.readJsonSync(filePath);
          taArticleCategory = null;
          groupName = null;
          let foundLocalization = false;

          if (groupData.length > 0) {
            for (let i = 0; i < groupData.length; i++ ) {
              const contextId = groupData[i].contextId;
              taArticleCategory = getArticleCategory(contextId.occurrenceNote, groupId);

              try {
                if (!taArticleCategory) {
                  throw new Error(`Link in Occurrence Note '${contextId.occurrenceNote}' does not have category for check at index: ${i}`);
                }

                const fileName = groupId + '.md';
                const articlePath = path.join(taCategoriesPath, taArticleCategory, fileName);
                groupName = getGroupName(articlePath);
                addGroupToCategory(groupId, groupName, categorizedGroupsIndex, categoryName);
                foundLocalization = true;
                break; // we got the category, so don't need to search anymore
              } catch (e) {
                let message = `error finding group name: groupId: '${groupId}', index: '${i}' in bookId '${bookid}, taArticleCategory: ${taArticleCategory}' `;
                console.error('generateGroupsIndex() - ' + message, e);
              }
            }

            if (!foundLocalization) {
              addGroupToCategory(groupId, groupId, categorizedGroupsIndex, categoryName); // add entry even though we could not find localized description
              console.error(`Could not find localization for '${groupId}' in '${categoryName}', adding stub entry`);
            }
          }
        } catch (e) {
          let message = `error processing entry: bookid: ${bookid}, groupDataFile: ${groupDataFile}, taArticleCategory: ${taArticleCategory}, groupName: ${groupName}: `;
          console.error('generateGroupsIndex() - ' + message, e);
          errors.push(message + e.toString());
        }
      });
    });
  });

  if (errors.length) {
    throw new Error(`generateGroupsIndex() - error processing index:\n${errors.join('\n')}`);
  }

  return categorizedGroupsIndex;
};

/**
 * Gets the category of the given groupId from the links in the occurrenceNote
 * @param {string} occurrenceNote
 * @param {string} groupId
 * @returns {string} the matched category
 */
export const getArticleCategory = (occurrenceNote, groupId) => {
  if (occurrenceNote && groupId) {
    const pattern = '(?<=rc:\\/\\/[^\\/]+\\/ta\\/man\\/)[^\\/]+?(?=\\/' + groupId + ')';
    const categoryRE = new RegExp(pattern);
    const match = occurrenceNote.match(categoryRE);

    if (match) {
      return match[0];
    }
  }
  return null;
};

const getGroupIndex = (groupId, groupName) => ({
  id: groupId,
  name: groupName,
});
