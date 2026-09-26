from pathlib import Path
import os
R=Path(__file__).resolve().parents[1]
os.environ['HF_HOME']=str(R/'work/models/huggingface')
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING']='1'
from huggingface_hub import snapshot_download
p=snapshot_download('microsoft/Florence-2-base',allow_patterns=['*.py','*.json','*.txt','*.safetensors'],local_dir=str(R/'work/models/florence2'))
print(p)
