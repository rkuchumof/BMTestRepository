import speech_recognition as sr
from pydub import AudioSegment
import argparse

def transcribe_audio_to_text(audio_file_path, output_file_path):
    # Initialize recognizer
    recognizer = sr.Recognizer()

    # Convert audio file to .wav format using pydub
    audio = AudioSegment.from_file(audio_file_path)
    audio = audio.set_channels(1).set_frame_rate(16000)  # Ensure the format is compatible with the recognizer

    wav_file_path = "converted_audio.wav"
    audio.export(wav_file_path, format="wav")

    # Recognize speech using the audio file
    with sr.AudioFile(wav_file_path) as source:
        audio_data = recognizer.record(source)

        try:
            # Recognize speech using Google Web Speech API
            text = recognizer.recognize_google(audio_data, language="ru-RU")
            print("Transcription: ", text)
            # Write the transcription to the output file
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(text)
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
        except sr.RequestError as e:
            print("Could not request results from Google Speech Recognition service; {0}".format(e))

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio files to text.")
    parser.add_argument("input", help="Path to the input audio file")
    parser.add_argument("output", help="Path to the output text file")

    args = parser.parse_args()

    transcribe_audio_to_text(args.input, args.output)

if __name__ == "__main__":
    main()
