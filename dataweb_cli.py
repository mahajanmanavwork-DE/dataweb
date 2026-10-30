#!/usr/bin/env python3
import argparse, sys, os, json, urllib.request
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
        open(users_path,"w").write(json.dumps({"admin":{"password":"admin"}}))
    for url,dest in DOWNLOADS:
        target = os.path.join(BASE,dest)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try: urllib.request.urlretrieve(url, target)
        except Exception as e: print(f"Download fail: {e}")
    print("dataweb setup complete (no pip here).")

def cmd_run(silent=False):
    import uvicorn; import sys; sys.path.insert(0, BASE)
    if silent:
        import logging; logging.getLogger("uvicorn").setLevel(logging.ERROR)
    uvicorn.run("main:app", host="0.0.0.0", port=5000, access_log=not silent)

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
    import scripts.auth as auth
    users = auth._load_users()
    print(f"Total users: {len(users)}")
    for u, info in users.items():
        print(f" - {u} (password={info.get('password')}, key={info.get('current_key')}, file={info.get('selected_file')}, ops={len(info.get('operations',{}))})")

def cmd_user_add(name, pw):
    import scripts.auth as auth
    ok = auth.create_user(name, pw)
    print("User added" if ok else "User exists")

def main():
    p = argparse.ArgumentParser(prog="dataweb")
    p.add_argument("command", choices=["setup","run","stop","users","user"])
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
    elif args.command == "stop": cmd_stop()
if __name__ == "__main__": main()
# Note: user commands appended below for CLI
