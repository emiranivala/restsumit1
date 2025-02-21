import asyncio 
import time
import os
import re
import subprocess
import requests
import traceback
from devgagan import app
from devgagan import sex as gf
import pymongo
from pyrogram import filters
from pyrogram.errors import ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid, PeerIdInvalid
from pyrogram.enums import MessageMediaType
from devgagan.core.func import progress_bar, video_metadata, screenshot
from devgagan.core.mongo import db
from pyrogram.types import Message
from config import MONGO_DB as MONGODB_CONNECTION_STRING, LOG_GROUP, SECONDS
import cv2
from telethon import events, Button

def thumbnail(sender):
    return f'{sender}.jpg' if os.path.exists(f'{sender}.jpg') else None

MAX_CHUNK_SIZE = 2000 * 1024**2

def split_file(file_path, chunk_size=MAX_CHUNK_SIZE):
    chunk_files = []
    chunk_number = 1
    buffer_size = 64 * 1024
    with open(file_path, "rb") as f:
        while True:
            bytes_written = 0
            chunk_filename = f"{file_path}.part{chunk_number}"
            with open(chunk_filename, "wb") as chunk_file:
                while bytes_written < chunk_size:
                    data = f.read(min(buffer_size, chunk_size - bytes_written))
                    if not data:
                        break
                    chunk_file.write(data)
                    bytes_written += len(data)
            if bytes_written == 0:
                break
            chunk_files.append(chunk_filename)
            chunk_number += 1
    return chunk_files

async def delete_after(message, delay=5):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

