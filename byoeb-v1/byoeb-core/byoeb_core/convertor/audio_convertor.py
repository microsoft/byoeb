import io
from gtts import gTTS
from pydub import AudioSegment

def text_to_wav_bytes(text: str) -> bytes:
    """
    Convert text to speech in WAV format and return it as bytes.

    :param text: The text to convert to speech.
    :return: WAV audio data as bytes.
    """
    # Generate TTS audio in MP3 format
    tts = gTTS(text)
    temp_mp3_buffer = io.BytesIO()
    tts.write_to_fp(temp_mp3_buffer)
    temp_mp3_buffer.seek(0)  # Reset buffer to the beginning

    # Convert MP3 to WAV format in-memory
    audio = AudioSegment.from_file(temp_mp3_buffer, format="mp3")
    wav_buffer = io.BytesIO()
    audio.export(wav_buffer, format="wav")
    wav_buffer.seek(0)  # Reset buffer to the beginning

    return wav_buffer.read()

def wav_to_ogg_opus_bytes(wav_bytes: bytes) -> bytes:
    """
    Convert WAV audio bytes to OGG format with OPUS codec.

    :param wav_bytes: Input audio data in WAV format as bytes.
    :return: Converted audio data in OGG OPUS format as bytes.
    """
    # Load WAV bytes into an AudioSegment
    wav_buffer = io.BytesIO(wav_bytes)
    audio = AudioSegment.from_file(wav_buffer, format="wav")
    
    # Convert to OGG OPUS in-memory
    ogg_buffer = io.BytesIO()
    audio.export(ogg_buffer, format="ogg", codec="libopus")
    ogg_buffer.seek(0)  # Reset buffer to the beginning

    return ogg_buffer.read()

def ogg_opus_to_wav_bytes(ogg_bytes: bytes) -> bytes:
    """
    Convert OGG audio bytes with OPUS codec to WAV format.

    :param ogg_bytes: Input audio data in OGG OPUS format as bytes.
    :return: Converted audio data in WAV format as bytes.
    """
    # Load OGG bytes into an AudioSegment
    ogg_buffer = io.BytesIO(ogg_bytes)
    audio = AudioSegment.from_file(ogg_buffer, format="ogg")
    
    # Convert to WAV in-memory
    wav_buffer = io.BytesIO()
    audio.export(wav_buffer, format="wav")
    wav_buffer.seek(0)  # Reset buffer to the beginning

    return wav_buffer.read()
