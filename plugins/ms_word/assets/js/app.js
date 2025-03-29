/**
 * Legal Document Analyzer for Microsoft Word
 * JavaScript client for the Word plugin
 */

// Global state
let appState = {
    apiUrl: null,
    apiKey: null,
    documentId: null,
    documentContent: null,
    statutes: []
};

// Initialize the application when the Office host is ready
Office.onReady(function(info) {
    // Only run if in Word context
    if (info.host === Office.HostType.Word) {
        // Initialize UI event handlers
        initializeUI();
        
        // Load saved settings
        loadSettings();
        
        console.log("Legal Document Analyzer add-in initialized in Word");
    }
});

/**
 * Initialize UI event handlers
 */
function initializeUI() {
    // Settings management
    $('#saveSettings').on('click', saveSettingsToLocalStorage);
    
    // Document analysis
    $('#analyzeDocument').on('click', handleAnalyzeDocument);
    $('#generateBrief').on('click', showBriefOptions);
    $('#validateStatutes').on('click', handleValidateStatutes);
    
    // Brief generation
    $('#generateBriefSubmit').on('click', handleGenerateBrief);
    $('#cancelBriefGeneration').on('click', hideBriefOptions);
    
    // Statute validation
    $('#insertStatuteResults').on('click', handleInsertStatuteResults);
}

/**
 * Load settings from localStorage
 */
function loadSettings() {
    try {
        const settings = JSON.parse(localStorage.getItem('legalAnalyzerSettings') || '{}');
        
        if (settings.apiUrl) {
            $('#apiUrl').val(settings.apiUrl);
            appState.apiUrl = settings.apiUrl;
        }
        
        if (settings.apiKey) {
            $('#apiKey').val(settings.apiKey);
            appState.apiKey = settings.apiKey;
        }
        
        updateStatusMessage("Settings loaded successfully.");
    } catch (error) {
        console.error("Error loading settings:", error);
        updateStatusMessage("Failed to load settings.", "error");
    }
}

/**
 * Save settings to localStorage
 */
function saveSettingsToLocalStorage() {
    try {
        const apiUrl = $('#apiUrl').val().trim();
        const apiKey = $('#apiKey').val().trim();
        
        if (!apiUrl) {
            updateStatusMessage("API URL is required.", "error");
            return;
        }
        
        if (!apiKey) {
            updateStatusMessage("API Key is required.", "error");
            return;
        }
        
        // Save to state and localStorage
        appState.apiUrl = apiUrl;
        appState.apiKey = apiKey;
        
        localStorage.setItem('legalAnalyzerSettings', JSON.stringify({
            apiUrl,
            apiKey
        }));
        
        updateStatusMessage("Settings saved successfully.");
    } catch (error) {
        console.error("Error saving settings:", error);
        updateStatusMessage("Failed to save settings.", "error");
    }
}

/**
 * Handle Analyze Document button click
 */
function handleAnalyzeDocument() {
    // Check if settings are configured
    if (!isConfigured()) {
        return;
    }
    
    showLoading("Retrieving document content...");
    
    // Get the document content
    Office.context.document.getFileAsync(Office.FileType.Text, { sliceSize: 65536 }, function(result) {
        if (result.status === Office.AsyncResultStatus.Succeeded) {
            // Get the file handle
            const fileHandle = result.value;
            
            // Read the file content
            fileHandle.getSliceAsync(0, function(sliceResult) {
                if (sliceResult.status === Office.AsyncResultStatus.Succeeded) {
                    // Store the document content
                    appState.documentContent = sliceResult.value.data;
                    
                    // Close the file handle
                    fileHandle.closeAsync(function() {
                        // Upload the document for analysis
                        uploadDocument(appState.documentContent);
                    });
                } else {
                    hideLoading();
                    console.error("Error getting slice:", sliceResult.error);
                    updateStatusMessage("Error retrieving document content.", "error");
                }
            });
        } else {
            hideLoading();
            console.error("Error getting file:", result.error);
            updateStatusMessage("Error retrieving document file.", "error");
        }
    });
}

/**
 * Upload document to the Legal Document Analyzer API
 */
