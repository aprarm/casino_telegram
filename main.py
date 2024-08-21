from config import *
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command, Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiocryptopay import AioCryptoPay, Networks
from aiocryptopay.exceptions import CodeErrorFactory
from re import compile, sub
import logging
from functions import *
from json import loads, dumps
from random import randint, choices
from datetime import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, parse_mode='HTML')
dp = Dispatcher(bot)

coinflip_heads_chance = (2, 1, 2)
coinflip_tails_chance = (1, 2, 1)

crypto = AioCryptoPay(token=CRYPTOBOT_TOKEN, network=Networks.MAIN_NET)

is_promotion = False
promotion_message = None
promotion_prize = 0
promotion_bets = []

async def get_max_promo():
    global promotion_bets

    max_promo = (None, 0)
    for bet in promotion_bets:
        if bet[2] > max_promo[1]:
            max_promo = (bet[0], bet[2], bet[1])
    return max_promo

async def update_promo_message():
    global promotion_message

    max_promo = await get_max_promo()
    await promotion_message.edit_text('''[💎] Бонус от <a href="https://t.me/+-0qkbRaDO484ZWEy">ForsBet</a> 

<code>Самая большая ставка до 22:00 получит 15$</code>

<code>Никнейм — %s</code>

<code>Сумма ставки — %.2f$</code>

<b><i>Прежде чем сделать ставку прочтите — https://teletype.in/@forsbet/help</i></b>

<u>Переходник — @forsb3t</u>''' % (max_promo[0], max_promo[1]))

async def count_bet(user, amount):
    global is_promotion
    global promotion_bets
    global promotion_message
    global promotion_prize

    if time() > time(22,0):
        is_promotion = False
        promotion_bets = []

        max_promo = await get_max_promo()

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton('🎁 Забрать выплату', url=SUPPORT_LINK))

        promotion_message = await bot.send_message('[💎] Выплата в %.2f$ за самую большую ставку для %s на сумму %f$' % (promotion_prize, max_promo[0], max_promo[1]), reply_markup=keyboard)
        await promotion_message.pin()

        return

    for i in range(len(promotion_bets)):
        if promotion_bets[i][1] == user[1]:
            promotion_bets[i][2] += amount
            await update_promo_message()
            return
    promotion_bets.append((user[0], user[1], amount))
    await update_promo_message()

@dp.message_handler(commands=['start_promotion'])
async def start_promotion(message: types.Message):
    global is_promotion
    global promotion_message
    global promotion_prize

    if message.chat.id in ADMINS:
        args = message.text.split()
        try:
            promotion_prize = float(args[1])
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton('Сделать ставку', url=INVOICE_LINK))
            promotion_message = await bot.send_message(CHANNEL_ID, '''[💎] Бонус от <a href="https://t.me/+-0qkbRaDO484ZWEy">ForsBet</a> 

<code>Самая большая ставка до 22:00 получит %i$</code>

<b><i>Прежде чем сделать ставку, прочтите — https://teletype.in/@forsbet/help</i></b>

<u>Переходник — @forsb3t</u>''' % promotion_prize, reply_markup=keyboard)
            await promotion_message.pin()
            is_promotion = True
            await bot.send_message(message.chat.id, "Акция успешно запущена!")
        except ValueError:
            await bot.send_message(message.chat.id, "Невалидная сумма приза!")

@dp.message_handler(commands=['create_invoice'])
async def create_invoice(message: types.Message):
    if message.chat.id in ADMINS:
        args = message.text.split()
        try:
            amount = float(args[1])
            invoice = await crypto.create_invoice(amount=amount, asset='USDT')
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("Пополнить", url=invoice.bot_invoice_url))
            await bot.send_message(message.chat.id, "Пополнение счёта на %i$" % amount, reply_markup=keyboard)
        except ValueError:
            await bot.send_message(message.chat.id, "Невалидная сумма пополнения!")

