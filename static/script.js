// GSAP Initial Entry
gsap.from(".app-shell", { opacity: 0, y: 50, duration: 1, ease: "expo.out" });

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('fileInput');
const downloadBtn = document.getElementById('downloadBtn');
const loader = document.getElementById('loader');

let stage, layer, sessionId, edits = [];

// --- FIXED DRAG AND DROP ---
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
    }, false);
});

dropZone.addEventListener('dragover', () => dropZone.classList.add('dragover'));
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));

dropZone.addEventListener('drop', (e) => {
    dropZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
});

// --- FIXED CLICK UPLOAD ---
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleUpload(e.target.files[0]);
});

// --- UPLOAD LOGIC ---
async function handleUpload(file) {
    loader.style.display = 'flex';
    gsap.to("#upload-view", { opacity: 0, scale: 0.9, duration: 0.5 });

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch('/upload', { method: 'POST', body: formData });
        if (!res.ok) throw new Error("Upload Failed");
        const data = await res.json();
        
        sessionId = data.session_id;
        initEditor(data.image_url, data.words);

        document.getElementById('upload-view').style.display = 'none';
        document.getElementById('editor-view').style.display = 'block';
        gsap.to("#editor-view", { opacity: 1, duration: 1 });

    } catch (err) {
        alert("Server Error: Check if Render backend is awake.");
        location.reload();
    } finally {
        loader.style.display = 'none';
    }
}

// --- CANVAS LOGIC ---
function initEditor(url, words) {
    const img = new Image();
    img.onload = () => {
        stage = new Konva.Stage({
            container: 'konva-holder',
            width: img.naturalWidth,
            height: img.naturalHeight
        });
        layer = new Konva.Layer();
        stage.add(layer);

        layer.add(new Konva.Image({ image: img }));

        words.forEach(word => {
            const group = new Konva.Group({ x: word.x, y: word.y });
            const rect = new Konva.Rect({
                width: word.w, height: word.h,
                fill: 'rgba(99, 102, 241, 0.1)'
            });

            group.add(rect);
            layer.add(group);

            group.on('click', () => {
                const newText = prompt("Replace Text:", word.text);
                if (newText !== null) {
                    // Visual "Healing"
                    rect.fill('white');
                    group.add(new Konva.Text({
                        text: newText,
                        fontSize: word.h * 0.85,
                        fill: 'black',
                        fontFamily: 'Arial'
                    }));
                    layer.draw();
                    edits.push({ ...word, new_text: newText });
                    downloadBtn.disabled = false;
                    gsap.from(downloadBtn, { scale: 1.2, duration: 0.3 });
                }
            });
        });
    };
    img.src = url;
}

// --- EXPORT ---
downloadBtn.onclick = async () => {
    downloadBtn.innerText = "...";
    const fd = new FormData();
    fd.append('session_id', sessionId);
    fd.append('edits', JSON.stringify(edits));

    const res = await fetch('/edit', { method: 'POST', body: fd });
    const data = await res.json();
    window.location.href = data.download_url;
    downloadBtn.innerText = "DONE";
};
