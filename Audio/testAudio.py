import os
import wave
import json
import argparse
from pydub import AudioSegment
from vosk import Model, KaldiRecognizer

def transcribe_audio_to_text(audio_file_path, output_file_path, model_path):
    # Convert audio file to .wav format using pydub
    audio = AudioSegment.from_file(audio_file_path)
    audio = audio.set_channels(1).set_frame_rate(16000)  # Ensure the format is compatible with the recognizer

    wav_file_path = "converted_audio.wav"
    audio.export(wav_file_path, format="wav")

    # Load Vosk model
    if not os.path.exists(model_path):
        print(f"Model path {model_path} does not exist.")
        return

    model = Model(model_path)
    recognizer = KaldiRecognizer(model, 16000)

    # Read the audio file
    with wave.open(wav_file_path, "rb") as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
            print("Audio file must be WAV format mono PCM.")
            return

        result_text = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if recognizer.AcceptWaveform(data):
                result = recognizer.Result()
                result_text += json.loads(result).get("text", "") + " "
            else:
                partial_result = recognizer.PartialResult()
                result_text += json.loads(partial_result).get("partial", "") + " "

        final_result = recognizer.FinalResult()
        result_text += json.loads(final_result).get("text", "")

    # Write the transcription to the output file
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(result_text.strip())
    print("Transcription: ", result_text.strip())

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio files to text.")
    parser.add_argument("input", help="Path to the input audio file")
    parser.add_argument("output", help="Path to the output text file")
    parser.add_argument("model", help="Path to the Vosk model directory")

    args = parser.parse_args()

    transcribe_audio_to_text(args.input, args.output, args.model)

if __name__ == "__main__":
    main()
