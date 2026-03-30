#!/usr/bin/env python3
"""
export_codebase.py — Scan a codebase and generate a single Markdown file for AI context.
"""

import os
import sys
import argparse
import fnmatch
import subprocess
import datetime
import re
from pathlib import Path

# ---------------------------------------------
# Constants
# ---------------------------------------------

DEFAULT_SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__",
    ".idea", ".vscode", "dist", "build", ".mypy_cache",
    ".pytest_cache", ".tox", "egg-info", ".eggs",
}

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".htm",
    ".css", ".scss", ".sass", ".less",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".md", ".txt", ".rst", ".env.example",
    ".sh", ".bash", ".zsh", ".fish",
    ".sql", ".graphql", ".gql",
    ".xml", ".svg",
    ".dockerfile", ".containerfile",
    ".gitignore", ".gitattributes", ".editorconfig",
    ".eslintrc", ".prettierrc", ".babelrc",
    ".go", ".rs", ".rb", ".php", ".java", ".kt", ".swift", ".c", ".cpp", ".h", ".cs",
    ".r", ".R", ".lua", ".pl", ".ex", ".exs", ".erl", ".dart", ".vue", ".svelte",
}

EXTENSION_LANGUAGE_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "jsx", ".tsx": "tsx", ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "scss", ".sass": "sass", ".less": "less",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".ini": "ini", ".cfg": "ini",
    ".md": "markdown", ".txt": "text", ".rst": "rst",
    ".sh": "bash", ".bash": "bash", ".zsh": "zsh",
    ".sql": "sql", ".graphql": "graphql", ".gql": "graphql",
    ".xml": "xml", ".svg": "xml",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
    ".java": "java", ".kt": "kotlin", ".swift": "swift",
    ".c": "c", ".cpp": "cpp", ".h": "c", ".cs": "csharp",
    ".r": "r", ".R": "r", ".lua": "lua", ".pl": "perl",
    ".ex": "elixir", ".exs": "elixir", ".erl": "erlang",
    ".dart": "dart", ".vue": "vue", ".svelte": "svelte",
}

# Extensions that count as "code" for the line counter (excludes prose/data/config)
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".sh", ".bash", ".zsh", ".fish",
    ".sql", ".graphql", ".gql",
    ".go", ".rs", ".rb", ".php", ".java", ".kt", ".swift",
    ".c", ".cpp", ".h", ".cs",
    ".r", ".R", ".lua", ".pl",
    ".ex", ".exs", ".erl", ".dart", ".vue", ".svelte",
}

CODEBASEIGNORE_FILE = ".codebaseignore"
DEFAULT_IGNORE_CONTENT = """\
# .codebaseignore — Custom ignore file for export_codebase.py
# Syntax similar to .gitignore

# Directories
node_modules/
venv/
.venv/
dist/
build/

# File extensions
*.log
*.lock
*.min.js
*.min.css

# Specific files
secret.txt
.env
*.pem
*.key
"""

MAX_FILE_SIZE_DEFAULT_MB = 1.0

# ---------------------------------------------
# Helpers
# ---------------------------------------------

def print_header(text: str):
    width = 60
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)

def print_step(text: str):
    print(f"\n>>  {text}")

def print_info(text: str):
    print(f"    {text}")

def print_warn(text: str):
    print(f"    [!] {text}")

def prompt_yes_no(question: str) -> bool:
    while True:
        answer = input(f"\n{question} (Y/N): ").strip().upper()
        if answer in ("Y", "YES"):
            return True
        if answer in ("N", "NO"):
            return False
        print("   Please enter Y or N.")

def detect_language(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    name = Path(filepath).name.lower()
    if name == "dockerfile" or name.startswith("dockerfile."):
        return "dockerfile"
    return EXTENSION_LANGUAGE_MAP.get(ext, "")

def file_size_str(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024*1024):.2f} MB"

def format_mtime(path: str) -> str:
    try:
        ts = os.path.getmtime(path)
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "unknown"

