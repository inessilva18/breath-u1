import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

class FeedbackAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("OPENROUTER_MODEL", "alibaba/tongyi-deepresearch-30b-a3b:free")
        self.base_url = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1")
        self.request_timeout = float(os.getenv("OPENROUTER_TIMEOUT", "30.0"))
        self.max_retries = int(os.getenv("OPENROUTER_RETRIES", "3"))
        self.retry_backoff = float(os.getenv("OPENROUTER_BACKOFF", "1.0"))

        if self.api_key:
            self.openrouter_available = True
            logger.info("✅ OpenRouter configurado com sucesso")
            logger.info(f"   Modelo: {self.model}")
        else:
            self.openrouter_available = False
            logger.warning("❌ OpenRouter API key não encontrada - usando fallback heurístico")

    async def generate_feedback(self, emotion_summary: dict, calendar_suggestions: List[str]) -> Dict[str, Any]:
        """Gera feedback usando OpenRouter API ou heurísticas"""
        logger.info(f"Iniciando geração de feedback...")
        logger.info(f"   - Stress: {emotion_summary.get('stress_score')}")
        logger.info(f"   - Valence: {emotion_summary.get('valence')}")
        logger.info(f"   - Emoção: {emotion_summary.get('dominant')}")
        
        if self.openrouter_available:
            logger.info("🔄 Tentando OpenRouter...")
            try:
                result = await self._call_openrouter_with_retries(emotion_summary, calendar_suggestions)
                logger.info("✅ Sucesso com OpenRouter!")
                return result
            except Exception as e:
                logger.error(f"❌ Falha no OpenRouter: {e}")
                logger.info("🔄 Usando fallback heurístico...")
                return self._heuristic_feedback(emotion_summary, calendar_suggestions)
        else:
            logger.warning("🚫 OpenRouter não disponível - usando heurístico")
            return self._heuristic_feedback(emotion_summary, calendar_suggestions)

    async def _call_openrouter_with_retries(self, emotion_summary: dict, calendar_suggestions: List[str]) -> Dict[str, Any]:
        """Tentativas com retry"""
        last_exc = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return await self._call_openrouter(emotion_summary, calendar_suggestions)
            except Exception as e:
                last_exc = e
                backoff = self.retry_backoff * (2 ** (attempt - 1))
                logger.warning(f"Tentativa {attempt}/{self.max_retries} falhou: {e}. Backoff {backoff:.1f}s")
                if attempt < self.max_retries:
                    await asyncio.sleep(backoff)
        logger.error("Todas as tentativas ao OpenRouter falharam.")
        raise last_exc if last_exc is not None else Exception("Unknown OpenRouter error")

    async def _call_openrouter(self, emotion_summary: dict, calendar_suggestions: List[str]) -> Dict[str, Any]:
        """Chama API OpenRouter diretamente via HTTP"""
        url = f"{self.base_url}/chat/completions"
        
        # Headers simples sem caracteres problemáticos
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # System prompt mais simples e direto
        system_prompt = """És um assistente de bem-estar para estudantes. Gera 3 recomendações em formato JSON.

RESPONDE APENAS COM JSON, sem texto extra. Formato:
{
  "recommendations": [
    {"type": "immediate", "text": "texto", "why": "razão"},
    {"type": "short_term", "text": "texto", "why": "razão"},
    {"type": "professional", "text": "texto", "why": "razão"}
  ],
  "follow_up_prompt": "pergunta empática"
}

Usa português de Portugal."""

        user_prompt = (
            f"Estado emocional: Stress {emotion_summary.get('stress_score', 0):.2f}/1.0, "
            f"Valência {emotion_summary.get('valence', 0):.2f}/1.0, "
            f"Emoção: {emotion_summary.get('dominant', 'Não identificada')}. "
            f"Sugestões do calendário: {calendar_suggestions}. "
            "Gera recomendações personalizadas."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 800,
        }

        try:
            timeout = httpx.Timeout(self.request_timeout)
            
            async with httpx.AsyncClient(
                timeout=timeout,
                headers=headers,
                follow_redirects=True
            ) as client:
                
                logger.info(f"Enviando pedido para OpenRouter...")
                
                response = await client.post(url, json=payload)
                
                logger.info(f"Resposta recebida: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"❌ Erro HTTP: {response.status_code}")
                    if response.status_code == 401:
                        raise Exception("API key inválida ou não autorizada")
                    elif response.status_code == 429:
                        raise Exception("Rate limit excedido")
                    else:
                        raise Exception(f"Erro HTTP {response.status_code}")

                data = response.json()
                logger.info(f"✅ Resposta JSON parseada, tipo: {type(data)}")
                
                content = self._extract_content_from_response(data)
                
                if not content:
                    logger.error("❌ Não foi possível extrair conteúdo da resposta")
                    raise Exception("Resposta da API vazia ou inválida")

                logger.info(f"Conteúdo extraído ({len(content)} caracteres): {content[:100]}...")

                result = self._parse_json_response(content)
                
                if not result:
                    logger.error("❌ Não foi possível parsear JSON da resposta")
                    raise Exception("Resposta não contém JSON válido")

                # Validação da estrutura
                if not isinstance(result, dict):
                    logger.error("❌ Resultado não é um dicionário")
                    raise Exception("Formato de resposta inválido")
                    
                if "recommendations" not in result:
                    logger.error("❌ Resposta não contém 'recommendations'")
                    logger.error(f"   Chaves disponíveis: {list(result.keys())}")
                    raise Exception("Estrutura de resposta inválida")

                # Validar recomendações
                recommendations = result.get("recommendations", [])
                if not isinstance(recommendations, list) or len(recommendations) == 0:
                    logger.error("❌ 'recommendations' não é uma lista ou está vazia")
                    raise Exception("Recomendações inválidas")

                logger.info(f"✅ {len(recommendations)} recomendações processadas com sucesso")
                result["source"] = "openrouter"
                return result

        except httpx.RequestError as e:
            logger.error(f"❌ Erro de rede: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Erro na chamada OpenRouter: {e}")
            raise

    def _extract_content_from_response(self, data: Any) -> Optional[str]:
        """Extrai conteúdo da resposta da API de forma flexível"""
        try:
            # Tentar diferentes estruturas comuns de resposta
            if isinstance(data, dict):
                # Estrutura padrão OpenAI
                if "choices" in data and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        return choice["message"]["content"]
                    elif "text" in choice:
                        return choice["text"]
                
                # Estrutura alternativa
                if "content" in data:
                    return data["content"]
                if "text" in data:
                    return data["text"]
                if "output" in data:
                    return data["output"]
                    
            # Se for string, retornar diretamente
            if isinstance(data, str):
                return data
                
            # Última tentativa: converter para string
            return str(data)
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair conteúdo: {e}")
            return None

    def _parse_json_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Parseia resposta JSON de forma robusta"""
        if not content or not isinstance(content, str):
            return None
            
        # Tentar parse direto primeiro
        try:
            result = json.loads(content)
            logger.info("✅ JSON parseado diretamente")
            return result
        except json.JSONDecodeError:
            logger.info("⚠️ Parse direto falhou, tentando extrair JSON...")
            pass
        
        # Múltiplas tentativas de extração JSON
        json_patterns = [
            r'\{[^{}]*\{[^{}]*\{[^{}]*\}[^{}]*\}[^{}]*\}',  # JSON aninhado
            r'\{.*\}',  # Qualquer JSON
            r'\{[^}]+\}',  # JSON simples
        ]
        
        for pattern in json_patterns:
            try:
                import re
                matches = re.findall(pattern, content, re.DOTALL)
                if matches:
                    # Tentar o match mais longo (provavelmente o JSON completo)
                    longest_match = max(matches, key=len)
                    logger.info(f"Tentando parsear JSON extraído ({len(longest_match)} caracteres)")
                    result = json.loads(longest_match)
                    logger.info("✅ JSON extraído com sucesso via regex")
                    return result
            except (json.JSONDecodeError, Exception) as e:
                logger.debug(f"⚠️ Pattern {pattern} falhou: {e}")
                continue
        try:
            
            cleaned_content = content.replace('```json', '').replace('```', '').strip()
            result = json.loads(cleaned_content)
            logger.info("✅ JSON parseado após limpeza")
            return result
        except json.JSONDecodeError:
            logger.error("❌ Todas as tentativas de parse JSON falharam")
            return None

    def craft_message(self, emotion_summary: dict, calendar_suggestions: List[str], user_text: str = "") -> Dict[str, Any]:
        """
        Versão síncrona para integração com o Coordinator/Streamlit.
        """
        logger.info("Iniciando craft_message (síncrono)")
        
        if not self.openrouter_available:
            logger.warning("OpenRouter não disponível em craft_message")
            result = self._heuristic_feedback(emotion_summary, calendar_suggestions)
            result["source"] = "heuristic_fallback"
            return result

        coro = self.generate_feedback(emotion_summary, calendar_suggestions)

        try:
            # Tentar obter loop atual
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Se o loop já está a correr, submeter a tarefa
                logger.info("🔄 Loop já em execução - submetendo tarefa...")
                future = asyncio.run_coroutine_threadsafe(coro, loop)
                result = future.result(timeout=self.request_timeout + 10)
                return result
            else:
                # Se não está a correr, podemos usar run_until_complete
                logger.info("🔄 Criando novo loop...")
                result = loop.run_until_complete(coro)
                return result
        except RuntimeError:
            # Não há loop, criar um novo
            try:
                logger.info("🔄 Criando novo loop com asyncio.run...")
                result = asyncio.run(coro)
                return result
            except Exception as e:
                logger.error(f"❌ Erro ao correr asyncio.run: {e}")
                result = self._heuristic_feedback(emotion_summary, calendar_suggestions)
                result["source"] = "heuristic_fallback"
                return result
        except Exception as e:
            logger.error(f"❌ Erro em craft_message: {e}")
            result = self._heuristic_feedback(emotion_summary, calendar_suggestions)
            result["source"] = "heuristic_fallback"
            return result

    def _heuristic_fallback(self, emotion_summary: dict, calendar_suggestions: List[str]) -> Dict[str, Any]:
        """Fallback heurístico simplificado"""
        logger.warning("Usando fallback heurístico")
        return self._heuristic_feedback(emotion_summary, calendar_suggestions)

    def _heuristic_feedback(self, emotion_summary: dict, calendar_suggestions: List[str]) -> Dict[str, Any]:
        """Heurísticas robustas baseadas em evidências científicas"""
        try:
            stress = float(emotion_summary.get("stress_score", 0.0))
            valence = float(emotion_summary.get("valence", 0.0))
            dominant = str(emotion_summary.get("dominant", "")).lower()
        except (AttributeError, TypeError, ValueError):
            stress, valence, dominant = 0.0, 0.0, ""

        recommendations = []

        if stress > 0.8 or "ansiedade" in dominant or "panic" in dominant:
            recommendations = [
                {
                    "type": "immediate",
                    "text": "TÉCNICA 5-4-3-2-1: Identifica 5 coisas que vês, 4 que tocas, 3 que ouves, 2 que cheiras, 1 que gostas",
                    "why": "Grounding sensorial reduz sintomas de ansiedade aguda"
                },
                {
                    "type": "short_term",
                    "text": "POMODORO: 25min estudo + 5min pausa ativa - 4 ciclos + pausa longa",
                    "why": "Intervalos regulares melhoram foco e reduzem exaustão mental"
                },
                {
                    "type": "professional",
                    "text": "Procura apoio psicológico universitário ou linha de crise local",
                    "why": "Apoio imediato previne escalada de crise emocional"
                }
            ]
        elif stress > 0.6:
            recommendations = [
                {
                    "type": "immediate",
                    "text": "RESPIRAÇÃO 4-7-8: Inspira 4s, segura 7s, expira 8s (3 repetições)",
                    "why": "Respiração diafragmática ativa sistema parassimpático"
                },
                {
                    "type": "short_term",
                    "text": "Priorização por urgência e blocos de estudo",
                    "why": "Reduz sobrecarga decisória"
                },
                {
                    "type": "professional",
                    "text": "Marca consulta no Gabinete de Apoio ao Estudante",
                    "why": "Intervenção precoce ajuda"
                }
            ]
        elif stress > 0.4:
            recommendations = [
                {
                    "type": "immediate",
                    "text": "PAUSA ATIVA: 5min a caminhar ou alongar",
                    "why": "Reduz tensão e aumenta circulação"
                },
                {
                    "type": "short_term",
                    "text": "Planeamento semanal com blocos de 2h",
                    "why": "Estrutura reduz incerteza"
                },
                {
                    "type": "professional",
                    "text": "Diário emocional: regista emoções e gatilhos",
                    "why": "Auto-monitorização desenvolve inteligência emocional"
                }
            ]
        elif valence < 0.3:
            recommendations = [
                {
                    "type": "immediate",
                    "text": "MÚSICA + MOVIMENTO: 1 música que gostes + movimento breve",
                    "why": "Melhora humor e aumenta energia"
                },
                {
                    "type": "short_term",
                    "text": "Exposição à luz natural 15min/dia",
                    "why": "Regula ritmo circadiano e humor"
                },
                {
                    "type": "professional",
                    "text": "Conecta com alguém de confiança",
                    "why": "Apoio social protege bem-estar"
                }
            ]
        else:
            recommendations = [
                {
                    "type": "immediate",
                    "text": "Aproveita estado de flow para tarefas que exigem foco",
                    "why": "Estados positivos potenciam performance"
                },
                {
                    "type": "short_term",
                    "text": "Técnica Feynman para consolidar conhecimento",
                    "why": "Aumenta retenção através da explicação ativa"
                },
                {
                    "type": "professional",
                    "text": "Explora workshops e iniciativas de desenvolvimento pessoal",
                    "why": "Engajamento em atividades promove bem-estar"
                }
            ]

        # Personalização com calendário
        if calendar_suggestions:
            calendar_context = " ".join(calendar_suggestions).lower()
            if any(word in calendar_context for word in ["reunião", "aula", "evento", "compromisso"]):
                if stress > 0.5:
                    recommendations.append({
                        "type": "short_term",
                        "text": "BLOCO DE TRANSIÇÃO: 15min entre compromissos para recuperação",
                        "why": "Previne acumulação de fadiga decisória"
                    })

        return {
            "recommendations": recommendations[:3],
            "follow_up_prompt": "Como te sentes em relação a estas sugestões? Alguma faz particular sentido para ti?",
            "source": "heuristic_evidence_based"
        }