@dp.channel_post_handler(chat_id=LOGS_ID)
async def invoice_handler(message: types.Message):
    global is_promotion

    user = message.entities[0].user
    try:
        first_name = sub(compile('<.*?>'), '', user.first_name)
    except AttributeError:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton('Вернуть средства', url=SUPPORT_LINK))
        keyboard.add(InlineKeyboardButton('Сделать ставку', url=INVOICE_LINK))
        return await bot.send_message(CHANNEL_ID, '<b>❌ Ошибка у игрока %s</b>\n\n<b>Включите пересылку в Настройки > Конфиденциальность</b>\nСредства возвращены на ваш CryptoBot кошелёк <b>за вычетом комиссии 10%%</b>\n\n<u>Прочитайте <a href="%s">статью</> ниже перед тем, как делать ставку.</u>' % (first_name, HELP_LINK), reply_markup=keyboard)
    invoice = await get_invoice_from_message(message.text)
    amount = invoice['amount']

    try:
        if is_promotion: await count_bet((first_name, user.id), amount)
    except:
        pass

    try:
        comment = invoice['comment']
        bet = comment.lower()
    except AttributeError:
        cashback = amount - (amount / 10)
        check = await crypto.create_check(asset='USDT', amount=cashback, pin_to_user_id=user.id)
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton('Вернуть средства', url=check.bot_check_url))
        keyboard.add(InlineKeyboardButton('Сделать ставку', url=INVOICE_LINK))
        return await bot.send_message(CHANNEL_ID, '<b>❌ Ошибка у игрока %s</b>\n\n<b>Вы не указали команду!</b>\nСредства возвращены на ваш CryptoBot кошелёк <b>за вычетом комиссии 10%%</b>\n\n<u>Прочитайте <a href="%s">статью</> ниже перед тем, как делать ставку.</u>' % (first_name, HELP_LINK), reply_markup=keyboard)

    logger.info(f"NEW PAY | USER @{user.username} | {user.id} | PAY: {amount} | COMMENT: {comment}")
    
    await bot.send_message(CHANNEL_ID, '⚡️ Игрок <b>%s</b> ставит <b>%.2f$</b>\n\n<blockquote>Исход: %s</blockquote>\n\n<b>Удачи!</b>' % (first_name, amount, comment))
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton('Сделать ставку', url=INVOICE_LINK))
    try:
        if bet.startswith('куб'):
            try:
                value = int(bet.split()[1])
                dice_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')
                dice_value = dice_message.dice.value
                if dice_value == value:
                    check = await crypto.create_check(asset='USDT', amount=amount * 5, pin_to_user_id=user.id)
                    keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                    await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * 5, LINKS_TEXT), reply_markup=keyboard)
                else:
                    await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i].\n\n<blockquote>Бросай кубик заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
            except ValueError:
                cashback = amount - (amount / 10)
                check = await crypto.create_check(asset='USDT', amount=cashback, pin_to_user_id=user.id)
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton('Вернуть средства', url=check.bot_check_url))
                keyboard.add(InlineKeyboardButton('Сделать ставку', url=INVOICE_LINK))
                return await bot.send_message(CHANNEL_ID, '<b>❌ Ошибка у игрока %s</b>\n\n<b>Такой команды не существует!</b>\nСредства возвращены на ваш CryptoBot кошелёк <b>за вычетом комиссии 10%%</b>\n\n<u>Прочитайте <a href="%s">статью</> ниже перед тем, как делать ставку.</u>' % (first_name, HELP_LINK), reply_markup=keyboard)
        elif bet == 'меньше':
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')
            dice_value = dice_message.dice.value
            if dice_value in (1, 2, 3):
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            elif dice_value in (4, 5, 6):
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i].\n\n<blockquote>Бросай кубик заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet == 'больше':
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')
            dice_value = dice_message.dice.value
            if dice_value in (4, 5, 6):
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            elif dice_value in (1, 2, 3):
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i].\n\n<blockquote>Бросай кубик заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet in ('чётное', 'четное', 'чёт', 'чет'):
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')
            dice_value = dice_message.dice.value
            if dice_value in (2, 4, 6):
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            elif dice_value in (1, 3, 5):
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i].\n\n<blockquote>Бросай кубик заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet in ('нечётное', 'нечетное', 'нечёт', 'нечет'):
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')
            dice_value = dice_message.dice.value
            if dice_value in (1, 3, 5):
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            elif dice_value in (2, 4, 6):
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i].\n\n<blockquote>Бросай кубик заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet.startswith('wheel'):
            value = int(bet.split()[1])
            dice_value = randint(0, 36)
            await bot.send_sticker(CHANNEL_ID, WHEEL_STICKERS[dice_value])
            if dice_value == value:
                check = await crypto.create_check(asset='USDT', amount=amount * 35, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * 35, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i].\n\n<blockquote>Крути колесо заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet == '1-18':
            dice_value = randint(0, 36)
            await bot.send_sticker(CHANNEL_ID, WHEEL_STICKERS[dice_value])
            if dice_value in range(1, 19):
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i].\n\n<blockquote>Крути колесо заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet == '1-36':
            dice_value = randint(0, 36)
            await bot.send_sticker(CHANNEL_ID, WHEEL_STICKERS[dice_value])
            if dice_value in range(1, 37):
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i].\n\n<blockquote>Крути колесо заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet == '1-12':
            dice_value = randint(0, 36)
            await bot.send_sticker(CHANNEL_ID, WHEEL_STICKERS[dice_value])
            if dice_value in range(1, 13):
                check = await crypto.create_check(asset='USDT', amount=amount * 2.6, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * 2.6, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i].\n\n<blockquote>Крути колесо заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet == '13-24':
            dice_value = randint(0, 36)
            await bot.send_sticker(CHANNEL_ID, WHEEL_STICKERS[dice_value])
            if dice_value in range(13, 25):
                check = await crypto.create_check(asset='USDT', amount=amount * 2.6, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * 2.6, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i].\n\n<blockquote>Крути колесо заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet == '25-36':
            dice_value = randint(0, 36)
            await bot.send_sticker(CHANNEL_ID, WHEEL_STICKERS[dice_value])
            if dice_value in range(25, 37):
                check = await crypto.create_check(asset='USDT', amount=amount * 2.6, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * 2.6, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i].\n\n<blockquote>Крути колесо заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet == 'красное':
            dice_value = randint(0, 36)
            await bot.send_sticker(CHANNEL_ID, WHEEL_STICKERS[dice_value])
            if dice_value in (1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36):
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i], красное.\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            elif dice_value == 0:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i], зеленое.\n\n<blockquote>Крути колесо заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i], черное.\n\n<blockquote>Крути колесо заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet in ('черное', 'чёрное'):
            dice_value = randint(0, 36)
            await bot.send_sticker(CHANNEL_ID, WHEEL_STICKERS[dice_value])
            if dice_value in (2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35):
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i], черное.\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            elif dice_value == 0:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i], зеленое.\n\n<blockquote>Крути колесо заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i], красное.\n\n<blockquote>Крути колесо заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet in ('зеленое', 'зелёное'):
            dice_value = randint(0, 36)
            await bot.send_sticker(CHANNEL_ID, WHEEL_STICKERS[dice_value])
            if dice_value == 0:
                check = await crypto.create_check(asset='USDT', amount=amount * 35, pin_to_user_id=user.id)
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпало значение [%i], зеленое.\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            elif dice_value in (2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35):
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i], черное.\n\n<blockquote>Крути колесо заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпало значение [%i], красное.\n\n<blockquote>Крути колесо заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet in ('орел', 'орёл'):
            rand = randint(0, 2)
            dice_value = coinflip_heads_chance[rand] if amount < 5 else 1
            await bot.send_sticker(CHANNEL_ID, HEADS_AND_TAILS_STICKERS[dice_value-1])
            if dice_value == 1:
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпал орёл.\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпала решка.\n\n<blockquote>Бросай монетку заново и испытай свою удачу!</blockquote></b>\n\n%s' % LINKS_TEXT, reply_markup=keyboard)
        elif bet == 'решка':
            rand = randint(0, 2)
            dice_value = coinflip_tails_chance[rand] if amount < 5 else 1
            await bot.send_sticker(CHANNEL_ID, HEADS_AND_TAILS_STICKERS[dice_value-1])
            if dice_value == 2:
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Выпала решка.\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Выпал орёл.\n\n<blockquote>Бросай монетку заново и испытай свою удачу!</blockquote></b>\n\n%s' % LINKS_TEXT, reply_markup=keyboard)
        elif bet == 'слоты':
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='🎰')
            dice_value = dice_message.dice.value
            if dice_value in (1, 22, 43):
                check = await crypto.create_check(asset='USDT', amount=amount * 7, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Занос!\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (amount * 7, LINKS_TEXT), reply_markup=keyboard)
            elif dice_value in (16, 32, 48):
                check = await crypto.create_check(asset='USDT', amount=amount * 5, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Куш!\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (amount * 5, LINKS_TEXT), reply_markup=keyboard)
            elif dice_value == 64:
                check = await crypto.create_check(asset='USDT', amount=amount * 10, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Джекпот!\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (amount * 10, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш!\n\n<blockquote>Крути слоты заново и испытай свою удачу!</blockquote></b>\n\n%s' % LINKS_TEXT, reply_markup=keyboard)
        elif bet in ('к', 'н', 'б'):
            if bet == 'к':
                await bot.send_message(CHANNEL_ID, '✊')
                await bot.send_message(CHANNEL_ID, '✋')
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш!\n\n<blockquote>Играй заново и испытай свою удачу!</blockquote></b>\n\n%s' % LINKS_TEXT, reply_markup=keyboard)
            elif bet == 'н':
                await bot.send_message(CHANNEL_ID, '✌️')
                await bot.send_message(CHANNEL_ID, '✊')
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш!\n\n<blockquote>Играй заново и испытай свою удачу!</blockquote></b>\n\n%s' % LINKS_TEXT, reply_markup=keyboard)
            elif bet == 'б':
                await bot.send_message(CHANNEL_ID, '✋')
                await bot.send_message(CHANNEL_ID, '✌')
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш!\n\n<blockquote>Играй заново и испытай свою удачу!</blockquote></b>\n\n%s' % LINKS_TEXT, reply_markup=keyboard)
        elif bet == 'центр':
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='🎯')
            dice_value = dice_message.dice.value
            if dice_value == 6:
                check = await crypto.create_check(asset='USDT', amount=amount * 3, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>Победа!</b>\n\n<blockquote>Победитель может забрать <b>чек на сумму в размере %.2f$.</b></blockquote>\n\n%s' % (amount * 3, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>Проигрыш!\n\n<blockquote>Бросай дротик заново и испытай свою удачу!</blockquote></b>\n\n%s' % (LINKS_TEXT), reply_markup=keyboard)
        elif bet == 'красный':
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='🎯')
            dice_value = dice_message.dice.value
            if dice_value % 2 == 0:
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>Победа!</b>\n\n<blockquote>Победитель может забрать <b>чек на сумму в размере %.2f$.</b></blockquote>\n\n%s' % (amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>Проигрыш!\n\n<blockquote>Бросай дротик заново и испытай свою удачу!</blockquote></b>\n\n%s' % (LINKS_TEXT), reply_markup=keyboard)
        elif bet == 'белый':
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='🎯')
            dice_value = dice_message.dice.value
            if dice_value % 2 != 0:
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>Победа!</b>\n\n<blockquote>Победитель может забрать <b>чек на сумму в размере %.2f$.</b></blockquote>\n\n%s' % (amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>Проигрыш!\n\n<blockquote>Бросай дротик заново и испытай свою удачу!</blockquote></b>\n\n%s' % (LINKS_TEXT), reply_markup=keyboard)
        elif bet == 'гол':
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='⚽')
            dice_value = dice_message.dice.value
            if dice_value in (3, 4, 5):
                check = await crypto.create_check(asset='USDT', amount=amount * 1.5, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>Победа!</b>\n\n<blockquote>Победитель может забрать <b>чек на сумму в размере %.2f$.</b></blockquote>\n\n%s' % (amount * 1.5, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>Проигрыш!\n\n<blockquote>Пинай мяч заново и испытай свою удачу!</blockquote></b>\n\n%s' % (LINKS_TEXT), reply_markup=keyboard)
        elif bet == 'промах':
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='⚽')
            dice_value = dice_message.dice.value
            if dice_value in (1, 2):
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>Победа!</b>\n\n<blockquote>Победитель может забрать <b>чек на сумму в размере %.2f$.</b></blockquote>\n\n%s' % (amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>Проигрыш!\n\n<blockquote>Пинай мяч заново и испытай свою удачу!</blockquote></b>\n\n%s' % (LINKS_TEXT), reply_markup=keyboard)
        elif bet == 'попал':
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='🏀')
            dice_value = dice_message.dice.value
            if dice_value in (4, 5):
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>Победа!</b>\n\n<blockquote>Победитель может забрать <b>чек на сумму в размере %.2f$.</b></blockquote>\n\n%s' % (amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>Проигрыш!\n\n<blockquote>Бросай мяч заново и испытай свою удачу!</blockquote></b>\n\n%s' % (LINKS_TEXT), reply_markup=keyboard)
        elif bet == 'мимо':
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='🏀')
            dice_value = dice_message.dice.value
            if dice_value in (1, 2, 3):
                check = await crypto.create_check(asset='USDT', amount=amount * 1.5, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>Победа!</b>\n\n<blockquote>Победитель может забрать <b>чек на сумму в размере %.2f$.</b></blockquote>\n\n%s' % (amount * 1.5, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>Проигрыш!\n\n<blockquote>Бросай мяч заново и испытай свою удачу!</blockquote></b>\n\n%s' % (LINKS_TEXT), reply_markup=keyboard)
        elif bet in ('все', 'страйк', 'strike'):
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='🎳')
            dice_value = dice_message.dice.value
            if dice_value == 6:
                check = await crypto.create_check(asset='USDT', amount=amount * 2, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>Победа!</b>\n\n<blockquote>Победитель может забрать <b>чек на сумму в размере %.2f$.</b></blockquote>\n\n%s' % (amount * 2, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>Проигрыш!\n\n<blockquote>Бросай шар заново и испытай свою удачу!</blockquote></b>\n\n%s' % (LINKS_TEXT), reply_markup=keyboard)
        elif bet in ('1', '2', '3', '4', '5', '6'):
            bet = int(bet)
            dice_message = await bot.send_dice(CHANNEL_ID, emoji='🎳')
            dice_value = dice_message.dice.value
            if bet in (1, 2, 3):
                if 6 - dice_value == bet:
                    check = await crypto.create_check(asset='USDT', amount=amount * 3, pin_to_user_id=user.id)
                    keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                    await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>Победа!</b>\n\n<blockquote>Победитель может забрать <b>чек на сумму в размере %.2f$.</b></blockquote>\n\n%s' % (amount * 3, LINKS_TEXT), reply_markup=keyboard)
                else:
                    await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>Проигрыш!\n\n<blockquote>Бросай шар заново и испытай свою удачу!</blockquote></b>\n\n%s' % (LINKS_TEXT), reply_markup=keyboard)
            elif bet == 4:
                    await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>Проигрыш!\n\n<blockquote>Бросай шар заново и испытай свою удачу!</blockquote></b>\n\n%s' % (LINKS_TEXT), reply_markup=keyboard)
            elif bet == 5:
                if dice_value == 2:
                    check = await crypto.create_check(asset='USDT', amount=amount * 3, pin_to_user_id=user.id)
                    keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                    await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>Победа!</b>\n\n<blockquote>Победитель может забрать <b>чек на сумму в размере %.2f$.</b></blockquote>\n\n%s' % (amount * 3, LINKS_TEXT), reply_markup=keyboard)
                else:
                    await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>Проигрыш!\n\n<blockquote>Бросай шар заново и испытай свою удачу!</blockquote></b>\n\n%s' % (LINKS_TEXT), reply_markup=keyboard)
            elif bet == 6:
                if dice_value == 1:
                    check = await crypto.create_check(asset='USDT', amount=amount * 3, pin_to_user_id=user.id)
                    keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                    await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>Победа!</b>\n\n<blockquote>Победитель может забрать <b>чек на сумму в размере %.2f$.</b></blockquote>\n\n%s' % (amount * 3, LINKS_TEXT), reply_markup=keyboard)
                else:
                    await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>Проигрыш!\n\n<blockquote>Бросай шар заново и испытай свою удачу!</blockquote></b>\n\n%s' % (LINKS_TEXT), reply_markup=keyboard)
        elif bet in ('п1', 'победа 1', 'пвп', 'дуэль'):
            dice1_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')
            dice2_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')

            dice1_value = dice1_message.dice.value
            dice2_value = dice2_message.dice.value

            if dice1_value > dice2_value:
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Сессия закрыта в пользу первого кубика [%i:%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice1_value, dice2_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Сессия закрыта в пользу второго кубика [%i:%i].\n\n<blockquote>Бросай кубики заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice1_value, dice2_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet in ('п2', 'победа 2'):
            dice1_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')
            dice2_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')

            dice1_value = dice1_message.dice.value
            dice2_value = dice2_message.dice.value

            if dice2_value > dice1_value:
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Сессия закрыта в пользу второго кубика [%i:%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice1_value, dice2_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Сессия закрыта в пользу первого кубика [%i:%i].\n\n<blockquote>Бросай кубики заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice1_value, dice2_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet == 'ничья':
            dice1_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')
            dice2_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')

            dice1_value = dice1_message.dice.value
            dice2_value = dice2_message.dice.value

            if dice1_value == dice2_value:
                check = await crypto.create_check(asset='USDT', amount=amount * COEFFICIENT, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Сессия закрыта со счетом [%i:%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice1_value, dice2_value, amount * 3, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Сессия закрыта со счетом [%i:%i].\n\n<blockquote>Бросай кубики заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice1_value, dice2_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet in ('2м', '2 меньше'):
            dice1_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')
            dice2_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')

            dice1_value = dice1_message.dice.value
            dice2_value = dice2_message.dice.value

            if dice1_value < 4 and dice2_value < 4:
                check = await crypto.create_check(asset='USDT', amount=amount * 2.6, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Сессия закрыта со счетом [%i:%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice1_value, dice2_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Сессия закрыта со счетом [%i:%i].\n\n<blockquote>Бросай кубики заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice1_value, dice2_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet in ('2б', '2 больше'):
            dice1_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')
            dice2_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')

            dice1_value = dice1_message.dice.value
            dice2_value = dice2_message.dice.value

            if dice1_value > 3 and dice2_value > 3:
                check = await crypto.create_check(asset='USDT', amount=amount * 2.6, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Сессия закрыта со счетом [%i:%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice1_value, dice2_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Сессия закрыта со счетом [%i:%i].\n\n<blockquote>Бросай кубики заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice1_value, dice2_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet in ('2н', '2 нечет', '2 нечёт'):
            dice1_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')
            dice2_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')

            dice1_value = dice1_message.dice.value
            dice2_value = dice2_message.dice.value

            if dice1_value in (1, 3, 5) and dice2_value in (1, 3, 5):
                check = await crypto.create_check(asset='USDT', amount=amount * 2.6, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Сессия закрыта со счетом [%i:%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice1_value, dice2_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Сессия закрыта со счетом [%i:%i].\n\n<blockquote>Бросай кубики заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice1_value, dice2_value, LINKS_TEXT), reply_markup=keyboard)
        elif bet in ('2ч', '2 чет', '2 чёт'):
            dice1_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')
            dice2_message = await bot.send_dice(CHANNEL_ID, emoji='🎲')

            dice1_value = dice1_message.dice.value
            dice2_value = dice2_message.dice.value

            if dice1_value in (2, 4, 6) and dice2_value in (2, 4, 6):
                check = await crypto.create_check(asset='USDT', amount=amount * 2.6, pin_to_user_id=user.id)
                keyboard.add(InlineKeyboardButton('🎁 Забрать чек', url=check.bot_check_url))
                await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа! Сессия закрыта со счетом [%i:%i].\n\n<blockquote>Победитель может забрать чек на сумму в размере %.2f$.</blockquote></b>\n\n%s' % (dice1_value, dice2_value, amount * COEFFICIENT, LINKS_TEXT), reply_markup=keyboard)
            else:
                await bot.send_photo(CHANNEL_ID, photo=LOSE, caption='<b>❌ Проигрыш! Сессия закрыта со счетом [%i:%i].\n\n<blockquote>Бросай кубики заново и испытай свою удачу!</blockquote></b>\n\n%s' % (dice1_value, dice2_value, LINKS_TEXT), reply_markup=keyboard)
        else:
            cashback = amount - (amount / 10)
            check = await crypto.create_check(asset='USDT', amount=cashback, pin_to_user_id=user.id)
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton('Вернуть средства', url=check.bot_check_url))
            keyboard.add(InlineKeyboardButton('Сделать ставку', url=INVOICE_LINK))
            return await bot.send_message(CHANNEL_ID, '<b>❌ Ошибка у игрока %s</b>\n\n<b>Такой команды не существует!</b>\nСредства возвращены на ваш CryptoBot кошелёк <b>за вычетом комиссии 10%%</b>\n\n<u>Прочитайте <a href="%s">статью</> ниже перед тем, как делать ставку.</u>' % (first_name, HELP_LINK), reply_markup=keyboard)
    except CodeErrorFactory as e:
        if e.name == 'NOT_ENOUGH_COINS':
            keyboard.add(InlineKeyboardButton('🎁 Забрать выигрыш', url=SUPPORT_LINK))
            await bot.send_photo(CHANNEL_ID, photo=WIN, caption='<b>🎉 Победа!\n\n<blockquote>Победитель может забрать выигрыш у администрации.</blockquote></b>\n\n%s' % LINKS_TEXT, reply_markup=keyboard)
    except Exception as e:
        print(e)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)