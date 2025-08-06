High-level Refactor & Enhancement Blueprint  
================================================

0. Guiding Principles  
   • Keep the current business logic 100 % intact – only **move, wrap, and extend** it.  
   • Treat “GUI” and “Core” as two completely independent products that talk through a narrow, well-defined channel (signals / callbacks).  
   • Write new code so that it can be unit-tested without a display, a Pixiv account, or real images.  
   • Prefer libraries that are mature, actively maintained, cross-platform, and have a permissive licence (MIT/LGPL/BSD).

--------------------------------------------------------------------
1. Technology Choices & Why
--------------------------------------------------------------------
GUI Framework     : **PySide6** (Qt 6 – LGPL)  
  – Modern widgets, CSS-like styling, high-DPI-aware, threaded signals/slots.  
  – Ships with a full graphics scene framework (needed for the brush editor).  
  – LGPL ⇒ no licence worries; indistinguishable API from PyQt6.

Image/FX Library : **Pillow + OpenCV**  
  – Keep Pillow for all existing resizing / watermark code.  
  – Use OpenCV only inside the new mosaic/blur tools (fast convolution & pixelate).  
  – Both work with NumPy arrays, making brush operations trivial.

Metadata Library : **piexif** for JPEG / WEBP, **Pillow’s PngInfo** for PNG.  
  – Wrap both in a tiny helper so the rest of the code never worries about format differences.

Threading Model  : **Qt Worker-Thread pattern**  
  – Long tasks live in a QThread; they emit progress(int), log(str) & finished() signals.  
  – UI only connects & reacts ⇒ always responsive.

Packaging         : **PyInstaller –-onefile**.  
  – Re-use the existing executable workflow.

