from typing import Any
import azure.cognitiveservices.speech as speechsdk
from byoeb_core.translators.speech.base import BaseSpeechTranslator

class AsyncAzureSpeechTranslator(BaseSpeechTranslator):
    __voice_dict = {
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
    def __init__(self,
        region,
        key=None,
        token_provider=None,
        resource_id=None,
        speech_voice: str = "female",
        country_code: str = "IN",
        **kwargs
    ):
        if region is None:
            raise ValueError("region must be provided")
        if token_provider is None and key is None:
            raise ValueError("Either token_provider or key must be provided with region")
        if token_provider is not None and resource_id is None:
            raise ValueError("resource_id must be provided with token_provider")
        self.__key = key
        self.__region = region
        self.__speech_voice = speech_voice
        self.__token_provider = token_provider
        self.__resource_id = resource_id
        self.__country_code = f"-{country_code.upper()}"

    def speech_to_text(
        self,
        audio_file: str,
        source_language: str, 
        **kwargs
    ) -> Any:
        raise NotImplementedError
    
    async def aspeech_to_text(
        self,
        audio_data: bytes,
        source_language: str,
        **kwargs
    ) -> str:
        speech_config = self.__get_speech_config()
        speech_config.speech_recognition_language =  f"{source_language}-IN"
        # Create a push stream
        push_stream = speechsdk.audio.PushAudioInputStream()
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

        # Create speech recognizer with audio stream
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )
        try:
            # Push audio bytes to the stream
            push_stream.write(audio_data)
            push_stream.close()

            # Perform speech recognition
            result = speech_recognizer.recognize_once_async().get()
            return result.text
        except Exception as e:
            raise RuntimeError(f"Error in speech recognition: {e}")
        
    def text_to_speech(
        self,
        input_text: str,
        source_language: str,
        **kwargs
    ) -> Any:
        raise NotImplementedError

    async def atext_to_speech(
        self,
        input_text: str,
        source_language: str,
        **kwargs
    ) -> bytes:
        speech_config = self.__get_speech_config()
        speech_config.speech_synthesis_voice_name = self.__voice_dict[self.__speech_voice][source_language + self.__country_code]

        # Create a pull audio output stream
        pull_stream = speechsdk.audio.PullAudioOutputStream()

        # Configure the audio output to use the pull stream
        audio_config = speechsdk.audio.AudioOutputConfig(stream=pull_stream)

        # Create the speech synthesizer
        speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_config
        )

        try:
            # Perform text-to-speech synthesis
            result = speech_synthesizer.speak_text_async(input_text).get()
            audio_bytes: bytes = result.audio_data
            return audio_bytes
        except Exception as e:
            raise RuntimeError(f"Error in text-to-speech: {e}")
    
    def __get_speech_config(self):
        if self.__token_provider is not None:
            auth_token = "aad#" + self.__resource_id + "#" + self.__token_provider()
            return speechsdk.SpeechConfig(
                auth_token=auth_token, region=self.__region
            )
        return speechsdk.SpeechConfig(
            subscription=self.__key, region=self.__region
        )
    def change_speech_voice(
        self,
        speech_voice: str
    ):
        self.__speech_voice = speech_voice

    def change_voice_dict(
        self,
        voice_dict: dict
    ):
        self.__voice_dict = voice_dict