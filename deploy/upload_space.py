"""Create (or update) the private Hugging Face Space and upload the assistant.

Usage (from the agent folder):
    py -3.12 -m pip install -U huggingface_hub
    py -3.12 deploy\\upload_space.py YOUR-HF-NAME/voron-assistant

YOUR-HF-NAME can be your user name or an organization you created on huggingface.co.
The first time, it asks for an access token (huggingface.co > Settings > Access Tokens > "Write").
"""
import sys, pathlib
from huggingface_hub import HfApi, get_token, login

A = pathlib.Path(__file__).resolve().parents[1]
if len(sys.argv) != 2 or "/" not in sys.argv[1]:
    sys.exit("Usage: py -3.12 deploy\\upload_space.py YOUR-HF-NAME/voron-assistant")
repo = sys.argv[1]

if not get_token():
    print("Paste a Hugging Face access token with 'Write' permission (it is not shown while you type).")
    login()

api = HfApi()
api.create_repo(repo, repo_type="space", space_sdk="docker", private=True, exist_ok=True)
print(f"Space ready: https://huggingface.co/spaces/{repo}  (private)")

# Only what the online assistant needs. Not uploaded: evaluation data, training data, the third-party
# troubleshooting guide (chunks_D), embeddings of the experiment arms, local scripts and git files.
IGNORE = [".git/*", ".vscode/*", "**/__pycache__/*", "*.pyc", "*.bat", "README.md", "BUILD_PLAN.md", "PUSH_TO_GITHUB.md",
          "FINAL_HANDOFF.md", "GRAPH_VERSION_CHECKLIST.md", "check_result.txt",
          "eval/*", "evaluation/*", "finetune/*", "notebooks/*", "data/finetune/*", "deploy/*",
          "tools/cad/*.zip", "tools/cad/*.step", "tools/cad/*.stp",
          "data/indexes/chunks_D.jsonl", "data/indexes/chunks_BP.jsonl",
          "data/indexes/emb_B_*", "data/indexes/emb_BP_*", "data/indexes/emb_C_*", "data/indexes/emb_C2_*", "data/indexes/emb_D_*",
          "data/indexes/emb_V2_nomic-embed-text.npy"]
print("Uploading files (about 30 MB, a few minutes) ...")
api.upload_folder(folder_path=str(A), repo_id=repo, repo_type="space", ignore_patterns=IGNORE,
                  commit_message="Upload Voron assistant (basic mode)")
api.upload_file(path_or_fileobj=str(A / "deploy" / "hf_space" / "README.md"), path_in_repo="README.md",
                repo_id=repo, repo_type="space", commit_message="Space description")
print(f"Done. The Space now builds (3-5 minutes). Open: https://huggingface.co/spaces/{repo}")
