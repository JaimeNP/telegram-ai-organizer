from app.models.message import TelegramMessage


def parse_message(message):
    from_user = message.from_user

    text = message.text or message.caption

    user_id = from_user.id if from_user else 0
    username = from_user.username if from_user else None
    full_name = from_user.full_name if from_user else "Usuario desconocido"

    return TelegramMessage(
        telegram_message_id=message.message_id,
        telegram_chat_id=message.chat.id,

        thread_id=message.message_thread_id,
        thread_name="General" if message.message_thread_id is None else f"Topic {message.message_thread_id}",

        user_id=user_id,
        username=username,
        full_name=full_name,

        text=text,

        has_photo=bool(message.photo),
        has_video=message.video is not None,
        has_document=message.document is not None,

        reply_to_message_id=message.reply_to_message.message_id if message.reply_to_message else None,

        date=message.date,
    )