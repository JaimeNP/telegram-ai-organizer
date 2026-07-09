from app.models.message import TelegramMessage


def parse_message(message):

    return TelegramMessage(

        telegram_message_id=message.message_id,
        telegram_chat_id=message.chat.id,

        thread_id=message.message_thread_id,
        thread_name="General" if message.message_thread_id is None else f"Topic {message.message_thread_id}",

        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,

        text=message.text,

        has_photo=message.photo is not None,
        has_video=message.video is not None,
        has_document=message.document is not None,

        reply_to_message_id=message.reply_to_message.message_id if message.reply_to_message else None,

        date=message.date
    )