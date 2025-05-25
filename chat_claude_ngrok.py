#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chat_claude_ngrok.py
Flask + Anthropic + Ngrok dans un seul fichier.
Au lancement, demande les clés si elles ne sont pas déjà
présentes dans les variables d’environnement.
"""

import base64
import getpass
import json
import os
import threading

from flask import Flask, redirect, render_template_string, request, url_for

# ───────────────────────────────────────────────────────────────────────────────
# 1. RÉCUPÉRATION DES CLÉS (interaction console ou variables d'env)
# ───────────────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    ANTHROPIC_API_KEY = getpass.getpass("Entrez votre clé API Anthropic : ")
NGROK_AUTH_TOKEN =  "2jYaDeuLGtIQekL0UT0YiRzE54l_2tWD828DkdMbMtn8FN6XP"
#NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")
#if not NGROK_AUTH_TOKEN:
#    NGROK_AUTH_TOKEN = getpass.getpass("Entrez votre token Ngrok : ")

# ───────────────────────────────────────────────────────────────────────────────
# 2. IMPORTS DÉPENDANT DES CLÉS (anthropic, pyngrok)
# ───────────────────────────────────────────────────────────────────────────────
import anthropic                      # type: ignore  # noqa: E402
from pyngrok import ngrok             # type: ignore  # noqa: E402

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
ngrok.set_auth_token(NGROK_AUTH_TOKEN)

# ───────────────────────────────────────────────────────────────────────────────
# 3. FLASK APP + LOGIQUE DE CHAT
# ───────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
conversations: dict[int, list[dict]] = {}
TEMP_RESPONSE_FILE = "derniere_reponse_claude.txt"


def save_response_to_file(text: str) -> None:
    try:
        with open(TEMP_RESPONSE_FILE, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as exc:  # pragma: no cover
        print(f"[⚠] Impossible d’enregistrer la réponse : {exc}")


def send_message(conv_id: int,
                 user_message: str | None,
                 uploaded_file=None) -> str:
    """
    Envoie un message (et éventuellement un fichier) à Claude 3
    et renvoie le texte de la réponse.
    """
    conv = conversations.get(conv_id, [])

    # 1. Construction du contenu utilisateur
    message_content: list[dict] = []
    if user_message:
        message_content.append({"type": "text", "text": user_message})

    if uploaded_file and uploaded_file.filename:
        file_type = uploaded_file.content_type
        file_content = uploaded_file.read()

        if file_type.startswith("image/"):
            message_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": file_type,
                    "data": base64.b64encode(file_content).decode()
                }
            })
        else:
            message_content.append({
                "type": "text",
                "text": f"[Fichier attaché : {uploaded_file.filename} "
                        "(type non supporté)]"
            })

    conv.append({"role": "user", "content": message_content})

    # 2. Appel Anthropic
    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=4000,
            messages=conv
        )
        assistant_text = "".join(
            block.text for block in response.content if block.type == "text"
        )
    except Exception as exc:
        assistant_text = f"Erreur API Anthropic : {exc}"

    save_response_to_file(assistant_text)

    # 3. Mémorisation et retour
    conv.append({"role": "assistant",
                 "content": [{"type": "text", "text": assistant_text}]})
    conversations[conv_id] = conv
    return assistant_text


# ───────────────────────────────────────────────────────────────────────────────
# 4. ROUTES FLASK (index, nouvelle conversation, chat)
# ───────────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    conv_list = sorted(conversations.keys())
    # … (HTML identique à votre version, omis ici pour gagner de la place)
    return render_template_string(
        "<h1>Bienvenue !</h1>"
        "<p><a href='{{ url_for(\"new_conversation\") }}'>"
        "➕ Nouvelle conversation</a></p>"
        "<ul>{% for c in conv_list %}"
        "<li><a href='{{ url_for(\"chat\", conv_id=c) }}'>Conversation {{ c }}</a></li>"
        "{% endfor %}</ul>",
        conv_list=conv_list
    )


@app.route("/new")
def new_conversation():
    conv_id = len(conversations) + 1
    conversations[conv_id] = []
    return redirect(url_for("chat", conv_id=conv_id))


@app.route("/conversation/<int:conv_id>", methods=["GET", "POST"])
def chat(conv_id: int):
    if request.method == "POST":
        msg = request.form.get("message", "")
        file_ = request.files.get("file")
        if msg or file_:
            send_message(conv_id, msg, file_)
        return redirect(url_for("chat", conv_id=conv_id, _anchor="bottom"))

    conv = conversations.get(conv_id, [])
    # … (HTML complet de chat, conservé tel quel)
    return render_template_string(
        "<h2>Conversation {{ conv_id }}</h2>"
        "<pre>{{ conv|tojson(indent=2, ensure_ascii=False) }}</pre>"
        "<p><a href='{{ url_for(\"index\") }}'>Retour</a></p>",
        conv_id=conv_id, conv=conv
    )


# ───────────────────────────────────────────────────────────────────────────────
# 5. POINT D’ENTRÉE
# ───────────────────────────────────────────────────────────────────────────────
def main() -> None:
    # Lancement Flask dans un thread séparé
    threading.Thread(target=app.run, kwargs={
        "host": "0.0.0.0",
        "port": 5000,
        "debug": False,
        "use_reloader": False,
    }, daemon=True).start()

    # Tunnel Ngrok
    public_url = ngrok.connect(5000, bind_tls=True)
    print(f"🔗 URL publique : {public_url}")

    # Boucle blocante pour empêcher le script de se terminer
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\nInterruption : fermeture du tunnel…")
        ngrok.disconnect(public_url)
        ngrok.kill()


if __name__ == "__main__":
    main()
