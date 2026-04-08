"""Sample: `cd backend` then `python -m scripts.demo_transcription` (with PYTHONPATH=. or venv active)."""

from pathlib import Path

from app.services.transcription_service import transcribe_audio


def main() -> None:
    text = transcribe_audio(Path("sample_meeting_chunk.wav"))
    print(text)


if __name__ == "__main__":
    main()
