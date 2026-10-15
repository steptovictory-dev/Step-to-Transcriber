"""Real Windows device / GPU check, separate from unit tests.

Usage: python tests/smoke_live.py --seconds 15
Play speech through the default Windows output while this check runs.
"""

import argparse
import sys
from pathlib import Path
from threading import Event, Timer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.live import LiveJob, output_devices, run_live


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=15)
    parser.add_argument('--play', type=Path, help='Play a local control WAV through Windows during capture')
    parser.add_argument('--switch-after', type=float, help='Switch from automatic to the same explicit output')
    args = parser.parse_args()
    devices = output_devices()
    for device in devices:
        print(device['name'], 'DEFAULT' if device['default'] else '', flush=True)
    stopped = Event()
    timer = None
    switch_timer = None
    selected = {'name': 'Windows default', 'automatic': True}
    levels = []
    paragraphs = []

    def status(text):
        nonlocal timer, switch_timer
        print(text, flush=True)
        if text.startswith('Слушаем:') and timer is None:
            timer = Timer(args.seconds, stopped.set)
            timer.start()
            if args.play:
                import winsound
                winsound.PlaySound(str(args.play.resolve()), winsound.SND_FILENAME | winsound.SND_ASYNC)
            if args.switch_after:
                def switch():
                    nonlocal selected
                    selected = next(device for device in devices if device['default'])
                switch_timer = Timer(args.switch_after, switch)
                switch_timer.start()

    def paragraph(seconds, text):
        paragraphs.append(text)
        print(f'{seconds:.1f}: {text}', flush=True)

    try:
        run_live(LiveJob({'name': 'Windows default', 'automatic': True},
                         Path(__file__).resolve().parents[2] / 'output' / 'live_smoke'),
                 stopped.is_set, status, paragraph,
                 lambda level, backlog: levels.append(level),
                 lambda paths: print('FILES:', *paths, flush=True), selection=lambda: selected)
    finally:
        if timer:
            timer.cancel()
        if switch_timer:
            switch_timer.cancel()
        if args.play:
            import winsound
            winsound.PlaySound(None, 0)
    print(f'Capture blocks: {len(levels)}; peak RMS: {max(levels, default=0):.5f}; paragraphs: {len(paragraphs)}')


if __name__ == '__main__':
    main()
