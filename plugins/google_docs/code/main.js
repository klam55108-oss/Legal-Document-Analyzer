/**
 * Legal Document Analyzer for Google Docs
 * Main code file
 */

// Global variables
var API_URL = '';
var API_KEY = '';
var DOC_ID = '';

/**
 * Creates the add-on menu when the document is opened.
 * @param {Object} e The event parameter (unused).
 */
function onOpen(e) {
  DocumentApp.getUi()
    .createAddonMenu()
    .addItem('Analyze Document', 'showAnalyzeDocumentDialog')
    .addItem('Generate Brief', 'showGenerateBriefDialog')
    .addItem('Validate Statutes', 'showValidateStatutesDialog')
    .addSeparator()
    .addItem('Settings', 'showSettingsDialog')
    .addToUi();
}

/**
 * Runs when the add-on is installed.
 * @param {Object} e The event parameter (unused).
 */
function onInstall(e) {
  onOpen(e);
  showSettingsDialog();
}

/**
 * Shows a dialog to analyze the current document.
 */
function showAnalyzeDocumentDialog() {
  var ui = DocumentApp.getUi();
  
  // Check if API settings are configured
  if (!loadSettings()) {
    ui.alert('Please configure your API settings first.');
    showSettingsDialog();
    return;
  }
  
  // Get the document content
  var document = DocumentApp.getActiveDocument();
  var docText = document.getBody().getText();
  
  // Show loading dialog
  var htmlOutput = HtmlService.createHtmlOutput('<p>Analyzing document...</p>')
    .setWidth(300)
    .setHeight(100);
  ui.showModalDialog(htmlOutput, 'Please wait');
  
  try {
    // Call the API to analyze the document
    var response = analyzeDocument(docText);
    
    // Show results
    var htmlTemplate = HtmlService.createTemplateFromFile('analysis_results');
    htmlTemplate.data = response;
    
    htmlOutput = htmlTemplate.evaluate()
      .setWidth(600)
      .setHeight(400);
    ui.showModalDialog(htmlOutput, 'Analysis Results');
  } catch (error) {
    ui.alert('Error analyzing document: ' + error.toString());
  }
}

/**
 * Shows a dialog to generate a brief.
 */
function showGenerateBriefDialog() {
  var ui = DocumentApp.getUi();
  
  // Check if API settings are configured
  if (!loadSettings()) {
    ui.alert('Please configure your API settings first.');
    showSettingsDialog();
    return;
  }
  
  // Show brief generation dialog
  var htmlTemplate = HtmlService.createTemplateFromFile('generate_brief');
  
  var htmlOutput = htmlTemplate.evaluate()
    .setWidth(500)
    .setHeight(400);
  ui.showModalDialog(htmlOutput, 'Generate Brief');
}

/**
 * Shows a dialog to validate statutes.
 */
function showValidateStatutesDialog() {
  var ui = DocumentApp.getUi();
  
  // Check if API settings are configured
  if (!loadSettings()) {
    ui.alert('Please configure your API settings first.');
    showSettingsDialog();
    return;
  }
  
  // Get the document content
  var document = DocumentApp.getActiveDocument();
  var docText = document.getBody().getText();
  
  // Show loading dialog
  var htmlOutput = HtmlService.createHtmlOutput('<p>Validating statutes...</p>')
    .setWidth(300)
    .setHeight(100);
  ui.showModalDialog(htmlOutput, 'Please wait');
  
  try {
    // Call the API to analyze the document first (if not already analyzed)
    if (!DOC_ID) {
      var response = analyzeDocument(docText);
      DOC_ID = response.document_id;
    }
    
    // Call the API to validate statutes
    var statutes = validateStatutes(DOC_ID);
    
    // Show results
    var htmlTemplate = HtmlService.createTemplateFromFile('statute_results');
    htmlTemplate.data = statutes;
    
    htmlOutput = htmlTemplate.evaluate()
      .setWidth(600)
      .setHeight(400);
    ui.showModalDialog(htmlOutput, 'Statute Validation Results');
  } catch (error) {
    ui.alert('Error validating statutes: ' + error.toString());
  }
}

/**
 * Shows the settings dialog.
 */
function showSettingsDialog() {
  var ui = DocumentApp.getUi();
  
  // Load current settings
  loadSettings();
  
  // Create and show the settings dialog
  var htmlTemplate = HtmlService.createTemplateFromFile('settings');
  htmlTemplate.apiUrl = API_URL;
  htmlTemplate.apiKey = API_KEY;
  
  var htmlOutput = htmlTemplate.evaluate()
    .setWidth(400)
    .setHeight(300);
  ui.showModalDialog(htmlOutput, 'Legal Document Analyzer Settings');
}

/**
 * Saves the API settings.
 * @param {Object} settings The settings to save.
 */
function saveSettings(settings) {
  PropertiesService.getUserProperties().setProperties({
    'apiUrl': settings.apiUrl,
    'apiKey': settings.apiKey
  });
  
  API_URL = settings.apiUrl;
  API_KEY = settings.apiKey;
  
  return true;
}

/**
 * Loads the API settings.
 * @return {boolean} True if settings are loaded and valid.
 */
