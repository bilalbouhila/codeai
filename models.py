import base64
from anthropic import Anthropic
from config import  TEMP_RESPONSE_FILE
import getpass

# Paramètres de l'API
API_URL = "https://api.anthropic.com/v1/complete"  # URL de l'endpoint Claude
API_KEY = getpass.getpass("Entrez votre clé API Anthropic : ")

# Initialize Anthropic client
client = Anthropic(api_key=API_KEY)

# Global conversations store
conversations = {}

def save_response_to_file(response_text):
    """
    Save response to a temporary local file
    """
    try:
        with open(TEMP_RESPONSE_FILE, 'w', encoding='utf-8') as file:
            file.write(response_text)
        print(f"Response saved to {TEMP_RESPONSE_FILE}")
    except Exception as e:
        print(f"Error saving response: {e}")

def process_file(file):
    """
    Process a file and return its content as a message
    """
    try:
        # Read file content
        file_content = file.read()
        file_type = file.content_type
        
        # For images
        if file_type.startswith('image/'):
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": file_type,
                    "data": base64.b64encode(file_content).decode('utf-8')
                }
            }
        
        # For text files
        elif file_type.startswith('text/') or file.filename.endswith(('.txt', '.py', '.js', '.html', '.css', '.json', '.md')):
            try:
                text_content = file_content.decode('utf-8')
                return {
                    "type": "text",
                    "text": f"Content of {file.filename}:\n```\n{text_content}\n```"
                }
            except UnicodeDecodeError:
                return {
                    "type": "text",
                    "text": f"[Error: Unable to read {file.filename} as text]"
                }
        
        # For other file types
        else:
            return {
                "type": "text",
                "text": f"[File: {file.filename} ({file_type}) - Binary file]"
            }
    except Exception as e:
        return {
            "type": "text",
            "text": f"[Error processing file {file.filename}: {str(e)}]"
        }

def send_message(conv_id, user_message, files=None):
    """
    Enhanced function to send messages and files to Claude
    """
    conv = conversations.get(conv_id, [])

    # Get conversation settings
    from app import conversation_settings
    settings = conversation_settings.get(conv_id, {
        'model': 'claude-3-sonnet-20240229',
        'mode': 'casual',
        'system': "You are a helpful assistant."
    })

    # Prepare user message
    message_content = []

    # Add text content if present
    if user_message:
        message_content.append({
            "type": "text",
            "text": user_message
        })

    # Add files if they exist
    if files:
        if not isinstance(files, list):
            files = [files]
        
        for file in files:
            if file and file.filename:
                file_content = process_file(file)
                if file_content:
                    message_content.append(file_content)
                # Reset file pointer for potential reuse
                file.seek(0)

    # Add message to conversation
    conv.append({"role": "user", "content": message_content})

    try:
        response = client.messages.create(
            model=settings['model'],
            max_tokens=4000,
            messages=conv,
            system=settings['system']  # Pass system message as a separate parameter
        )
        print(settings['system'] + "\n")

        # Extract text from all text blocks in the response
        assistant_response_text = ""
        for content in response.content:
            if content.type == 'text':
                assistant_response_text += content.text

        # Save response to temporary file
        save_response_to_file(assistant_response_text)

    except Exception as e:
        assistant_response_text = f"API Request Error: {e}"
        save_response_to_file(assistant_response_text)

    # Store assistant's response in conversation
    conv.append({"role": "assistant", "content": [{"type": "text", "text": assistant_response_text}]})
    conversations[conv_id] = conv
    return assistant_response_text

def get_conversation(conv_id):
    """
    Get a conversation by ID
    """
    return conversations.get(conv_id, [])

def create_conversation():
    """
    Create a new conversation
    """
    conv_id = len(conversations) + 1
    conversations[conv_id] = []
    return conv_id

def get_all_conversations():
    """
    Get all conversation IDs
    """
    return sorted(conversations.keys())