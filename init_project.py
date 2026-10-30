import os, json
BASE = os.path.dirname(os.path.abspath(__file__))
for d in ["input_files","output_files","storage","env","metadata"]:
    os.makedirs(os.path.join(BASE,d), exist_ok=True)
if not os.path.exists(os.path.join(BASE,"env",".env")):
    open(os.path.join(BASE,"env",".env"),"w").write("users_path=storage/users.json\nmetadata_path=metadata/metadata.json\n")
if not os.path.exists(os.path.join(BASE,"storage","users.json")):
    open(os.path.join(BASE,"storage","users.json"),"w").write(json.dumps({"admin":{"password":"admin","current_key":None,"selected_file":None,"operations":{}}}))
