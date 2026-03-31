# PDF Editor - Setup Guide for Beginners
## What this tool does
- Open any PDF (including image-based PDFs)
- Preview all pages in separate tabs
- Draw **white mask rectangles** to hide/cover any content
- Add **draggable text** with custom font size and color
- Save as a new PDF with edits burned in permanently
- PDF quality and structure are fully preserved

---

## Step-by-Step Setup (Windows + VS Code)

### Step 1 — Make sure Python is installed correctly
1. Open **Command Prompt** (press Windows key, type `cmd`, press Enter)
2. Type: `python --version`
3. You should see something like `Python 3.11.x`
4. If you see an error, go to https://python.org/downloads, download Python, and during install **check the box that says "Add Python to PATH"**

### Step 2 — Install the required packages
In Command Prompt, type this and press Enter:
```
pip install flask pymupdf
```
Wait for it to finish (it will download two small packages).

### Step 3 — Open the project in VS Code
1. Open **VS Code**
2. Go to **File → Open Folder**
3. Select the `pdf_editor` folder (the folder containing `app.py`)

### Step 4 — Run the app
**Option A (easiest):** Double-click `START_EDITOR.bat`

**Option B (from VS Code terminal):**
1. In VS Code, go to **Terminal → New Terminal**
2. Type: `python app.py`
3. Press Enter

### Step 5 — Use the editor
1. Your browser should open automatically, or go to: **http://localhost:5000**
2. Click **Open PDF** or drag and drop a PDF file
3. Use the toolbar tools:
   - **White Mask** → Click and drag to draw a white box over content
   - **Add Text** → Click anywhere on the page to place text, then type
   - **Select** → Move or delete existing masks and text
4. Use **page tabs** at the top to switch between pages
5. Click **Save PDF** — it will download as `yourfile_edited.pdf`

---

## Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `M` | Switch to Mask tool |
| `T` | Switch to Text tool |
| `Escape` | Switch to Select tool |
| `Ctrl + Z` | Undo last action |

---

## Tips
- **Mask quality**: The white mask is drawn directly onto the PDF (not just a screenshot), so quality is perfectly preserved
- **Text over mask**: Yes! Add text, then drag it over a white mask — works perfectly
- **Image PDFs**: Works with scanned/image PDFs too — the mask covers the image content
- **File size**: The saved PDF uses compression so file size stays reasonable
- **Undo**: You can undo any mask or text addition before saving

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'flask'"**
→ Run: `pip install flask pymupdf`

**"pip is not recognized"**
→ Python isn't in PATH. Reinstall Python and check "Add to PATH"

**Page is blank / won't render**
→ Check the Command Prompt window for error messages

**Can't type text after clicking "Add Text"**
→ Make sure the Text tool is selected (orange highlight), then click on the page

**Saved PDF looks different**
→ Text font defaults to Helvetica. This is a standard PDF font and preserves quality perfectly.

---

## File Structure
```
pdf_editor/
├── app.py              ← Main Python server (don't edit unless you know Python)
├── requirements.txt    ← Package list
├── START_EDITOR.bat    ← Double-click to start on Windows
├── README.md           ← This file
├── templates/
│   └── index.html      ← The editor interface (runs in browser)
├── uploads/            ← Your uploaded PDFs are stored here temporarily
└── outputs/            ← Your saved/edited PDFs appear here
```