# ---------------------------------------------
# Ignore Pattern Handling
# ---------------------------------------------

def load_ignore_patterns(filepath: str) -> list[str]:
    patterns = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    except Exception as e:
        print_warn(f"Could not read ignore file: {e}")
    return patterns

def matches_ignore_patterns(rel_path: str, name: str, is_dir: bool, patterns: list[str]) -> bool:
    """Return True if the file/dir should be ignored."""
    for pattern in patterns:
        # Directory pattern: ends with /
        if pattern.endswith("/"):
            dir_pattern = pattern.rstrip("/")
            if is_dir and fnmatch.fnmatch(name, dir_pattern):
                return True
            # Also check if any component in the path matches
            for part in Path(rel_path).parts:
                if fnmatch.fnmatch(part, dir_pattern):
                    return True
        else:
            # File pattern
            if fnmatch.fnmatch(name, pattern):
                return True
            if fnmatch.fnmatch(rel_path, pattern):
                return True
    return False

# ---------------------------------------------
# Directory Traversal
# ---------------------------------------------

def collect_files(
    root: str,
    max_size_bytes: int,
    ignore_patterns: list[str],
) -> tuple[list[dict], list[dict]]:
    """
    Returns (included_files, excluded_files)
    Each entry: {"path": abs_path, "rel_path": rel, "size": bytes, "reason": str}
    """
    included = []
    excluded = []
    root_path = Path(root).resolve()

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Prune skip dirs
        rel_dir = str(Path(dirpath).relative_to(root_path))

        dirnames[:] = [
            d for d in dirnames
            if d not in DEFAULT_SKIP_DIRS
            and not matches_ignore_patterns(
                str(Path(rel_dir) / d), d, True, ignore_patterns
            )
        ]

        for filename in filenames:
            abs_path = os.path.join(dirpath, filename)
            rel_path = str(Path(abs_path).relative_to(root_path))
            ext = Path(filename).suffix.lower()
            name_lower = filename.lower()

            # Check ignore patterns
            if matches_ignore_patterns(rel_path, filename, False, ignore_patterns):
                excluded.append({"rel_path": rel_path, "reason": "ignore pattern"})
                continue

            # Check extension whitelist (also allow files with no extension like Dockerfile)
            is_allowed_ext = ext in ALLOWED_EXTENSIONS
            is_dockerfile = name_lower in ("dockerfile", "makefile", "rakefile", "procfile", "gemfile")
            is_dotfile_text = filename.startswith(".") and ext == "" and len(filename) < 30
            if not (is_allowed_ext or is_dockerfile or is_dotfile_text):
                excluded.append({"rel_path": rel_path, "reason": f"unsupported extension ({ext or 'none'})"})
                continue

            # Check file size
            try:
                size = os.path.getsize(abs_path)
            except OSError:
                excluded.append({"rel_path": rel_path, "reason": "unreadable (os error)"})
                continue

            if size > max_size_bytes:
                excluded.append({
                    "rel_path": rel_path,
                    "reason": f"too large ({file_size_str(size)} > {file_size_str(max_size_bytes)})"
                })
                continue

            included.append({
                "abs_path": abs_path,
                "rel_path": rel_path,
                "size": size,
                "mtime": format_mtime(abs_path),
            })

    included.sort(key=lambda x: x["rel_path"])
    return included, excluded

# ---------------------------------------------
# Tree Builder
# ---------------------------------------------

