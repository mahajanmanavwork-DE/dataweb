#!/usr/bin/env python3
import argparse, sys, os, json, urllib.request, subprocess, time
BASE = os.path.dirname(os.path.abspath(__file__))
PIDFILE = os.path.join(BASE, "dataweb.pid")
DOWNLOADS = [("https://example.com/file1.csv","input_files/file1.csv"),("https://example.com/file2.csv","input_files/file2.csv")]

def cmd_setup():
    if sys.version_info < (3,10): sys.exit(1)
    for d in ["input_files","output_files","storage","env","metadata"]:
        os.makedirs(os.path.join(BASE,d), exist_ok=True)
    env_path = os.path.join(BASE,"env",".env")
    if not os.path.exists(env_path):
        open(env_path,"w").write("users_path=storage/users.json\nmetadata_path=metadata/metadata.json\n")
    users_path = os.path.join(BASE,"storage","users.json")
    if not os.path.exists(users_path):
        open(users_path,"w").write(json.dumps({"admin":{"password":"admin","current_key":None,"selected_file":None,"operations":{}}}))
    # Ensure venv and dependencies installed FIRST
    venv_dir = os.path.join(BASE, ".venv")
    if not os.path.exists(venv_dir):
        print("Creating .venv...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=False)
    if sys.platform == "win32":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")
    # Activate venv environment variables
    if sys.platform == "win32":
        venv_bin = os.path.join(venv_dir, "Scripts")
    else:
        venv_bin = os.path.join(venv_dir, "bin")
    activated_env = {**os.environ, "VIRTUAL_ENV": venv_dir, "PATH": venv_bin + os.pathsep + os.environ.get("PATH", "")}
    if not os.path.exists(venv_python):
        venv_python = sys.executable
    print("Activated .venv at:", venv_dir)
    print("Installing dependencies in venv using:", venv_python)
    for cmd_args in [
        [venv_python, "-m", "pip", "install", "--upgrade", "pip"],
        [venv_python, "-m", "pip", "install", "-e", BASE],
    ]:
        try:
            subprocess.run(cmd_args, env=activated_env, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except Exception as e:
            print(f"Install step failed: {e}")
    req_path = os.path.join(BASE, "requirements.txt")
    if os.path.exists(req_path):
        try:
            subprocess.run([venv_python, "-m", "pip", "install", "-r", req_path], env=activated_env, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            print("Installed requirements.txt in venv.")
        except Exception as e:
            print(f"Requirements install failed: {e}")
    # Downloads after venv/dependency setup
    for url,dest in DOWNLOADS:
        target = os.path.join(BASE,dest)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try: urllib.request.urlretrieve(url, target)
        except Exception as e: print(f"Download fail: {e}")
    print("dataweb setup complete (venv ready).")
    binary_name = "cloudflared.exe" if sys.platform == "win32" else "cloudflared"
    binary_path = os.path.join(BASE, binary_name)
    if not os.path.exists(binary_path):
        possible_src = os.path.join(os.path.expanduser("~"), "Desktop", "college-prac-2", binary_name)
        if os.path.exists(possible_src):
            import shutil
            shutil.copy(possible_src, binary_path)
            print("Copied cloudflared binary from desktop.")
        else:
            print("cloudflared binary not found. Download it manually or run from project folder.")

def cmd_run(silent=False):
    import sys as s; s.path.insert(0, BASE)
    log_level = "warning" if silent else "info"
    stdout_dest = subprocess.DEVNULL if silent else None
    stderr_dest = subprocess.DEVNULL if silent else None
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--log-level", log_level],
        stdout=open(os.path.join(BASE,"uvicorn_stdout.log"),"w"),
        stderr=open(os.path.join(BASE,"uvicorn_stdout.log"),"w"),
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        cwd=BASE,
        env={**os.environ, "PYTHONPATH": BASE + ":" + os.environ.get("PYTHONPATH", "")}
    )
    with open(PIDFILE, "w") as f:
        f.write(str(proc.pid))
    print("Server started (PID", proc.pid, ")" + (" silent" if silent else ""))
    try:
        tunnel_log = os.path.join(BASE, "tunnel.log")
        with open(tunnel_log, "w") as logf:
            tunnel = subprocess.Popen(
                [os.path.join(BASE, "cloudflared.exe"), "tunnel", "--url", "http://localhost:5000"],
                stdout=logf, stderr=logf, stdin=subprocess.DEVNULL,
                start_new_session=True, cwd=BASE
            )
        import time
        for _ in range(20):
            time.sleep(0.3)
            if not os.path.exists(tunnel_log):
                continue
            with open(tunnel_log, "r") as f:
                content = f.read()
            for line in content.splitlines():
                if "trycloudflare.com" in line:
                    for part in line.split():
                        if part.startswith("https://") and "trycloudflare.com" in part:
                            print("Public URL:", part)
                            return
        # If not found in loop, show last URL found or nothing
        with open(tunnel_log, "r") as f:
            content = f.read()
        for line in content.splitlines():
            if "trycloudflare.com" in line:
                for part in line.split():
                    if part.startswith("https://") and "trycloudflare.com" in part:
                        print("Public URL:", part)
                        url_path = os.path.join(BASE, "tunnel_url.txt")
                        open(url_path, "w").write(part)
                        storage_dir = os.path.join(BASE, "storage")
                        os.makedirs(storage_dir, exist_ok=True)
                        history_path = os.path.join(storage_dir, "tunnel_history.log")
                        with open(history_path, "a") as h:
                            h.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {part}\n")
                        if os.path.exists(tunnel_log):
                            with open(tunnel_log, "r") as src, open(history_path, "a") as dst:
                                dst.write(src.read() + "\n---\n")
                        return
    except Exception as e:
        print("Tunnel error (cloudflared):", e)

def _find_pid_on_port(port=5000):
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(["netstat", "-ano"], text=True)
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    return int(parts[-1])
        except Exception:
            pass
    else:
        try:
            out = subprocess.check_output(["ss", "-tlnp"], text=True, stderr=subprocess.STDOUT)
            for line in out.splitlines():
                if f":{port}" in line:
                    import re
                    m = re.search(r"pid=(\d+)", line)
                    if m:
                        return int(m.group(1))
        except Exception:
            pass
    return None

def cmd_stop():
    pid = _find_pid_on_port(5000)
    if pid is None:
        if os.path.exists(PIDFILE):
            try:
                pid = int(open(PIDFILE).read())
            except Exception:
                pass
    if pid:
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(pid), "/T"], capture_output=True)
            else:
                try:
                    os.kill(pid, 9)
                except ProcessLookupError:
                    pass
            print("Server stopped.")
        except Exception as e:
            print(f"Stop error: {e}")
    else:
        print("Server not running (port 5000 not found).")
    if os.path.exists(PIDFILE):
        try:
            os.remove(PIDFILE)
        except Exception:
            pass
    url_file = os.path.join(BASE, "tunnel_url.txt")
    for temp in [url_file, os.path.join(BASE, "tunnel.log"), os.path.join(BASE, "uvicorn_stdout.log")]:
        if os.path.exists(temp):
            try:
                os.remove(temp)
            except Exception:
                pass

