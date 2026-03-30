# 📦 export_codebase.py

> Scan an entire codebase and export it into a single, well-structured Markdown file — optimized for AI context ingestion.

---

## Features

| Feature | Details |
|---|---|
| 📂 Recursive directory scan | Walks all subdirectories, skipping irrelevant ones |
| 🔍 Smart file filtering | Whitelist of text-based extensions + optional size limit |
| 🚫 Custom ignore file | `.codebaseignore` with `.gitignore`-style patterns |
| 🌳 Folder tree | ASCII tree of included files |
| 📋 Table of contents | Anchor links to every file section |
| 🏷️ Language detection | Correct syntax highlighting per file extension |
| 🤖 Ollama integration | Optional AI project description via a local LLM |
| ⚠️ Error handling | Gracefully skips unreadable/binary files and logs them |

---

## Installation

No external dependencies required for the core script.

```bash
python export_codebase.py --help
```

**Optional** — for Ollama AI descriptions:

```bash
# Install Ollama from https://ollama.com
ollama pull llama3        # or any model you prefer
```

---

## Usage

```bash
python export_codebase.py <input_dir> <output_file> [--max-size MB]
```

### Examples

```bash
# Basic usage
python export_codebase.py ./my_project output.md

# Set max file size to 2 MB
python export_codebase.py ./my_project output.md --max-size 2

# Scan current directory, limit to 500 KB per file
python export_codebase.py . context.md --max-size 0.5
```

---

## Interactive Prompts

When you run the script, it will ask you:

1. **Use `.codebaseignore`?** — Creates or reuses a custom ignore file
2. **Use `.gitignore` patterns?** — Extends ignore rules from your existing `.gitignore`
3. **Show preview** — Lists all files that will be included or excluded
4. **Confirm export** — Prompts before writing to disk
5. **Use Ollama?** — Optionally generate an AI project description

---

## Output Structure

```
# Codebase Export: `my_project`

## 🤖 AI-Generated Project Overview      ← (if Ollama was used)

## Project Overview
| Field         | Value              |
|---------------|--------------------|
| Root folder   | my_project         |
| Files included| 42                 |
| Generated at  | 2025-06-01 14:32:00|

## Table of Contents
  - [src/app.py](#src-app-py)
  - [src/utils/helper.py](#src-utils-helper-py)
  ...

## Folder Structure
```
my_project/
├── src/
│   ├── app.py
│   └── utils/
│       └── helper.py
└── README.md
```

## File Contents

### 📄 `src/app.py`
> **Size:** 1.2 KB | **Last modified:** 2025-05-30 10:12:00

```python
print("Hello World")
```

## ⚠️ Read Errors          ← only shown if there were issues
## 🚫 Excluded Files        ← full list of skipped files + reasons
```

---

## Ignored Directories (always skipped)

`.git`, `node_modules`, `venv`, `.venv`, `__pycache__`, `.idea`, `.vscode`, `dist`, `build`, `.mypy_cache`, `.pytest_cache`, `.tox`

---

## Supported File Types

`.py` `.js` `.ts` `.jsx` `.tsx` `.html` `.css` `.scss` `.json` `.yaml` `.toml` `.md` `.txt` `.sh` `.sql` `.graphql` `.xml` `.go` `.rs` `.rb` `.php` `.java` `.kt` `.swift` `.c` `.cpp` `.cs` `.vue` `.svelte` `.dart` `.lua` `.r` `.ex` `.erl` and more.

---

## `.codebaseignore` Format

Auto-created on first run (if you select Y). Edit it like a `.gitignore`:

```
# Directories (trailing slash)
node_modules/
dist/

# Extensions
*.log
*.lock

# Specific files
secret.txt
.env
```

---

## Example Snippet (output)

````markdown
### 📄 `src/utils/helper.py`

> **Size:** 512 B | **Last modified:** 2025-05-29 08:45:00

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```
````

---

## Requirements

- Python **3.10+** (uses `str | None` type unions)
- No third-party pip packages required
- Ollama (optional): https://ollama.com