def build_tree(root: str, included_files: list[dict]) -> str:
    """Build a tree-like string from the included files."""
    rel_paths = [f["rel_path"] for f in included_files]
    # Build nested dict
    tree: dict = {}
    for p in rel_paths:
        parts = Path(p).parts
        node = tree
        for part in parts:
            node = node.setdefault(part, {})

    def render(node: dict, prefix: str = "", is_root: bool = False) -> list[str]:
        lines = []
        items = sorted(node.items(), key=lambda x: (bool(x[1]), x[0]))
        for i, (name, children) in enumerate(items):
            connector = "└── " if i == len(items) - 1 else "├── "
            extension = "    " if i == len(items) - 1 else "│   "
            if children:
                lines.append(f"{prefix}{connector}{name}/")
                lines.extend(render(children, prefix + extension))
            else:
                lines.append(f"{prefix}{connector}{name}")
        return lines

    root_name = Path(root).resolve().name
    lines = [f"{root_name}/"] + render(tree)
    return "\n".join(lines)

# ---------------------------------------------
# File Content Reader
# ---------------------------------------------

def read_file_safe(abs_path: str) -> tuple[str | None, str | None]:
    """Returns (content, error_message)."""
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(abs_path, "r", encoding=enc) as f:
                return f.read(), None
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return None, str(e)
    return None, "encoding error (tried utf-8, latin-1, cp1252)"

# ---------------------------------------------
# Lines of Code Counter
# ---------------------------------------------

def count_lines_of_code(included_files: list[dict]) -> tuple[int, int]:
    """
    Returns (total_lines, files_counted).
    Only counts files whose extension is in CODE_EXTENSIONS.
    Blank lines and comment lines are included (standard LOC definition).
    """
    total = 0
    files_counted = 0
    for f in included_files:
        ext = Path(f["rel_path"]).suffix.lower()
        if ext not in CODE_EXTENSIONS:
            continue
        content, err = read_file_safe(f["abs_path"])
        if content and not err:
            total += content.count("\n") + (1 if content and not content.endswith("\n") else 0)
            files_counted += 1
    return total, files_counted




def generate_markdown(
    root: str,
    included_files: list[dict],
    excluded_files: list[dict],
    tree_str: str,
    ai_description: str | None,
    errors: list[str],
    loc_total: int,
    loc_files: int,
) -> str:
    root_name = Path(root).resolve().name
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []

    # -- AI Description (if any) --
    if ai_description:
        lines += [
            "## AI-Generated Project Overview",
            "",
            ai_description.strip(),
            "",
            "---",
            "",
        ]

    # -- Project Overview --
    lines += [
        f"# Codebase Export: `{root_name}`",
        "",
        "## Project Overview",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| **Root folder** | `{root_name}` |",
        f"| **Files included** | {len(included_files)} |",
        f"| **Files excluded** | {len(excluded_files)} |",
        f"| **Lines of code** | {loc_total:,} (across {loc_files} source files) |",
        f"| **Generated at** | {now} |",
        "",
        "---",
        "",
    ]

    # -- Table of Contents --
    lines += [
        "## Table of Contents",
        "",
        "1. [Folder Structure](#folder-structure)",
        "2. [File Contents](#file-contents)",
    ]
    for f in included_files:
        anchor = re.sub(r"[^a-z0-9\-]", "-", f["rel_path"].lower().replace("/", "-").replace("\\", "-"))
        anchor = re.sub(r"-+", "-", anchor).strip("-")
        lines.append(f"   - [`{f['rel_path']}`](#{anchor})")
    lines += ["", "---", ""]

    # -- Folder Structure --
    lines += [
        "## Folder Structure",
        "",
        "```",
        tree_str,
        "```",
        "",
        "---",
        "",
    ]

    # -- File Contents --
    lines += ["## File Contents", ""]

    for f in included_files:
        rel = f["rel_path"]
        abs_p = f["abs_path"]
        lang = detect_language(rel)
        size_str = file_size_str(f["size"])
        mtime = f["mtime"]

        # Anchor ID
        anchor = re.sub(r"[^a-z0-9\-]", "-", rel.lower().replace("/", "-").replace("\\", "-"))
        anchor = re.sub(r"-+", "-", anchor).strip("-")

        lines += [
            f'<a id="{anchor}"></a>',
            f"### File: `{rel}`",
            "",
            f"> **Size:** {size_str} &nbsp;|&nbsp; **Last modified:** {mtime}",
            "",
        ]

        content, err = read_file_safe(abs_p)
        if err:
            errors.append(f"{rel}: {err}")
            lines += [
                f"> ⚠️ **Could not read file:** {err}",
                "",
            ]
        else:
            lines += [
                f"```{lang}",
                content.rstrip(),
                "```",
                "",
            ]

    # -- Errors / Skipped --
    if errors:
        lines += [
            "---",
            "",
            "## Read Errors",
            "",
        ]
        for e in errors:
            lines.append(f"- `{e}`")
        lines.append("")

    # -- Excluded Files --
    if excluded_files:
        lines += [
            "---",
            "",
            "## Excluded Files",
            "",
            "| File | Reason |",
            "|------|--------|",
        ]
        for f in excluded_files:
            lines.append(f"| `{f['rel_path']}` | {f['reason']} |")
        lines.append("")

    return "\n".join(lines)

