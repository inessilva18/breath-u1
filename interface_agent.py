from typing import Dict, Any, Optional
import re
import logging
import tempfile
import os 

# Tente importar speech_recognition, mas não falhe se não estiver disponível
try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False


logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

class InterfaceAgent:
    """
    Agente de interface responsável por receber entrada do utilizador (texto ou voz),
    normalizar, interpretar e extrair intenções/slots.
    
    - Suporta texto diretamente.
    - Suporte STT usando speech_recognition se disponível.
    """
     
    def __init__(self, llm=None, sst_backend: str = "auto"):
        self.llm = llm
        self.sst_backend = sst_backend
        self.recognizer = None
        if STT_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                logger.info("SpeechRecognition inicializado para STT")
            except Exception as e:
                logger.warning(f"Erro ao inicializar SpeechRecognition: {e}")


    def handle_input(self, text: Optional[str] = None, audio_bytes: Optional[bytes] = None) -> Dict[str, Any]:
        """
        Entrada principal do agente.
        - Se for áudio → STT (se disponível)
        - Se for texto → extrai intenção.
        """

        if audio_bytes is not None:
            if not STT_AVAILABLE or not self.recognizer:
                return {
                    "error": "Speech-to-text not available - install SpeechRecognition",
                    "text": None,
                    "slots": {},
                    "confidence": 0.0
                }
            try:
                transcribed_text = self.transcribe_audio(audio_bytes)
                if transcribed_text and transcribed_text.strip():
                    # Usar texto transcrito como entrada
                    return self.extract_intent(transcribed_text)
                else:
                    return {
                        "error": "Could not transcribe audio",
                        "text": None,
                        "slots": {},
                        "confidence": 0.0
                    }
            except Exception as e:
                logger.error(f"STT error: {e}")
                return {
                    "error": f"Audio processing failed: {str(e)}",
                    "text": None,
                    "slots": {},
                    "confidence": 0.0
                }

        if not text or text.strip() == "":
            logger.error("Entrada vazia ou inválida.")
            return {
                "error": "No input provided",
                "slots": {},
                "confidence": 0.0
            }

        return self.extract_intent(text)
    
    def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcreve áudio para texto usando SpeechRecognition"""
        try:
            # Salvar áudio temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
                temp_audio.write(audio_bytes)
                temp_audio_path = temp_audio.name

            # Usar speech recognition
            with sr.AudioFile(temp_audio_path) as source:
                # Ajustar para ruído ambiente
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.record(source)
                
                # Tentar reconhecimento em Português
                text = self.recognizer.recognize_google(audio, language='pt-PT')
                
            # Limpar ficheiro temporário
            os.unlink(temp_audio_path)
            
            return text
            
        except sr.UnknownValueError:
            logger.warning("Não foi possível entender o áudio")
            return ""
        except sr.RequestError as e:
            logger.error(f"Erro no serviço de STT: {e}")
            return ""
        except Exception as e:
            logger.error(f"Erro inesperado na transcrição: {e}")
            return ""

    def extract_intent(self, text: str) -> Dict[str, Any]:
        """
        Extrai intenção do utilizador com heurísticas simples.
        (Pode ser substituído por LLM no futuro).
        """

        slots = {
            "sleep_hours": None,
            "tasks": [],
            "deadline": None,
            "explicit_emotion": None
        }

        lower = text.lower()

        
        sleep_match = re.search(r"(\d+)\s*(h|horas)", lower)
        if sleep_match:
            slots["sleep_hours"] = int(sleep_match.group(1))

        # Detetar menção a tarefas ou estudo
        if any(word in lower for word in ["estudar", "tarefa", "trabalho", "projeto"]):
            slots["tasks"].append("referência a estudo/trabalho")

        # Deadlines
        if "prazo" in lower or "deadline" in lower:
            slots["deadline"] = True
            if "tem" not in slots["tasks"]:
                slots["tasks"].append("tem prazos")

        # Emoções explícitas
        emotions_map = {
            "stress": "stress",
            "stressado": "stress",
            "ansioso": "ansiedade",
            "ansiosa": "ansiedade",
            "cansado": "cansaço",
            "exausto": "exaustão",
            "triste": "tristeza",
            "feliz": "felicidade",
        }
        for k, v in emotions_map.items():
            if k in lower:
                slots["explicit_emotion"] = v
                break

        # Confidence é fixa por enquanto
        return {
            "raw_text": text,
            "slots": slots,
            "confidence": 0.85
        }

    def is_stt_available(self) -> bool:
        """Verifica se STT está disponível"""
        return self.recognizer is not None and STT_AVAILABLE