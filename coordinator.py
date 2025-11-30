# coordinator.py 
from agents.interface_agent import InterfaceAgent
from agents.emotion_agent import EmotionAgent
from agents.calendar_agent import CalendarAgent
from agents.feedback_agent import FeedbackAgent
from uninformed_search import bfs_schedule, calculate_stress_slots
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)

class Coordinator:
    def __init__(self, use_dr4: bool = True):
        self.use_dr4 = use_dr4
        self.agents_initialized = False
        self._initialize_agents()

    def _initialize_agents(self):
        """Inicialização robusta de todos os agentes"""
        try:
            self.interface = InterfaceAgent()
            logger.info("InterfaceAgent initialized successfully")
        except Exception as e:
            logger.exception("Falha inicializando InterfaceAgent: %s", e)
            self.interface = None

        try:
            self.emotion = EmotionAgent()
            logger.info("EmotionAgent initialized successfully")
        except Exception as e:
            logger.exception("Falha inicializando EmotionAgent: %s", e)
            self.emotion = None

        try:
            self.calendar = CalendarAgent()
            if self.calendar.calendar:
                logger.info("CalendarAgent initialized successfully")
            else:
                logger.warning("CalendarAgent running in fallback mode")
        except Exception as e:
            logger.exception("Falha inicializando CalendarAgent: %s", e)
            self.calendar = None

        try:
            self.feedback = FeedbackAgent()
            # VERIFICAR SE OPENROUTER ESTÁ DISPONÍVEL
            if self.feedback.openrouter_available:
                logger.info("✅ FeedbackAgent initialized with OpenRouter support")
            else:
                logger.warning("⚠️ FeedbackAgent running in heuristic mode (no OpenRouter)")
            logger.info("FeedbackAgent initialized successfully")
        except Exception as e:
            logger.exception("Falha inicializando FeedbackAgent: %s", e)
            self.feedback = None
            
        self.agents_initialized = True

    def _extract_emotion_scores(self, emo_obj: Any) -> Dict[str, Any]:
        """Extrai scores emocionais de forma robusta"""
        out = {"stress_score": 0.0, "valence": 0.0, "dominant": None, "raw": emo_obj}
        
        try:
            if not emo_obj:
                return out
                
            if isinstance(emo_obj, dict):
                # Tentar diferentes estruturas possíveis
                if "emotion" in emo_obj:
                    emo = emo_obj["emotion"]
                    out["stress_score"] = float(emo.get("stress_score", 0.0) or 0.0)
                    out["valence"] = float(emo.get("valence", 0.0) or 0.0)
                    out["dominant"] = emo.get("dominant")
                elif "stress_score" in emo_obj:
                    out["stress_score"] = float(emo_obj.get("stress_score", 0.0) or 0.0)
                    out["valence"] = float(emo_obj.get("valence", 0.0) or 0.0)
                    out["dominant"] = emo_obj.get("dominant")
                elif "raw" in emo_obj and "emotion" in emo_obj["raw"]:
                    # Estrutura aninhada
                    emo = emo_obj["raw"]["emotion"]
                    out["stress_score"] = float(emo.get("stress_score", 0.0) or 0.0)
                    out["valence"] = float(emo.get("valence", 0.0) or 0.0)
                    out["dominant"] = emo.get("dominant")
                    
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning("Error extracting emotion scores: %s", e)
            
        return out

    def _safe_generate_feedback(self, emotion_summary: Dict[str, float], calendar_suggestions: List[str]) -> Dict[str, Any]:
        """Geração segura de feedback com prioridade para LLM"""
        default_response = {
            "recommendations": [
                {
                    "type": "immediate",
                    "text": "Faz uma pausa de 5 minutos e respira profundamente.",
                    "why": "Pausas curtas ajudam a reduzir o stress e melhorar o foco."
                },
                {
                    "type": "short_term", 
                    "text": "Organiza as tuas tarefas por prioridade.",
                    "why": "Priorização ajuda a gerir melhor o tempo e reduzir a ansiedade."
                },
                {
                    "type": "professional",
                    "text": "Mantém um diário das tuas emoções e progresso.",
                    "why": "Auto-reflexão promove bem-estar mental a longo prazo."
                }
            ],
            "follow_up_prompt": "Como te sentes após estas sugestões?",
            "source": "Heuristic"
        }
        
        if not self.feedback:
            logger.warning("FeedbackAgent não disponível - usando fallback")
            return default_response
            
        try:
            # Tentar LLM OpenRouter via craft_message (síncrono)
            logger.info("Tentando gerar feedback com LLM...")
            result = self.feedback.craft_message(emotion_summary, calendar_suggestions, "")
            
            if isinstance(result, dict) and result.get("recommendations"):
                logger.info(f"✅ LLM respondeu com sucesso! Fonte: {result.get('source', 'unknown')}")
                # Forçar source para LLM se veio do OpenRouter
                if "openrouter" in str(result.get("source", "")).lower():
                    result["source"] = "LLM (OpenRouter)"
                else:
                    result["source"] = "LLM"
                return result
            else:
                logger.warning("Resposta do LLM inválida - usando fallback")
                return default_response
                
        except Exception as e:
            logger.error(f"❌ Erro no LLM: {e} - usando fallback heurístico")
            # Tentar fallback heurístico do próprio FeedbackAgent
            try:
                heuristic_result = self.feedback._heuristic_feedback(emotion_summary, calendar_suggestions)
                heuristic_result["source"] = "Heuristic (Fallback)"
                return heuristic_result
            except Exception as heuristic_error:
                logger.error(f"❌ Fallback heurístico também falhou: {heuristic_error}")
                return default_response

    def _extract_tasks_from_text(self, text: str, slots: Dict) -> List[str]:
        """Extrai tarefas do texto do usuário"""
        tasks = []
        
        # Primeiro tentar slots do interface agent
        if isinstance(slots, dict) and slots.get("tasks"):
            task_data = slots["tasks"]
            if isinstance(task_data, list):
                tasks.extend([str(task) for task in task_data if task])
        
        # Fallback: extração por keywords
        lower_text = text.lower()
        
        study_keywords = ["estudar", "estudo", "revisar", "ler", "aprender"]
        project_keywords = ["projeto", "trabalho", "assignment", "tarefa"]
        exercise_keywords = ["exercício", "correr", "ginásio", "yoga", "desporto"]
        
        if any(keyword in lower_text for keyword in study_keywords):
            tasks.append("Estudo/Revisão")
        if any(keyword in lower_text for keyword in project_keywords):
            tasks.append("Trabalho de Projeto")
        if any(keyword in lower_text for keyword in exercise_keywords):
            tasks.append("Exercício Físico")
            
        # Default tasks se nenhuma for detectada
        if not tasks:
            tasks = ["Estudo", "Revisão", "Exercícios", "Planeamento"]
            
        return tasks[:4]  # Limitar a 4 tarefas

    def handle_text(self, text: str) -> Dict[str, Any]:
        """Processa texto do usuário e retorna análise completa"""
        if not text or not text.strip():
            return self._get_empty_response()
            
        try:
            # Extrair intenção
            if self.interface:
                intent_result = self.interface.extract_intent(text)
                if isinstance(intent_result, dict):
                    intent = intent_result
                else:
                    intent = {"raw_text": text, "slots": {}, "confidence": 0.0}
            else:
                intent = {"raw_text": text, "slots": {}, "confidence": 0.0}

            raw_text = intent.get("raw_text", text)
            slots = intent.get("slots", {})

            # Análise emocional
            emo_raw = {}
            if self.emotion:
                try:
                    emo_raw = self.emotion.classify(raw_text)
                except Exception as e:
                    logger.warning("Emotion classification failed: %s", e)

            emo = self._extract_emotion_scores(emo_raw)
            stress_score = max(0.0, min(1.0, emo.get("stress_score", 0.0)))
            valence = max(0.0, min(1.0, emo.get("valence", 0.0)))

            # Obter eventos do calendário
            events = []
            if self.calendar:
                try:
                    events = self.calendar.get_upcoming_events(days=3)  # Próximos 3 dias
                except Exception as e:
                    logger.warning("Calendar events fetch failed: %s", e)

            # Extrair e agendar tarefas
            tasks = self._extract_tasks_from_text(raw_text, slots)
            available_slots = calculate_stress_slots(float(stress_score))
            
            try:
                schedule = bfs_schedule(tasks, available_slots) or []
            except Exception as e:
                logger.warning("Scheduling failed: %s", e)
                schedule = [f"Tarefa: {task}" for task in tasks[:available_slots]]

            # Gerar feedback
            emotion_summary = {
                "stress_score": stress_score, 
                "valence": valence, 
                "dominant": emo.get("dominant")
            }
    
            calendar_suggestions = []
            if self.calendar and hasattr(self.calendar, "suggest_plan"):
                try:
                    calendar_suggestions = self.calendar.suggest_plan(emotion_summary, events) or []
                except Exception as e:
                    logger.warning("Calendar suggestions failed: %s", e)

            message_obj = self._safe_generate_feedback(emotion_summary, calendar_suggestions)

            # Construir resposta final
            response = {
                "emotion": {
                    "stress_score": round(stress_score, 3),
                    "valence": round(valence, 3),
                    "dominant": emo.get("dominant", "unknown"),
                },
                "optimized_schedule": {
                    "schedule": schedule, 
                    "available_slots": available_slots,
                    "total_tasks": len(tasks)
                },
                "events": events[:5],  # Limitar a 5 eventos
                "message": message_obj,
                "raw_intent": intent,
                "raw_emotion": emo_raw,
                "success": True
            }
            return response

        except Exception as e:
            logger.exception("Error in handle_text: %s", e)
            return self._get_error_response(str(e))

    def _get_empty_response(self) -> Dict[str, Any]:
        """Resposta para input vazio"""
        return {
            "emotion": {"stress_score": 0.0, "valence": 0.0, "dominant": "unknown"},
            "optimized_schedule": {"schedule": [], "notes": "No input provided"},
            "events": [],
            "message": {"recommendations": [], "follow_up_prompt": "Please provide some input.", "source": "System"},
            "success": False
        }

    def _get_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Resposta para erro"""
        return {
            "emotion": {"stress_score": 0.0, "valence": 0.0, "dominant": "unknown"},
            "optimized_schedule": {"schedule": [], "notes": f"Error: {error_msg}"},
            "events": [],
            "message": {
                "recommendations": [{
                    "type": "immediate",
                    "text": "Ocorreu um erro. Por favor, tenta novamente.",
                    "why": "Erro temporário do sistema"
                }],
                "follow_up_prompt": "Desculpa pelo inconveniente. Podes tentar novamente?",
                "source": "System"
            },
            "success": False
        }