# ---------------------------------------------
# Ollama Integration
# ---------------------------------------------

def check_ollama_installed() -> bool:
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True, text=True, timeout=5,
            encoding="utf-8", errors="replace"
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def list_ollama_models() -> list[str]:
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace"
        )
        lines = result.stdout.strip().split("\n")
        models = []
        for line in lines[1:]:  # Skip header
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except Exception:
        return []

def generate_ollama_description(model: str, tree_str: str, included_files: list[dict]) -> str:
    # Build a condensed context for Ollama (avoid exceeding context limits)
    sample_contents = []
    total_chars = 0
    char_limit = 12000

    for f in included_files:
        if total_chars >= char_limit:
            break
        content, err = read_file_safe(f["abs_path"])
        if content and not err:
            snippet = content[:800]
            sample_contents.append(f"### {f['rel_path']}\n```\n{snippet}\n```")
            total_chars += len(snippet)

    context = f"""
Project folder structure:
```
{tree_str}
```

Sample file contents (truncated):
{"".join(sample_contents[:10])}
""".strip()

    prompt = f"""You are a senior software engineer. Analyze this codebase and provide a concise, high-level description.

{context}

Please provide:
1. **Project Purpose** — What does this project do?
2. **Main Components/Modules** — Key files and their roles
3. **Technologies Used** — Languages, frameworks, libraries
4. **Architecture Overview** — How the system is structured
5. **Notable Patterns** — Any interesting design patterns or conventions

Keep the response clear and structured. Use Markdown formatting."""

    messages = [
        "Sending codebase context to Ollama...",
        "The AI is analyzing the structure...",
        "Generating project description, please wait...",
        "Still working, this may take a minute...",
        "Almost done, reviewing the output...",
    ]

    import threading
    import time

    # Determine the width needed to fully overwrite any previous message
    msg_width = max(len(m) for m in messages) + 6  # padding for prefix "    "

    stop_event = threading.Event()
    msg_index = [0]

    def spinner():
        while not stop_event.is_set():
            msg = messages[msg_index[0] % len(messages)]
            line = f"    {msg}"
            # Pad to fixed width so previous longer lines are fully overwritten
            line = line.ljust(msg_width)
            print(f"\r{line}", end="", flush=True)
            msg_index[0] += 1
            # Wait 4 seconds before switching to the next message
            for _ in range(40):
                if stop_event.is_set():
                    break
                time.sleep(0.1)

    t = threading.Thread(target=spinner, daemon=True)
    t.start()

    try:
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True, text=True, timeout=180,
            encoding="utf-8", errors="replace"
        )
        stop_event.set()
        t.join()
        clear_line = " " * msg_width
        print(f"\r{clear_line}\r    [OK] AI description generated successfully.")
        output = result.stdout.strip()
    except subprocess.TimeoutExpired:
        stop_event.set()
        t.join()
        clear_line = " " * msg_width
        print(f"\r{clear_line}\r    [!] Ollama timed out after 3 minutes.")
        output = "_Ollama timed out. Description could not be generated._"
    except Exception as e:
        stop_event.set()
        t.join()
        clear_line = " " * msg_width
        print(f"\r{clear_line}\r    [!] Ollama error: {e}")
        output = f"_Error generating description: {e}_"

    # Unload the model from memory once we are done with it
    print_info(f"Unloading model '{model}' from memory...")
    try:
        subprocess.run(
            ["ollama", "stop", model],
            capture_output=True, timeout=10,
            encoding="utf-8", errors="replace"
        )
        print_info("Model unloaded.")
    except Exception as e:
        print_warn(f"Could not unload model: {e}")

    return output

