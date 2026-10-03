# 🛡️ MIDINS TITAN - OSINT Tool

![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.x-green.svg)
![Status](https://img.shields.io/badge/status-stable-success.svg)
![Security](https://img.shields.io/badge/Privacy-Local--First-orange.svg)
![License](https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg)

**Go check my other tool : Midins Decryptor -> https://github.com/Med0-n/Midins-Decryptor**

---

**MIDINS TITAN** is a lightweight, local-first OSINT intelligent whiteboard. It is designed for investigators who need a fast, private, and professional way to map digital evidence and infrastructure without the complexity of bloated software.

---

## 📸 Preview (on the sakura osint challenge)
<img width="2559" height="1439" alt="Capture d&#39;écran 2026-02-05 205707" src="https://github.com/user-attachments/assets/af44aa9f-42c4-428a-b78f-3b5834463ee5" />

---

## 🦅 The Power of Simplicity

In OSINT, speed and clarity are everything. **MIDINS TITAN** focuses on what actually works: **Fast collection, smart visualization, and total privacy.** No useless features, just pure efficiency.

> "Focus on the investigation, not the tool."

---

## ✨ Key Features (V1.2.0)

### 📂 Case Management & Dashboard
* **Investigation Dashboard:** Save, rename, load, or delete multiple investigations. Everything is stored locally.
* **Smart Persistence:** Automatic saving of nodes, edges, positions and counters. Your workspace stays exactly as you left it.

### 🔍 Smart Intelligence & Mapping
* **Auto-Scraping:** Drop a URL to instantly pull the Site Title and Official Logo.
* **Variable System (%s):** Create custom variables to pivot your research across multiple external tools instantly.
* **Drag & Drop:** Drop images or files directly onto the canvas. Images are automatically compressed and stored as nodes.
* **🧠 Smart Input Parser (NEW):** Automatically detects the type of input (URL, Email, IP address, Phone number, Hash) and applies the appropriate color and icon to the node.

### 📸 Export & Reporting (NEW)
* **PNG Graph Export:** Capture the current state of your graph as a PNG image in one click — perfect for reports, presentations, and sharing.
* **Markdown Report (NEW):** Generate a full investigation report in `.md` format, organized by entity status, with relations and notes included.
* **JSON Export/Import:** Full export and import of your investigation data, including node positions.

### 🏷️ Status Tags & Notes (NEW)
* **Quick Status Tags:** Mark any node with one click: 🎯 *Target*, ⚠️ *Suspect*, 🔍 *To Verify*, ✅ *Confirmed*. Color and emoji are applied automatically.
* **📝 Investigation Notes:** Add detailed investigation notes per node (e.g., *"Pseudo spotted on Telegram on 12/05"*). Notes are saved, exported, and visible in the right panel.

### 🔎 Search & Navigation (NEW)
* **Ctrl+F Graph Search:** Instantly find any node on the graph by label, URL or notes. Navigate results with ▸ / ◂ buttons.
* **Auto-Layout (⚡):** One-click reorganization of the entire graph to untangle complex investigations.

### 📊 Live Statistics (NEW)
* **Stats Badge:** Real-time counters in the header showing number of Nodes, Links, and Targets.

### 🕸️ Advanced UX & Interactions
* **Properties Panel:** Right-hand panel for deep customization of nodes and edges (colors, shapes, sizes, comments, notes).
* **Double-Click Actions:** Instant copy-to-clipboard for node labels or URLs.
* **Stable Layout:** Undo/Redo system that preserves exact node positions. No more "auto-jumping" nodes.
* **Smart Placement:** New nodes automatically find free space on the canvas to avoid stacking.
* **Drag-to-Save:** Node positions are saved automatically when you drag them.

### 🛡️ Privacy & Sovereignty
* **100% Local:** Runs on a local Flask server. No cloud, no tracking, no external logs. Total confidentiality.

---

## 🚀 Installation & Launch

### 1. Get the Source Code
Go to [Releases](../../releases) and download the latest version (e.g. `Midins Titan V1.2.0.zip or Source code.zip`), then extract it.

### 2. Install Dependencies

**Windows:**
Double-click `install.bat`

**Linux / macOS:**
```bash
chmod +x install.sh
./install.sh
```

**Manual (any OS):**
```bash
pip install -r requirements.txt
```

### 3. Launch the Tool

- **Windows:** Double-click `launch.bat`
- **Linux / macOS:** Run `./launch.sh` (or `python3 app.py`)

Then open your browser at: **http://127.0.0.1:5000** (opened automatically by the launcher!)

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` / `Ctrl+Shift+Z` | Redo |
| `Ctrl+F` | Search nodes on graph |
| `Delete` / `Backspace` | Delete selected node or edge |
| `Enter` (in search bar) | Create node from input |
| `Double-click` node | Copy label/URL to clipboard |

---

## 📋 Requirements
- Python 3.9+
- pip

## 🛠️ Troubleshooting
If `lxml` fails to install, run the install script for your OS — it handles system dependencies automatically.

---

## 📜 Credits & License
**Developed by:** Med0
This project is licensed under the **CC BY-SA 4.0**.

**MIDINS TITAN**: *Multimedia Intelligence & Digital Investigation Network System.*
