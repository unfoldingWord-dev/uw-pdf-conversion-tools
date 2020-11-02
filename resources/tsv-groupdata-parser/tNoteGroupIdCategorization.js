/**
 * Hard coded list of tNotes categories
 */
export const tNotesCategories = {
  discourse: {
    'figs-declarative': 'Statements - Other Uses',
    'figs-events': 'Order of Events',
    'figs-exclamations': 'Exclamations',
    'figs-exmetaphor': 'Extended Metaphor',
    'figs-imperative': 'Imperatives - Other Uses',
    'figs-parables': 'Parables',
    'figs-pastforfuture': 'Predictive Past',
    'figs-quotations': 'Direct and Indirect Quotations',
    'figs-quotesinquotes': 'Quotes Within Quotes',
    'figs-sentences': 'Sentence Structure',
    'translate-versebridge': 'Verse Bridges',
    'writing-background': 'Background Information',
    'writing-connectingwords': 'Connecting Words',
    'writing-endofstory': 'End of Story',
    'writing-intro': 'Types of Writing',
    'writing-newevent': 'Introduction of a New Event',
    'writing-participants': 'Introduction of New and Old Participants',
    'writing-poetry': 'Poetry',
    'writing-proverbs': 'Proverbs',
    'writing-quotations': 'Quotations and Quote Margins',
  },
  numbers: {
    'translate-fraction': 'Fractions',
    'translate-numbers': 'Numbers',
    'translate-ordinal': 'Ordinal Numbers',
  },
  figures: {
    'figs-apostrophe': 'Apostrophe',
    'figs-doublenegatives': 'Double Negatives',
    'figs-doublet': 'Doublet',
    'figs-ellipsis': 'Ellipsis',
    'figs-euphemism': 'Euphemism',
    'figs-hendiadys': 'Hendiadys',
    'figs-hyperbole': 'Hyperbole and Generalization',
    'figs-idiom': 'Idiom',
    'figs-irony': 'Irony',
    'figs-litotes': 'Litotes',
    'figs-merism': 'Merism',
    'figs-metaphor': 'Metaphor',
    'figs-metonymy': 'Metonymy',
    'figs-parallelism': 'Parallelism',
    'figs-personification': 'Personification',
    'figs-rquestion': 'Rhetorical Question',
    'figs-simile': 'Simile',
    'figs-synecdoche': 'Synecdoche',
  },
  culture: {
    'figs-explicit': 'Assumed Knowledge and Implicit Information',
    'figs-go': 'Go and Come',
    'translate-bdistance': 'Biblical Distance',
    'translate-bmoney': 'Biblical Money',
    'translate-bvolume': 'Biblical Volume',
    'translate-hebrewmonths': 'Hebrew Months',
    'translate-names': 'How to Translate Names',
    'translate-bweight': 'Biblical Weight',
    'translate-symaction': 'Symbolic Action',
    'translate-unknown': 'Translate Unknowns',
    'writing-symlanguage': 'Symbolic Language',
  },
  grammar: {
    'figs-abstractnouns': 'Abstract Nouns',
    'figs-activepassive': 'Active or Passive',
    'figs-distinguish': 'Distinguishing versus Informing or Reminding',
    'figs-exclusive': 'Exclusive and Inclusive "We"',
    'figs-123person': 'First, Second, or Third Person',
    'figs-they': 'Forms of They',
    'figs-you': 'Forms of You',
    'figs-we': 'Forms of We',
    'figs-genericnoun': 'Generic Noun Phrases',
    'figs-hypo': 'Hypothetical Situations',
    'figs-inclusive': 'Inclusive "We"',
    'figs-nominaladj': 'Nominal Adjectives',
    'figs-possession': 'Possession',
    'figs-pronouns': 'Pronouns',
    'figs-rpronouns': 'Reflexive Pronouns',
    'figs-gendernotations': 'When Masculine Words Include Women',
  },
  other: {
    'guidelines-sonofgodprinciples': 'Translating Son and Father',
    'translate-manuscripts': 'Original Manuscripts',
    'translate-textvariants': 'Textual Variants',
    'translate-transliterate': 'Copy or Borrow Words',
  },
};

/**
 * Gets the category name of a groupId. Returns other as a categpory name
 * if the groupId is not found in the tNotes categories in the list above.
 * @param {string} groupId tA article slug.
 * @returns {string} The category name of a groupId: discourse,
 * numbers, figures, culture, grammar or other.
 */
export const getCategoryForGroupId = groupId => {
  let result = 'other';

  Object.keys(tNotesCategories).forEach(category => {
    if (tNotesCategories[category][groupId]) {
      result = category;
    }
  });

  return result;
};

/**
 * Categorizes the group data into five categories: discourse,
 * numbers, figures, culture, grammar or other.
 * @param {Object} groupData Object of groupids that contain an
 * array of contextIds for each groupId.
 * @returns The group data categorized into five categories:
 * discourse, numbers, figures, culture, grammar or other.
 */
export const categorizeGroupData = groupData => {
  const categorizedGroupData = {
    discourse: {},
    numbers: {},
    figures: {},
    culture: {},
    grammar: {},
    other: {},
  };

  Object.keys(groupData).forEach(groupId => {
    const category = getCategoryForGroupId(groupId);
    categorizedGroupData[category][groupId] = groupData[groupId];
  });

  return categorizedGroupData;
};