def handle_ollama(tree_str: str, included_files: list[dict]) -> str | None:
    print_step("Checking Ollama installation...")
    if not check_ollama_installed():
        print_warn("Ollama is not installed or not in PATH. Skipping AI description.")
        print_info("Install it from: https://ollama.com")
        return None

    print_info("Ollama detected.")
    print_step("Fetching available models...")
    models = list_ollama_models()

    if not models:
        print_warn("No Ollama models found. Run `ollama pull <model>` to download one.")
        return None

    print_info("Available models:")
    for i, m in enumerate(models, 1):
        print_info(f"  {i}. {m}")

    while True:
        choice = input("\n   Select a model (number or name): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(models):
            selected = models[int(choice) - 1]
            break
        elif choice in models:
            selected = choice
            break
        else:
            print_warn("Invalid selection. Try again.")

    print_info(f"Using model: {selected}")
    return generate_ollama_description(selected, tree_str, included_files)

# ---------------------------------------------
# Gitignore Support
# ---------------------------------------------

def load_gitignore_patterns(root: str) -> list[str]:
    gitignore_path = os.path.join(root, ".gitignore")
    if not os.path.exists(gitignore_path):
        return []
    patterns = []
    try:
        with open(gitignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    except Exception:
        pass
    return patterns

# ---------------------------------------------
# CLI & Main
# ---------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Scan a codebase and export it as a Markdown file for AI context.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python export_codebase.py ./my_project output.md
  python export_codebase.py ./my_project output.md --max-size 2
  python export_codebase.py . context.md --max-size 0.5
        """
    )
    parser.add_argument("input_dir", nargs="?", help="Root directory to scan")
    parser.add_argument("output_file", nargs="?", help="Output Markdown file path")
    parser.add_argument(
        "--max-size",
        type=float,
        default=MAX_FILE_SIZE_DEFAULT_MB,
        metavar="MB",
        help=f"Maximum file size in MB to include (default: {MAX_FILE_SIZE_DEFAULT_MB})"
    )
    return parser.parse_args()

def main():
    args = parse_args()

    # -- Determine Root and Output --
    if args.input_dir:
        root = os.path.abspath(args.input_dir)
        if args.output_file:
            output_path = args.output_file
        else:
            output_path = os.path.join(root, "codebase.md")
    else:
        # Interactive Mode
        print_header("Codebase Exporter (Interactive)")
        while True:
            p = input("   Enter the path to your codebase: ").strip().strip("'\"")
            if p and os.path.isdir(p):
                root = os.path.abspath(p)
                break
            print("   [!] Invalid directory. Please try again.")

        default_out = "codebase.md"
        print(f"\n   Enter output file path (default: {default_out} inside codebase)")
        o = input("   > ").strip().strip("'\"")

        if not o:
            output_path = os.path.join(root, default_out)
        else:
            output_path = os.path.join(root, o)

    max_size_bytes = int(args.max_size * 1024 * 1024)

    print_header("Codebase Exporter")
    print_info(f"Root directory : {root}")
    print_info(f"Output file    : {output_path}")
    print_info(f"Max file size  : {args.max_size} MB")

    if not os.path.isdir(root):
        print(f"\nERROR: '{root}' is not a valid directory.")
        sys.exit(1)

    # -- Ignore File Setup --
    ignore_patterns: list[str] = []

    use_custom_ignore = prompt_yes_no("Do you want to use a custom ignore file (.codebaseignore)?")
    if use_custom_ignore:
        ignore_file_path = os.path.join(root, CODEBASEIGNORE_FILE)
        if not os.path.exists(ignore_file_path):
            print_info(f"Creating default {CODEBASEIGNORE_FILE} in {root} ...")
            try:
                with open(ignore_file_path, "w", encoding="utf-8") as f:
                    f.write(DEFAULT_IGNORE_CONTENT)
                print_info(f"Created. You can edit it before re-running. Proceeding with defaults.")
            except Exception as e:
                print_warn(f"Could not create ignore file: {e}")
        else:
            print_info(f"Found {CODEBASEIGNORE_FILE}, loading patterns...")
        ignore_patterns += load_ignore_patterns(ignore_file_path)
        print_info(f"Loaded {len(ignore_patterns)} custom ignore pattern(s).")

    use_gitignore = prompt_yes_no("Do you want to also use .gitignore patterns (if present)?")
    if use_gitignore:
        gi_patterns = load_gitignore_patterns(root)
        if gi_patterns:
            print_info(f"Loaded {len(gi_patterns)} pattern(s) from .gitignore.")
            ignore_patterns += gi_patterns
        else:
            print_info("No .gitignore found or it is empty.")

    # -- File Collection --
    print_step("Scanning directory...")
    included, excluded = collect_files(root, max_size_bytes, ignore_patterns)

    # -- Show Preview --
    print_header("File Scan Results")
    print_info(f"Files to INCLUDE ({len(included)}):")
    for f in included:
        print_info(f"  [+]  {f['rel_path']}  ({file_size_str(f['size'])})")

    if excluded:
        print_info(f"\nFiles to EXCLUDE ({len(excluded)}):")
        for f in excluded[:50]:  # Cap display at 50 to avoid flooding
            print_info(f"  [-]  {f['rel_path']}  -- {f['reason']}")
        if len(excluded) > 50:
            print_info(f"  ... and {len(excluded) - 50} more excluded files.")

    if not included:
        print("\n[!] No files to include. Exiting.")
        sys.exit(0)

    confirm = prompt_yes_no(f"\nProceed with exporting {len(included)} file(s) to '{output_path}'?")
    if not confirm:
        print("\nAborted by user.")
        sys.exit(0)

    # -- Build Tree --
    print_step("Building folder tree...")
    tree_str = build_tree(root, included)

    # -- Ollama (optional) --
    ai_description = None
    use_ollama = prompt_yes_no("Do you want to generate an AI description using a local model (Ollama)?")
    if use_ollama:
        ai_description = handle_ollama(tree_str, included)

    # -- Count Lines of Code --
    print_step("Counting lines of code...")
    loc_total, loc_files = count_lines_of_code(included)
    print_info(f"Total lines of code: {loc_total:,} (across {loc_files} source file(s))")

    # -- Generate Markdown --
    print_step("Generating Markdown...")
    errors: list[str] = []
    markdown = generate_markdown(root, included, excluded, tree_str, ai_description, errors, loc_total, loc_files)

    # -- Write Output --
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)
    except Exception as e:
        print(f"\nERROR: Failed to write output: {e}")
        sys.exit(1)

    # -- Final Summary Report --
    print_header("Export Complete")
    print_info(f"Output file      : {output_path}")
    print_info(f"Files included   : {len(included)}")
    print_info(f"Files excluded   : {len(excluded)}")
    print_info(f"Lines of code    : {loc_total:,} (across {loc_files} source file(s))")
    print_info(f"AI description   : {'Yes (Ollama)' if ai_description else 'No'}")
    if errors:
        print_info(f"Read errors      : {len(errors)} (listed in the output file)")
    print_info(f"Generated at     : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    input("    Press Enter to exit...")

if __name__ == "__main__":
    main()
