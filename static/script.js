// State Management
const State = {
  sessionId: null,
  edits: [],
  stage: null,
  layer: null,
};

const UI = {
  dropZone: document.getElementById("drop-zone"),
  fileInput: document.getElementById("fileInput"),
  uploadView: document.getElementById("upload-section"),
  editorView: document.getElementById("editor-section"),
  downloadBtn: document.getElementById("downloadBtn"),
  loader: document.getElementById("loader"),
};

// --- Initialization ---
function init() {
  setupDragAndDrop();
}

// --- Connection: Drag & Drop ---
function setupDragAndDrop() {
  ["dragenter", "dragover"].forEach((n) => {
    UI.dropZone.addEventListener(n, () =>
      UI.dropZone.classList.add("dragover")
    );
  });
  ["dragleave", "drop"].forEach((n) => {
    UI.dropZone.addEventListener(n, () =>
      UI.dropZone.classList.remove("dragover")
    );
  });

  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length) handleFileUpload(e.dataTransfer.files[0]);
  });

  UI.dropZone.onclick = () => UI.fileInput.click();
  UI.fileInput.onchange = (e) => handleFileUpload(e.target.files[0]);
}

// --- Connection: API Upload ---
async function handleFileUpload(file) {
  if (!file) return;
  UI.loader.style.display = "flex";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("/upload", { method: "POST", body: formData });
    const data = await response.json();

    State.sessionId = data.session_id;
    setupCanvas(data.image_url, data.words);

    UI.uploadView.style.display = "none";
    UI.editorView.style.display = "block";
  } catch (err) {
    alert("Server connection failed. Ensure Docker/Uvicorn is running.");
  } finally {
    UI.loader.style.display = "none";
  }
}

// --- Connection: Canvas Editor ---
function setupCanvas(url, words) {
  const img = new Image();
  img.crossOrigin = "Anonymous";
  img.onload = () => {
    State.stage = new Konva.Stage({
      container: "konva-holder",
      width: img.naturalWidth,
      height: img.naturalHeight,
    });

    State.layer = new Konva.Layer();
    State.stage.add(State.layer);

    // Background
    const kImg = new Konva.Image({
      image: img,
      width: img.naturalWidth,
      height: img.naturalHeight,
    });
    State.layer.add(kImg);

    // OCR Bounding Boxes
    words.forEach((word) => {
      const group = new Konva.Group({ x: word.x, y: word.y });
      const rect = new Konva.Rect({
        width: word.w,
        height: word.h,
        fill: "rgba(79, 70, 229, 0.08)",
        strokeWidth: 1,
      });

      group.add(rect);
      State.layer.add(group);

      group.on("mouseenter", () => {
        rect.stroke("#4f46e5");
        document.body.style.cursor = "text";
        State.layer.draw();
      });
      group.on("mouseleave", () => {
        rect.stroke("transparent");
        document.body.style.cursor = "default";
        State.layer.draw();
      });

      group.on("click", () => {
        const updatedText = prompt("Edit text value:", word.text);
        if (updatedText !== null && updatedText !== word.text) {
          // Update UI state
          rect.fill("white");
          const label = new Konva.Text({
            text: updatedText,
            fontSize: word.h * 0.9,
            fill: "#000",
            width: word.w,
            padding: 1,
          });
          group.add(label);
          State.layer.draw();

          // Track changes for export
          State.edits.push({
            x: word.x,
            y: word.y,
            w: word.w,
            h: word.h,
            new_text: updatedText,
          });
          UI.downloadBtn.disabled = false;
        }
      });
    });
  };
  img.src = url;
}

// --- Connection: Final Export ---
UI.downloadBtn.onclick = async () => {
  UI.downloadBtn.innerText = "Processing...";
  UI.downloadBtn.disabled = true;

  const fd = new FormData();
  fd.append("session_id", State.sessionId);
  fd.append("edits", JSON.stringify(State.edits));

  try {
    const res = await fetch("/edit", { method: "POST", body: fd });
    const data = await res.json();

    // Final Download Link
    const a = document.createElement("a");
    a.href = data.download_url;
    a.download = "Edited_Scan.pdf";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch (err) {
    alert("Export failed.");
  } finally {
    UI.downloadBtn.innerText = "Export PDF";
    UI.downloadBtn.disabled = false;
  }
};

init();
