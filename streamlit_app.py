# streamlit_app.py 
import streamlit as st
from coordinator import Coordinator
from dotenv import load_dotenv
from datetime import datetime
import streamlit.components.v1 as components

#CARREGAR VARIÁVEIS DE AMBIENTE
load_dotenv()

# Configuração da página
st.set_page_config(
    page_title="BreathU - Seu Assistente Pessoal",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .emotion-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
    }
    .recommendation-card {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .stress-high { color: #ff4b4b; font-weight: bold; }
    .stress-medium { color: #ffa500; font-weight: bold; }
    .stress-low { color: #00cc66; font-weight: bold; }
    .llm-badge { 
        background-color: #10b981; 
        color: white; 
        padding: 2px 8px; 
        border-radius: 12px; 
        font-size: 0.8em;
        margin-left: 8px;
    }
    .heuristic-badge { 
        background-color: #f59e0b; 
        color: white; 
        padding: 2px 8px; 
        border-radius: 12px; 
        font-size: 0.8em;
        margin-left: 8px;
    }
    .welcome-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .welcome-text {
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .welcome-subtext {
        font-size: 1rem;
        opacity: 0.9;
    }
    .time-display {
        font-size: 0.9rem;
        opacity: 0.8;
        margin-top: 0.5rem;
    }
    .feedback-button {
        display: inline-block;
        padding: 12px 24px;
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        color: white;
        text-decoration: none;
        border-radius: 8px;
        font-weight: bold;
        font-size: 1.1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        text-align: center;
        border: none;
        cursor: pointer;
    }
    .feedback-button:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
    }
</style>
""", unsafe_allow_html=True)

# Inicializar coordenador
@st.cache_resource
def get_coordinator():
    return Coordinator(use_dr4=True)

def get_time_based_greeting():
    
    current_hour = datetime.now().hour
    
    if 5 <= current_hour < 12:
        return "Bom dia", "🌅", "Que tenhas um dia maravilhoso e produtivo!"
    elif 12 <= current_hour < 18:
        return "Boa tarde", "☀️", "Que a tua tarde seja cheia de energia positiva!"
    elif 18 <= current_hour < 22:
        return "Boa noite", "🌇", "Que tenhas uma noite tranquila e relaxante!"
    else:
        return "Boa noite", "🌙", "Que tenhas um descanso reparador!"

def get_motivational_quote():
    
    quotes = [
        "A persistência é o caminho do êxito. - Charles Chaplin",
        "O sucesso nasce do querer, da determinação e persistência. - Chico Xavier",
        "Acredite que você pode, assim você já está no meio do caminho. - Theodore Roosevelt",
        "Cada dia é uma nova oportunidade para recomeçar.",
        "Tu és mais forte do que imaginas e capaz de mais do que sonhas.",
        "Respira, acalma o coração. Tu consegues superar este desafio.",
        "Pequenos progressos diários levam a grandes resultados.",
        "A tua mente é poderosa. Acredita nela e em ti."
    ]
    import random
    return random.choice(quotes)

def display_welcome_message(user_name, study_focus):
    #Exibe mensagem de boas-vindas personalizada
    greeting, emoji, wish = get_time_based_greeting()
    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%d/%m/%Y")
    quote = get_motivational_quote()
    
    display_name = user_name.strip() if user_name and user_name.strip() else "bem vindo ao BreauthU"
    
    st.markdown(f"""
    <div class="welcome-message">
        <div class="welcome-text">
            {emoji} {greeting}, <strong>{display_name}</strong>!
        </div>
        <div class="welcome-subtext">
            {wish}
        </div>
        <div class="welcome-subtext">
            ✨ {quote}
        </div>
        <div class="time-display">
            {current_date} | {current_time}
        </div>
    </div>
    """, unsafe_allow_html=True)

def setup_google_form_feedback(user_name=None):
    display_name = user_name.strip() if user_name and user_name.strip() else " "
    
    st.markdown("---")
    st.subheader(" Avaliação do BreathU")
    
    st.markdown(f"""
    ### Olá, {display_name}! A Tua Opinião Constrói o Futuro! 
    
    **Precisamos da tua ajuda para melhorar o BreathU.** 
    A tua experiência vale ouro para nós - partilha-a em **apenas 2-3 minutos**:
    """)
   
    GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSei2ax9WYIWGEommWV5fC4npDog7Wef-veo4gCeqlKuram1gw/viewform?usp=dialog"  # 🔥 SUBSTITUIR PELO TEU URL
    
    st.markdown(f"""
        Formulário Completo de Avaliação
    
    **Clica no botão abaixo para abrir o formulário de avaliação:**
    """)
    # Botão para abrir o formulário
    st.markdown(f"""
    <div style="text-align: center; margin: 2rem 0;">
        <a href="{GOOGLE_FORM_URL}" target="_blank">
            <button class="feedback-button">
                 Abrir Formulário de Avaliação
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)

def main():
    coord = get_coordinator()
    
    # Header
    st.markdown('<h1 class="main-header">🧠 BreathU - Seu Assistente Pessoal</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("breathU_image1.png", width=150)
        st.markdown("### Perfil Pessoal")
        
        user_name = st.text_input("**O teu nome**", placeholder="Ex: Inês, Beatriz...", key="user_name")
        study_focus = st.selectbox("**Área de estudo**", 
                                 ["Engenharia", "Medicina", "Direito", "Artes", "Ciências", "Outra"],
                                 key="study_focus")
        
        # MENSAGEM DE BOAS-VINDAS PERSONALIZADA
        display_welcome_message(user_name, study_focus)
        
        #MOSTRAR STATUS DO LLM
        st.markdown("---")
        st.markdown("### 🛠 Status do Sistema")
        if coord.feedback and hasattr(coord.feedback, 'openrouter_available'):
            if coord.feedback.openrouter_available:
                st.success("✅ **LLM (OpenRouter) Disponível**")
                st.info(f"**Modelo:** {getattr(coord.feedback, 'model', 'N/A')}")
            else:
                st.warning("⚠️ **LLM Indisponível**")
                st.info("Usando sistema heurístico")

    # Área principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(" Como estás e o que tens para fazer?")
        
        # Input de áudio
        audio_value = st.audio_input("🎙️ Grava uma mensagem de voz")
        
        # Processar áudio se existir
        transcribed_text = ""
        if audio_value:
            st.audio(audio_value)
            
            if coord.interface and hasattr(coord.interface, 'is_stt_available') and coord.interface.is_stt_available():
                with st.spinner("🔄 A transcrever áudio..."):
                    try:
                        audio_bytes = audio_value.getvalue()
                        result = coord.interface.handle_input(audio_bytes=audio_bytes)
                        
                        if result and result.get("raw_text"):
                            transcribed_text = result['raw_text']
                            st.success("✅ Áudio transcrito com sucesso!")
                            st.info(f"**Texto transcrito:** {transcribed_text}")
                        else:
                            st.warning("Não foi possível transcrever o áudio.")
                    except Exception as e:
                        st.error(f"Erro ao processar áudio: {str(e)}")
            else:
                st.warning("Funcionalidade de voz não disponível.")

        # Input de texto
        user_input = st.text_area(
            "💭 Descreve como te sentes e as tuas tarefas...",
            value=transcribed_text,  # Usar o texto transcrito se existir
            height=120,
            placeholder="Ex: Hoje sinto-me um pouco ansioso porque tenho um exame na sexta e preciso de organizar o meu estudo...",
            key="text_input"
        )

    with col2:
        st.subheader("📊 Status")
        if transcribed_text:
            st.success(" Áudio transcrito e pronto para análise!")
        elif user_input.strip():
            st.success(" Texto pronto para análise!")
        else:
            st.info("💡 Podes gravar áudio ou escrever diretamente")
            
        # 🔥 DICA PERSONALIZADA BASEADA NA HORA
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            st.info("**🌅 Dica matinal:** Começa o dia com uma tarefa pequena para ganhar momentum!")
        elif 12 <= current_hour < 14:
            st.info("**🍽️ Dica do almoço:** Uma pequena pausa após almoço aumenta a produtividade da tarde!")
        elif 14 <= current_hour < 18:
            st.info("**☀️ Dica da tarde:** Divide tarefas grandes em partes menores para manter o foco!")
        else:
            st.info("**🌙 Dica noturna:** Planeia o dia seguinte antes de descansar para acordar com propósito!")

    # Botão de análise
    if st.button("🧠 Analisar com BreathU", type="primary", use_container_width=True):
        # Usar o texto transcrito se existir, senão usar o texto manual
        current_input = transcribed_text if transcribed_text else user_input.strip()
        
        if current_input:
            with st.spinner("🔍 BreathU está a analisar o teu estado..."):
                try:
                    # Analisar o texto
                    result = coord.handle_text(current_input)
                    
                    # Mostrar resultados
                    display_results(result, user_name)
                        
                except Exception as e:
                    st.error(f"❌ Erro na análise: {str(e)}")
                    st.info("Por favor, tenta novamente.")
        else:
            st.warning("⚠️ Por favor, escreve ou grava uma mensagem para analisar.")


    setup_google_form_feedback(user_name)

def display_results(result, user_name):
    """Função para mostrar os resultados da análise"""
    # PERSONALIZAR MENSAGEM DE RESULTADO COM NOME
    display_name = user_name.strip() if user_name and user_name.strip() else " "
    
    st.success(f"## 📊 Análise Personalizada para {display_name}")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("😊 Estado Emocional")
        
        stress_score = result['emotion']['stress_score']
        valence = result['emotion']['valence']
        dominant = result['emotion']['dominant'] or "Não especificado"
        
        # Visualização de stress
        if stress_score > 0.7:
            stress_class = "stress-high"
            stress_emoji = "🔴"
            stress_message = f" {display_name}, vamos trabalhar juntos para reduzir este stress!"
        elif stress_score > 0.4:
            stress_class = "stress-medium" 
            stress_emoji = "🟡"
            stress_message = f" {display_name}, pequenos ajustes podem fazer uma grande diferença!"
        else:
            stress_class = "stress-low"
            stress_emoji = "🟢"
            stress_message = f" Ótimo trabalho, {display_name}! Continua a cuidar de ti!"
            
        st.markdown(f"""
        <div class="emotion-card">
            <p><strong>Nível de Stress:</strong> <span class="{stress_class}">{stress_emoji} {stress_score:.2f}/1.0</span></p>
            <p><strong>Valência:</strong> {valence:.2f}/1.0</p>
            <p><strong>Emoção Dominante:</strong> {dominant}</p>
            <p><em>{stress_message}</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("📅 Horário Otimizado")
        schedule = result['optimized_schedule'].get('schedule', [])
        if schedule:
            for i, task in enumerate(schedule, 1):
                st.write(f"{i}. {task}")
            
            # 🔥 MENSAGEM PERSONALIZADA SOBRE O PLANEAMENTO
            if stress_score > 0.6:
                st.info(f" **Para {display_name}:** Este plano foi ajustado para ajudar a gerir o stress. Lembra-te de fazer pausas!")
            elif len(schedule) > 3:
                st.info(f" **Para {display_name}:** Tens um dia cheio! Foca numa tarefa de cada vez.")
            else:
                st.info(f" **Para {display_name}:** Bom planeamento! Mantém o ritmo e celebra pequenas vitórias.")
        else:
            st.info("Nenhuma tarefa planeada.")
            
        if result.get('events'):
            st.subheader("📋 Próximos Eventos")
            for event in result['events'][:3]:
                st.write(f"• {event.get('subject', 'Evento')}")

    with col_b:
        st.subheader("💡 Recomendações Personalizadas")
        
        message = result['message']
        if isinstance(message, dict):
            recommendations = message.get('recommendations', [])
            
            # MOSTRAR BADGE DA FONTE
            source = message.get('source', 'Desconhecida')
            if 'LLM' in source or 'openrouter' in source.lower():
                badge_html = '<span class="llm-badge">LLM</span>'
                source_text = "Recomendações geradas por IA avançada"
            else:
                badge_html = '<span class="heuristic-badge">Heurístico</span>'
                source_text = "Recomendações baseadas em evidências científicas"
                
            st.markdown(f"**Fonte:** {source} {badge_html}", unsafe_allow_html=True)
            st.caption(f"✨ {source_text}")
            
            if recommendations:
                for rec in recommendations:
                    if isinstance(rec, dict):
                        #PERSONALIZAR RECOMENDAÇÕES COM O NOME
                        rec_text = rec.get('text', '')
                        rec_why = rec.get('why', '')
                        
                        # Adicionar nome às recomendações quando fizer sentido
                        if any(word in rec_text.lower() for word in ['tenta', 'experimenta', 'faz', 'pratica']):
                            personalized_text = rec_text
                        else:
                            personalized_text = f"{display_name}, {rec_text.lower()}"
                            
                        st.markdown(f"""
                        <div class="recommendation-card">
                            <strong>🎯 {rec.get('type', 'Recomendação').title()}:</strong><br/>
                            {personalized_text}<br/>
                            <em>💡 Porquê: {rec_why}</em>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("Nenhuma recomendação disponível.")
            
            if message.get('follow_up_prompt'):
                follow_up = message['follow_up_prompt']
                personalized_follow_up = follow_up.replace("te sentes", f"te sentes, {display_name}")
                st.info(f"💬 {personalized_follow_up}")
        else:
            st.info(message)

if __name__ == "__main__":
    main()