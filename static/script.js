gsap.from(".glass-container", { opacity: 0, y: 40, duration: 1.2, ease: "power4.out" });
gsap.to("#blob1", { x: 150, y: 100, duration: 12, repeat: -1, yoyo: true, ease: "sine.inOut" });
gsap.to("#blob2", { x: -120, y: -80, duration: 15, repeat: -1, yoyo: true, ease: "sine.inOut" });

document.addEventListener('DOMContentLoaded', () => M.AutoInit());

// Fix drag and drop globally
document.addEventListener('dragover', e => e.preventDefault());
document.addEventListener('drop', e => e.preventDefault());

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const downloadBtn = document.getElementById('downloadBtn');
const modal = document.getElementById('editModal');
const newTextInput = document.getElementById('newText');
const fontSizeSlider = document.getElementById('fontSizeSlider');
const fontSizeValue = document.getElementById('fontSizeValue');
const textColor = document.getElementById('textColor');
const saveEditBtn = document.getElementById('saveEditBtn');

let stage, layer, sessionId, edits = [];
let currentWord = null;
let currentGroup = null;

['dragenter', 'dragover', 'dragleave', 'drop'].forEach(event => {
    dropZone.addEventListener(event, e => { e.preventDefault(); e.stopPropagation(); });
});

dropZone.addEventListener('dragenter', () => dropZone.classList.add('dragover'));
dropZone.addEventListener('dragover', () => dropZone.classList.add('dragover'));
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
});

dropZone.onclick = () => fileInput.click();
browseBtn.onclick = () => fileInput.click();
fileInput.onchange = e => { if (e.target.files[0]) handleFile(e.target.files[0]); };

async function handleFile(file) {
    dropZone.innerHTML = "<h5>Processing document...</h5><p>Please wait</p>";
    const form = new FormData();
    form.append("file", file);

    const res = await fetch('/upload', { method: 'POST', body: form });
    const data = await res.json();

    sessionId = data.session_id;
    initEditor(data.image_url, data.words);

    gsap.to("#upload-view", { opacity: 0, duration: 0.5, onComplete: () => {
        document.getElementById('upload-view').style.display = 'none';
        document.getElementById('editor-view').style.display = 'block';
        gsap.from("#editor-view", { opacity: 0, y: 30, duration: 0.7 });
    }});
}

function initEditor(imageUrl, words) {
    const img = new Image();
    img.onload = () => {
        stage = new Konva.Stage({
            container: 'konva-holder',
            width: img.naturalWidth,
            height: img.naturalHeight
        });
        layer = new Konva.Layer();
        stage.add(layer);

        const bg = new Konva.Image({ image: img });
        layer.add(bg);

        words.forEach(word => {
            const group = new Konva.Group({ x: word.x, y: word.y });
            const rect = new Konva.Rect({
                width: word.w,
                height: word.h,
                fill: 'rgba(99,102,241,0.08)'
            });
            group.add(rect);
            layer.add(group);

            group.on('mouseenter', () => {
                rect.fill('rgba(99,102,241,0.25)');
                layer.draw();
                document.body.style.cursor = 'pointer';
            });
            group.on('mouseleave', () => {
                rect.fill('rgba(99,102,241,0.08)');
                layer.draw();
                document.body.style.cursor = 'default';
            });

            group.on('click', () => {
                currentGroup = group;
                currentWord = word;
                newTextInput.value = word.text || '';
                fontSizeSlider.value = Math.round(word.h * 0.8);
                fontSizeValue.textContent = fontSizeSlider.value;
                textColor.value = '#000000';
                M.updateTextFields();
                M.Modal.getInstance(modal).open();
            });
        });

        layer.draw();
    };
    img.src = imageUrl;
}

fontSizeSlider.addEventListener('input', () => {
    fontSizeValue.textContent = fontSizeSlider.value;
});

saveEditBtn.onclick = () => {
    if (!currentWord || !currentGroup) return;

    const newText = newTextInput.value || currentWord.text;
    const fontSize = parseInt(fontSizeSlider.value);
    const color = textColor.value;

    const edited = {
        ...currentWord,
        new_text: newText,
        font_size: fontSize,
        color: color
    };

    edits = edits.filter(e => !(e.x === currentWord.x && e.y === currentWord.y));
    edits.push(edited);

    // Update canvas preview
    const rect = currentGroup.getChildren()[0];
    rect.fill('white');

    // Remove old text if exists
    if (currentGroup.getChildren().length > 1) {
        currentGroup.getChildren()[1].destroy();
    }

    const konvaText = new Konva.Text({
        text: newText,
        fontSize: fontSize,
        fill: color,
        width: currentWord.w,
        height: currentWord.h,
        align: 'center',
        verticalAlign: 'middle'
    });
    currentGroup.add(konvaText);
    layer.draw();

    downloadBtn.classList.add('active');
    M.Modal.getInstance(modal).close();
};

downloadBtn.onclick = async () => {
    if (!downloadBtn.classList.contains('active')) return;

    downloadBtn.innerHTML = "⏳";
    const form = new FormData();
    form.append('session_id', sessionId);
    form.append('edits', JSON.stringify(edits));

    const res = await fetch('/edit', { method: 'POST', body: form });
    const data = await res.json();

    window.location.href = data.download_url;
    downloadBtn.innerHTML = "✓";
};
