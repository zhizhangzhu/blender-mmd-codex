"""Estimate the MV-intro offset from original vocal/inst audio and VMD mouth tracks.

This is a gross timebase check, not a claim of manually verified lyric sync.
"""

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--project", type=Path, required=True)
p.add_argument("--vmd-reader", type=Path, required=True)
p.add_argument("--ffmpeg", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
args = p.parse_args()
cfg = json.loads(args.project.read_text(encoding="utf-8"))
spec = importlib.util.spec_from_file_location("alignment_vmd", args.vmd_reader)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
rate = 12000
def decode(path):
    result = subprocess.run([str(args.ffmpeg),"-v","error","-nostdin","-i",path,"-vn","-ac","1","-ar",str(rate),"-f","f32le","-"],capture_output=True,check=True)
    return np.frombuffer(result.stdout,dtype="<f4").copy()
voice = decode(cfg["audio"]["bgm"])
inst = decode(cfg["audio"]["instrumental"])
length = min(len(voice),len(inst)) - 600
base = np.arange(12*rate,35*rate,12)
fits=[]
for lag in range(-240,241):
    y=voice[base].astype(np.float64);x=inst[base+lag].astype(np.float64)
    gain=float(np.dot(x,y)/max(np.dot(x,x),1e-12))
    fits.append((float(np.mean((y-gain*x)**2)),lag,gain))
error,lag,gain=min(fits)
begin=max(0,-lag);end=min(len(voice),len(inst)-lag)
residual=np.zeros_like(voice)
residual[begin:end]=voice[begin:end]-gain*inst[begin+lag:end+lag]
block=rate//30
count=len(residual)//block
envelope=np.sqrt(np.mean(residual[:count*block].reshape(count,block)**2,axis=1))
envelope=np.convolve(envelope,np.ones(3)/3,mode="same")
mouth=np.zeros(6368,dtype=np.float64)
weights={"あ":1,"い":.45,"う":.55,"え":.75,"お":.7}
for actor in cfg["performers"]:
    motion=module.File();motion.load(filepath=actor["motion"])
    current=np.zeros_like(mouth)
    for name,weight in weights.items():
        keys=motion.shapeKeyAnimation.get(name,[])
        if keys:
            current+=weight*np.interp(np.arange(len(mouth)),[k.frame_number for k in keys],[k.weight for k in keys])
    mouth+=current
mouth=np.convolve(mouth,np.ones(3)/3,mode="same")
scores=[]
for offset in range(0,601):
    n=min(count,len(mouth)-offset)
    x=mouth[offset:offset+n]
    y=envelope[:n]
    scores.append({"offset_source_frames":offset,"offset_seconds":offset/30,"correlation":float(np.corrcoef(x,y)[0,1])})
best=sorted(scores,key=lambda x:x["correlation"],reverse=True)[:12]
report={"method":"least-squares instrumental cancellation then mouth-envelope correlation; not source-engine timecode or manual beat sync","instrumental_fit_lag_samples_12khz":lag,"instrumental_gain":gain,"fit_mean_square_error":error,"best_candidates":best,"scores":scores,"manual_sync_claimed":False}
args.output.parent.mkdir(parents=True,exist_ok=True)
with args.output.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!="scores"},indent=2))
