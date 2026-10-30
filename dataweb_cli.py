#!/usr/bin/env python3
import argparse, subprocess, sys, os, json, urllib.request
BASE = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS = [("https://example.com/file1.csv","input_files/file1.csv"),("https://example.com/file2.csv","input_files/file2.csv")]
def cmd_setup():
    if sys.version_info < (3,10): sys.exit(1)
    subprocess.check_call([sys.executable,"-m","pip","install","-r","requirements.txt"])
    for d in ["input_files","output_files","storage","env","metadata"]: os.makedirs(os.path.join(BASE,d), exist_ok=True)
    env_path = os.path.join(BASE,"env",".env")
    if not os.path.exists(env_path): open(env_path,"w").write("users_path=storage/users.json\nmetadata_path=metadata/metadata.json\n")
    users_path = os.path.join(BASE,"storage","users.json")
    if not os.path.exists(users_path): open(users_path,"w").write(json.dumps({"admin":{"password":"admin"}}))
    for url,dest in DOWNLOADS:
        target = os.path.join(BASE,dest)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try: urllib.request.urlretrieve(url, target)
        except Exception as e: print(f"Download fail: {e}")
    print("dataweb setup complete.")

def cmd_run():
    import uvicorn; import sys; sys.path.insert(0, BASE); uvicorn.run("main:app", host="0.0.0.0", port=5000)

def main():
    p = argparse.ArgumentParser(prog="dataweb")
    p.add_argument("command", choices=["setup","run"])
    args = p.parse_args()
    if args.command == "setup": cmd_setup()
    elif args.command == "run": cmd_run()
if __name__ == "__main__": main()