async def get_msg(userbot, sender, edit_id, msg_link, i, message):
    edit = ""
    chat = ""
    round_message = False
    if "?single" in msg_link:
        msg_link = msg_link.split("?single")[0]
    msg_id = int(msg_link.split("/")[-1]) + int(i)
    
    # Modified block to handle public groups (t.me/) along with t.me/c/ and t.me/b/ links
    if 't.me/c/' in msg_link or 't.me/b/' in msg_link or 't.me/' in msg_link:
        try:
            if 't.me/b/' in msg_link:
                chat = int(msg_link.split("/")[-2])
            elif 't.me/c/' in msg_link:
                parts = msg_link.split("/")
                chat = int('-100' + str(parts[parts.index('c') + 1]))
            else:
                chat_name = msg_link.split('/')[-2]
                chat = (await userbot.get_chat(f"@{chat_name}")).id
        except Exception as e:
            print(f"ChatID Error: {e}")
            return
        file = ""
        try:
            chatx = message.chat.id
            msg = await userbot.get_messages(chat, msg_id)
            caption = None
            if msg.service is not None:
                return None
            if msg.empty is not None:
                return None
            if msg.media:
                snt_msgs = []
                if msg.media == MessageMediaType.WEB_PAGE:
                    target_chat_id = user_chat_ids.get(chatx, chatx)
                    edit = await app.edit_message_text(target_chat_id, edit_id, "Cloning...")
                    m = await app.send_message(sender, msg.text.markdown)
                    snt_msgs.append(m)
                    if msg.pinned_message:
                        try:
                            await m.pin(both_sides=True)
                        except Exception:
                            await m.pin()
                    await m.copy(LOG_GROUP)
                    try:
                        await edit.delete()
                    except Exception:
                        pass
                    await message.reply_text("Content will be deleted in 5 minutes.\nForward to saved messages", parse_mode="markdown")
                    await asyncio.sleep(SECONDS)
                    for m in snt_msgs:
                        try:
                            await m.delete()
                        except Exception:
                            pass
                    return
            if not msg.media:
                snt_msgs = []
                if msg.text:
                    target_chat_id = user_chat_ids.get(chatx, chatx)
                    edit = await app.edit_message_text(target_chat_id, edit_id, "Cloning...")
                    m = await app.send_message(sender, msg.text.markdown)
                    snt_msgs.append(m)
                    if msg.pinned_message:
                        try:
                            await m.pin(both_sides=True)
                        except Exception:
                            await m.pin()
                    await m.copy(LOG_GROUP)
                    try:
                        await edit.delete()
                    except Exception:
                        pass
                    await message.reply_text("Content will be deleted in 5 minutes.\nForward to saved messages", parse_mode="markdown")
                    await asyncio.sleep(SECONDS)
                    for m in snt_msgs:
                        try:
                            await m.delete()
                        except Exception:
                            pass
                    return
            edit = await app.edit_message_text(sender, edit_id, "Trying to Download...")
            file = await userbot.download_media(
                msg,
                progress=progress_bar,
                progress_args=("**__Downloading: __**", edit, time.time()))
            custom_rename_tag = get_user_rename_preference(chatx)
            last_dot_index = str(file).rfind('.')
            if last_dot_index != -1 and last_dot_index != 0:
                ggn_ext = str(file)[last_dot_index + 1:]
                if ggn_ext.isalpha() and len(ggn_ext) <= 4:
                    if ggn_ext.lower() == 'mov':
                        original_file_name = str(file)[:last_dot_index]
                        file_extension = ggn_ext.lower()
                        if file_extension == 'mov':
                            file_extension = 'mp4'
                    else:
                        original_file_name = str(file)[:last_dot_index]
                        file_extension = ggn_ext
                else:
                    original_file_name = str(file)
                    file_extension = 'mp4'
            else:
                original_file_name = str(file)
                file_extension = 'mp4'
            delete_words = load_delete_words(chatx)
            for word in delete_words:
                original_file_name = original_file_name.replace(word, "")
            video_file_name = original_file_name + " " + custom_rename_tag
            replacements = load_replacement_words(chatx)
            for word, replace_word in replacements.items():
                original_file_name = original_file_name.replace(word, replace_word)
            new_file_name = original_file_name + " " + custom_rename_tag + "." + file_extension
            os.rename(file, new_file_name)
            file = new_file_name
            file_size = os.path.getsize(file)
            if file_size > 2 * 1024**3:
                try:
                    await edit.delete()
                except Exception:
                    pass
                status_msg1 = await app.send_message(sender, f"Large file detected (> {file_size/1024**3:.2f} GB). Splitting into 2GB chunks...")
                status_msg2 = await app.send_message(sender, "Starting to split the file...")
                chunk_files = split_file(file, MAX_CHUNK_SIZE)
                total_chunks = len(chunk_files)
                status_msg3 = await app.send_message(sender, f"File split into {total_chunks} chunk(s).")
                target_chat_id = user_chat_ids.get(chatx, sender)
                delete_words = load_delete_words(sender)
                custom_caption = get_user_caption_preference(sender)
                original_caption = msg.caption if msg.caption else ''
                final_caption = f"{original_caption}"
                replacements = load_replacement_words(chatx)
                for word, replace_word in replacements.items():
                    final_caption = final_caption.replace(word, replace_word)
                caption = f"{final_caption}\n\n__**{custom_caption}**__" if custom_caption else f"{final_caption}"
                upload_failed = False
                for i, chunk in enumerate(chunk_files):
                    try:
                        chunk_status_msg = await app.send_message(sender, f"Uploading chunk {i+1} of {total_chunks}...")
                        progress_status = await app.send_message(sender, f"Uploading chunk {i+1} of {total_chunks} ...")
                        chunk_caption = caption + f"\n\nPart {i+1} of {total_chunks}"
                        devgaganin = await app.send_document(
                            chat_id=target_chat_id,
                            document=chunk,
                            caption=chunk_caption,
                            progress=progress_bar,
                            progress_args=('**Uploading...**', progress_status, time.time())
                        )
                        if msg.pinned_message:
                            try:
                                await devgaganin.pin(both_sides=True)
                            except Exception:
                                await devgaganin.pin()
                        try:
                            await devgaganin.copy(LOG_GROUP)
                        except Exception as e:
                            print(f"Error copying chunk to LOG_GROUP: {e}")
                        await app.edit_message_text(sender, progress_status.id, f"Chunk {i+1} of {total_chunks} uploaded successfully!")
                        asyncio.create_task(delete_after(chunk_status_msg))
                        asyncio.create_task(delete_after(progress_status))
                    except Exception as chunk_error:
                        upload_failed = True
                        await app.send_message(sender, f"Error uploading chunk {i+1}: {chunk_error}")
                    finally:
                        if os.path.exists(chunk):
                            os.remove(chunk)
                if os.path.exists(file):
                    os.remove(file)
                if not upload_failed:
                    asyncio.create_task(delete_after(status_msg1))
                    asyncio.create_task(delete_after(status_msg2))
                    asyncio.create_task(delete_after(status_msg3))
                    final_status = await app.send_message(sender, "All chunks uploaded successfully!")
                    asyncio.create_task(delete_after(final_status))
                return
            await app.edit_message_text(sender, edit_id, "Trying to Uplaod ...")
            if msg.media == MessageMediaType.VIDEO and msg.video.mime_type in ["video/mp4", "video/x-matroska"]:
                snt_msgs = []
                metadata = video_metadata(file)
                width = metadata['width']
                height = metadata['height']
                duration = metadata['duration']
                if duration <= 300:
                    devgaganin = await app.send_video(
                        chat_id=sender,
                        video=file,
                        caption=caption,
                        height=height,
                        width=width,
                        duration=duration,
                        thumb=None,
                        progress=progress_bar,
                        progress_args=('**UPLOADING:**\n', edit, time.time())
                    )
                    snt_msgs.append(devgaganin)
                    if msg.pinned_message:
                        try:
                            await devgaganin.pin(both_sides=True)
                        except Exception:
                            await devgaganin.pin()
                    try:
                        await devgaganin.copy(LOG_GROUP)
                    except Exception as e:
                        print(f"Error copying video to LOG_GROUP: {e}")
                    try:
                        await edit.delete()
                    except Exception:
                        pass
                    await message.reply_text("Content will be deleted in 5 minutes.\nForward to saved messages", parse_mode="markdown")
                    await asyncio.sleep(SECONDS)
                    for m in snt_msgs:
                        try:
                            await m.delete()
                        except Exception:
                            pass
                    return
                delete_words = load_delete_words(sender)
                custom_caption = get_user_caption_preference(sender)
                original_caption = msg.caption if msg.caption else ''
                final_caption = f"{original_caption}" if custom_caption else f"{original_caption}"
                replacements = load_replacement_words(sender)
                for word, replace_word in replacements.items():
                    final_caption = final_caption.replace(word, replace_word)
                caption = f"{final_caption}\n\n__**{custom_caption}**__" if custom_caption else f"{final_caption}"
                target_chat_id = user_chat_ids.get(chatx, chatx)
                thumb_path = await screenshot(file, duration, chatx)
                try:
                    devgaganin = await app.send_video(
                        chat_id=target_chat_id,
                        video=file,
                        caption=caption,
                        supports_streaming=True,
                        height=height,
                        width=width,
                        duration=duration,
                        thumb=thumb_path,
                        progress=progress_bar,
                        progress_args=('**__Uploading...__**', edit, time.time())
                    )
                    if msg.pinned_message:
                        try:
                            await devgaganin.pin(both_sides=True)
                        except Exception:
                            await devgaganin.pin()
                    try:
                        await devgaganin.copy(LOG_GROUP)
                    except Exception as e:
                        print(f"Error copying video to LOG_GROUP: {e}")
                except Exception:
                    try:
                        await app.edit_message_text(sender, edit_id, ".")
                    except Exception:
                        pass
                os.remove(file)
            elif msg.media == MessageMediaType.PHOTO:
                await app.edit_message_text(sender, edit_id, "**Uploading photo...**")
                delete_words = load_delete_words(sender)
                custom_caption = get_user_caption_preference(sender)
                original_caption = msg.caption if msg.caption else ''
                final_caption = f"{original_caption}\n\n__**{custom_caption}**__" if custom_caption else f"{original_caption}"
                target_chat_ids = user_chat_ids.get(sender, sender)
                devgaganin = await app.send_photo(chat_id=target_chat_ids, photo=file, caption=caption)
                if msg.pinned_message:
                    try:
                        await devgaganin.pin(both_sides=True)
                    except Exception:
                        await devgaganin.pin()
                try:
                    await devgaganin.copy(LOG_GROUP)
                except Exception as e:
                    print(f"Error copying photo to LOG_GROUP: {e}")
            else:
                thumb_path = thumbnail(chatx)
                delete_words = load_delete_words(sender)
                custom_caption = get_user_caption_preference(sender)
                original_caption = msg.caption if msg.caption else ''
                final_caption = f"{original_caption}\n\n__**{custom_caption}**__" if custom_caption else f"{original_caption}"
                target_chat_id = user_chat_ids.get(chatx, chatx)
                try:
                    if msg.media == MessageMediaType.DOCUMENT:
                        devgaganin = await app.send_document(
                            chat_id=target_chat_id,
                            document=file,
                            caption=caption,
                            thumb=thumb_path,
                            progress=progress_bar,
                            progress_args=('**Uploading...**', edit, time.time())
                        )
                    elif msg.media == MessageMediaType.AUDIO:
                        devgaganin = await app.send_audio(
                            chat_id=target_chat_id,
                            audio=file,
                            caption=caption,
                            progress=progress_bar,
                            progress_args=('**Uploading...**', edit, time.time())
                        )
                    elif msg.media == MessageMediaType.VOICE:
                        devgaganin = await app.send_voice(
                            chat_id=target_chat_id,
                            voice=file,
                            caption=caption,
                            progress=progress_bar,
                            progress_args=('**Uploading...**', edit, time.time())
                        )
                    else:
                        devgaganin = await app.send_document(
                            chat_id=target_chat_id,
                            document=file,
                            caption=caption,
                            thumb=thumb_path,
                            progress=progress_bar,
                            progress_args=('**Uploading...**', edit, time.time())
                        )
                except Exception:
                    try:
                        await app.edit_message_text(sender, edit_id, ".")
                    except Exception:
                        pass
                os.remove(file)
            try:
                await edit.delete()
            except Exception:
                pass
        except (ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid):
            try:
                await app.edit_message_text(sender, edit_id, "Have you joined the channel?")
            except Exception:
                pass
            return
        except Exception as e:
            if "PEER_ID_INVALID" in str(e):
                try:
                    await app.edit_message_text(sender, edit_id, ".")
                except Exception:
                    pass
            else:
                try:
                    await app.edit_message_text(sender, edit_id, f". Error: {e}")
                except Exception:
                    pass
    else:
        edit = await app.edit_message_text(sender, edit_id, "Cloning...")
        try:
            chat = msg_link.split("/")[-2]
            await copy_message_with_chat_id(app, sender, chat, msg_id)
            try:
                await edit.delete()
            except Exception:
                pass
        except Exception as e:
            try:
                await app.edit_message_text(sender, edit_id, f". Error: {e}")
            except Exception:
                pass

