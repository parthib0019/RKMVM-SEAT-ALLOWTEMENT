import re

with open("templates/index.html", "r") as f:
    html = f.read()

# 1. Add socket.io script
html = html.replace("</head>", "  <script src=\"https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js\"></script>\n</head>")

# 2. Add styles
styles = """
    .live-preview-container { width: 50%; border-radius: 15px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05); background: var(--card-background-light); display: none; flex-direction: column; height: 800px; padding: 20px;}
    .dark-mode .live-preview-container { box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3); }
    .card-container.started { width: 50%; max-width: none; margin: 0; }
    .main-container.started { flex-direction: row; gap: 20px; padding: 20px; }
"""
html = html.replace("/* NEW: Upgraded Summary Row Styles */", styles + "\n    /* NEW: Upgraded Summary Row Styles */")

# 3. Modify main container layout
old_main = """  <div class="main-container">
    <main class="card-container">
      <h2>Seat Allocation Input</h2>

      <div id="initialStep" class="form-section">
        <div class="num-inputs-container">
          <label for="numInputs">Number of Exam Papers</label>
          <div class="num-inputs-group">
            <input type="number" id="numInputs" min="1" value="1">
            <button class="action-button" onclick="startWizard()">Start</button>
          </div>
        </div>
      </div>

      <div id="wizardStep" style="display: none;">
        <div id="inputsContainer"></div>
        <div id="summaryContainer"></div>
      </div>
      
    </main>
  </div>"""

new_main = """  <div class="main-container" id="mainContainer">
    <main class="card-container" id="cardContainer">
      <h2>Seat Allocation Input</h2>

      <div id="initialStep" class="form-section">
        <div class="num-inputs-container">
          <div class="num-inputs-group">
            <button class="action-button" onclick="startWizard()">Start</button>
          </div>
        </div>
      </div>

      <div id="wizardStep" style="display: none;">
        <div id="inputsContainer"></div>
        <div id="summaryContainer"></div>
      </div>
    </main>

    <div id="livePreviewContainer" class="live-preview-container">
        <h2>Live Preview</h2>
        <iframe id="pdfPreviewIframe" src="" width="100%" height="100%" style="border: none;"></iframe>
    </div>
  </div>"""
html = html.replace(old_main, new_main)

# 4. Modify startWizard
old_start = """  function startWizard() {
    totalPapers = parseInt(document.getElementById("numInputs").value, 10);
    if (isNaN(totalPapers) || totalPapers < 1) {
      showCustomAlert("Please enter a valid number of papers.", 'error', 'Input Error');
      return;
    }
    currentPaperIndex = 0;
    allPapersData = [];
    summaryContainer.innerHTML = "";
    initialStep.style.display = "none";
    wizardStep.style.display = "block";
    showCurrentPaperForm();
  }"""

new_start = """  const socket = io({autoConnect: false});
  socket.on('allocation_result', function(data) {
      if(data.status === 'success') {
          document.getElementById('pdfPreviewIframe').src = data.pdf_url;
      } else {
          showCustomAlert(data.message || 'Error generating preview', 'error', 'Error');
      }
  });
  socket.on('finish_result', function(data) {
      if(data.status === 'success') {
          document.getElementById('pdfPreviewIframe').src = data.pdf_url;
          window.location.href = data.download_url;
      } else {
          showCustomAlert(data.message || 'Error finishing allocation', 'error', 'Error');
      }
  });

  function startWizard() {
    socket.connect();
    currentPaperIndex = 0;
    allPapersData = [];
    summaryContainer.innerHTML = "";
    initialStep.style.display = "none";
    wizardStep.style.display = "block";
    document.getElementById("mainContainer").classList.add("started");
    document.getElementById("cardContainer").classList.add("started");
    document.getElementById("livePreviewContainer").style.display = "flex";
    showCurrentPaperForm();
  }
  
  function finishAllocation() {
    socket.emit('finish_allocation');
  }"""
html = html.replace(old_start, new_start)

# 5. Modify showCurrentPaperForm buttons and header
old_form_1 = """const buttonText = isEditing ? "Save Changes" : (currentPaperIndex === totalPapers - 1) ? "Finish & Review" : "Save & Next Paper";
    const headerText = isEditing ? `Editing Paper ${i + 1} of ${total}` : `Paper ${allPapersData.length + 1} of ${total} Details`;"""

new_form_1 = """const buttonText = isEditing ? "Save Changes" : "Next";
    const headerText = isEditing ? `Editing Paper ${i + 1}` : `Paper ${allPapersData.length + 1} Details`;"""

html = html.replace(old_form_1, new_form_1)

old_form_2 = """<button class="action-button" style="margin-top: 25px;" onclick="handleNextClick()">${buttonText}</button>
      ${removedPapers.length > 0 ? '<button class="action-button" style="margin-top: 10px;" onclick="undoRemove()">Undo Remove</button>' : ''}"""

new_form_2 = """<div style="display: flex; gap: 10px; margin-top: 25px;">
        <button class="action-button" onclick="finishAllocation()">Done</button>
        <button class="action-button" onclick="handleNextClick()">${buttonText}</button>
      </div>
      ${removedPapers.length > 0 ? '<button class="action-button" style="margin-top: 10px;" onclick="undoRemove()">Undo Remove</button>' : ''}"""

html = html.replace(old_form_2, new_form_2)

# Also fix the early return in showCurrentPaperForm
old_early_return = """    if (currentPaperIndex >= totalPapers && !isEditing) {
      showFinalSummary();
      return;
    }"""
html = html.replace(old_early_return, "")

# 6. Modify handleNextClick to emit and NOT validate totally yet
# We need to find the end of handleNextClick where it pushes to allPapersData
old_handle_end = """    if (isEditing) {
      allPapersData[editingIndex] = paperData;
      reRenderSummaries();
      isEditing = false;
      editingIndex = -1;
    } else {
      allPapersData.push(paperData);
      renderSummaryRow(paperData, allPapersData.length - 1);
      currentPaperIndex++;
    }
    showCurrentPaperForm();"""

new_handle_end = """    if (isEditing) {
      allPapersData[editingIndex] = paperData;
      reRenderSummaries();
      isEditing = false;
      editingIndex = -1;
    } else {
      allPapersData.push(paperData);
      renderSummaryRow(paperData, allPapersData.length - 1);
      currentPaperIndex++;
    }
    
    // Emit to websocket for allocation and preview
    socket.emit('allocate_paper', paperData);
    
    showCurrentPaperForm();"""
html = html.replace(old_handle_end, new_handle_end)

with open("templates/index.html", "w") as f:
    f.write(html)
