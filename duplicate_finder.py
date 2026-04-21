import os
import sys
import hashlib
import shutil
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Try to use ThreadingHTTPServer (Python 3.7+), fallback to custom mixin if needed
try:
    from http.server import ThreadingHTTPServer
except ImportError:
    from socketserver import ThreadingMixIn
    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

# Try to import send2trash, fallback to os.remove if not available
try:
    import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

# ─────────────────────────── Setup ───────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

log_filename = LOG_DIR / f"duplicate_finder_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("DuplicateFinder")

# ─────────────────────────── Hashing Utilities ────────────────────────────────

def compute_hash(filepath: str, algorithm: str = "md5", chunk_size: int = 65536) -> str | None:
    try:
        h = hashlib.new(algorithm)
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, PermissionError) as e:
        logger.warning(f"Cannot hash '{filepath}': {e}")
        return None

# ─────────────────────────── Scanner ─────────────────────────────────────────

scan_progress = {"scanned": 0, "total": 0, "status": "idle", "current": ""}

def scan_directories(
    directories: list[str],
    algorithm: str = "md5",
    min_size: int = 1,
    extensions: list[str] | None = None,
) -> dict:
    global scan_progress
    scan_progress = {"scanned": 0, "total": 0, "status": "scanning", "current": ""}

    logger.info("=" * 60)
    logger.info(f"Scan started at {datetime.now().isoformat()}")
    logger.info(f"Directories: {directories}")
    logger.info(f"Algorithm: {algorithm.upper()}, Min size: {min_size} bytes")

    all_files: list[str] = []
    for directory in directories:
        if not os.path.isdir(directory):
            logger.warning(f"Skipping '{directory}': not a valid directory")
            continue
        try:
            for root, _, files in os.walk(directory):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    if extensions:
                        if not any(fname.lower().endswith(ext.lower()) for ext in extensions):
                            continue
                    try:
                        if os.path.getsize(fpath) < min_size:
                            continue
                    except OSError:
                        continue
                    all_files.append(fpath)
        except Exception as e:
            logger.error(f"Error walking directory '{directory}': {e}")

    scan_progress["total"] = len(all_files)
    logger.info(f"Total files to scan: {len(all_files)}")

    hash_map: dict[str, list[str]] = defaultdict(list)
    for i, fpath in enumerate(all_files):
        scan_progress["scanned"] = i + 1
        scan_progress["current"] = fpath
        file_hash = compute_hash(fpath, algorithm)
        if file_hash:
            hash_map[file_hash].append(fpath)

    duplicate_groups: list[dict] = []
    total_wasted = 0
    total_duplicates = 0

    for file_hash, paths in hash_map.items():
        if len(paths) < 2:
            continue
        sizes = []
        mtimes = []
        for p in paths:
            try:
                stat = os.stat(p)
                sizes.append(stat.st_size)
                mtimes.append(stat.st_mtime)
            except OSError:
                sizes.append(0)
                mtimes.append(0)

        file_size = sizes[0] if sizes else 0
        wasted = file_size * (len(paths) - 1)
        total_wasted += wasted
        total_duplicates += len(paths) - 1

        files_info = []
        for idx, (p, sz, mt) in enumerate(zip(paths, sizes, mtimes)):
            files_info.append({
                "path": p,
                "name": os.path.basename(p),
                "directory": os.path.dirname(p),
                "size": sz,
                "size_human": human_readable_size(sz),
                "modified": datetime.fromtimestamp(mt).strftime("%Y-%m-%d %H:%M:%S") if mt else "—",
                "index": idx,
            })

        files_info.sort(key=lambda x: x["modified"], reverse=True)

        duplicate_groups.append({
            "hash": file_hash,
            "algorithm": algorithm,
            "file_size": file_size,
            "file_size_human": human_readable_size(file_size),
            "wasted_space": wasted,
            "wasted_space_human": human_readable_size(wasted),
            "count": len(paths),
            "files": files_info,
        })

    duplicate_groups.sort(key=lambda g: g["wasted_space"], reverse=True)
    scan_progress["status"] = "done"
    
    return {
        "groups": duplicate_groups,
        "summary": {
            "total_files_scanned": len(all_files),
            "duplicate_groups": len(duplicate_groups),
            "total_duplicates": total_duplicates,
            "total_wasted": total_wasted,
            "total_wasted_human": human_readable_size(total_wasted),
            "algorithm": algorithm,
            "scan_time": datetime.now().isoformat(),
            "log_file": str(log_filename),
        },
    }