async def copy_message_with_chat_id(client, sender, chat_id, message_id):
    target_chat_id = user_chat_ids.get(sender, sender)
    try:
        msg = await client.get_messages(chat_id, message_id)
        custom_caption = get_user_caption_preference(sender)
        original_caption = msg.caption if msg.caption else ''
        final_caption = f"{original_caption}" if custom_caption else f"{original_caption}"
        delete_words = load_delete_words(sender)
        for word in delete_words:
            final_caption = final_caption.replace(word, '  ')
        replacements = load_replacement_words(sender)
        for word, replace_word in replacements.items():
            final_caption = final_caption.replace(word, replace_word)
        caption = f"{final_caption}\n\n__**{custom_caption}**__" if custom_caption else f"{final_caption}"
        if msg.media:
            if msg.media == MessageMediaType.VIDEO:
                result = await client.send_video(target_chat_id, msg.video.file_id, caption=caption)
            elif msg.media == MessageMediaType.DOCUMENT:
                result = await client.send_document(target_chat_id, msg.document.file_id, caption=caption)
            elif msg.media == MessageMediaType.PHOTO:
                result = await client.send_photo(target_chat_id, msg.photo.file_id, caption=caption)
            else:
                result = await client.copy_message(target_chat_id, chat_id, message_id)
        else:
            result = await client.copy_message(target_chat_id, chat_id, message_id)
        try:
            await result.copy(LOG_GROUP)
        except Exception:
            pass
        if msg.pinned_message:
            try:
                await result.pin(both_sides=True)
            except Exception:
                await result.pin()
    except Exception as e:
        try:
            await client.send_message(sender, f". Error in copy_message: {e}")
            await client.send_message(sender, ".")
        except Exception:
            pass