--------------------------------------------------------------------
2. Recommended Folder / Module Layout
--------------------------------------------------------------------
project/
│
├─ core/
│   ├─ processor.py            # ImageProcessorCore (pure logic)
│   ├─ metadata.py             # extract(), embed()
│   ├─ watermark.py            # apply_watermark()
│   ├─ auto_mosaic.py          # run_auto_mosaic()
│   └─ utils.py                # helpers, logging mix-in
│
├─ gui/
│   ├─ main_window.py          # MainWindow (PySide6)
│   ├─ manual_editor.py        # MosaicEditor
│   └─ widgets/…               # reusable Qt widgets (log box, folder selector…)
│
├─ assets/
│   └─ watermarks/*.png
│
├─ external/
│   ├─ pixivMosaic2.py
│   └─ PixivMosaicWorkflowAPI.json
│
├─ requirements.txt
└─ run.py                      # boots MainWindow

Unit tests live in tests/.

--------------------------------------------------------------------
3. Core Layer – Pseudocode Sketch
--------------------------------------------------------------------
class ImageProcessorCore:
    def __init__(self, cfg: CoreConfig, *, callbacks):  
        self.cfg = cfg                    # dataclass with all user settings  
        self.progress_cb = callbacks.progress   # callable(int 0-100)  
        self.log_cb      = callbacks.log        # callable(str, lvl)

    def extract_metadata(self, root: Path) -> None:
        folders = self._discover_packs(root)
        for n, folder in enumerate(folders, 1):
            self.log_cb(f'📦 {folder.name}: scanning …')
            pngs = folder.glob('*.png')
            meta = threaded_map(self._read_one_png, pngs)
            (Path(folder) / 'metadata.json').write_text(json.dumps(meta, …))
            self.progress_cb(int(n / len(folders) * 100))

    def process_images(self, root: Path) -> None:
        # mostly identical to today’s run_image_processing()
        # but without any GUI calls – only self.log_cb / self.progress_cb
        …

    def run_auto_mosaic(self, pack: Path) -> None:
        safe_dir = pack / 'pixiv_safe'
        safe_dir.mkdir(exist_ok=True)
        workflow = PROJECT_ROOT / 'external' / 'PixivMosaicWorkflowAPI.json'

        for n, src in enumerate((pack / 'original_images').glob('*.png'), 1):
            dst = safe_dir / src.name            # keep same file name
            cmd = ['python', 'pixivMosaic2.py', workflow, src, dst]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode:
                self.log_cb(f'❌ {src.name}: {result.stderr}', 'ERROR')
                continue
            # re-embed full metadata
            meta = self._load_meta(pack / 'metadata.json')[src.name]
            metadata.embed(dst, meta)            # uses helper module
            self.progress_cb(int(n / total * 100))

Utilities (metadata.py):

def extract_png(path):
    with Image.open(path) as im:
        text = im.text.get('Comment') or '{}'
    return json.loads(text)

def embed(path, meta: dict):
    if path.suffix.lower() == '.png':
        info = PngImagePlugin.PngInfo()
        info.add_text('Comment', json.dumps(meta, ensure_ascii=False))
        Image.open(path).save(path, pnginfo=info)
    else:                                  # webp / jpeg
        exif = piexif.dump({'0th': {piexif.ImageIFD.ImageDescription:
                                     json.dumps(meta).encode()}})
        Image.open(path).save(path, exif=exif)

--------------------------------------------------------------------
4. GUI Layer – Design Details
--------------------------------------------------------------------
MainWindow (PySide6.QMainWindow)  
  • QStackedWidget central area with two “pages”:  
    – SettingsPage: the current controls, now in Qt Designer layout.  
    – LogPage: progress bar + QTextEdit log.  
  • QAction toolbar or left-aligned QPushButton column for the four actions.  
  • Non-blocking behaviour: Every action spawns a **QThread worker** wrapping one core function.  
    Signals: progress(int), log(str, lvl), finished(success).

Manual Mosaic Editor (manual_editor.py)  
  • QSplitter: left pane – QListView thumbnails (QListWidget with icon mode).  
  • Right pane – QGraphicsView with a custom MosaicCanvas(QGraphicsPixmapItem).  
  • Brush Options Toolbar:  
     BrushSize(QSlider), EffectType(QComboBox), Strength(QSlider), Save(QPushButton).  
  • Painting Algorithm (simplified):  
    on mousePress → start new QPainterPath  
    on mouseMove  → add point, draw overlay stroke for live feedback  
    on mouseRelease:  
        – Convert path to a mask (white on black np.ndarray)  
        – If EffectType == Gaussian: blurred = cv2.GaussianBlur(region, (k,k), sigma)  
        – If Pixelate: resize-down then resize-up region  
        – Paste modified region back onto pixmap  
        – Clear overlay  
  • On Save → convert QPixmap to Pillow Image → metadata.embed() → overwrite file.

Progress / Log integration:  
  Workers emit log(str,lvl) → connected to QTextEdit.appendHtml() with colour per lvl.

--------------------------------------------------------------------
5. Typical Signal Flow (Extract Metadata Button)
--------------------------------------------------------------------
1 User clicks → MainWindow.start_extract()  
2 WorkerThread = Worker(core.extract_metadata, root_path)  
3 connect(worker.progress, ui.progressBar.setValue)  
  connect(worker.log,      ui.append_log)  
  connect(worker.finished, ui.on_action_done)  
4 WorkerThread.start()  
5 Core code runs, emits callbacks → worker emits signals → UI updates instantly.

--------------------------------------------------------------------
6. Potential Pitfalls & Mitigations
--------------------------------------------------------------------
PNG metadata size  : Comment chunk limited to < 64 kB.  
  Mitigation: warn the user when json.dumps(meta).encode() > 60 kB.

piexif & WEBP     : piexif cannot write EXIF into WebP on older Pillow versions.  
  Mitigation: require Pillow ≥ 10.0 (supports WebP EXIF).

External script timeouts: some images may lock up pixivMosaic2.py.  
  Mitigation: subprocess.run(cmd, timeout=120) + retry logic.

Thread-safety: Pillow is not 100 % thread-safe for writes on Windows.  
  Mitigation: keep ThreadPool max_workers = min(8, os.cpu_count()) and open images inside the worker function only.

High-DPI scaling issues: Qt 6 auto-scales, but watermark preview may appear blurry.  
  Mitigation: disable Qt::AA_EnableHighDpiScaling and handle scaling manually if needed.

--------------------------------------------------------------------
7. Requirements.txt (initial)
--------------------------------------------------------------------
PySide6>=6.5  
Pillow>=10.0  
opencv-python>=4.9  
piexif>=1.1  
numpy>=1.24

--------------------------------------------------------------------
8. Milestone Checklist
--------------------------------------------------------------------
Phase 1 – Core Refactor  
  [ ] processor.py passes original unit tests.  
  [ ] New metadata keys round-trip correctly.

Phase 2 – New GUI  
  [ ] Main window reproduces all old controls.  
  [ ] Log & progress verified with dummy worker.

Phase 3 – Auto Mosaic  
  [ ] Generates pixiv_safe/ with metadata.  
  [ ] Handles subprocess errors gracefully.

Phase 4 – Manual Editor  
  [ ] Brush applies blur & pixelate.  
  [ ] Saving preserves EXIF / PNG comment.  
  [ ] Undo (optional but desirable).

Phase 5 – QA & Packaging  
  [ ] Tests on Windows + macOS + Linux.  
  [ ] PyInstaller onefile build (< 100 MB).  
  [ ] README updated with screenshots & workflow.

This roadmap gives you the what, why, and how without locking you into a specific coding style.  You can now schedule the work, split tasks among team-mates, and start writing production code with clear boundaries and minimal risk.


--------

Second guide, enhanced:
Refactor & Enhancement Master-Plan  
(based on the senior developer’s blueprint, enriched with the best ideas from the junior and full-stack proposals)

────────────────────────────────────────
0. Guiding Principles
────────────────────────────────────────
• Business logic first – move, wrap, extend; never rewrite what already works.  
• Core and GUI are two standalone “products” wired only through a tiny signal/callback layer.  
• All long-running work is off the GUI thread; the UI must never freeze.  
• Every new unit can be tested head-less (CI friendly).  
• Favour battle-tested, LGPL / MIT libraries; keep optional/fast extras pluggable not mandatory.

────────────────────────────────────────
1. Technology & Library Choices
────────────────────────────────────────
GUI            : PySide6  (Qt6 – LGPL, designer, high-DPI, graphics-scene)  
Image / FX     : Pillow  (stable API)  + optional OpenCV  (fast kernels)  
Metadata       : piexif  (JPEG/WEBP)   + Pillow.PngInfo (“Comment” text chunk)  
Async / Threads: Qt Worker-thread pattern (signals / slots)  
Packaging      : PyInstaller  --onefile  
Optional UI    : If Qt is an installation blocker, plug-in CustomTkinter stub (junior’s insight) that calls the same core class. This keeps the door open for a light fallback.

────────────────────────────────────────
2. Recommended Repository Layout
────────────────────────────────────────
project/
│
├─ core/                       # NO GUI imports here
│   ├─ processor.py            # ImageProcessorCore  (all business rules)
│   ├─ metadata.py             # extract(), embed(), size guards
│   ├─ watermark.py            # apply_watermark()
│   ├─ auto_mosaic.py          # run_auto_mosaic()
│   └─ utils.py                # logging mix-in, path helpers
│
├─ gui/                        # Qt only
│   ├─ main_window.py          # MainWindow  (4-button workflow)
│   ├─ manual_editor.py        # MosaicEditor (brush canvas)
│   └─ widgets/…               # reusable Qt widgets (log box…)
│
├─ assets/
│   └─ watermarks/*.png
│
├─ external/
│   ├─ pixivMosaic2.py
│   └─ PixivMosaicWorkflowAPI.json
│
├─ tests/                      # pytest unit tests for core/*
├─ run.py                      # boots MainWindow
└─ requirements.txt

Tip (junior): when frozen with PyInstaller use  
`base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))`  
to resolve assets and external scripts.

────────────────────────────────────────
3. Core Layer – Design Detail
────────────────────────────────────────
3.1  Callbacks & Signals
    class CoreCallbacks(NamedTuple):
        progress: Callable[[int], None]    # 0-100
        log     : Callable[[str,str],None] # msg, level ("INFO","WARN","ERROR")
        status  : Callable[[str], None]

3.2  ImageProcessorCore  (simplified sketch)

class ImageProcessorCore:
    def __init__(self, cfg: CoreConfig, cb: CoreCallbacks):
        self.cfg, self.cb = cfg, cb

    # 1. Metadata Extraction -------------------------------------------------
    def extract_metadata(self, root: Path):
        packs = self._discover_packs(root)
        for n, pack in enumerate(packs, 1):
            pngs = list(pack.glob("*.png"))
            data = threaded_map(metadata.extract_png, pngs)
            (pack/"metadata.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
            self.cb.progress(int(n/len(packs)*100))
            self.cb.log(f"✔ {pack.name}: {len(data)} items", "SUCCESS")

    # 2. Standard Image Processing ------------------------------------------
    def process_images(self, root: Path):
        … (move in existing Tkinter logic untouched but
           replace every print()/UI call by self.cb.log / progress) …

    # 3. Auto-Mosaic ---------------------------------------------------------
    def run_auto_mosaic(self, pack: Path):
        safe_dir = pack/"pixiv_safe"; safe_dir.mkdir(exist_ok=True)
        originals = (pack/"original_images").glob("*.png")
        meta_map  = json.loads((pack/"metadata.json").read_text())
        wkf = PROJECT_ROOT/"external"/"PixivMosaicWorkflowAPI.json"
        script = PROJECT_ROOT/"external"/"pixivMosaic2.py"

        for i, src in enumerate(originals, 1):
            dst = safe_dir/src.name
            cmd = [sys.executable, str(script), str(wkf), str(src), str(dst)]
            ret = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if ret.returncode:
                self.cb.log(f"❌ {src.name}: {ret.stderr}", "ERROR"); continue
            metadata.embed(dst, meta_map[src.name])
            self.cb.progress(int(i/total*100))

3.3  Watermark routine kept verbatim, but moved to watermark.py.

3.4  threaded_map helper (junior idea) uses ThreadPoolExecutor for PNG scans.

3.5  Metadata helpers (metadata.py)

def extract_png(path):
    with Image.open(path) as im:
        raw = im.text.get("Comment", "{}")
    try:
        return json.loads(raw)
    except ValueError:
        return {"raw_comment": raw}     # keep it; warn later

def embed(path, meta: dict):
    txt = json.dumps(meta, ensure_ascii=False)
    if len(txt.encode()) > 60_000:      # 64 kB PNG tEXt guard (senior note)
        raise ValueError("Metadata too large (>64kB).")
    if path.suffix.lower()==".png":
        info = PngImagePlugin.PngInfo(); info.add_text("Comment", txt)
        Image.open(path).save(path, pnginfo=info)
    else:
        exif = piexif.dump({"0th": {piexif.ImageIFD.ImageDescription: txt.encode("utf-8")}})
        Image.open(path).save(path, exif=exif)

────────────────────────────────────────
4. GUI Layer – Main Window (PySide6)
────────────────────────────────────────
Layout (full-dev’s suggestion adapted):

Left column (QVBoxLayout)  
  • Folder selector (QFileDialog)  
  • Watermark dropdown + “Advanced” collapsible group (position, opacity, scale, margins)  
  • 4 Action Buttons (big, labelled)  
Right column  
  • QProgressBar (top)  
  • QPlainTextEdit log (colourised per level)  
  • QLabel status strip (bottom)

Enable/Disable matrix (junior idea):
• Auto-Mosaic button becomes enabled when original_images exists OR metadata.json present.  
• Manual Review button becomes enabled when pixiv_safe exists.

Threading:
Each button instantiates Worker(core_fn, *args) ⇒ Worker lives in its own QThread ⇒ emits progress(int), log(str,lvl), finished(bool).  
GUI connects/updates widgets, then self.setEnabled(False/True).

────────────────────────────────────────
5. Manual Mosaic Editor
────────────────────────────────────────
Canvas choice = QGraphicsView + QGraphicsScene.

Left: QListWidget in icon-mode (thumbnails)  
Right: MosaicCanvas (subclass QGraphicsPixmapItem) + Toolbar

Brush algorithm (combined ideas):

Option A – direct per-stroke effect (junior, better UX):
    def paint_at(self, x,y):
        r = self.brush_size
        box = (x-r, y-r, x+r, y+r)
        region = self.np_img[box]                     # NumPy slice
        if self.mode == "Pixelate":
            k = max(1, self.strength)
            region[:] = cv2.resize(cv2.resize(region, (r//k, r//k),
                                interpolation=cv2.INTER_NEAREST),
                                (2*r,2*r), interpolation=cv2.INTER_NEAREST)
        else:  # BLUR
            region[:] = cv2.GaussianBlur(region, (0,0), sigmaX=self.strength)

Option B – mask-then-apply (senior, faster implementation). Start with A, fall back to B if perf hits on large 8K.

Save flow (full-dev pseudocode)  
1. Read original metadata before editing.  
2. Composite edited pixmap to Pillow Image.  
3. metadata.embed() to preserve EXIF / PNG Comment.  
4. Overwrite file; emit thumbnail refresh.

Undo: maintain a stack of previous pixmaps (optional milestone).

────────────────────────────────────────
6. Error Handling & Logging
────────────────────────────────────────
• All core routines wrap try/except and log(level="ERROR").  
• Subprocess time-out (180 s) with retries=1.  
• Disk space guard: before writing massive zip, check shutil.disk_usage.  
• Interaction mistakes surfaced via QMessageBox; details still logged.

Log colouring (level→HTML):  
INFO = white, SUCCESS = green, WARN = orange, ERROR = red, FATAL = magenta.

────────────────────────────────────────
7. Performance & Thread-Safety Notes
────────────────────────────────────────
• Pillow write-access is not fully thread-safe on Windows; in `_process_single_image` open/close inside worker and keep max_workers ≤ min(8, os.cpu_count()).  
• Use Pillow ≥ 10 to ensure WebP EXIF support (full-dev reminder).  
• OpenCV is optional – wrap imports in try/except and fall back to pure Pillow filters.

────────────────────────────────────────
8. Packaging & Deployment
────────────────────────────────────────
requirements.txt

PySide6>=6.5  
Pillow>=10.0  
piexif>=1.1  
opencv-python>=4.9      # optional, flagged in setup  
numpy>=1.24  

build.bat (snippet)

py -m pip install -r requirements.txt  
py -m PyInstaller --noconsole --onefile run.py

Assets inside PyInstaller:  
`--add-data "assets;assets" --add-data "external;external"`

────────────────────────────────────────
9. Milestone / Checklist
────────────────────────────────────────
Phase 1 – Core Extraction  
  ☐ processor.py passes unit tests, no GUI deps  
  ☐ New pixiv_* keys round-trip

Phase 2 – Qt GUI  
  ☐ MainWindow reproduces all controls, 4-button workflow  
  ☐ Logs/progress streamed from dummy worker

Phase 3 – Auto-Mosaic  
  ☐ Successful pixiv_safe creation with metadata  
  ☐ Handles script errors, timeout, missing workflow JSON

Phase 4 – Manual Editor  
  ☐ Brush blur & pixelate, live preview ≤ 50 ms/stroke (1080p)  
  ☐ Save preserves metadata  
  ☐ Undo (1-level minimal)

Phase 5 – QA & Package  
  ☐ Windows / macOS / Linux smoke test  
  ☐ PyInstaller onefile (< 100 MB)  
  ☐ README with screenshots, workflow diagram

────────────────────────────────────────
10. Quick-Start for Developers
────────────────────────────────────────
git clone …  
cd project  
python -m venv venv && venv\Scripts\activate      # or source venv/bin/activate  
pip install -r requirements.txt  
python run.py                                     # launch GUI

Run unit tests:  `pytest -q tests/`

────────────────────────────────────────
With this consolidated guide you inherit the senior blueprint’s robustness, the junior engineer’s pragmatic tips, and the full-stack developer’s architectural clarifications—all in one actionable roadmap.