function uploadDocument(content) {
    updateLoadingMessage("Uploading document for analysis...");
    
    // Create a FormData object with the document content
    const formData = new FormData();
    const blob = new Blob([content], { type: 'text/plain' });
    formData.append('file', blob, 'document.txt');
    
    // Make API request
    $.ajax({
        url: `${appState.apiUrl}/api/documents`,
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        headers: {
            'X-API-Key': appState.apiKey
        },
        success: function(response) {
            hideLoading();
            
            if (response && response.id) {
                // Store the document ID
                appState.documentId = response.id;
                
                // Enable additional actions
                $('#generateBrief').prop('disabled', false);
                $('#validateStatutes').prop('disabled', false);
                
                // Show analysis results
                showAnalysisResults(response);
                
                updateStatusMessage("Document uploaded and analyzed successfully.");
            } else {
                updateStatusMessage("Invalid response from server.", "error");
            }
        },
        error: function(xhr, status, error) {
            hideLoading();
            console.error("Error uploading document:", error);
            updateStatusMessage(`Error uploading document: ${getErrorMessage(xhr)}`, "error");
        }
    });
}

/**
 * Display analysis results
 */
function showAnalysisResults(response) {
    const resultsHtml = `
        <div class="alert alert-success mb-3">
            <i class="fas fa-check-circle me-2"></i>
            Document analyzed successfully!
        </div>
        <div class="mb-3">
            <strong>Document ID:</strong> ${response.id}<br>
            <strong>Statutes Found:</strong> ${response.statutes_found || 0}
        </div>
        <div class="alert alert-info">
            <i class="fas fa-info-circle me-2"></i>
            Use the buttons above to generate a legal brief or validate statute references.
        </div>
    `;
    
    $('#resultsContent').html(resultsHtml);
    $('#analysisResults').removeClass('d-none');
}

/**
 * Show brief generation options
 */
function showBriefOptions() {
    // Hide analysis results
    $('#analysisResults').addClass('d-none');
    
    // Show brief options
    $('#briefOptions').removeClass('d-none');
    
    // Clear form
    $('#briefTitle').val('');
    $('#focusAreas').val('');
}

/**
 * Hide brief generation options
 */
function hideBriefOptions() {
    // Show analysis results
    $('#analysisResults').removeClass('d-none');
    
    // Hide brief options
    $('#briefOptions').addClass('d-none');
}

/**
 * Handle Generate Brief button click
 */
function handleGenerateBrief() {
    // Check if document ID is available
    if (!appState.documentId) {
        updateStatusMessage("Please analyze a document first.", "error");
        return;
    }
    
    // Get form values
    const title = $('#briefTitle').val().trim();
    const focusAreasText = $('#focusAreas').val().trim();
    const focusAreas = focusAreasText ? focusAreasText.split('\n').filter(Boolean) : [];
    
    showLoading("Generating legal brief...");
    
    // Make API request
    $.ajax({
        url: `${appState.apiUrl}/api/briefs`,
        type: 'POST',
        data: JSON.stringify({
            document_id: appState.documentId,
            title: title || undefined,
            focus_areas: focusAreas.length > 0 ? focusAreas : undefined
        }),
        contentType: 'application/json',
        headers: {
            'X-API-Key': appState.apiKey
        },
        success: function(response) {
            hideLoading();
            
            if (response && response.id) {
                // Hide brief options
                hideBriefOptions();
                
                // Fetch brief details
                fetchBrief(response.id);
                
                updateStatusMessage("Brief generated successfully.");
            } else {
                updateStatusMessage("Invalid response from server.", "error");
            }
        },
        error: function(xhr, status, error) {
            hideLoading();
            console.error("Error generating brief:", error);
            updateStatusMessage(`Error generating brief: ${getErrorMessage(xhr)}`, "error");
        }
    });
}

/**
 * Fetch brief details
 */
function fetchBrief(briefId) {
    showLoading("Fetching brief details...");
    
    // Make API request
    $.ajax({
        url: `${appState.apiUrl}/api/briefs/${briefId}`,
        type: 'GET',
        headers: {
            'X-API-Key': appState.apiKey
        },
        success: function(response) {
            hideLoading();
            
            if (response && response.content) {
                // Insert brief into document
                insertBriefIntoDocument(response);
            } else {
                updateStatusMessage("Invalid response from server.", "error");
            }
        },
        error: function(xhr, status, error) {
            hideLoading();
            console.error("Error fetching brief:", error);
            updateStatusMessage(`Error fetching brief: ${getErrorMessage(xhr)}`, "error");
        }
    });
}

