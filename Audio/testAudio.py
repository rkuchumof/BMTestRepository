import speech_recognition as sr
from pydub import AudioSegment
import argparse
from tqdm import tqdm
import wave

def transcribe_audio_to_text(audio_file_path, output_file_path):
    # Initialize recognizer
    recognizer = sr.Recognizer()

    # Convert audio file to .wav format using pydub
    audio = AudioSegment.from_file(audio_file_path)
    audio = audio.set_channels(1).set_frame_rate(16000)  # Ensure the format is compatible with the recognizer

    wav_file_path = "converted_audio.wav"
    audio.export(wav_file_path, format="wav")

    # Recognize speech using the audio file
    with wave.open(wav_file_path, "rb") as wf:
        total_frames = wf.getnframes()
        chunk_size = 4000

        # Create a progress bar
        progress_bar = tqdm(total=total_frames, unit="frame", desc="Processing")

        result_text = ""
        while True:
            data = wf.readframes(chunk_size)
            if len(data) == 0:
                break
            if recognizer.AcceptWaveform(data):
                result = recognizer.Result()
                result_text += result
            else:
                result_text += recognizer.PartialResult()
            progress_bar.update(chunk_size)

        progress_bar.close()
        result_text += recognizer.FinalResult()

    # Write the transcription to the output file
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(result_text)
    print("Transcription: ", result_text)

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio files to text.")
    parser.add_argument("input", help="Path to the input audio file")
    parser.add_argument("output", help="Path to the output text file")

    args = parser.parse_args()

    transcribe_audio_to_text(args.input, args.output)

if __name__ == "__main__":
    main()
