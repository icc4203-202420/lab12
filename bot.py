from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_community.chat_message_histories import ChatMessageHistory

from dotenv import load_dotenv
import os

from games.hangman import Hangman


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
# Diccionario para almacenar juegos activos por chat
active_games = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = "¡Hola! Soy un chatbot. Usa /juegos para ver los juegos disponibles."
    await update.message.reply_text(message)
    
    # Guardar en el historial
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    memory_key = get_memory_key(update)
    
    if memory_key not in chat_histories:
        chat_histories[memory_key] = ChatMessageHistory()
    
    chat_histories[memory_key].add_user_message(update.message.text)
    chat_histories[memory_key].add_ai_message(message)

def get_memory_key(update: Update) -> str:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if update.effective_chat.type == Chat.GROUP:
        return f"group_{chat_id}"
    return f"private_{chat_id}_{user_id}"

async def rendirse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    memory_key = get_memory_key(update)
    
    if chat_id not in active_games:
        message = "No hay ningún juego activo en este momento."
        await update.message.reply_text(message)
        chat_histories[memory_key].add_user_message("/rendirse")
        chat_histories[memory_key].add_ai_message(message)
        return
        
    game = active_games[chat_id]
    message = f"Juego terminado. La palabra era: {game.word}"
    await update.message.reply_text(message)
    
    # Guardar en el historial
    chat_histories[memory_key].add_user_message("/rendirse")
    chat_histories[memory_key].add_ai_message(message)
    
    # Eliminar el juego activo
    del active_games[chat_id]

async def juegos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Ahorcado", callback_data='juego_1')],
        [InlineKeyboardButton("Juego 2", callback_data='juego_2')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = "Selecciona un juego:"
    await update.message.reply_text(message, reply_markup=reply_markup)
    
    # Guardar en el historial
    memory_key = get_memory_key(update)
    if memory_key not in chat_histories:
        chat_histories[memory_key] = ChatMessageHistory()
    
    chat_histories[memory_key].add_user_message(update.message.text)
    chat_histories[memory_key].add_ai_message(message)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    memory_key = get_memory_key(update)

    if query.data == 'juego_1':
        if chat_id in active_games:
            message = "Ya hay un juego en curso en este chat."
            await query.edit_message_text(text=message)
            chat_histories[memory_key].add_ai_message(message)
            return

        game = Hangman("python")
        active_games[chat_id] = game
        message = (
            "¡Ahorcado iniciado! Adivina la palabra letra por letra.\n\n"
            f"Palabra: {game.get_masked_word()}\n"
            f"Vidas restantes: {game.lives}"
        )
        await query.edit_message_text(text=message)
        chat_histories[memory_key].add_ai_message(message)
        
    elif query.data == 'juego_2':
        message = "¡Has seleccionado Juego 2!"
        await query.edit_message_text(text=message)
        chat_histories[memory_key].add_ai_message(message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_message = update.message.text
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)
    memory_key = get_memory_key(update)
    
    # Inicializar el historial si no existe
    if memory_key not in chat_histories:
        chat_histories[memory_key] = ChatMessageHistory()
    
    # Formatear el mensaje para grupos
    if update.effective_chat.type == Chat.GROUP:
        formatted_message = f"{username}: {user_message}"
    else:
        formatted_message = user_message
    
    # Agregar mensaje del usuario al historial
    chat_histories[memory_key].add_user_message(formatted_message)
    
    # Verificar si es una mención al bot en grupo
    is_bot_mention = '@app_moviles_bot' in user_message
    
    # Manejar el juego activo
    if chat_id in active_games and not is_bot_mention:
        game = active_games[chat_id]
        
        # Verificar si es una letra válida
        if len(user_message) != 1 or not user_message.isalpha():
            message = "Por favor, introduce solo una letra o mencióname si quieres hablar conmigo."
            await update.message.reply_text(message)
            chat_histories[memory_key].add_ai_message(message)
            return

        guess = user_message.lower()
        result = game.guess(guess)
        
        response = f"{result}\n\nPalabra: {game.get_masked_word()}\nVidas restantes: {game.lives}\nLetras incorrectas: {', '.join(game.incorrect_guesses)}"
        await update.message.reply_text(response)
        chat_histories[memory_key].add_ai_message(response)

        if game.is_game_over():
            if game.get_masked_word().replace(' ', '') == game.word:
                message = "¡Felicidades! Adivinaste la palabra."
            else:
                message = f"Perdiste. La palabra era: {game.word}"
            await update.message.reply_text(message)
            chat_histories[memory_key].add_ai_message(message)
            del active_games[chat_id]
        return
    
    # Procesar mensaje con el chatbot si:
    # 1. Es un chat privado
    # 2. Es una mención en grupo
    should_respond = (
        update.effective_chat.type == Chat.PRIVATE or
        is_bot_mention
    )

    if should_respond:
        try:
            all_messages = chat_histories[memory_key].messages
            if update.effective_chat.type == Chat.GROUP:
                system_message = HumanMessage(content="""Eres un asistente en un grupo de chat. 
                Los mensajes que ves tienen el formato "usuario: mensaje".
                Cuando respondas, ten en cuenta todo el contexto de la conversación del grupo.
                Si te preguntan sobre lo que ha dicho alguien, menciona específicamente quién lo dijo.""")
                all_messages = [system_message] + all_messages

            response = await llm.ainvoke(all_messages)
            chat_histories[memory_key].add_ai_message(response.content)
            await update.message.reply_text(response.content)
            
        except Exception as e:
            print(f"Error al procesar mensaje: {e}")
            message = "Lo siento, hubo un error al procesar tu mensaje. Por favor, intenta de nuevo."
            await update.message.reply_text(message)
            chat_histories[memory_key].add_ai_message(message)

def main() -> None:
    print("Starting bot...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("juegos", juegos))
    application.add_handler(CommandHandler("rendirse", rendirse)) 
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()