/**
 * Insert brief content into Word document
 */
function insertBriefIntoDocument(brief) {
    showLoading("Inserting brief into document...");
    
    // Format brief content for Word
    const content = formatBriefContent(brief);
    
    // Insert into document
    Office.context.document.setSelectedDataAsync(content, { coercionType: Office.CoercionType.Html }, function(result) {
        hideLoading();
        
        if (result.status === Office.AsyncResultStatus.Succeeded) {
            updateStatusMessage("Brief inserted into document successfully.");
        } else {
            console.error("Error inserting brief:", result.error);
            updateStatusMessage("Error inserting brief into document.", "error");
        }
    });
}

/**
 * Format brief content as HTML for Word
 */
function formatBriefContent(brief) {
    // Convert Markdown-ish content to HTML
    let content = brief.content;
    
    // Replace headings
    content = content.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    content = content.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    content = content.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    
    // Replace lists
    content = content.replace(/^- (.+)$/gm, '<li>$1</li>');
    
    // Replace paragraphs
    content = content.replace(/^([^<\s].+)$/gm, '<p>$1</p>');
    
    // Wrap the whole thing in a div
    return `
        <div style="font-family: 'Calibri', sans-serif;">
            <h1>${brief.title}</h1>
            ${content}
        </div>
    `;
}

/**
 * Handle Validate Statutes button click
 */
function handleValidateStatutes() {
    // Check if document ID is available
    if (!appState.documentId) {
        updateStatusMessage("Please analyze a document first.", "error");
        return;
    }
    
    showLoading("Validating statute references...");
    
    // Make API request
    $.ajax({
        url: `${appState.apiUrl}/api/statutes`,
        type: 'GET',
        data: {
            document_id: appState.documentId
        },
        headers: {
            'X-API-Key': appState.apiKey
        },
        success: function(response) {
            hideLoading();
            
            if (response && response.items) {
                // Store statutes
                appState.statutes = response.items;
                
                // Display statute validation results
                showStatuteValidationResults(response.items);
                
                updateStatusMessage("Statute references validated successfully.");
            } else {
                updateStatusMessage("Invalid response from server.", "error");
            }
        },
        error: function(xhr, status, error) {
            hideLoading();
            console.error("Error validating statutes:", error);
            updateStatusMessage(`Error validating statutes: ${getErrorMessage(xhr)}`, "error");
        }
    });
}

/**
 * Display statute validation results
 */
function showStatuteValidationResults(statutes) {
    if (statutes.length === 0) {
        $('#statuteResults').html(`
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                No statute references found in this document.
            </div>
        `);
    } else {
        let resultsHtml = '';
        let outdatedCount = 0;
        
        // Process each statute
        statutes.forEach(function(statute) {
            const isCurrent = statute.is_current;
            const statusClass = isCurrent ? 'statute-current' : 'statute-outdated';
            const statusBadgeClass = isCurrent ? 'status-current' : 'status-outdated';
            const statusText = isCurrent ? 'Current' : 'Outdated';
            
            if (!isCurrent) {
                outdatedCount++;
            }
            
            resultsHtml += `
                <div class="statute-item ${statusClass}">
                    <div class="statute-reference">${statute.reference}</div>
                    <div class="statute-status ${statusBadgeClass}">${statusText}</div>
                    <div class="statute-details">
                        <small>Verified: ${new Date(statute.verified_at).toLocaleString()}</small>
                        <br>
                        <small>Source: ${statute.source_database || 'Unknown'}</small>
                    </div>
                </div>
            `;
        });
        
        // Add summary
        resultsHtml = `
            <div class="alert ${outdatedCount > 0 ? 'alert-warning' : 'alert-success'} mb-3">
                <i class="fas ${outdatedCount > 0 ? 'fa-exclamation-triangle' : 'fa-check-circle'} me-2"></i>
                Found ${statutes.length} statute references, ${outdatedCount} outdated.
            </div>
            ${resultsHtml}
        `;
        
        $('#statuteResults').html(resultsHtml);
    }
    
    // Show statute validation results
    $('#analysisResults').addClass('d-none');
    $('#statuteValidation').removeClass('d-none');
}

/**
 * Handle Insert Statute Results button click
 */