def cmd_users():
    users_path = os.path.join(BASE, "storage", "users.json")
    if not os.path.exists(users_path):
        print("No users file.")
        return
    users = json.load(open(users_path))
    print(f"Total users: {len(users)}")
    for name in users:
        print(f" - {name}")

def cmd_user_add(name, pw):
    users_path = os.path.join(BASE, "storage", "users.json")
    users = {}
    if os.path.exists(users_path):
        users = json.load(open(users_path))
    if name in users:
        print("User exists")
        return
    users[name] = {"password": pw, "current_key": None, "selected_file": None, "operations": {}}
    open(users_path, "w").write(json.dumps(users, indent=4))
    print("User added")

def cmd_start():
    # Check if anything is listening on port 5000 (cross-platform)
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(("127.0.0.1", 5000))
        s.close()
        if result == 0:
            print("running")
            return
    except Exception:
        pass
    print("stopped")

def main():
    p = argparse.ArgumentParser(prog="dataweb")
    p.add_argument("command", choices=["setup","run","stop","users","user","start","status"])
    p.add_argument("--name", default=None)
    p.add_argument("--password", default=None)
    p.add_argument("--silent", action="store_true")
    args = p.parse_args()
    if args.command == "setup": cmd_setup()
    elif args.command == "run": cmd_run(silent=args.silent)
    elif args.command == "users": cmd_users()
    elif args.command == "user":
        if args.name and args.password:
            cmd_user_add(args.name, args.password)
        else:
            print("Usage: dataweb user --name NAME --password PASS")
    elif args.command == "start" or args.command == "status": cmd_start()
    elif args.command == "stop": cmd_stop()
if __name__ == "__main__":
    main()
