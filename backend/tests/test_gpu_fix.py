import sys, time, os
sys.path.insert(0, '.')
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'expandable_segments:True')

import torch
torch.backends.cudnn.benchmark = False

import psutil
print(f'RAM available: {psutil.virtual_memory().available/1e9:.2f} GB')
print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}')
free, total = torch.cuda.mem_get_info(0)
print(f'VRAM free: {free/1e9:.2f} GB / {total/1e9:.2f} GB')

t0 = time.time()
import easyocr
reader = easyocr.Reader(
    ['ta', 'en'], gpu=True,
    model_storage_directory='../models/indic-ocr',
    download_enabled=True, verbose=False
)
t1 = time.time()
print(f'EasyOCR GPU loaded in {t1-t0:.2f}s')
free2, _ = torch.cuda.mem_get_info(0)
print(f'VRAM after load: {(total-free2)/1e9:.3f} GB used, {free2/1e9:.2f} GB free')
print(f'GPU flag: {reader.gpu}')

import numpy as np, cv2
dummy = (np.ones((1000, 700, 3), dtype=np.uint8) * 240)
t2 = time.time()
results = reader.readtext(dummy, batch_size=16)
t3 = time.time()
print(f'OCR inference: {(t3-t2)*1000:.0f}ms, blocks: {len(results)}')
print(f'VRAM peak allocated: {torch.cuda.max_memory_allocated()/1e9:.3f} GB')
print('GPU OCR: SUCCESS' if reader.gpu else 'GPU OCR: FALLBACK to CPU')
