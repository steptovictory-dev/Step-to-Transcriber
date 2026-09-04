from pathlib import Path

from src.transcriber import TranscriptSegment
from src.exporters import export_markdown, export_txt


segments = [
    TranscriptSegment(
        start=4.2,
        end=8.7,
        text='Сегодня мы рассмотрим методы машинного обучения.',
    ),
    TranscriptSegment(
        start=11.5,
        end=16.3,
        text='Начнём с задачи классификации.',
    ),
    TranscriptSegment(
        start=78.4,
        end=83.1,
        text='Теперь рассмотрим функцию потерь.',
    ),
]

txt_path = export_txt(
    segments,
    Path('output/test_transcript.txt'),
)

md_path = export_markdown(
    segments,
    Path('output/test_transcript.md'),
    title='Тестовая лекция',
)

print(f'TXT: {txt_path.resolve()}')
print(f'Markdown: {md_path.resolve()}')