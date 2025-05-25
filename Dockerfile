# ---- 1. image de base légère -------------
FROM python:3.11-slim

# ---- 2. variables d'env : on laisse vide,
#        elles seront écrasées à l'exécution
ENV PYTHONUNBUFFERED=1 \
    ANTHROPIC_API_KEY="" \
    NGROK_AUTH_TOKEN=""

# ---- 3. installation des dépendances ----
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- 4. copie du code --------------------
COPY chat_claude_ngrok.py .

# ---- 5. port exposé (Flask) --------------
EXPOSE 5000

# ---- 6. point d’entrée -------------------
CMD ["python", "chat_claude_ngrok.py"]
