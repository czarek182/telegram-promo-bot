#!/usr/bin/env python3
"""
Telegram Promotion Bot - System Zarabiania na Promocjach
Kompatybilny z Python 3.14.3
"""

import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

# ============================================================================
# KONFIGURACJA
# ============================================================================

BOT_TOKEN = "8690157604:AAGabKVyuyLeef3ZbSgRpiPbUxSFOqrprc0"  # Wstaw swój token od BotFather
ADMIN_IDS = [6899601385]  # Wstaw swoje ID - wyślij /getid do @userinfobot
DATABASE_FILE = "bot_database.json"

# Stany konwersacji
WAITING_FOR_EMAIL = 1
WAITING_FOR_CONSENT = 2
WAITING_FOR_PROMO_CHOICE = 3
WAITING_FOR_OFFER_PROOF = 4
WAITING_FOR_ADMIN_DECISION = 5

# ============================================================================
# BAZA DANYCH
# ============================================================================

def load_database() -> Dict[str, Any]:
    """Wczytaj bazę danych"""
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "users": {},
        "offers": [],
        "referrals": {},
        "pending_offers": []
    }

def save_database(db: Dict[str, Any]) -> None:
    """Zapisz bazę danych"""
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

# ============================================================================
# FUNKCJE POMOCNICZE
# ============================================================================

def get_user_data(user_id: int, db: Dict[str, Any]) -> Optional[Dict]:
    """Pobierz dane użytkownika"""
    return db["users"].get(str(user_id))

def create_user(user_id: int, email: str, db: Dict[str, Any]) -> None:
    """Utwórz nowego użytkownika"""
    db["users"][str(user_id)] = {
        "email": email,
        "points": 0,
        "completed_offers": [],
        "referral_code": f"REF_{user_id}",
        "registered_at": datetime.now().isoformat()
    }
    save_database(db)

