import requests, uuid
import os
import azure.cognitiveservices.speech as speechsdk
from datetime import datetime


class translator:
    def __init__(self):
        self.translation_key = os.environ["AZURE_TRANSLATION_KEY"].strip()
        self.translation_endpoint = "https://api.cognitive.microsofttranslator.com"
        self.location = os.environ["AZURE_REGION"].strip()
        self.translation_path = "/translate"
        self.translation_url = self.translation_endpoint + self.translation_path
        self.speech_key = os.environ["AZURE_SPEECH_KEY"].strip()
        self.speech_voice = "female"
        self.voice_dict = {
            "male": {
                "en-IN": "en-IN-PrabhatNeural",
                "hi-IN": "hi-IN-MadhurNeural",
                "kn-IN": "kn-IN-GaganNeural",
                "ta-IN": "ta-IN-ValluvarNeural",
                "te-IN": "te-IN-MohanNeural",
            },
            "female": {
                "en-IN": "en-IN-NeerjaNeural",
                "hi-IN": "hi-IN-SwaraNeural",
                "kn-IN": "kn-IN-SapnaNeural",
                "ta-IN": "ta-IN-PallaviNeural",
                "te-IN": "te-IN-ShrutiNeural",
            },
        }

    def translate_text(self, input_text, source_language, target_language, logger):
        """
        This function translates the given input text from source language to target language.
        """
        if source_language == target_language:
            return input_text
        params = {
            "api-version": "3.0",
            "from": source_language,
            "to": [target_language],
        }

        headers = {
            "Ocp-Apim-Subscription-Key": self.translation_key,
            "Ocp-Apim-Subscription-Region": self.location,
            "Content-type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }

        body = [{"text": input_text}]

        request = requests.post(
            self.translation_url, params=params, headers=headers, json=body
        )
        response = request.json()

        translated_text = response[0]["translations"][0]["text"]
        logger.add_log(
            sender_id="bot",
            receiver_id="bot",
            message_id=None,
            action_type="translate",
            details={
                "source_language": source_language,
                "translated_language": target_language,
                "input text": input_text,
                "translated_text": translated_text,
            },
            timestamp=datetime.now(),
        )

        return translated_text

    def speech_translate_text(self, audio_file, source_language, logger, blob_name):
        """
        This function returns the translated english text from the source language audio.
        """

        # This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"
        speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key, region=self.location
        )
        speech_config.speech_recognition_language = source_language + "-IN"
        audio_config = speechsdk.audio.AudioConfig(filename=audio_file)

        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )

        speech_recognition_result = speech_recognizer.recognize_once_async().get()
        result = speech_recognition_result.text
        logger.add_log(
            sender_id="bot",
            receiver_id="bot",
            message_id=None,
            action_type="speech_to_text",
            details={
                "source_language": "en",
                "blob_name": blob_name,
                "output_text": result,
            },
            timestamp=datetime.now(),
        )

        english_text = self.translate_text(result, source_language, "en", logger)
        return result, english_text

    def text_translate_speech(
        self, english_text, source_audio_language, save_filename, logger
    ):
        """
        This function stores the translated speech into save_filename location.
        It takes as input the english text from gpt and tranlates into the source language audio.
        """

        speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key, region=self.location
        )
        audio_config = speechsdk.audio.AudioOutputConfig(filename=save_filename)
        speech_config.speech_synthesis_voice_name = self.voice_dict[self.speech_voice][
            source_audio_language
        ]
        speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_config
        )

        source_text = self.translate_text(
            english_text, "en", source_audio_language[:2], logger
        )

        speech_synthesizer.speak_text_async(source_text).get()
        logger.add_log(
            sender_id="bot",
            receiver_id="bot",
            message_id=None,
            action_type="text_to_speech",
            details={
                "source_language": source_audio_language[:2],
                "input_text": source_text,
            },
            timestamp=datetime.now(),
        )

        return source_text

    def text_to_speech(self, text, source_audio_language, save_filename):
        speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key, region=self.location
        )
        audio_config = speechsdk.audio.AudioOutputConfig(filename=save_filename)
        speech_config.speech_synthesis_voice_name = self.voice_dict[self.speech_voice][
            source_audio_language
        ]
        speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_config
        )

        speech_synthesizer.speak_text_async(text).get()

        return
