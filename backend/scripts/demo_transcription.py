"""Sample: `cd backend` then `python -m scripts.demo_transcription` (with PYTHONPATH=. or venv active)."""

from pathlib import Path

from app.services.transcription_service import transcribe_audio


def main() -> None:
    result = transcribe_audio(Path("sample_meeting_chunk.wav"))
    print(f"Language: {result.language} | Duration: {result.duration_ms} ms")
    print(result.text)
    for seg in result.segments[:5]:
        print(f"  [{seg.start_ms/1000:6.2f}s] {seg.speaker_label}: {seg.text}")


if __name__ == "__main__":
    main()