DB_NAME = "smart_users"
COLLECTION_NAME = "super_user"
mongo_client = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
db = mongo_client[DB_NAME]
collection = db[COLLECTION_NAME]

def load_authorized_users():
    authorized_users = set()
    for user_doc in collection.find():
        if "user_id" in user_doc:
            authorized_users.add(user_doc["user_id"])
    return authorized_users

def save_authorized_users(authorized_users):
    collection.delete_many({})
    for user_id in authorized_users:
        collection.insert_one({"user_id": user_id})

SUPER_USERS = load_authorized_users()
user_chat_ids = {}
MDB_NAME = "logins"
MCOLLECTION_NAME = "stringsession"
m_client = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
mdb = m_client[MDB_NAME]
mcollection = mdb[MCOLLECTION_NAME]

def load_delete_words(user_id):
    try:
        words_data = collection.find_one({"_id": user_id})
        if words_data:
            return set(words_data.get("delete_words", []))
        else:
            return set()
    except Exception as e:
        print(f"Error loading delete words: {e}")
        return set()

def save_delete_words(user_id, delete_words):
    try:
        collection.update_one(
            {"_id": user_id},
            {"$set": {"delete_words": list(delete_words)}},
            upsert=True
        )
    except Exception as e:
        print(f"Error saving delete words: {e}")

