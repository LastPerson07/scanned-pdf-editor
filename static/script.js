// GSAP Intro
gsap.from(".glass-shell", { opacity: 0, y: 30, duration: 1, ease: "power4.out" });
gsap.to(".liquid-blob", { x: 100, y: 50, duration: 8, repeat: -1, yoyo: true, ease: "sine.inOut" });

const dz = document.getElementById('drop-zone');
const fi = document.getElementById('fileInput');
const dl = document.getElementById('downloadBtn');

let stage, layer, sid, edits = [];

// --- DRAG AND DROP FIX ---
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(e => {
    dz.addEventListener(e, (evt) => {
        evt.preventDefault();
        evt.stopPropagation();
    });
});

dz.addEventListener('dragover', () => dz.classList.add('dragover'));
dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));

dz.addEventListener('drop', (e) => {
    dz.classList.remove('dragover');
    if (e.dataTransfer.files[0]) handleUpload(e.dataTransfer.files[0]);
});

dz.onclick = () => fi.click();
fi.onchange = (e) => { if(e.target.files[0]) handleUpload(e.target.files[0]); };

async function handleUpload(file) {
    dz.innerHTML = "<h1>Processing...</h1>";
    const fd = new FormData();
    fd.append("file", file);

    const res = await fetch('/upload', { method: 'POST', body: fd });
    const data = await res.json();
    
    sid = data.session_id;
    initEditor(data.image_url, data.words);

    gsap.to("#upload-view", { opacity: 0, display: "none", duration: 0.5, onComplete: () => {
        document.getElementById('editor-view').style.display = "block";
        gsap.from("#editor-view", { opacity: 0, y: 20, duration: 0.5 });
    }});
}

function initEditor(url, words) {
    const img = new Image();
    img.onload = () => {
        stage = new Konva.Stage({ container: 'konva-holder', width: img.naturalWidth, height: img.naturalHeight });
        layer = new Konva.Layer();
        stage.add(layer);
        layer.add(new Konva.Image({ image: img }));

        words.forEach(w => {
            const group = new Konva.Group({ x: w.x, y: w.y });
            const r = new Konva.Rect({ width: w.w, height: w.h, fill: 'rgba(99,102,241,0.05)' });
            group.add(r);
            layer.add(group);

            group.on('mouseenter', () => { r.fill('rgba(99,102,241,0.2)'); layer.draw(); document.body.style.cursor='pointer'; });
            group.on('mouseleave', () => { r.fill('rgba(99,102,241,0.05)'); layer.draw(); document.body.style.cursor='default'; });

            group.on('click', () => {
                const txt = prompt("Edit text:", w.text);
                if (txt) {
                    r.fill('white');
                    group.add(new Konva.Text({ text: txt, fontSize: w.h * 0.8, fill: 'black' }));
                    layer.draw();
                    edits.push({ ...w, new_text: txt });
                    dl.classList.add('active');
                }
            });
        });
    };
    img.src = url;
}

dl.onclick = async () => {
    dl.innerText = "⏳";
    const fd = new FormData();
    fd.append('session_id', sid);
    fd.append('edits', JSON.stringify(edits));
    const res = await fetch('/edit', { method: 'POST', body: fd });
    const data = await res.json();
    window.location.href = data.download_url;
    dl.innerText = "✓";
};
