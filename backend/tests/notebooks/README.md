# Notebooks

To ensure notebooks can import the backend package `app.*` after the repository restructure, add this cell at the very top of your notebooks (already added to some OCR notebooks):

```python
# Bootstrap sys.path to include backend root for `import app.*`
import sys
from pathlib import Path
cwd = Path.cwd()
backend = None
p = cwd
for _ in range(6):
    if (p / 'app').exists():
        backend = p
        break
    if (p / 'backend' / 'app').exists():
        backend = p / 'backend'
        break
    p = p.parent
if backend and str(backend) not in sys.path:
    sys.path.insert(0, str(backend))
print('✅ sys.path[0]=', sys.path[0])
```

Notes:
- This walks up the folder tree to locate a directory that contains `app/` (the backend root) and prepends it to `sys.path`.
- No external dependencies are required.
- If you use environment variables from `.env`, prefer launching Jupyter via `backend/start_jupyter.sh` so it starts in the backend directory and inherits your shell environment.