# ─────────────────────────── Actions ─────────────────────────────────────────

def delete_files(file_paths: list[str], mode: str = "trash") -> dict:
    results = {"success": [], "failed": [], "space_freed": 0}
    logger.info(f"Delete action: mode={mode}, files={len(file_paths)}")

    for fpath in file_paths:
        try:
            size = os.path.getsize(fpath)
            if mode == "trash":
                if HAS_SEND2TRASH:
                    send2trash.send2trash(fpath)
                    logger.info(f"[TRASH] {fpath}")
                else:
                    os.remove(fpath)
                    logger.info(f"[DELETE (Fallback)] {fpath}")
            else:
                os.remove(fpath)
                logger.info(f"[DELETE] {fpath}")
            results["success"].append(fpath)
            results["space_freed"] += size
        except Exception as e:
            logger.error(f"Failed to remove '{fpath}': {e}")
            results["failed"].append({"path": fpath, "error": str(e)})

    results["space_freed_human"] = human_readable_size(results["space_freed"])
    return results

# ─────────────────────────── Helpers ─────────────────────────────────────────

def human_readable_size(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} PB"

# ─────────────────────────── HTTP Server ──────────────────────────────────────

_scan_result: dict | None = None
_scan_lock = threading.Lock()

class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filename: str):
        filepath = BASE_DIR / filename
        if not filepath.exists():
            self.send_response(404)
            self.end_headers()
            return
        
        mime = "text/html" if filename.endswith(".html") else \
               "text/css" if filename.endswith(".css") else \
               "application/javascript" if filename.endswith(".js") else \
               "application/octet-stream"
        
        content = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(content))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._send_file("index.html")
        elif path == "/style.css":
            self._send_file("style.css")
        elif path == "/app.js":
            self._send_file("app.js")
        elif path == "/api/progress":
            self._send_json(scan_progress)
        elif path == "/api/results":
            global _scan_result
            with _scan_lock:
                if _scan_result is None:
                    self._send_json({"error": "No scan results yet"}, 404)
                else:
                    self._send_json(_scan_result)
        elif path == "/api/logs":
            try:
                log_content = log_filename.read_text(encoding="utf-8", errors="replace")
                self._send_json({"log": log_content, "file": str(log_filename)})
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        if path == "/api/scan":
            dirs = payload.get("directories", [])
            algorithm = payload.get("algorithm", "md5")
            min_size = int(payload.get("min_size", 1))
            extensions = payload.get("extensions") or None

            def run_scan():
                global _scan_result
                result = scan_directories(dirs, algorithm, min_size, extensions)
                with _scan_lock:
                    _scan_result = result

            t = threading.Thread(target=run_scan, daemon=True)
            t.start()
            self._send_json({"status": "scanning"})

        elif path == "/api/delete":
            files = payload.get("files", [])
            mode = payload.get("mode", "trash")
            result = delete_files(files, mode)
            self._send_json(result)
        else:
            self._send_json({"error": "Unknown endpoint"}, 404)

def run_server(port: int = 5500):
    while port < 5510:
        try:
            # Use "" to listen on all available interfaces
            server = ThreadingHTTPServer(("", port), APIHandler)
            print(f"\n{'='*50}")
            print(f"SUCCESS! DuplicateFinder is live")
            print(f"Local Link: http://localhost:{port}")
            print(f"Network Link: http://127.0.0.1:{port}")
            print(f"Press Ctrl+C to stop the server.")
            print(f"{'='*50}\n")
            logger.info(f"Server started on port {port}")
            server.serve_forever()
            break
        except OSError as e:
            if e.errno == 98 or e.errno == 10048: # Port already in use
                print(f"Port {port} is busy, trying {port + 1}...")
                port += 1
            else:
                print(f"Failed to start server: {e}")
                break

if __name__ == "__main__":
    try:
        run_server()
    except Exception as e:
        print("\n" + "!"*50)
        print(f"CRITICAL ERROR DURING STARTUP:")
        print(f" {e}")
        print("!"*50)
        import traceback
        traceback.print_exc()
        print("\nPossible fix: Run 'pip install Send2Trash'")
        input("\nPress ENTER to close this window...")


