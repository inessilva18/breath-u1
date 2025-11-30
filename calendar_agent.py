# agents/calendar_agent.py
"""
CalendarAgent unificado 
"""
import os
from datetime import datetime, timedelta, timezone
import logging 
from O365 import Account

logger = logging.getLogger(__name__)

class CalendarAgent:
    def __init__(self, client_id=None, client_secret=None):
        client_id = client_id or os.getenv("O365_CLIENT_ID")
        client_secret = client_secret or os.getenv("O365_CLIENT_SECRET")

        self.account = None
        self.schedule = None
        self.calendar = None
        self.events_cache = []
        
        if client_id and client_secret:
            self._initialize_o365(client_id, client_secret)

    def _initialize_o365(self, client_id, client_secret):
        """Inicialização robusta do O365"""
        try:
            creds = (client_id, client_secret)
            self.account = Account(creds)
            
            # Verificar autenticação
            if not self.account.is_authenticated:
                logger.info("Authenticating O365 account...")
                # Para autenticação interativa em desenvolvimento
                if not self.account.authenticate(scopes=['basic', 'calendar_all']):
                    logger.error("O365 authentication failed")
                    return
            
            self.schedule = self.account.schedule()
            self.calendar = self.schedule.get_default_calendar()
            
            if self.calendar:
                logger.info("CalendarAgent initialized successfully")
            else:
                logger.warning("No default calendar found")
                
        except Exception as e:
            logger.exception("CalendarAgent init error: %s", e)

    def get_upcoming_events(self, days=7):
        """Obtém eventos com tratamento robusto de erros"""
        if not self.calendar:
            logger.warning("No calendar available - using cache")
            return self.events_cache
            
        try:
            start = datetime.now(timezone.utc)
            end = start + timedelta(days=days)
            
            query = self.calendar.new_query()
            query = query.on_attribute('start').greater_equal(start)
            query = query.on_attribute('end').less_equal(end)
            
            events = list(self.calendar.get_events(query=query, limit=50))
            
            out = []
            for event in events:
                try:
                    event_data = {
                        "subject": getattr(event, "subject", "No Subject"),
                        "start": getattr(event, "start", None),
                        "end": getattr(event, "end", None),
                        "location": getattr(event, "location", ""),
                        "is_all_day": getattr(event, "is_all_day", False)
                    }
                    out.append(event_data)
                except Exception as e:
                    logger.warning("Error processing event: %s", e)
                    continue
            
            self.events_cache = out  # Update cache
            return out
            
        except Exception as e:
            logger.exception("Error getting events: %s", e)
            return self.events_cache

    def analyze_daily_load(self, events):
        """Analisa carga diária baseada em eventos"""
        if not events:
            return {"daily_events": 0, "total_hours": 0, "load_level": "light"}
        
        daily_count = len(events)
        total_hours = 0
        
        for event in events:
            try:
                if event.get('start') and event.get('end'):
                    start = event['start']
                    end = event['end']
                    if isinstance(start, datetime) and isinstance(end, datetime):
                        duration = (end - start).total_seconds() / 3600
                        total_hours += duration
            except Exception:
                continue
        
        # Classificar carga
        if daily_count <= 2 or total_hours <= 2:
            load_level = "light"
        elif daily_count <= 5 or total_hours <= 6:
            load_level = "medium"
        else:
            load_level = "heavy"
            
        return {
            "daily_events": daily_count,
            "total_hours": round(total_hours, 2),
            "load_level": load_level
        }

    def find_free_slots(self, events, day_start="09:00", day_end="18:00"):
        """Encontra slots livres no dia"""
        # Implementação simplificada - em produção usar algoritmo mais sofisticado
        free_slots = []
        
        if not events:
            return [f"{day_start}-{day_end}"]
            
        # Ordenar eventos por horário de início
        sorted_events = sorted(
            [e for e in events if e.get('start') and isinstance(e['start'], datetime)],
            key=lambda x: x['start']
        )
        
        # Aqui seria implementada a lógica real de deteção de slots livres
        # Por enquanto, retornar slots padrão
        free_slots = ["09:00-10:00", "14:00-15:00", "16:00-17:00"]
        
        return free_slots

    def classify_event(self, subject):
        """Classifica tipo de evento baseado no assunto"""
        subject_lower = (subject or "").lower()
        
        academic_keywords = ["aula", "lecture", "study", "estudo", "exam", "exame", "project", "projeto"]
        personal_keywords = ["break", "pausa", "lunch", "almoço", "dinner", "jantar"]
        exercise_keywords = ["exercise", "exercício", "gym", "yoga", "run", "correr"]
        
        if any(keyword in subject_lower for keyword in academic_keywords):
            return "academic"
        elif any(keyword in subject_lower for keyword in exercise_keywords):
            return "exercise"
        elif any(keyword in subject_lower for keyword in personal_keywords):
            return "personal"
        else:
            return "other"

    def classify_all_events(self, events):
        """Classifica todos os eventos"""
        return [self.classify_event(event.get('subject', '')) for event in events]

    def compute_stress_prediction(self, emotion_summary, load, event_types):
        """Previsão de stress baseada em múltiplos fatores"""
        stress_score = emotion_summary.get('stress_score', 0)
        load_score = 0
        
        # Fator carga
        if load.get('load_level') == 'medium':
            load_score = 0.3
        elif load.get('load_level') == 'heavy':
            load_score = 0.6
            
        # Fator tipos de eventos
        academic_count = event_types.count('academic')
        if academic_count > 3:
            load_score += 0.2
            
        # Combinar fatores
        total_stress = min(1.0, stress_score + load_score)
        
        return {
            "predicted_stress": total_stress,
            "factors": {
                "emotional_stress": stress_score,
                "workload_stress": load_score,
                "academic_events": academic_count
            }
        }

    def suggest_plan(self, emotion_summary, events=None):
        """Sugestões de plano melhoradas"""
        suggestions = []
        
        if events is None:
            events = self.events_cache
            
        try:
            stress_score = emotion_summary.get("stress_score", 0.0)
            daily_load = self.analyze_daily_load(events)
            event_types = self.classify_all_events(events)
            stress_prediction = self.compute_stress_prediction(emotion_summary, daily_load, event_types)
            
            # Sugestões baseadas no stress
            if stress_score > 0.7:
                suggestions.append("Prioridade: Fazer pausas de 5-10min a cada 45min de estudo")
                suggestions.append("Exercício de respiração 4-7-8: 4s inspirar, 7s segurar, 8s expirar")
                suggestions.append("Beber água regularmente e evitar cafeína em excesso")
            elif stress_score > 0.4:
                suggestions.append("Fazer pausas curtas: 5min a cada 50min de estudo")
                suggestions.append("Caminhar 10min ao ar livre durante as pausas")
                suggestions.append("Ouvir música relaxante durante as pausas")
            else:
                suggestions.append("Manter blocos de foco de 90min com 15min de descanso")
                suggestions.append("Revisão rápida do plano do dia a cada manhã")
                
            # Sugestões baseadas na carga
            if daily_load.get('load_level') == 'heavy':
                suggestions.append(f"⚡ Carga pesada: {daily_load['daily_events']} eventos - considerar priorização")
                suggestions.append("Usar técnica Pomodoro: 25min foco, 5min pausa")
            elif daily_load.get('load_level') == 'medium':
                suggestions.append(f"Carga moderada: {daily_load['daily_events']} eventos - manter organização")
                
            # Free slots suggestion
            free_slots = self.find_free_slots(events)
            if free_slots:
                suggestions.append(f"⏰ Slots livres disponíveis: {', '.join(free_slots[:2])}")
                
        except Exception as e:
            logger.exception("Error in suggest_plan: %s", e)
            suggestions = [
                "Sugestão padrão: organizar blocos de estudo e pausas",
                "Fazer pausas regulares para manter produtividade"
            ]
            
        return suggestions