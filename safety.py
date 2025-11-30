# safety.py
RISK_KEYWORDS = ["suicidio", "matar-me", "auto-mutililação", "tirar a vida", "quero morrer", "não aguento"]

def check_risk(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in RISK_KEYWORDS)