function loadSettings() {
  var props = PropertiesService.getUserProperties().getProperties();
  
  API_URL = props.apiUrl || '';
  API_KEY = props.apiKey || '';
  
  return API_URL && API_KEY;
}

/**
 * Analyzes a document.
 * @param {string} docText The document text.
 * @return {Object} The analysis results.
 */
function analyzeDocument(docText) {
  // Create a blob with the document content
  var blob = Utilities.newBlob(docText, 'text/plain', 'document.txt');
  
  // Create a form data object
  var formData = {
    'file': blob
  };
  
  // Make API request
  var response = UrlFetchApp.fetch(API_URL + '/api/documents', {
    'method': 'post',
    'payload': formData,
    'headers': {
      'X-API-Key': API_KEY
    },
    'muteHttpExceptions': true
  });
  
  // Check response
  if (response.getResponseCode() !== 200) {
    throw new Error('API request failed: ' + response.getContentText());
  }
  
  // Parse response
  var result = JSON.parse(response.getContentText());
  
  // Store document ID for later use
  DOC_ID = result.id;
  
  return result;
}

/**
 * Generates a brief.
 * @param {Object} briefData The brief data.
 * @return {Object} The generated brief.
 */
function generateBrief(briefData) {
  // Make API request
  var response = UrlFetchApp.fetch(API_URL + '/api/briefs', {
    'method': 'post',
    'contentType': 'application/json',
    'payload': JSON.stringify({
      'document_id': briefData.documentId,
      'title': briefData.title || undefined,
      'focus_areas': briefData.focusAreas || undefined
    }),
    'headers': {
      'X-API-Key': API_KEY
    },
    'muteHttpExceptions': true
  });
  
  // Check response
  if (response.getResponseCode() !== 200) {
    throw new Error('API request failed: ' + response.getContentText());
  }
  
  // Parse response
  var result = JSON.parse(response.getContentText());
  
  // Fetch brief details
  return fetchBrief(result.id);
}

/**
 * Fetches a brief.
 * @param {string} briefId The brief ID.
 * @return {Object} The brief details.
 */
function fetchBrief(briefId) {
  // Make API request
  var response = UrlFetchApp.fetch(API_URL + '/api/briefs/' + briefId, {
    'method': 'get',
    'headers': {
      'X-API-Key': API_KEY
    },
    'muteHttpExceptions': true
  });
  
  // Check response
  if (response.getResponseCode() !== 200) {
    throw new Error('API request failed: ' + response.getContentText());
  }
  
  // Parse response
  return JSON.parse(response.getContentText());
}

/**
 * Validates statutes in a document.
 * @param {string} documentId The document ID.
 * @return {Object} The validation results.
 */
function validateStatutes(documentId) {
  // Make API request
  var response = UrlFetchApp.fetch(API_URL + '/api/statutes?document_id=' + documentId, {
    'method': 'get',
    'headers': {
      'X-API-Key': API_KEY
    },
    'muteHttpExceptions': true
  });
  
  // Check response
  if (response.getResponseCode() !== 200) {
    throw new Error('API request failed: ' + response.getContentText());
  }
  
  // Parse response
  var result = JSON.parse(response.getContentText());
  
  // Process statutes
  var statutes = result.items || [];
  var outdatedCount = 0;
  
  statutes.forEach(function(statute) {
    if (!statute.is_current) {
      outdatedCount++;
    }
  });
  
  return {
    'statutes': statutes,
    'outdatedCount': outdatedCount,
    'totalCount': statutes.length,
    'documentId': documentId
  };
}

/**
 * Inserts the brief into the document.
 * @param {Object} brief The brief to insert.
 */
function insertBrief(brief) {
  var document = DocumentApp.getActiveDocument();
  var body = document.getBody();
  
  // Insert brief at cursor position
  var cursor = document.getCursor();
  
  if (cursor) {
    // Insert at cursor position
    var element = cursor.getElement();
    var parent = element.getParent();
    
    // Find the paragraph containing the cursor
    while (parent && parent.getType() !== DocumentApp.ElementType.PARAGRAPH) {
      element = parent;
      parent = element.getParent();
    }
    
    if (parent) {
      var index = parent.getChildIndex(element);
      
      // Insert brief content
      insertBriefContent(body, index, brief);
    } else {
      // Fallback to appending at the end
      insertBriefContent(body, body.getNumChildren(), brief);
    }
  } else {
    // No cursor, append to the end
    insertBriefContent(body, body.getNumChildren(), brief);
  }
}

/**
 * Inserts the brief content.
 * @param {Body} body The document body.
 * @param {number} index The insertion index.
 * @param {Object} brief The brief to insert.
 */
function insertBriefContent(body, index, brief) {
  // Insert title
  body.insertParagraph(index++, brief.title)
    .setHeading(DocumentApp.ParagraphHeading.HEADING1);
  
  // Insert content
  var content = brief.content;
  
  // Split into paragraphs
  var paragraphs = content.split('\n');
  
  // Add each paragraph
  paragraphs.forEach(function(paragraph) {
    if (paragraph.trim()) {
      body.insertParagraph(index++, paragraph);
    }
  });
}