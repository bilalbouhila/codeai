import json
from flask import Flask, request, redirect, url_for, render_template_string
import anthropic
import base64


app = Flask(__name__)

# Paramètres de l'API
API_URL = "https://api.anthropic.com/v1/complete"  # URL de l'endpoint Claude
API_KEY = getpass.getpass("Entrez votre clé API Anthropic : ")



# Initialisation du client Anthropica
client = anthropic.Anthropic(api_key=API_KEY)

# Dictionnaire global pour stocker les conversations
conversations = {}

# Définir le chemin du fichier temporaire pour stocker la dernière réponse
TEMP_RESPONSE_FILE = "derniere_reponse_claude.txt"

# Classe TextBlock pour formater la réponse
class TextBlock:
    def __init__(self, citations, text, type):
        self.citations = citations
        self.text = text
        self.type = type

    def __repr__(self):
        return f"TextBlock(citations={self.citations}, text={repr(self.text)}, type={repr(self.type)})"

def save_response_to_file(response_text):
    """
    Sauvegarde la réponse dans un fichier temporaire local
    """
    try:
        with open(TEMP_RESPONSE_FILE, 'w', encoding='utf-8') as file:
            file.write(response_text)
        print(f"Réponse sauvegardée dans {TEMP_RESPONSE_FILE}")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la réponse: {e}")

def send_message(conv_id, user_message, uploaded_file=None):
    """
    Fonction améliorée pour envoyer des messages et des fichiers à Claude
    """
    conv = conversations.get(conv_id, [])

    # Préparer le message utilisateur
    message_content = []

    # Ajouter le texte de l'utilisateur si présent
    if user_message:
        message_content.append({
            "type": "text",
            "text": user_message
        })

    # Ajouter le fichier s'il existe
    if uploaded_file and uploaded_file.filename:
        # Déterminer le type de média
        file_type = uploaded_file.content_type

        # Lire le contenu du fichier
        file_content = uploaded_file.read()

        # Pour les images uniquement - les autres types de fichiers ne sont pas supportés directement
        if file_type.startswith('image/'):
            message_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": file_type,
                    "data": base64.b64encode(file_content).decode('utf-8')
                }
            })
        else:
            # Pour les autres types de fichiers, on ajoute simplement une note
            message_content.append({
                "type": "text",
                "text": f"[Fichier attaché: {uploaded_file.filename} - Ce type de fichier n'est pas directement supporté]"
            })

    # Ajouter le message à la conversation
    conv.append({"role": "user", "content": message_content})

    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=4000,
            messages=conv
        )

        # Extraire le texte de tous les blocs de texte dans la réponse
        assistant_response_text = ""
        for content in response.content:
            if content.type == 'text':
                assistant_response_text += content.text

        # Sauvegarder la réponse dans un fichier temporaire
        save_response_to_file(assistant_response_text)

    except Exception as e:
        assistant_response_text = f"Erreur lors de la requête API : {e}"
        save_response_to_file(assistant_response_text)

    # Stocker la réponse de l'assistant dans la conversation
    conv.append({"role": "assistant", "content": [{"type": "text", "text": assistant_response_text}]})
    conversations[conv_id] = conv
    return assistant_response_text

@app.route("/")
def index():
    conv_list = sorted(conversations.keys())
    html = '''
    <!DOCTYPE html>
    <html lang="fr">
    <head>
      <meta charset="UTF-8">
      <title>Chat avec Claude</title>
      <style>
          body {
              font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
              background-color: #f0f2f5;
              margin: 0;
              padding: 0;
          }
          .container {
              max-width: 900px;
              margin: 40px auto;
              padding: 20px;
              background-color: #ffffff;
              box-shadow: 0 2px 8px rgba(0,0,0,0.1);
              border-radius: 12px;
          }
          h1, h2 {
              text-align: center;
              color: #2980b9;
          }
          .button {
              display: inline-block;
              padding: 12px 20px;
              margin: 10px 0;
              background-color: #3498db;
              color: #fff;
              text-decoration: none;
              border-radius: 8px;
              transition: background-color 0.3s;
              font-weight: bold;
          }
          .button:hover {
              background-color: #2980b9;
              transform: translateY(-2px);
              box-shadow: 0 4px 8px rgba(0,0,0,0.1);
          }
          ul {
              list-style: none;
              padding: 0;
          }
          li {
              margin: 10px 0;
          }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>Interface de Chat avec Claude</h1>
        <a href="{{ url_for('new_conversation') }}" class="button">Créer une nouvelle conversation</a>
        <h2>Conversations existantes</h2>
        <ul>
          {% for conv in conv_list %}
            <li><a href="{{ url_for('chat', conv_id=conv) }}" class="button">Conversation {{ conv }}</a></li>
          {% endfor %}
        </ul>
      </div>
    </body>
    </html>
    '''
    return render_template_string(html, conv_list=conv_list)


