import yaml # pip install PyYAML
import os
import shutil
import subprocess

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

config_lock = {}

LOCK_FILE_NAME = "config.lock.yaml"

if os.path.exists(LOCK_FILE_NAME):
    with open(LOCK_FILE_NAME, "r") as f:
        config_lock = yaml.safe_load(f)

all_cloned_packages = list(config.keys())

for folder_name, data in config.items():
    if "dependencies" in data:
        all_cloned_packages += list(data["dependencies"].keys())

def print_blue(text):
    BLUE = '\x1b[34m'
    RESET = '\x1b[0m'
    print(f"{BLUE}{text}{RESET}")

def get_git_head(repo_path='.'):
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"git error: {result.stderr.strip()}")
    return result.stdout.strip()

def integrate_package(folder_name, data):
    global config_lock

    repo_url = data['git']
    keep_list = ["lib", "test", "LICENSE", "pubspec.yaml", "android", "ios"]
    if "keep" in data:
        keep_list += [item.rstrip('/') for item in data['keep']]
    
    
    print(f"Processing {folder_name}...")

    if os.path.exists(folder_name):
        shutil.rmtree(folder_name)
    
    subprocess.run(["git", "clone", repo_url, folder_name], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    last_commit_hash = get_git_head(folder_name)

    if folder_name in config_lock:
        if config_lock[folder_name] != last_commit_hash:
            print_blue(f"{folder_name} has a new update!")
        subprocess.run(["git", "checkout", config_lock[folder_name]], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=folder_name)
    else:
        config_lock[folder_name] = last_commit_hash 
    

    for item in os.listdir(folder_name):
        if item not in keep_list:
            item_path = os.path.join(folder_name, item)
            
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path) 

pubspec = {
    "dependency_overrides": {},
}

for folder_name, data in config.items():

    pubspec["dependency_overrides"][folder_name] = {}
    pubspec["dependency_overrides"][folder_name]["path"] = f"./dependencies/{folder_name}"
    
    integrate_package(folder_name, data)
    if "dependencies" in data:
        for folder_name, data in data["dependencies"].items():
            integrate_package(folder_name, data)
            pubspec["dependency_overrides"][folder_name] = {}
            pubspec["dependency_overrides"][folder_name]["path"] = f"./dependencies/{folder_name}"


with open(LOCK_FILE_NAME, "w") as f:
    yaml.safe_dump(config_lock, f, sort_keys=True) 

with open("pubspec.yaml", "w") as f:
    yaml.safe_dump(pubspec, f, sort_keys=True) 