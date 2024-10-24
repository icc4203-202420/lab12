from telegram import Update, Chat
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from dotenv import load_dotenv

load_dotenv("/.env")

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Inicializar el modelo de lenguaje
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model="gpt-4"
)

# Almacenar historiales de chat por usuario/grupo
chat_histories = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("¡Hola! Soy un chatbot. ¿En qué puedo ayudarte hoy?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_message = update.message.text
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)

    # Si es un grupo, usar solo el chat_id como clave
    # Si es privado, usar combinación de chat_id y user_id
    if update.effective_chat.type == Chat.GROUP:
        memory_key = f"group_{chat_id}"
        # Agregar el nombre del usuario al mensaje para mantener contexto
        user_message = f"{username}: {user_message}"
    else:
        memory_key = f"private_{chat_id}_{user_id}"

    # Inicializar o recuperar el historial de chat
    if memory_key not in chat_histories:
        chat_histories[memory_key] = ChatMessageHistory()

    history = chat_histories[memory_key]

    # Siempre guardar el mensaje en el historial, independientemente del tipo de chat
    history.add_user_message(user_message)

    # Determinar si el bot debe responder
    should_respond = (
        update.effective_chat.type == Chat.PRIVATE or
        (update.effective_chat.type == Chat.GROUP and '@app_moviles_bot' in user_message)
    )

    if should_respond:
        try:
            # Obtener todo el historial de mensajes
            all_messages = history.messages

            # Si es un grupo, agregar contexto adicional al prompt
            if update.effective_chat.type == Chat.GROUP:
                system_message = HumanMessage(content="""Eres un asistente en un grupo de chat. 
                Los mensajes que ves tienen el formato "usuario: mensaje".
                Cuando respondas, ten en cuenta todo el contexto de la conversación del grupo.
                Si te preguntan sobre lo que ha dicho alguien, menciona específicamente quién lo dijo.""")
                all_messages = [system_message] + all_messages

            # Obtener respuesta del modelo
            response = await llm.ainvoke(all_messages)
            
            # Guardar la respuesta del bot en el historial
            history.add_ai_message(response.content)
            
            # Enviar la respuesta
            await update.message.reply_text(response.content)
            
        except Exception as e:
            print(f"Error al procesar mensaje: {e}")
            await update.message.reply_text("Lo siento, hubo un error al procesar tu mensaje. Por favor, intenta de nuevo.")

def main() -> None:
    print("Starting bot...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()