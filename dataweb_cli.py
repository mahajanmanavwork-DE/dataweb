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
    for url,dest in DOWNLOADS:
        target = os.path.join(BASE,dest)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try: urllib.request.urlretrieve(url, target)
        except Exception as e: print(f"Download fail: {e}")
    print("dataweb setup complete (no pip here).")

def cmd_run(silent=False):
    import sys as s; s.path.insert(0, BASE)
    log_level = "warning" if silent else "info"
    stdout_dest = subprocess.DEVNULL if silent else None
    stderr_dest = subprocess.DEVNULL if silent else None
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--log-level", log_level],
        stdout=stdout_dest,
        stderr=stderr_dest,
        start_new_session=True,
        cwd=BASE,
        env={**os.environ, "PYTHONPATH": BASE + ":" + os.environ.get("PYTHONPATH", "")}
    )
    with open(PIDFILE, "w") as f:
        f.write(str(proc.pid))
    print("Server started (PID", proc.pid, ")" + (" silent" if silent else ""))

def cmd_stop():
    if not os.path.exists(PIDFILE):
        print("Server not running (no pidfile).")
        return
    try:
        pid = int(open(PIDFILE).read())
        os.kill(pid, 9)
        os.remove(PIDFILE)
        print("Server stopped.")
    except Exception as e:
        print(f"Stop error: {e}")

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
    if os.path.exists(PIDFILE):
        try:
            pid = int(open(PIDFILE).read())
            os.kill(pid, 0)
            print("running")
            return
        except (OSError, ValueError):
            pass
    print("stopped")

def main():
    p = argparse.ArgumentParser(prog="dataweb")
    p.add_argument("command", choices=["setup","run","stop","users","user","start"])
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
    elif args.command == "start": cmd_start()
    elif args.command == "stop": cmd_stop()
if __name__ == "__main__":
    main()