@app.route("/new")
def new_conversation():
  conv_id = len(conversations) + 1
  conversations[conv_id] = []
  return redirect(url_for('chat', conv_id=conv_id))


@app.route("/conversation/<int:conv_id>", methods=["GET", "POST"])
def chat(conv_id):
    if request.method == "POST":
        user_message = request.form.get("message", "")

        # Récupérer le fichier téléchargé s'il existe
        uploaded_file = request.files.get('file')

        if user_message or uploaded_file:
            # Envoyer le message avec le fichier éventuel
            send_message(conv_id, user_message, uploaded_file)

        return redirect(url_for('chat', conv_id=conv_id, _anchor="bottom"))

    conv = conversations.get(conv_id, [])
    chat_html = ""
    for msg in conv:
        if msg["role"] == "user":
            # Extract just the text content from the user's message
            user_text = ""
            if isinstance(msg["content"], list):
                for content_item in msg["content"]:
                    if isinstance(content_item, dict) and "text" in content_item:
                        user_text += content_item["text"]
            else:
                user_text = str(msg["content"])

            chat_html += (
                f'<div class="message user">'
                f'<strong>Vous :</strong> '
                f'<div class="message-content">{user_text}</div>'
                f'</div>'
            )
        elif msg["role"] == "assistant":
            # Extract just the text content from the assistant's response
            assistant_text = ""
            if isinstance(msg["content"], list):
                for content_item in msg["content"]:
                    if isinstance(content_item, dict) and "text" in content_item:
                        assistant_text += content_item["text"]
            else:
                assistant_text = str(msg["content"])

            chat_html += (
                f'<div class="message assistant">'
                f'<strong>Claude :</strong> '
                f'<div class="message-content">{assistant_text}</div>'
                f'</div>'
            )

    html = '''
    <!DOCTYPE html>
    <html lang="fr">
    <head>
      <meta charset="UTF-8">
      <title> {{ conv_id }}</title>
      <style>
          body {
              font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
              background-color: #f0f2f5;
              color: #333;
              margin: 0;
              padding: 0;
              line-height: 1.6;
          }
          .container {
              max-width: 1000px;
              margin: 20px auto;
              padding: 25px;
              background-color: #ffffff;
              box-shadow: 0 4px 15px rgba(0,0,0,0.1);
              border-radius: 16px;
          }
          h1 {
              text-align: center;
              color: #2980b9;
              font-size: 28px;
              margin-bottom: 20px;
              border-bottom: 2px solid #eee;
              padding-bottom: 10px;
          }
          .chat-box {
              height: 550px;
              padding: 20px;
              overflow-y: auto;
              background: #ffffff;
              border-radius: 12px;
              border: 1px solid #e0e0e0;
              box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
              margin-bottom: 20px;
          }
          .message {
              margin-bottom: 20px;
              padding: 15px;
              border-radius: 12px;
              box-shadow: 0 2px 5px rgba(0,0,0,0.03);
              max-width: 85%;
          }
          .message-content {
              white-space: pre-wrap;
              font-family: Consolas, "Courier New", monospace;
              line-height: 1.5;
          }
          .user {
              background-color: #e1f5fe;
              margin-left: auto;
              margin-right: 0;
              border-bottom-right-radius: 4px;
          }
          .assistant {
              background-color: #f5f5f5;
              margin-right: auto;
              margin-left: 0;
              border-bottom-left-radius: 4px;
          }
          .message strong {
              display: block;
              margin-bottom: 8px;
              font-size: 14px;
              color: #555;
          }

          /* Style pour les blocs de code Python */
          .python-code-block {
              position: relative;
              background-color: #282c34;
              color: #abb2bf;
              border-radius: 8px;
              padding: 16px 12px 12px;
              margin: 15px 0;
              overflow: auto;
              box-shadow: 0 3px 10px rgba(0,0,0,0.1);
          }
          .python-code-block pre {
              margin: 0;
              white-space: pre-wrap;
              font-family: 'Fira Code', Consolas, Monaco, monospace;
              font-size: 14px;
              line-height: 1.5;
          }
          .python-label {
              position: absolute;
              top: 0;
              left: 0;
              background-color: #61afef;
              color: #282c34;
              padding: 3px 10px;
              font-size: 12px;
              border-radius: 8px 0 8px 0;
              font-weight: bold;
          }
          .copy-code-button {
              position: absolute;
              top: 0;
              right: 0;
              background-color: #61afef;
              color: #282c34;
              border: none;
              border-radius: 0 8px 0 8px;
              padding: 3px 12px;
              font-size: 12px;
              cursor: pointer;
              font-weight: bold;
              transition: all 0.2s ease;
          }
          .copy-code-button:hover {
              background-color: #56b6c2;
              transform: translateY(-1px);
          }
          .copy-code-button.copied {
              background-color: #98c379;
          }

          .version-info {
              text-align: center;
              font-size: 12px;
              color: #888;
              margin-top: 20px;
          }
          .input-box {
              margin-top: 20px;
              display: flex;
              background-color: #f9f9f9;
              padding: 15px;
              border-radius: 12px;
              box-shadow: 0 2px 5px rgba(0,0,0,0.05);
          }
          .input-box textarea {
              flex: 1;
              padding: 12px;
              font-size: 16px;
              border: 1px solid #ddd;
              border-radius: 8px;
              resize: none;
              box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
          }
          .input-box textarea:focus {
              outline: none;
              border-color: #3498db;
              box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
          }
          .input-box input[type="submit"] {
              padding: 12px 25px;
              font-size: 16px;
              margin-left: 10px;
              background-color: #3498db;
              border: none;
              color: #fff;
              border-radius: 8px;
              cursor: pointer;
              transition: all 0.3s ease;
              font-weight: bold;
          }
          .input-box input[type="submit"]:hover {
              background-color: #2980b9;
              transform: translateY(-2px);
              box-shadow: 0 4px 8px rgba(0,0,0,0.1);
          }
          a.button {
              display: inline-block;
              padding: 10px 20px;
              background-color: #3498db;
              color: #fff;
              text-decoration: none;
              border-radius: 8px;
              transition: all 0.3s ease;
              font-weight: bold;
              margin-top: 10px;
          }
          a.button:hover {
              background-color: #2980b9;
              transform: translateY(-2px);
              box-shadow: 0 4px 8px rgba(0,0,0,0.1);
          }
          .file-upload {
              margin: 0 10px;
              position: relative;
          }
          .file-label {
              display: inline-block;
              padding: 12px 15px;
              background-color: #7f8c8d;
              color: #fff;
              text-decoration: none;
              border-radius: 8px;
              cursor: pointer;
              transition: all 0.3s ease;
              font-weight: bold;
          }
          .file-label:hover {
              background-color: #6c7a7a;
              transform: translateY(-2px);
              box-shadow: 0 4px 8px rgba(0,0,0,0.1);
          }
          input[type="file"] {
              display: none;
          }
          .file-name {
              position: absolute;
              bottom: -20px;
              left: 0;
              font-size: 12px;
              color: #555;
              max-width: 150px;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
          }
      </style>
      <script>
          // Fonction pour faire défiler la boîte de chat jusqu'en bas
          function scrollChatToBottom() {
              const chatBox = document.querySelector('.chat-box');
              if (chatBox) {
                  chatBox.scrollTop = chatBox.scrollHeight;
              }
          }

          // Fonction simplifiée pour traiter les blocs de code Python
          function processPythonCodeBlocks() {
              console.log("Recherche des blocs de code Python...");

              // Rechercher tous les messages de Claude
              const assistantMessages = document.querySelectorAll('.message.assistant .message-content');

              assistantMessages.forEach(function(messageContent) {
                  // Obtenir le texte brut du message
                  const originalContent = messageContent.innerHTML;

                  // Créer une expression régulière pour trouver les blocs de code Python
                  // Cette regex recherche ```python suivi de n'importe quel contenu jusqu'à ```
                  const regex = /```python\s*([\s\S]*?)```/g;

                  // Créer une copie du contenu pour le modifier
                  let newContent = originalContent;

                  // Trouver tous les blocs de code Python et les remplacer
                  let match;
                  let count = 0;

                  // Pour chaque bloc de code Python trouvé
                  while ((match = regex.exec(originalContent)) !== null) {
                      count++;

                      // Extraire le code Python et le bloc complet
                      const fullMatch = match[0];  // Le bloc complet ```python ... ```
                      const codeOnly = match[1];   // Juste le code Python

                      // Créer un ID unique pour ce bloc de code
                      const blockId = 'python-code-' + Date.now() + '-' + count;

                      // Échapper les caractères HTML dans le code
                      const safeCode = codeOnly
                          .replace(/&/g, "&amp;")
                          .replace(/</g, "&lt;")
                          .replace(/>/g, "&gt;")
                          .replace(/"/g, "&quot;")
                          .replace(/'/g, "&#039;");

                      // Créer le HTML pour le bloc de code avec bouton de copie
                      const codeBlock = `
                          <div class="python-code-block" id="${blockId}">
                              <div class="python-label">Python</div>
                              <button class="copy-code-button" onclick="copyPythonCode('${blockId}')">Copier</button>
                              <pre><code>${safeCode}</code></pre>
                          </div>
                      `;

                      // Remplacer le bloc de code original par notre version stylisée
                      newContent = newContent.replace(fullMatch, codeBlock);
                  }

                  // Si des blocs de code ont été trouvés, mettre à jour le contenu
                  if (count > 0) {
                      messageContent.innerHTML = newContent;
                      console.log(`${count} bloc(s) de code Python trouvé(s) et stylisé(s)`);
                  }
              });
          }

          // Fonction simplifiée pour copier le code Python
          function copyPythonCode(blockId) {
              // Trouver le bloc de code
              const codeBlock = document.getElementById(blockId);
              if (!codeBlock) return;

              // Obtenir le texte du code
              const codeContent = codeBlock.querySelector('code').innerText;

              // Créer un élément textarea temporaire pour la copie
              const textarea = document.createElement('textarea');
              textarea.value = codeContent;
              textarea.setAttribute('readonly', '');
              textarea.style.position = 'absolute';
              textarea.style.left = '-9999px';
              document.body.appendChild(textarea);

              // Sélectionner et copier le texte
              textarea.select();
              document.execCommand('copy');

              // Supprimer l'élément textarea
              document.body.removeChild(textarea);

              // Mettre à jour l'apparence du bouton
              const button = codeBlock.querySelector('.copy-code-button');
              button.innerText = 'Copié!';
              button.classList.add('copied');

              // Rétablir l'état original après 2 secondes
              setTimeout(() => {
                  button.innerText = 'Copier';
                  button.classList.remove('copied');
              }, 2000);
          }

          // Exécuter lorsque le DOM est complètement chargé
          document.addEventListener('DOMContentLoaded', function() {
              console.log("DOM chargé, initialisation...");

              // Faire défiler la boîte de chat jusqu'en bas
              scrollChatToBottom();

              // Traiter les blocs de code Python immédiatement
              processPythonCodeBlocks();

              // Configurer l'affichage du nom de fichier
              const fileInput = document.getElementById('file-input');
              if (fileInput) {
                  fileInput.addEventListener('change', function(e) {
                      // Créer ou mettre à jour l'élément span pour afficher le nom du fichier
                      let fileNameSpan = document.querySelector('.file-name');
                      if (!fileNameSpan) {
                          fileNameSpan = document.createElement('span');
                          fileNameSpan.className = 'file-name';
                          document.querySelector('.file-upload').appendChild(fileNameSpan);
                      }

                      if (this.files.length > 0) {
                          fileNameSpan.textContent = this.files[0].name;
                      } else {
                          fileNameSpan.textContent = '';
                      }
                  });
              }

              // Ajouter un observateur de mutations pour traiter les nouveaux messages
              const chatBox = document.querySelector('.chat-box');
              if (chatBox) {
                  const observer = new MutationObserver(function(mutations) {
                      processPythonCodeBlocks();
                  });

                  observer.observe(chatBox, {
                      childList: true,
                      subtree: true
                  });
              }
          });
      </script>
    </head>
    <body>
      <div class="container">
        <h1> {{ conv_id }}</h1>
        <div class="chat-box">
          {{ chat_html|safe }}
        </div>
        <form method="post" class="input-box" enctype="multipart/form-data">
          <textarea name="message" rows="3" placeholder="Posez votre question à Claude..." autofocus
            onkeydown="if(event.key === 'Enter' && !event.shiftKey){ event.preventDefault(); this.form.submit(); }"></textarea>
          <div class="file-upload">
            <input type="file" name="file" id="file-input">
            <label for="file-input" class="file-label">Fichier</label>
          </div>
          <input type="submit" value="Envoyer">
        </form>
        <br>
        <a href="{{ url_for('index') }}" class="button">Retour à l'accueil</a>
      </div>
    </body>
    </html>
    '''
    return render_template_string(html, conv_id=conv_id, chat_html=chat_html)

# Important: cette fonction run() doit être accessible
def run(debug=False, use_reloader=False):
    app.run(host='0.0.0.0', port=5000, debug=debug, use_reloader=use_reloader)

# Si le fichier est exécuté directement
if __name__ == '__main__':
    run(debug=True)