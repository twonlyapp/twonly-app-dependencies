import yaml # pip install PyYAML
import os
import shutil
import subprocess

# 1. Read the config file
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
    # Remove trailing slashes from keep list for easier comparison
    keep_list = ["lib", "test", "LICENSE", "pubspec.yaml"]
    if "keep" in data:
        keep_list += [item.rstrip('/') for item in data['keep']]
    
    
    print(f"Processing {folder_name}...")

    # Clone the repository
    # We check if folder exists to avoid git errors, or remove it to start fresh
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
    

    # 3. Clean up files (Remove all except 'keep')
    for item in os.listdir(folder_name):
        # We also usually want to remove the hidden .git folder unless explicitly kept
        if item not in keep_list:
            item_path = os.path.join(folder_name, item)
            
            if os.path.isdir(item_path):
                shutil.rmtree(item_path) # Delete directory
            else:
                os.remove(item_path)     # Delete file

    # 4. Find and replace in .dart files

    # replacing = [
    #     ("import '/", f"import 'package:twonly/src/packages/{folder_name}/lib/"),
    #     ("export '/", f"export 'package:twonly/src/packages/{folder_name}/lib/"),
    # ]

    # for package_name in all_cloned_packages:
    #     replacing.append(
    #         (f"import 'package:{package_name}/", f"import 'package:twonly/src/packages/{package_name}/lib/")
    #     )
    #     replacing.append(
    #         (f"export 'package:{package_name}/", f"export 'package:twonly/src/packages/{package_name}/lib/")
    #     )

    
    # print(f"Updating imports in .dart files...")

    # os.walk allows us to go into subdirectories recursively
    # for root, dirs, files in os.walk(folder_name):
    #     for file in files:
    #         if file.endswith(".dart"):
    #             file_path = os.path.join(root, file)
                
    #             try:
    #                 with open(file_path, "r", encoding="utf-8") as f:
    #                     content = f.read()

    #                 for search_text, replace_text in replacing:
                    
    #                     content = content.replace(search_text, replace_text)
    #                     content = content.replace(search_text.replace("'", '"'), replace_text.replace("'", '"'))
                    
    #                 if "replace" in data:
    #                     replace = data['replace']
    #                     for values in replace:
    #                         content = content.replace(values[0], values[1])
                    
    #                 with open(file_path, "w", encoding="utf-8") as f:
    #                     f.write(content)
                            
    #             except Exception as e:
    #                 print(f"Skipped {file_path}: {e}")

    # print(f"Done! Cleaned {folder_name}.")

pubspec = {
    "dependencies": {},
    "dependency_overrides": {},
}


# 2. Iterate through each entry
for folder_name, data in config.items():

    pubspec["dependencies"][folder_name] = {}
    pubspec["dependencies"][folder_name]["path"] = f"./dependencies/{folder_name}"
    # update = ["libsignal_protocol_dart"]
    # if folder_name not in update:
    #     continue
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