def load_replacement_words(user_id):
    try:
        words_data = collection.find_one({"_id": user_id})
        if words_data:
            return words_data.get("replacement_words", {})
        else:
            return {}
    except Exception as e:
        print(f"Error loading replacement words: {e}")
        return {}

def save_replacement_words(user_id, replacements):
    try:
        collection.update_one(
            {"_id": user_id},
            {"$set": {"replacement_words": replacements}},
            upsert=True
        )
    except Exception as e:
        print(f"Error saving replacement words: {e}")

user_rename_preferences = {}
user_caption_preferences = {}

def load_user_session(sender_id):
    user_data = collection.find_one({"user_id": sender_id})
    if user_data:
        return user_data.get("session")
    else:
        return None

async def set_rename_command(user_id, custom_rename_tag):
    user_rename_preferences[str(user_id)] = custom_rename_tag

def get_user_rename_preference(user_id):
    return user_rename_preferences.get(str(user_id), 'Team SPY')

async def set_caption_command(user_id, custom_caption):
    user_caption_preferences[str(user_id)] = custom_caption

def get_user_caption_preference(user_id):
    return user_caption_preferences.get(str(user_id), '')

sessions = {}
SET_PIC = "settings.jpg"
MESS = "Customize by your end and Configure your settings ..."

@gf.on(events.NewMessage(incoming=True, pattern='/settings'))
async def settings_command(event):
    buttons = [
        [Button.inline("Set Chat ID", b'setchat'), Button.inline("Set Rename Tag", b'setrename')],
        [Button.inline("Caption", b'setcaption'), Button.inline("Replace Words", b'setreplacement')],
        [Button.inline("Remove Words", b'delete'), Button.inline("Reset", b'reset')],
        [Button.inline("Login", b'addsession'), Button.inline("Logout", b'logout')],
        [Button.inline("Set Thumbnail", b'setthumb'), Button.inline("Remove Thumbnail", b'remthumb')],
        [Button.url("Report Errors", "https://t.me/She_who_remain")]
    ]
    await gf.send_file(
        event.chat_id,
        file=SET_PIC,
        caption=MESS,
        buttons=buttons
    )

pending_photos = {}

