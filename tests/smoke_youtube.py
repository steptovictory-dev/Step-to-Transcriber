"""Explicit network/GPU smoke test using a user-supplied video URL."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline import Job, run_job


if __name__ == '__main__':
    job = Job(sys.argv[1], Path(__file__).resolve().parents[2] / 'output', youtube=True)
    previous = [-1]

    def progress(value):
        percent = int(value * 100)
        if percent // 10 != previous[0] // 10:
            print(f'Progress: {percent}%', flush=True)
            previous[0] = percent

    result = run_job(job, lambda text: print(text, flush=True), progress, lambda: False)
    print(f'TXT: {result.txt}\nMarkdown: {result.markdown}', flush=True)
