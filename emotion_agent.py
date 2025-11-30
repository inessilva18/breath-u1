# agents/emotion_agent.py
from typing import Dict, Any, List, Optional
import logging
import os
import importlib
import re

logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)


class EmotionAgent:
    """
    Emotion classifier that uses a HuggingFace pipeline (lazy init) or a heuristic fallback.
    Returns dict: {"raw": [...], "emotion": {"stress_score": float, "valence": float, "dominant": str}}
    """

    def __init__(self, model_name: Optional[str] = None, use_hf: Optional[bool] = None):
        self.model_name = model_name
        env_use_hf = os.getenv("USE_HF")
        if use_hf is None:
            if env_use_hf is not None:
                use_hf = not (env_use_hf.strip() in ("0", "false", "False", "no", "n"))
            else:
                use_hf = False  # Mudar para False para forçar heurístico
        self._use_hf = bool(use_hf)
        self.pipeline = None
        self._pipeline_initialized = False

        logger.info(f"EmotionAgent inicializado (use_hf={self._use_hf})")

    def _ensure_pipeline_initialized(self) -> bool:
        """Inicializa o pipeline apenas quando necessário e uma vez (lazy import)."""
        if self._pipeline_initialized:
            return self.pipeline is not None

        # se o utilizador explicitamente desativou HF, não tentamos importar
        if not self._use_hf:
            self._pipeline_initialized = True
            logger.info("Uso de HF desativado (flag). Pulando inicialização do pipeline.")
            return False

        try:
            # IMPORT LAZY: só aqui tentamos carregar transformers (pode demorar)
            logger.info("Tentando importar 'transformers' de forma lazy...")
            transformers = importlib.import_module("transformers")
            pipeline_fn = getattr(transformers, "pipeline", None)
            if pipeline_fn is None:
                logger.warning("'transformers' não tem atributo 'pipeline'. Desativando HF.")
                self._use_hf = False
                self._pipeline_initialized = True
                return False

            model = self.model_name or "joeddav/distilbert-base-uncased-go-emotions-student"
            logger.info(f"Inicializando pipeline HF com modelo: {model}")

            # Usar device=-1 para forçar CPU e evitar problemas de GPU
            # Chamar pipeline a partir do objecto importado
            self.pipeline = pipeline_fn(
                "text-classification",
                model=model,
                top_k=5,
                device=-1
            )

            self._pipeline_initialized = True
            logger.info("Pipeline HF inicializado com sucesso")
            return True

        except Exception as exc:
            logger.exception("Falha ao inicializar pipeline HF; usando heurística. %s", exc)
            self.pipeline = None
            self._use_hf = False
            self._pipeline_initialized = True
            return False

    def classify(self, text: str) -> Dict[str, Any]:
        text = text or ""

        self._use_hf = False  # Forçar heurístico sempre

        # Tentar HF apenas se texto for suficientemente longo E se HF estiver ativo
        if self._use_hf and len(text.strip()) > 5:
            try:
                if self._ensure_pipeline_initialized() and self.pipeline:
                    hf_result = self._classify_with_hf(text)
                    stress_score = hf_result['emotion']['stress_score']
                    if stress_score < 0.3:  # Se HF der score muito baixo
                        logger.warning(f"HF deu score baixo ({stress_score}), usando heurístico")
                        return self._classify_heuristic(text)
                    return hf_result
            except Exception as exc:
                logger.warning("Classificação HF falhou, usando fallback: %s", exc)

        # Fallback para heurística (sempre ativo agora)
        return self._classify_heuristic(text)

    def _classify_with_hf(self, text: str) -> Dict[str, Any]:
        """Classificação usando Hugging Face"""
        try:
            results = self.pipeline(text, truncation=True, top_k=5)
            flat: List[Dict[str, Any]] = []

            # Aplanar resultados
            if isinstance(results, list) and results:
                if isinstance(results[0], list):
                    for item in results:
                        if isinstance(item, list):
                            flat.extend(item)
                        else:
                            flat.append(item)
                else:
                    flat = results.copy()
            else:
                flat = [results]

            # Labels mais específicos para o modelo escolhido
            stress_labels = {"anger", "sadness", "fear", "annoyance", "disapproval", "disappointment", "nervousness"}
            valence_labels = {"joy", "love", "approval", "admiration", "optimism", "excitement"}

            stress = sum(
                float(r.get("score", 0.0))
                for r in flat
                if isinstance(r.get("label", ""), str) and r.get("label", "").lower() in stress_labels
            )

            valence = sum(
                float(r.get("score", 0.0))
                for r in flat
                if isinstance(r.get("label", ""), str) and r.get("label", "").lower() in valence_labels
            )

            dominant = None
            if flat:
                try:
                    dominant = max(flat, key=lambda r: float(r.get("score", 0.0))).get("label")
                except Exception:
                    dominant = None

            return {
                "raw": flat,
                "emotion": {
                    "stress_score": min(1.0, float(stress)),
                    "valence": min(1.0, float(valence)),
                    "dominant": dominant,
                },
            }
        except Exception as exc:
            logger.exception("Erro durante classificação HF: %s", exc)
            raise  # Re-levanta a exceção para cair no fallback

    def _classify_heuristic(self, text: str) -> Dict[str, Any]:
        """Fallback heurístico MELHORADO para stress alto - AGORA MAIS SENSÍVEL"""
        lower = text.lower()
        stress = 0.0
        valence = 0.0
        dominant = None

        stress_indicators = [
            # Stress geral
            "stress", "stressado", "estressado", "estressada", "tensão", "tenso", "tensa",
            # Ansiedade
            "ansios", "ansiedade", "ansioso", "ansiosa", "nervos", "nervoso", "nervosa", "nervousness",
            "preocupad", "preocupado", "preocupada", "angustia", "angústia", "angustiado", "angustiada",
            # Medo/Pânico
            "medo", "tem medo", "assustado", "assustada", "pânico", "ataque de pânico", "aterrorizado",
            # Sobrecarga
            "sobrecarreg", "sobrecarregado", "sobrecarregada", "pressão", "deadline", "prazo", "prazos",
            "exame", "teste", "prova", "exaust", "exausto", "exausta", "esgotado", "esgotada", "faculdade", "universidade",
            # Sintomas físicos
            "não consigo dormir", "insônia", "insonia", "coração acelerado", "suor frio",
            "não consigo respirar", "falta de ar", "tremor", "tremores", "cansado", "cansada",
            # Desespero
            "desesperado", "desesperada", "sem esperança", "não aguento mais", "no limite",
            "fatigado", "fatigada", "esgotamento",
            # Irritação
            "irritado", "irritada", "zangado", "zangada", "raiva", "furioso", "furiosa",
            # Overwhelm
            "sobrecarregado", "sobrecarregada", "não dou conta", "muito para fazer",
            "muitas tarefas", "muito trabalho", "muita pressão", "muitos exames", "muitos trabalhos"
        ]
        
        valence_indicators = [
            "feliz", "alegre", "bom", "boa", "satisfeito", "satisfeita", "alegria",
            "joy", "happy", "love", "content", "contente", "bem", "optimista", "otimista",
            "grato", "grata", "sorridente", "sorriso", "entusiasmado", "entusiasmada",
            "animado", "animada", "felicidade", "prazer", "diversão", "brincar"
        ]

        stress_count = 0
        for w in stress_indicators:
            if w in lower:
                # Dar mais peso a palavras mais fortes
                if w in ["ataque de pânico", "não aguento mais", "no limite", "desesperado", "desesperada"]:
                    stress_count += 4
                elif w in ["exausto", "exausta", "esgotado", "esgotada", "sobrecarregado", "sobrecarregada"]:
                    stress_count += 3
                elif w in ["ansiedade", "pânico", "angústia", "nervousness"]:
                    stress_count += 2
                else:
                    stress_count += 1

        valence_count = sum(1 for w in valence_indicators if w in lower)


        if stress_count > 0:
            # Base mais alta + incremento mais agressivo
            base_stress = 0.5  # Base mais alta
            increment = 0.15   # Incremento mais agressivo
            stress = min(1.0, base_stress + (stress_count * increment))
            
            # Bónus para múltiplos indicadores fortes
            if stress_count >= 6:
                stress = min(1.0, stress + 0.3)
            elif stress_count >= 4:
                stress = min(1.0, stress + 0.2)
            elif stress_count >= 2:
                stress = min(1.0, stress + 0.1)
                
        # Se não detetou stress mas tem palavras específicas, dar mínimo
        elif any(word in lower for word in ["stress", "ansiedade", "preocupado", "sobrecarregado"]):
            stress = 0.4

        if valence_count > 0:
            valence = min(0.9, 0.3 + (valence_count * 0.1))

        # 🔥 DETETOR DE FRASES ESPECÍFICAS DE STRESS ALTO
        high_stress_phrases = [
            r"estou\s+muito\s+stressado",
            r"muitos\s+exames",
            r"muitos\s+trabalhos", 
            r"sinto.me\s+sobrecarregado",
            r"sinto.me\s+sobrecarregada",
            r"sinto.me\s+cansado",
            r"sinto.me\s+cansada",
            r"não\s+aguento\s+mais",
            r"estou\s+no\s+limite",
            r"ataque\s+de\s+pânico",
            r"não\s+consigo\s+respirar",
            r"coração\s+acelerado",
            r"vou\s+ter\s+um\s+ataque",
            r"não\s+vejo\s+solução",
            r"estou\s+desesperado",
            r"estou\s+desesperada"
        ]
        
        for phrase in high_stress_phrases:
            if re.search(phrase, lower):
                stress = max(stress, 0.7)  # Mínimo 0.7 se detetar estas frases
                break

        # Determinar emoção dominante
        if stress > 0.7:
            dominant = "alto_stress"
        elif stress > 0.4:
            dominant = "stress"
        elif stress > valence:
            dominant = "stress_leve"
        elif valence > stress:
            dominant = "felicidade"
        else:
            dominant = "neutro"

        # 🔥 LOG DETALHADO PARA DEBUGGING
        logger.info(f"🔍 Heurístico - Texto: '{text}'")
        logger.info(f"🔍 Heurístico - Stress: {stress:.2f}, Valence: {valence:.2f}, Counts: {stress_count}/{valence_count}")
        logger.info(f"🔍 Heurístico - Dominant: {dominant}")

        return {
            "raw": [],
            "emotion": {
                "stress_score": round(stress, 2),
                "valence": round(valence, 2),
                "dominant": dominant,
            },
        }