@gf.on(events.CallbackQuery)
async def callback_query_handler(event):
    user_id = event.sender_id
    if event.data == b'setchat':
        await event.respond("Send me the ID of that chat:")
        sessions[user_id] = 'setchat'
    elif event.data == b'setrename':
        await event.respond("Send me the rename tag:")
        sessions[user_id] = 'setrename'
    elif event.data == b'setcaption':
        await event.respond("Send me the caption:")
        sessions[user_id] = 'setcaption'
    elif event.data == b'setreplacement':
        await event.respond("Send me the replacement words in the format: 'WORD(s)' 'REPLACEWORD'")
        sessions[user_id] = 'setreplacement'
    elif event.data == b'addsession':
        await event.respond("This method depreciated ... use /login")
    elif event.data == b'delete':
        await event.respond("Send words seperated by space to delete them from caption/filename ...")
        sessions[user_id] = 'deleteword'
    elif event.data == b'logout':
        result = mcollection.delete_one({"user_id": user_id})
        if result.deleted_count > 0:
            await event.respond("Logged out and deleted session successfully.")
        else:
            await event.respond("You are not logged in")
    elif event.data == b'setthumb':
        pending_photos[user_id] = True
        await event.respond('Please send the photo you want to set as the thumbnail.')
    elif event.data == b'remthumb':
        try:
            os.remove(f'{user_id}.jpg')
            await event.respond('Thumbnail removed successfully!')
        except FileNotFoundError:
            await event.respond("No thumbnail found to remove.")

@gf.on(events.NewMessage(func=lambda e: e.sender_id in pending_photos))
async def save_thumbnail(event):
    user_id = event.sender_id
    if event.photo:
        temp_path = await event.download_media()
        if os.path.exists(f'{user_id}.jpg'):
            os.remove(f'{user_id}.jpg')
        os.rename(temp_path, f'./{user_id}.jpg')
        await event.respond('Thumbnail saved successfully!')
    else:
        await event.respond('Please send a photo... Retry')
    pending_photos.pop(user_id, None)

@gf.on(events.NewMessage)
async def handle_user_input(event):
    user_id = event.sender_id
    if user_id in sessions:
        session_type = sessions[user_id]
        if session_type == 'setchat':
            try:
                chat_id = int(event.text)
                user_chat_ids[user_id] = chat_id
                await event.respond("Chat ID set successfully!")
            except ValueError:
                await event.respond("Invalid chat ID!")
        elif session_type == 'setrename':
            custom_rename_tag = event.text
            await set_rename_command(user_id, custom_rename_tag)
            await event.respond(f"Custom rename tag set to: {custom_rename_tag}")
        elif session_type == 'setcaption':
            custom_caption = event.text
            await set_caption_command(user_id, custom_caption)
            await event.respond(f"Custom caption set to: {custom_caption}")
        elif session_type == 'setreplacement':
            match = re.match(r"'(.+)' '(.+)'", event.text)
            if not match:
                await event.respond("Usage: 'WORD(s)' 'REPLACEWORD'")
            else:
                word, replace_word = match.groups()
                delete_words = load_delete_words(user_id)
                if word in delete_words:
                    await event.respond(f"The word '{word}' is in the delete set and cannot be replaced.")
                else:
                    replacements = load_replacement_words(user_id)
                    replacements[word] = replace_word
                    save_replacement_words(user_id, replacements)
                    await event.respond(f"Replacement saved: '{word}' will be replaced with '{replace_word}'")
        elif session_type == 'addsession':
            session_data = {
                "user_id": user_id,
                "session_string": event.text
            }
            mcollection.update_one(
                {"user_id": user_id},
                {"$set": session_data},
                upsert=True
            )
            await event.respond("Session string added successfully.")
        elif session_type == 'deleteword':
            words_to_delete = event.message.text.split()
            delete_words = load_delete_words(user_id)
            delete_words.update(words_to_delete)
            save_delete_words(user_id, delete_words)
            await event.respond(f"Words added to delete list: {', '.join(words_to_delete)}")
        del sessions[user_id]
