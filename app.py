import json
from flask import Flask, request, redirect, url_for, render_template_string
import anthropic
import base64




from flask import Flask, request, redirect, url_for, render_template
from models import send_message, get_conversation, create_conversation, get_all_conversations

app = Flask(__name__)

# Store model and mode preferences for each conversation
conversation_settings = {}

# Mode-specific configurations
MODE_CONFIGS = {
    'professional': {
        'default_model': 'claude-3-opus-20240229',
        'system': """You are a professional assistant. Follow these guidelines:
- Always detect and respond in the same language as the user message.
- If the message is in French, reply in French. If in Spanish, reply in Spanish, etc.
- Use formal and precise language
- Structure responses with clear sections and bullet points
- Provide detailed, well-researched information
- Maintain a professional tone throughout
- Focus on accuracy and clarity
- Include relevant citations or sources when appropriate"""
    },
    'casual': {
        'default_model': 'claude-3-haiku-20240307',
        'system': """You are a friendly and casual assistant. Follow these guidelines:
- Always detect and respond in the same language as the user message.
- If the message is in French, reply in French. If in Spanish, reply in Spanish, etc.
- Use conversational, easy-to-understand language
- Keep responses concise and engaging
- Add appropriate emojis to make conversations more lively
- Be helpful while maintaining a relaxed tone
- Avoid overly technical language unless necessary
- Make complex topics more approachable"""
    },
    'code': {
        'default_model': 'claude-3-opus-20240229',
        'system': """You are a coding assistant. Follow these guidelines:
- Always detect and respond in the same language as the user message.
- If the message is in French, reply in French. If in Spanish, reply in Spanish, etc.
- Focus on providing clean, efficient code solutions
- Always include code comments and documentation
- Explain the reasoning behind your code choices
- Follow best practices and design patterns
- Highlight potential issues or edge cases
- Suggest optimizations when relevant
- Include example usage when helpful"""
    },
    'correction': {
        'default_model': 'claude-3-sonnet-20240229',
        'system': """You are a text correction assistant. Follow these guidelines:
- Always detect and respond in the same language as the user message.
- If the message is in French, reply in French. If in Spanish, reply in Spanish, etc.
- Improve grammar, spelling, and punctuation
- Enhance clarity and readability
- Maintain the original message's intent
- Explain all corrections made
- Suggest better word choices or phrasing
- Format text for better readability
- Consider context and tone
- Provide both corrected version and explanation of changes"""
    }
}

@app.route("/")
def index():
    """
    Main page showing all conversations
    """
    conv_list = get_all_conversations()
    return render_template('index.html', conv_list=conv_list)

@app.route("/new")
def new_conversation():
    """
    Create a new conversation with selected model and mode
    """
    model = request.args.get('model', 'claude-3-sonnet-20240229')
    mode = request.args.get('mode', 'casual')
    
    conv_id = create_conversation()
    conversation_settings[conv_id] = {
        'model': model,
        'mode': mode,
        'system': MODE_CONFIGS[mode]['system']
    }
    print(f"New conversation created with ID: {conv_id}")
    print(f"Model: {model}, Mode: {mode}")
    print(f"System message: {MODE_CONFIGS[mode]['system']}")
    
    return redirect(url_for('chat', conv_id=conv_id))

@app.route("/delete/<int:conv_id>")
def delete_conversation(conv_id):
    """
    Delete a conversation
    """
    from models import conversations
    if conv_id in conversations:
        del conversations[conv_id]
        if conv_id in conversation_settings:
            del conversation_settings[conv_id]
    return redirect(url_for('index'))

@app.route("/conversation/<int:conv_id>", methods=["GET", "POST"])
def chat(conv_id):
    """
    Chat interface for a specific conversation
    """
    if request.method == "POST":
        user_message = request.form.get("message", "")
        files = request.files.getlist('files')  # Get multiple files

        if user_message or files:
            send_message(conv_id, user_message, files)
        print(f"Conversation {conv_id} updated.")
        print(f"user_message: {user_message}")

        return redirect(url_for('chat', conv_id=conv_id, _anchor="bottom"))
    print(conversation_settings[conv_id])
    conv = get_conversation(conv_id)
    settings = conversation_settings.get(conv_id, {
        'model': 'claude-3-sonnet-20240229',
        'mode': 'casual',
        'system': MODE_CONFIGS['casual']['system']
    })
    
    terminal_output = ""
    
    # Add welcome message if conversation is empty
    if not conv:
        terminal_output += f'''<div class="welcome-message">
<h2>Welcome to Terminal {conv_id}</h2>
<p>Model: {settings['model']}<br>Mode: {settings['mode']}</p>
<hr>
</div>'''
    
    # Process conversation into terminal output
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

            terminal_output += f'<div class="user-message">{user_text}</div>'
        
        elif msg["role"] == "assistant":
            # Extract just the text content from the assistant's response
            assistant_text = ""
            if isinstance(msg["content"], list):
                for content_item in msg["content"]:
                    if isinstance(content_item, dict) and "text" in content_item:
                        assistant_text += content_item["text"]
            else:
                assistant_text = str(msg["content"])
            
            # Process Python code blocks
            import re
            pattern = r'```(\w+)?\s*([\s\S]*?)```'

            def replace_code_block(match):
                language = match.group(1) or "code"
                code = match.group(2)
                block_id = f'code-{hash(code)}'
                return f'''
                <div class="code-block" id="{block_id}">
                    <div class="code-header">
                        <span class="code-language">{language.capitalize()}</span>
                        <button class="copy-button" onclick="copyCode('{block_id}')">Copy</button>
                    </div>
                    <pre><code class="{language}">{code}</code></pre>
                </div>
                '''

            # pattern = r'```python\s*([\s\S]*?)```'
            
            # # Function to replace code blocks with styled versions
            # def replace_code_block(match):
            #     code = match.group(1)
            #     block_id = f'code-{hash(code)}'
            #     return f'''
            #     <div class="code-block" id="{block_id}">
            #         <div class="code-header">
            #             <span class="code-language">Python</span>
            #             <button class="copy-button" onclick="copyCode('{block_id}')">Copy</button>
            #         </div>
            #         <pre><code>{code}</code></pre>
            #     </div>
            #     '''
            
            # Replace code blocks in the text
            processed_text = re.sub(pattern, replace_code_block, assistant_text)
            
            # Add the processed text to terminal output
            terminal_output += f'<div class="assistant-message">{processed_text}</div>'

    return render_template('chat.html', conv_id=conv_id, terminal_output=terminal_output, settings=settings)

if __name__ == "__main__":
    print("Server running at http://localhost:5000")
    app.run(debug=False)