function handleInsertStatuteResults() {
    // Check if statutes are available
    if (!appState.statutes || appState.statutes.length === 0) {
        updateStatusMessage("No statute validation results to insert.", "error");
        return;
    }
    
    showLoading("Inserting statute validation results...");
    
    // Format statute validation results for Word
    const content = formatStatuteResults(appState.statutes);
    
    // Insert into document
    Office.context.document.setSelectedDataAsync(content, { coercionType: Office.CoercionType.Html }, function(result) {
        hideLoading();
        
        if (result.status === Office.AsyncResultStatus.Succeeded) {
            updateStatusMessage("Statute validation results inserted into document successfully.");
        } else {
            console.error("Error inserting statute results:", result.error);
            updateStatusMessage("Error inserting statute validation results into document.", "error");
        }
    });
}

/**
 * Format statute validation results as HTML for Word
 */
function formatStatuteResults(statutes) {
    let outdatedCount = 0;
    let statutesHtml = '';
    
    // Process each statute
    statutes.forEach(function(statute) {
        const isCurrent = statute.is_current;
        const color = isCurrent ? '#198754' : '#dc3545';
        const statusText = isCurrent ? 'Current' : 'Outdated';
        
        if (!isCurrent) {
            outdatedCount++;
        }
        
        statutesHtml += `
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">${statute.reference}</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: ${color};">${statusText}</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">${statute.source_database || 'Unknown'}</td>
                <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">${new Date(statute.verified_at).toLocaleString()}</td>
            </tr>
        `;
    });
    
    // Create the complete HTML
    return `
        <div style="font-family: 'Calibri', sans-serif; margin-bottom: 20px;">
            <h2>Statute Validation Results</h2>
            <p><strong>Total References:</strong> ${statutes.length}</p>
            <p><strong>Outdated References:</strong> ${outdatedCount}</p>
            
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <thead>
                    <tr style="background-color: #f8f9fa;">
                        <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">Reference</th>
                        <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">Status</th>
                        <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">Source</th>
                        <th style="padding: 8px; text-align: left; border-bottom: 2px solid #dee2e6;">Verified</th>
                    </tr>
                </thead>
                <tbody>
                    ${statutesHtml}
                </tbody>
            </table>
            
            <p style="margin-top: 15px; font-size: 11px; color: #6c757d;">
                Report generated by Legal Document Analyzer on ${new Date().toLocaleString()}
            </p>
        </div>
    `;
}

/**
 * Update status message
 */
function updateStatusMessage(message, type = 'info') {
    const statusElement = $('#status-message');
    
    statusElement.removeClass('alert-info alert-success alert-warning alert-danger');
    
    let alertClass = 'alert-info';
    let icon = 'fa-info-circle';
    
    switch(type) {
        case 'success':
            alertClass = 'alert-success';
            icon = 'fa-check-circle';
            break;
        case 'warning':
            alertClass = 'alert-warning';
            icon = 'fa-exclamation-triangle';
            break;
        case 'error':
            alertClass = 'alert-danger';
            icon = 'fa-exclamation-circle';
            break;
    }
    
    statusElement.addClass(alertClass);
    statusElement.html(`<i class="fas ${icon} me-2"></i>${message}`);
}

/**
 * Show loading overlay
 */
function showLoading(message = 'Processing...') {
    $('.loading-message').text(message);
    $('#loadingOverlay').removeClass('d-none');
}

/**
 * Update loading message
 */
function updateLoadingMessage(message) {
    $('.loading-message').text(message);
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    $('#loadingOverlay').addClass('d-none');
}

/**
 * Check if the plugin is configured
 */
function isConfigured() {
    if (!appState.apiUrl || !appState.apiKey) {
        updateStatusMessage("Please configure API URL and API Key first.", "error");
        return false;
    }
    
    return true;
}

/**
 * Get error message from AJAX response
 */
function getErrorMessage(xhr) {
    if (xhr.responseJSON && xhr.responseJSON.error) {
        return xhr.responseJSON.error;
    } else if (xhr.responseJSON && xhr.responseJSON.message) {
        return xhr.responseJSON.message;
    } else if (xhr.responseText) {
        try {
            const response = JSON.parse(xhr.responseText);
            return response.error || response.message || xhr.statusText;
        } catch(e) {
            return xhr.responseText;
        }
    }
    
    return xhr.statusText || "Unknown error";
}