def add_points(user_id: int, points: int, db: Dict[str, Any]) -> None:
    """Dodaj punkty użytkownikowi"""
    if str(user_id) in db["users"]:
        db["users"][str(user_id)]["points"] += points
        save_database(db)

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Utwórz główne menu"""
    keyboard = [
        [InlineKeyboardButton("🎁 Bonusy z Blikiem", callback_data="promo_bliki")],
        [InlineKeyboardButton("🏦 Promocje Bankowe", callback_data="promo_bank")],
        [InlineKeyboardButton("✈️ AirDrop", callback_data="promo_airdrop")],
        [InlineKeyboardButton("📊 Moje Punkty", callback_data="my_points")],
        [InlineKeyboardButton("👥 Poleć Znajomego", callback_data="referral")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_promo_keyboard(category: str) -> InlineKeyboardMarkup:
    """Utwórz menu promocji"""
    promos = {
        "bliki": [
            ("Bonus 50 zł", "offer_bliki_50"),
            ("Bonus 100 zł", "offer_bliki_100"),
            ("Bonus 200 zł", "offer_bliki_200"),
        ],
        "bank": [
            ("PKO BP - 100 zł", "offer_bank_pko"),
            ("ING - 150 zł", "offer_bank_ing"),
            ("Santander - 120 zł", "offer_bank_santander"),
        ],
        "airdrop": [
            ("Crypto Airdrop 1", "offer_airdrop_1"),
            ("Crypto Airdrop 2", "offer_airdrop_2"),
            ("Crypto Airdrop 3", "offer_airdrop_3"),
        ]
    }
    
    keyboard = []
    for promo_name, callback in promos.get(category, []):
        keyboard.append([InlineKeyboardButton(promo_name, callback_data=callback)])
    
    keyboard.append([InlineKeyboardButton("⬅️ Wróć", callback_data="back_menu")])
    return InlineKeyboardMarkup(keyboard)

# ============================================================================
# KOMENDY
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Komenda /start"""
    user_id = update.effective_user.id
    db = load_database()
    
    user_data = get_user_data(user_id, db)
    
    if user_data:
        # Użytkownik już zarejestrowany
        await update.message.reply_text(
            f"Witaj! 👋\n\n"
            f"Email: {user_data['email']}\n"
            f"Punkty: {user_data['points']}\n"
            f"Kod polecenia: {user_data['referral_code']}\n\n"
            f"Wybierz akcję:",
            reply_markup=get_main_menu_keyboard()
        )
        return ConversationHandler.END
    else:
        # Nowy użytkownik - poproś o email
        await update.message.reply_text(
            "Witaj w PromoZarabiacz! 🎉\n\n"
            "Aby zacząć zarabiać na promocjach, podaj swój email:"
        )
        return WAITING_FOR_EMAIL

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Obsługuj wiadomość z emailem"""
    email = update.message.text
    
    # Walidacja email
    if "@" not in email or "." not in email:
        await update.message.reply_text("Nieprawidłowy email! Spróbuj ponownie:")
        return WAITING_FOR_EMAIL
    
    context.user_data["email"] = email
    
    # Poproś o zgodę
    keyboard = [
        [InlineKeyboardButton("✅ Zgadzam się", callback_data="consent_yes")],
        [InlineKeyboardButton("❌ Nie zgadzam się", callback_data="consent_no")],
    ]
    
    await update.message.reply_text(
        f"Email: {email}\n\n"
        f"Czy zgadzasz się na wiadomości marketingowe?\n"
        f"(Obiecujemy - nie wysyłamy spamu! 🚫📧)",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return WAITING_FOR_CONSENT

async def handle_consent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Obsługuj zgodę"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "consent_yes":
        user_id = update.effective_user.id
        email = context.user_data.get("email", "unknown")
        
        db = load_database()
        create_user(user_id, email, db)
        
        await query.edit_message_text(
            "Świetnie! 🎉\n\n"
            "Jesteś zarejestrowany!\n"
            "Teraz możesz zarabiać na promocjach.\n\n"
            "Wybierz akcję:",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await query.edit_message_text(
            "Rozumiem. Możesz wrócić kiedy zmienisz zdanie!\n"
            "Wyślij /start aby zacząć."
        )
    
    return ConversationHandler.END

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Obsługuj przyciski"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db = load_database()
    user_data = get_user_data(user_id, db)
    
    if not user_data:
        await query.edit_message_text("Musisz się najpierw zarejestrować! /start")
        return
    
    data = query.data
    
    # Menu główne
    if data == "promo_bliki":
        await query.edit_message_text(
            "🎁 Bonusy z Blikiem\n\n"
            "Wybierz bonus:",
            reply_markup=get_promo_keyboard("bliki")
        )
    
    elif data == "promo_bank":
        await query.edit_message_text(
            "🏦 Promocje Bankowe\n\n"
            "Wybierz promocję:",
            reply_markup=get_promo_keyboard("bank")
        )
    
    elif data == "promo_airdrop":
        await query.edit_message_text(
            "✈️ AirDrop\n\n"
            "Wybierz airdrop:",
            reply_markup=get_promo_keyboard("airdrop")
        )
    
    elif data == "my_points":
        points = user_data["points"]
        bliki_value = (points // 50) * 5
        
        await query.edit_message_text(
            f"📊 Twoje Punkty\n\n"
            f"Punkty: {points}\n"
            f"Możesz wymienić na: {bliki_value} zł Blika\n\n"
            f"50 punktów = 5 zł na Blika",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Wróć", callback_data="back_menu")]
            ])
        )
    
    elif data == "referral":
        referral_code = user_data["referral_code"]
        await query.edit_message_text(
            f"👥 Poleć Znajomego\n\n"
            f"Twój kod: {referral_code}\n\n"
            f"Za każdego znajomego:\n"
            f"• 1 punkt za pierwszą ofertę\n"
            f"• 5 punktów za potwierdzoną ofertę\n\n"
            f"Podziel się kodem!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Wróć", callback_data="back_menu")]
            ])
        )
    
    elif data == "back_menu":
        await query.edit_message_text(
            "Główne menu:",
            reply_markup=get_main_menu_keyboard()
        )
    
    # Oferty
    elif data.startswith("offer_"):
        context.user_data["current_offer"] = data
        await query.edit_message_text(
            "Wykonaj ofertę i wyślij zrzut ekranu jako dowód.\n\n"
            "Czekam na zdjęcie..."
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Obsługuj zdjęcia"""
    user_id = update.effective_user.id
    db = load_database()
    
    if "current_offer" not in context.user_data:
        await update.message.reply_text("Najpierw wybierz ofertę!")
        return
    
    offer = context.user_data["current_offer"]
    photo = update.message.photo[-1]
    
    # Zapisz ofertę do weryfikacji
    pending_offer = {
        "user_id": user_id,
        "offer": offer,
        "photo_id": photo.file_id,
        "timestamp": datetime.now().isoformat(),
        "status": "pending"
    }
    
    db["pending_offers"].append(pending_offer)
    save_database(db)
    
    await update.message.reply_text(
        "✅ Zdjęcie zostało przesłane!\n\n"
        "Administrator sprawdzi Twoją ofertę.\n"
        "Otrzymasz powiadomienie gdy zostanie zatwierdzona.\n\n"
        "Powrót do menu: /start"
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Panel administratora"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Nie masz dostępu!")
        return
    
    db = load_database()
    pending = db["pending_offers"]
    
    if not pending:
        await update.message.reply_text("Brak oczekujących ofert!")
        return
    
    # Pokaż pierwszą oczekującą ofertę
    offer = pending[0]
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Zatwierdź", callback_data=f"approve_{pending.index(offer)}"),
            InlineKeyboardButton("❌ Odrzuć", callback_data=f"reject_{pending.index(offer)}")
        ]
    ]
    
    await update.message.reply_photo(
        photo=offer["photo_id"],
        caption=f"Oferta od: {offer['user_id']}\n"
                f"Typ: {offer['offer']}\n"
                f"Czas: {offer['timestamp']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Obsługuj decyzję administratora"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in ADMIN_IDS:
        await query.answer("Nie masz dostępu!", show_alert=True)
        return
    
    await query.answer()
    
    data = query.data
    db = load_database()
    
    if data.startswith("approve_"):
        idx = int(data.split("_")[1])
        offer = db["pending_offers"][idx]
        
        # Dodaj punkty
        add_points(offer["user_id"], 5, db)
        
        # Usuń z oczekujących
        db["pending_offers"].pop(idx)
        save_database(db)
        
        await query.edit_message_text("✅ Oferta zatwierdzona! Użytkownik otrzymał 5 punktów.")
    
    elif data.startswith("reject_"):
        idx = int(data.split("_")[1])
        db["pending_offers"].pop(idx)
        save_database(db)
        
        await query.edit_message_text("❌ Oferta odrzucona.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Komenda /help"""
    await update.message.reply_text(
        "🤖 PromoZarabiacz - Pomoc\n\n"
        "/start - Rozpocznij\n"
        "/help - Pomoc\n"
        "/admin - Panel administratora (tylko admin)\n\n"
        "Jak zarabiać:\n"
        "1. Zarejestruj się\n"
        "2. Wybierz promocję\n"
        "3. Wykonaj ofertę\n"
        "4. Wyślij zrzut ekranu\n"
        "5. Czekaj na zatwierdzenie\n"
        "6. Otrzymaj punkty!\n\n"
        "50 punktów = 5 zł na Blika 💰"
    )

# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    """Uruchom bota"""
    # Utwórz aplikację
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Konwersacja rejestracji
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)],
            WAITING_FOR_CONSENT: [CallbackQueryHandler(handle_consent)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    
    # Dodaj handlery
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(admin_decision))
    app.add_handler(CommandHandler("help", help_command))
    
    # Uruchom bota
    print("🤖 Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
