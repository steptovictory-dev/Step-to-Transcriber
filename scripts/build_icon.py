"""Package the approved PNG as a Windows ICO containing multiple resolutions."""

from pathlib import Path

from PIL import Image


ASSETS = Path(__file__).resolve().parents[1] / 'assets'
SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


if __name__ == '__main__':
    destination = ASSETS / 'step-to-transcriber.ico'
    with Image.open(ASSETS / 'step-to-transcriber.png') as original:
        original.convert('RGBA').save(destination, format='ICO', sizes=[(size, size) for size in SIZES])
    with Image.open(destination) as saved:
        assert saved.ico.sizes() == {(size, size) for size in SIZES}
    print(f'{destination}: {len(SIZES)} resolutions')
