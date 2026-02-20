"""Telegram Bot Service for Anki Card Creator.

This bot replicates all functionality from the old CLI bot:
- /start - Initial setup with Anki deck file
- /help - Show available commands
- /csv, /export, /e - Export dictionary to CSV
- /dictionary - View saved words
- /list, /l - List all decks
- /chosedict - Switch to a different deck
- /rmdict - Remove words by index or character
- /search - Search for words
- /clearmydata - Clear all user data
- /dictinfo - Show dictionary statistics
- /changelog - Show updates
- Handle text messages (extract Chinese words)
- Handle images (OCR to extract Chinese words)

Admin commands:
- /admin - Admin menu
- /stats - Show system statistics
- /refresh - Refresh word data (admin only)
- /wipedict - Wipe a deck
"""
import os
import io
import csv
import logging
import re
import base64
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from src.models.database import db
from src.models.user import User
from src.utils.chinese_utils import extract_chinese_words
from src.services.dictionary_service import dictionary_service

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Admin ID from environment
ADMIN_ID = os.environ.get('TELEGRAM_ADMIN_ID')


class TelegramBotService:
    """Telegram bot service for Anki Card Creator."""
    
    def __init__(self):
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.application = None
        
    def initialize(self):
        """Initialize the bot application."""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not set!")
            return False
            
        self.application = Application.builder().token(self.token).build()
        self._setup_handlers()
        return True
    
    def _setup_handlers(self):
        """Set up command and message handlers."""
        # Basic commands
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        
        # Dictionary commands
        self.application.add_handler(CommandHandler("dictionary", self.cmd_dictionary))
        self.application.add_handler(CommandHandler("dictinfo", self.cmd_dictinfo))
        self.application.add_handler(CommandHandler("csv", self.cmd_export))
        self.application.add_handler(CommandHandler("export", self.cmd_export))
        self.application.add_handler(CommandHandler("e", self.cmd_export))
        self.application.add_handler(CommandHandler("oldexport", self.cmd_oldexport))
        
        # Deck management
        self.application.add_handler(CommandHandler("list", self._show_deck_list_handler))
        self.application.add_handler(CommandHandler("l", self._show_deck_list_handler))
        self.application.add_handler(CommandHandler("chosedict", self.cmd_chosedeck))
        self.application.add_handler(CommandHandler("chosedeck", self.cmd_chosedeck))
        
        # Word management
        self.application.add_handler(CommandHandler("rmdict", self.cmd_rmdict))
        self.application.add_handler(CommandHandler("rm", self.cmd_rm))
        self.application.add_handler(CommandHandler("search", self.cmd_search))
        self.application.add_handler(CommandHandler("clearmydata", self.cmd_clearmydata))
        
        # Other commands
        self.application.add_handler(CommandHandler("changelog", self.cmd_changelog))
        
        # Admin commands
        self.application.add_handler(CommandHandler("admin", self.cmd_admin))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        self.application.add_handler(CommandHandler("wipedict", self.cmd_wipedict))
        self.application.add_handler(CommandHandler("refresh", self.cmd_refresh))
        self.application.add_handler(CommandHandler("listall", self.cmd_listall))
        self.application.add_handler(CommandHandler("pending", self.cmd_pending))
        self.application.add_handler(CommandHandler("approve", self.cmd_approve))
        self.application.add_handler(CommandHandler("deny", self.cmd_deny))
        
        # Callback handlers for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.callback_handler, pattern="^"))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        
    # ==================== Helper Methods ====================
    
    def _get_user_by_telegram(self, telegram_id: str) -> Optional[Dict]:
        """Get user by Telegram ID."""
        return db.get_user_by_telegram_id(str(telegram_id))
    
    def _get_current_deck_id(self, context) -> Optional[str]:
        """Get current deck ID from context, or return None if using main deck."""
        deck_id = context.user_data.get('current_deck')
        if deck_id:
            return str(deck_id)
        return None
    
    def _get_all_decks(self) -> List[Dict]:
        """Get all decks from database with word counts."""
        # Get all words and count by user_id
        try:
            all_words = db.get_all_words()
        except:
            all_words = []
        
        if not all_words:
            return []
        
        # Count words per user_id
        deck_counts = {}
        for word in all_words:
            if not word:
                continue
            uid = word.get('user_id')
            if uid:
                deck_counts[uid] = deck_counts.get(uid, 0) + 1
        
        # Get users for admin status
        try:
            users = db.get_users()
        except:
            users = []
        
        # Build deck list
        decks = []
        for uid, count in deck_counts.items():
            user = next((u for u in users if u.get('id') == uid), None)
            is_admin = user.get('is_admin') if user else False
            decks.append({
                'id': uid,
                'word_count': count,
                'is_admin': is_admin
            })
        
        # Sort by word count descending
        decks.sort(key=lambda x: x['word_count'], reverse=True)
        return decks
    
    def _get_or_create_user(self, telegram_id: str, username: str = None) -> Tuple[Dict, bool]:
        """Get existing user or create new one. Returns (user_data, is_new)."""
        user = self._get_user_by_telegram(telegram_id)
        if user:
            # Check if this user should be admin (matches TELEGRAM_ADMIN_ID)
            should_be_admin = self._is_admin(telegram_id)
            # Update admin status if needed
            if should_be_admin and not user.get('is_admin'):
                db.update_user(user['id'], {'is_admin': True, 'is_active': True})
                user = self._get_user_by_telegram(telegram_id)
            return user, False
        
        # Check if this is the admin
        is_admin = self._is_admin(telegram_id)
        
        # Create new user (auto-approve if admin)
        user_id = User.generate_id()
        db.create_user(
            user_id=user_id,
            email=None,
            password_hash=None,
            telegram_id=str(telegram_id),
            telegram_username=username,
            is_active=is_admin,  # Auto-activate if admin
            is_admin=is_admin    # Set as admin if matches TELEGRAM_ADMIN_ID
        )
        
        # Only add to pending if not admin
        if not is_admin:
            db.create_pending_approval(user_id)
        
        return db.get_user_by_id(user_id), True
    
    def _get_user_deck_id(self, user_id: str) -> str:
        """Get current deck ID for user (stored in memory context)."""
        # Default to user_id-1 format
        return f"{user_id}-1"
    
    def _format_word_list(self, words: List[Dict], page: int = 1, per_page: int = 20) -> str:
        """Format word list for display."""
        if not words:
            return "📚 Your dictionary is empty.\n\nSend me Chinese text or images to add words!"
        
        start = (page - 1) * per_page
        end = start + per_page
        page_words = words[start:end]
        
        lines = [f"📚 Your Dictionary ({len(words)} words)\n"]
        lines.append("Use /rmdict [number] to remove a word\n")
        
        for i, word in enumerate(page_words, start=start + 1):
            char = word.get('character', '?')
            pinyin = word.get('pinyin', '')[:30]
            translation = word.get('translation', '')[:40]
            lines.append(f"{i}. {char} - {pinyin}")
            if translation:
                lines.append(f"   {translation}")
        
        total_pages = (len(words) + per_page - 1) // per_page
        if total_pages > 1:
            lines.append(f"\n📄 Page {page}/{total_pages}")
            lines.append(f"Use /dictionary {page+1} for next page")
        
        return "\n".join(lines)
    
    def _export_to_csv(self, user_id: str) -> bytes:
        """Export user's dictionary to CSV bytes - matches old app format EXACTLY."""
        words = db.get_words_by_user(user_id)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # NO HEADER - matches old app exactly (old app commented out the header line)
        
        # Process each word exactly like the old app
        for word in words:
            character = word.get('character', '')
            styled_term = word.get('styled_term', '')
            pinyin = word.get('pinyin', '')
            translation = word.get('translation', '')
            meaning = word.get('meaning', '')
            
            # Ensure pronunciation uses correct API URL (old app used 212.227.211.88:80)
            pronunciation = word.get('pronunciation', '')
            if not pronunciation:
                pronunciation = dictionary_service._get_pronunciation_url(character)
            
            example_link = word.get('example_link', '')
            exemplary_image = word.get('exemplary_image', '')
            
            # Field order from old app: example_usage, reading, component2, component1
            # (Note: based on actual old CSV data, component2 comes before component1)
            # These fields are mostly legacy/empty in new implementation
            example_usage = word.get('anki_usage_examples', '')  # Field 9
            reading = word.get('reading', '')  # Field 10
            component2 = word.get('component2', '')  # Field 11 (Developer Note text)
            component1 = word.get('component1', '')  # Field 12 (Developer note styled)
            
            # Real AI-generated examples (field 13)
            real_usage_examples = word.get('real_usage_examples', '')
            
            # Split stroke GIFs by comma and space (old format)
            stroke_gifs = word.get('stroke_gifs', '')
            stroke_order_list = stroke_gifs.split(", ") if stroke_gifs else []
            stroke_order_fields = stroke_order_list[:6]  # Limit to 6
            
            # Pad to ensure all 6 columns are present
            stroke_order_fields += [''] * (6 - len(stroke_order_fields))
            
            # CSV row format matching old app EXACTLY (based on actual old CSV data):
            # [character, styled_term, pinyin, translation, meaning, pronunciation, 
            #  example_link, exemplary_image, example_usage, reading, component2, 
            #  component1, real_usage_examples] + stroke_order_fields
            # Note: component2 comes before component1 to match old data
            csv_row = [
                character,
                styled_term,
                pinyin,
                translation,
                meaning,
                pronunciation,
                example_link,
                exemplary_image,
                example_usage,
                reading,
                component2,
                component1,
                real_usage_examples
            ] + stroke_order_fields
            
            writer.writerow(csv_row)
        
        return output.getvalue().encode('utf-8')
    
    def _is_admin(self, telegram_id: str) -> bool:
        """Check if user is admin."""
        if not ADMIN_ID:
            return False
        return str(telegram_id) == str(ADMIN_ID)
    
    # ==================== Command Handlers ====================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - includes Anki template setup."""
        import os
        
        user = update.effective_user
        user_data, is_new = self._get_or_create_user(str(user.id), user.username)
        
        # Path to Anki template file
        template_path = os.path.join(os.path.dirname(__file__), '..', '..', 'static', 'anki_import.apkg')
        
        setup_text = (
            "📚 *Welcome to Anki Card Creator!*\n\n"
            "This bot creates Anki flashcards from Chinese text and images.\n\n"
            "*Initial Setup:*\n"
            "→ First, import the template deck below into Anki\n"
            "→ Then send me Chinese words to add to your dictionary\n"
            "→ Export with /export and import into the same deck\n\n"
            "*How to import the template:*\n"
            "📱 *Phone:* Download → Open Anki → Import → Select .apkg file\n"
            "💻 *Computer:* Download → Open with Anki → Import"
        )
        
        # Send setup text with template file
        if os.path.exists(template_path):
            await update.message.reply_text(setup_text, parse_mode='Markdown')
            await update.message.reply_document(
                document=open(template_path, 'rb'),
                filename='First setup - Personal vocabulary.apkg',
                caption="📥 Import this template into Anki first!"
            )
        else:
            await update.message.reply_text(
                setup_text + "\n\n⚠️ Template file not found. Please download from the website.",
                parse_mode='Markdown'
            )
        
        # Account status message
        if is_new:
            await update.message.reply_text(
                "⚠️ Your account is pending admin approval.\n"
                "You'll be notified once approved.\n\n"
                "Use /help to see available commands."
            )
        elif not user_data.get('is_active'):
            await update.message.reply_text(
                "⏳ Your account is still pending approval.\n"
                "Please wait for an admin to approve your account."
            )
        else:
            await update.message.reply_text(
                "✅ Your account is active!\n\n"
                "Send me Chinese text or images to add words to your dictionary.\n"
                "Use /help for all commands."
            )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = (
            "📖 *Anki Card Creator - Help*\n\n"
            "*Initial Setup:*\n"
            "1. Use /start to get the template file\n"
            "2. Import 'First setup - Personal vocabulary.apkg' into Anki\n"
            "3. Send me Chinese text to add words\n"
            "4. Export and import into the same deck\n\n"
            "*Adding Words:*\n"
            "• Send Chinese text - I'll extract all words\n"
            "• Send images - I'll use OCR to extract text\n\n"
            "*Dictionary Commands:*\n"
            "/dictionary - View your saved words\n"
            "/dictinfo - Show statistics\n"
            "/search [word] - Search for a word\n\n"
            "*Export to Anki:*\n"
            "/export or /csv or /e - Get CSV file\n\n"
            "*How to import to Anki:*\n"
            "1. Click the CSV file\n"
            "2. 'Open With' Anki\n"
            "3. Set 'Field separator' to 'Comma'\n"
            "4. Enable 'Allow HTML in fields'\n"
            "5. Choose the 'Personal Vocabulary' note type\n"
            "6. Select your deck and click Import 🎉\n\n"
            "*Managing Words:*\n"
            "/rmdict [number] - Remove word by index\n"
            "/rmdict [汉字] - Remove word by character\n"
            "/clearmydata - Clear all your data\n\n"
            "*Decks:*\n"
            "/list or /l - List your decks\n"
            "/chosedict [number] - Switch to a different deck\n\n"
            "*Other:*\n"
            "/changelog - See latest updates\n"
            "/help - Show this help message"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def cmd_dictionary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dictionary command."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first to register.")
            return
        
        if not user_data.get('is_active'):
            await update.message.reply_text("⏳ Your account is pending approval.")
            return
        
        # Get current deck or use main user deck
        current_deck = self._get_current_deck_id(context)
        base_user_id = user_data['id']
        
        # Get page number from args
        args = context.args
        page = int(args[0]) if args and args[0].isdigit() else 1
        
        words = db.get_words_by_user(base_user_id, current_deck)
        text = self._format_word_list(words, page=page)
        
        await update.message.reply_text(text)
    
    async def cmd_dictinfo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dictinfo command."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        if not user_data.get('is_active'):
            await update.message.reply_text("⏳ Your account is pending approval.")
            return
        
        # Get current deck or use main user deck
        current_deck = self._get_current_deck_id(context)
        base_user_id = user_data['id']
        
        # Construct the target user_id for this deck
        target_user_id = f"{base_user_id}-{current_deck}" if current_deck and current_deck != "1" else base_user_id
        
        stats = db.get_user_stats(target_user_id)
        words = db.get_words_by_user(base_user_id, current_deck)
        
        current_marker = "" if not current_deck else f" (Deck: {current_deck})"
        
        info_text = (
            f"📊 *Your Dictionary Stats*{current_marker}\n\n"
            f"Total Words: {len(words)}\n"
            f"User ID: `{base_user_id[:8]}...`\n\n"
            "Keep adding words to build your vocabulary!"
        )
        await update.message.reply_text(info_text, parse_mode='Markdown')
    
    async def cmd_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /export, /csv, /e commands."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        if not user_data.get('is_active'):
            await update.message.reply_text("⏳ Your account is pending approval.")
            return
        
        # Get current deck or use main user deck
        current_deck = self._get_current_deck_id(context)
        base_user_id = user_data['id']
        
        words = db.get_words_by_user(base_user_id, current_deck)
        if not words:
            await update.message.reply_text(
                "📚 This deck is empty!\n\n"
                "Send me some Chinese text first to add words."
            )
            return
        
        # Generate CSV with proper deck identification
        target_user_id = f"{base_user_id}-{current_deck}" if current_deck and current_deck != "1" else base_user_id
        csv_data = self._export_to_csv(target_user_id)
        
        deck_name = f"_{current_deck}" if current_deck else ""
        
        # Send file
        await update.message.reply_document(
            document=csv_data,
            filename=f"anki_dictionary_{user.id}{deck_name}.csv",
            caption=(
                f"📥 Your dictionary ({len(words)} words)\n\n"
                "Import this CSV into Anki:\n"
                "1. Set Field separator to 'Comma'\n"
                "2. Enable 'Allow HTML'\n"
                "3. Choose your deck and import!"
            )
        )
    
    async def cmd_oldexport(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /oldexport command - old format without APP_URL prefix."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        if not user_data.get('is_active'):
            await update.message.reply_text("⏳ Your account is pending approval.")
            return
        
        # Get current deck or use main user deck
        current_deck = self._get_current_deck_id(context)
        base_user_id = user_data['id']
        
        words = db.get_words_by_user(base_user_id, current_deck)
        if not words:
            await update.message.reply_text(
                "📚 This deck is empty!\n\n"
                "Send me some Chinese text first to add words."
            )
            return
        
        # Generate CSV using old format (no APP_URL prefix)
        import os
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        for word in words:
            character = word.get('character', '')
            styled_term = word.get('styled_term', '')
            pinyin = word.get('pinyin', '')
            translation = word.get('translation', '')
            meaning = word.get('meaning', '')
            
            pronunciation = word.get('pronunciation', '')
            if not pronunciation or '212.227.211.88' in pronunciation:
                pronunciation = dictionary_service._get_pronunciation_url(character)
            
            example_link = word.get('example_link', '')
            exemplary_image = word.get('exemplary_image', '')
            example_usage = word.get('anki_usage_examples', '')
            reading = word.get('reading', '')
            component2 = word.get('component2', '')  # Field 11
            component1 = word.get('component1', '')  # Field 12
            real_usage_examples = word.get('real_usage_examples', '')
            
            stroke_gifs = word.get('stroke_gifs', '')
            stroke_order_list = stroke_gifs.split(", ") if stroke_gifs else []
            stroke_order_fields = stroke_order_list[:6]
            stroke_order_fields += [''] * (6 - len(stroke_order_fields))
            
            # Old format - no APP_URL prefix
            # Note: component2 comes before component1 to match old data
            csv_row = [
                character,
                styled_term,
                pinyin,
                translation,
                meaning,
                pronunciation,
                example_link,
                exemplary_image,
                example_usage,
                reading,
                component2,
                component1,
                real_usage_examples
            ] + stroke_order_fields
            
            writer.writerow(csv_row)
        
        csv_data = output.getvalue().encode('utf-8')
        
        deck_name = f"_{current_deck}" if current_deck else ""
        
        await update.message.reply_document(
            document=csv_data,
            filename=f"anki_dictionary_{user.id}{deck_name}.csv",
            caption=(
                f"📥 Your dictionary - OLD FORMAT ({len(words)} words)\n\n"
                "Import this CSV into Anki:\n"
                "1. Set Field separator to 'Comma'\n"
                "2. Enable 'Allow HTML'\n"
                "3. Choose your deck and import!"
            )
        )
    
    async def cmd_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        # For now, show a simple deck list (in full app, this queries user_decks table)
        text = (
            "📚 *Your Decks*\n\n"
            "Deck 1: Main Deck (Default)\n\n"
            "Use /chosedict to switch decks.\n"
            "New decks are created automatically when you switch to a new number."
        )
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_chosedeck(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /chosedict command."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        args = context.args
        if not args:
            await update.message.reply_text(
                "Usage: /chosedeck [deck_number]\n\n"
                "Example: /chosedeck 1\n\n"
                "This switches you to a different vocabulary deck.\n"
                "If the deck doesn't exist, it will be created.\n\n"
                "Tip: Just use /l to see all decks and click to select."
            )
            return
        
        # If no args, show deck list with inline keyboard
        if not args:
            await self._show_deck_list(update, context)
            return
        
        try:
            deck_num = int(args[0])
            if deck_num < 1:
                raise ValueError()
        except ValueError:
            await update.message.reply_text("❌ Deck number must be a positive integer (1, 2, 3, etc.)")
            return
        
        # Store deck preference in context
        context.user_data['current_deck'] = str(deck_num)
        
        await update.message.reply_text(
            f"✅ Switched to Deck {deck_num}.\n\n"
            f"New words will be added to this deck.\n"
            f"Use /dictionary to see words in this deck."
        )
    
    async def _show_deck_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show list of decks with inline keyboard selection."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        base_user_id = user_data['id']
        
        # Get all decks and filter to only this user's decks
        all_decks = self._get_all_decks()
        
        # Filter decks that belong to this user:
        # - Main deck: deck_id == base_user_id
        # - Other decks: deck_id starts with "base_user_id-"
        user_decks = []
        for deck in all_decks:
            deck_id = deck['id']
            if deck_id == base_user_id or deck_id.startswith(f"{base_user_id}-"):
                user_decks.append(deck)
        
        if not user_decks:
            await update.message.reply_text(
                "📚 You don't have any decks yet.\n\n"
                "Send me some Chinese text to create your first deck!"
            )
            return
        
        current_deck = self._get_current_deck_id(context)
        
        keyboard = []
        message_text = "📚 *Your Decks*\n\n"
        
        for deck in user_decks:
            deck_id = deck['id']
            count = deck['word_count']
            
            # Extract deck number from full ID for display
            if deck_id == base_user_id:
                deck_num = "1"  # Main deck
            elif '-' in deck_id:
                # Extract number from end (format: USERID-N)
                deck_num = deck_id.rsplit('-', 1)[1]
            else:
                deck_num = "?"
            
            # Check if this is the current deck
            is_current = (current_deck == deck_num) or (current_deck is None and deck_num == "1")
            marker = "🎯 " if is_current else ""
            
            button_label = f"{marker}Deck {deck_num} ({count} words)"
            
            keyboard.append([InlineKeyboardButton(button_label, callback_data=f"switch_deck_{deck_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def _show_deck_list_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /l command to show deck list."""
        await self._show_deck_list(update, context)
    
    async def cmd_rmdict(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /rmdict command."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        if not user_data.get('is_active'):
            await update.message.reply_text("⏳ Your account is pending approval.")
            return
        
        # Get current deck or use main user deck
        current_deck = self._get_current_deck_id(context)
        base_user_id = user_data['id']
        
        args = context.args
        if not args:
            await update.message.reply_text(
                "Usage: /rmdict [index] or /rmdict [character]\n\n"
                "Examples:\n"
                "/rmdict 5 (removes 5th word)\n"
                "/rmdict 你好 (removes '你好')\n\n"
                "Use /dictionary to see word indices."
            )
            return
        
        words = db.get_words_by_user(base_user_id, current_deck)
        if not words:
            deck_name = "main deck" if not current_deck else f"deck {current_deck}"
            await update.message.reply_text(f"📚 Your {deck_name} is empty.")
            return
        
        # Get the actual user_id format used in database for this deck
        target_user_id = f"{base_user_id}-{current_deck}" if current_deck and current_deck != "1" else base_user_id
        
        target = args[0]
        
        # Try to remove by index
        if target.isdigit():
            idx = int(target) - 1  # 1-based to 0-based
            if 0 <= idx < len(words):
                word = words[idx]
                db.delete_word(word['id'], target_user_id)
                await update.message.reply_text(f"✅ Removed: {word['character']}")
            else:
                await update.message.reply_text(f"❌ Invalid index. Use 1-{len(words)}")
        else:
            # Remove by character
            found = False
            for word in words:
                if word['character'] == target:
                    db.delete_word(word['id'], target_user_id)
                    await update.message.reply_text(f"✅ Removed: {target}")
                    found = True
                    break
            if not found:
                await update.message.reply_text(f"❌ Word '{target}' not found in this deck.")
    
    async def cmd_rm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /rm command (alias for /rmdict)."""
        await self.cmd_rmdict(update, context)
    
    async def cmd_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        # Get current deck or use main user deck
        current_deck = self._get_current_deck_id(context)
        base_user_id = user_data['id']
        
        args = context.args
        if not args:
            await update.message.reply_text(
                "Usage: /search [character or pinyin]\n\n"
                "Example: /search 你好\n"
                "Example: /search nihao"
            )
            return
        
        query = args[0].lower()
        words = db.get_words_by_user(base_user_id, current_deck)
        
        results = []
        for i, word in enumerate(words, 1):
            char = word.get('character', '').lower()
            pinyin = word.get('pinyin', '').lower()
            if query in char or query in pinyin:
                results.append(f"{i}. {word['character']} - {word['pinyin'][:30]}")
        
        if results:
            text = "🔍 *Search Results:*\n\n" + "\n".join(results[:20])
            if len(results) > 20:
                text += f"\n\n...and {len(results) - 20} more"
        else:
            text = f"🔍 No results for '{args[0]}'"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_clearmydata(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clearmydata command."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, delete all", callback_data="confirm_wipe"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_wipe")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚠️ *WARNING*\n\n"
            "This will delete ALL your vocabulary data.\n"
            "This action cannot be undone.\n\n"
            "Are you sure?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def cmd_changelog(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /changelog command."""
        changelog_text = (
            "📈 *Changelog*\n\n"
            "*Current Features:*\n"
            "✅ Extract words from text\n"
            "✅ OCR from images\n"
            "✅ Auto-generate pinyin with tone colors\n"
            "✅ Example sentences from DeepSeek AI\n"
            "✅ Stroke order GIFs\n"
            "✅ Exemplary images\n"
            "✅ CSV export for Anki\n"
            "✅ Multi-deck support\n"
            "✅ Web dashboard\n"
            "✅ Telegram bot\n\n"
            "*Coming Soon:*\n"
            "• More data sources\n"
            "• Enhanced card templates"
        )
        await update.message.reply_text(changelog_text, parse_mode='Markdown')
    
    # ==================== Admin Commands ====================
    
    async def cmd_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command."""
        user = update.effective_user
        
        if not self._is_admin(user.id):
            await update.message.reply_text("🚫 Access denied.")
            return
        
        admin_text = (
            "🔧 *Admin Menu*\n\n"
            "/stats - System statistics\n"
            "/listall - List all users and decks\n"
            "/pending - Show pending approvals\n"
            "/approve [user_id] - Approve a user\n"
            "/deny [user_id] - Remove pending user\n"
            "/wipedict [user_id] - Wipe user deck\n"
            "/refresh [word] - Refresh word data\n"
            "/admin - Show this menu"
        )
        await update.message.reply_text(admin_text, parse_mode='Markdown')
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        user = update.effective_user
        
        if not self._is_admin(user.id):
            await update.message.reply_text("🚫 Access denied.")
            return
        
        stats = db.get_stats()
        users = db.get_users()
        
        text = (
            "📊 *System Statistics*\n\n"
            f"Total Users: {stats.get('total_users', 0)}\n"
            f"Total Words: {stats.get('total_words', 0)}\n"
            f"Active Users: {stats.get('active_users', 0)}\n"
            f"Pending Approvals: {len(db.get_pending_approvals())}\n\n"
            f"Database Mode: {stats.get('mode', 'unknown')}"
        )
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_wipedict(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /wipedict command (admin only)."""
        user = update.effective_user
        
        if not self._is_admin(user.id):
            await update.message.reply_text("🚫 Access denied.")
            return
        
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /wipedict [user_id]")
            return
        
        target_user_id = args[0]
        db.delete_all_words(target_user_id)
        await update.message.reply_text(f"✅ Wiped all words for user {target_user_id}")
    
    async def cmd_refresh(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /refresh command (admin only) - refresh word data."""
        user = update.effective_user
        
        if not self._is_admin(user.id):
            await update.message.reply_text("🚫 Access denied.")
            return
        
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /refresh [chinese_word]")
            return
        
        word = args[0]
        status_msg = await update.message.reply_text(f"⏳ Refreshing data for: {word}")
        
        try:
            # Get fresh word details with scraping
            word_details = dictionary_service.get_word_details(word)
            
            # Show what was retrieved
            result_text = f"✅ Refreshed: {word}\n\n"
            result_text += f"📍 Pinyin: {word_details.get('pinyin', 'N/A')[:50]}...\n"
            result_text += f"📚 Translation: {word_details.get('translation', 'N/A')[:50]}...\n"
            result_text += f"🎨 Stroke GIFs: {'YES' if word_details.get('stroke_gifs') else 'NO'}\n"
            result_text += f"🖼️ Image: {'YES' if word_details.get('exemplary_image') else 'NO'}\n"
            result_text += f"💬 Examples: {'YES' if word_details.get('real_usage_examples') else 'NO'}"
            
            await status_msg.edit_text(result_text)
            
        except Exception as e:
            logger.error(f"Error refreshing word {word}: {e}")
            await status_msg.edit_text(f"❌ Error refreshing {word}: {str(e)}")
    
    async def cmd_listall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /listall command - list all users and their decks (admin only)."""
        user = update.effective_user
        
        if not self._is_admin(user.id):
            await update.message.reply_text("🚫 Access denied.")
            return
        
        users = db.get_users()
        
        if not users:
            await update.message.reply_text("No users found.")
            return
        
        text = "👥 *All Users and Their Decks*\n\n"
        
        for u in users:
            user_id = u.get('id', '')[:12] + '...'
            telegram_id = u.get('telegram_id', 'N/A')
            username = u.get('telegram_username', 'N/A')
            is_active = "✅" if u.get('is_active') else "⏳"
            is_admin = "🔧" if u.get('is_admin') else ""
            
            # Get word count for this user
            try:
                words = db.get_words_by_user(u.get('id'))
                word_count = len(words)
            except:
                word_count = 0
            
            text += f"{is_active} {is_admin} `{telegram_id}`\n"
            text += f"   Words: {word_count}\n"
            if username and username != 'N/A':
                text += f"   @{username}\n"
            text += "\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_pending(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pending command - show pending users (admin only)."""
        user = update.effective_user
        
        if not self._is_admin(user.id):
            await update.message.reply_text("🚫 Access denied.")
            return
        
        pending = db.get_pending_approvals()
        
        if not pending:
            await update.message.reply_text("✅ No pending approvals.")
            return
        
        text = "⏳ *Pending Approvals*\n\n"
        
        for p in pending:
            user_id = p.get('user_id', '')[:12] + '...'
            telegram_id = p.get('telegram_id', 'N/A')
            username = p.get('telegram_username', 'N/A')
            requested = p.get('requested_at', 'N/A')
            
            text += f"📋 `{telegram_id}`\n"
            if username and username != 'N/A':
                text += f"   @{username}\n"
            text += f"   ID: `{user_id}`\n"
            text += f"   Use /approve {p.get('user_id', '')}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_approve(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /approve command - approve a user (admin only)."""
        user = update.effective_user
        
        if not self._is_admin(user.id):
            await update.message.reply_text("🚫 Access denied.")
            return
        
        args = context.args
        if not args:
            await update.message.reply_text(
                "Usage: /approve [user_id]\n\n"
                "Get user_id from /pending command"
            )
            return
        
        target_user_id = args[0]
        
        # Activate the user
        success = db.update_user(target_user_id, {'is_active': True})
        
        if success:
            # Remove from pending
            db.remove_pending_approval(target_user_id)
            await update.message.reply_text(f"✅ User {target_user_id[:12]}... approved!")
        else:
            await update.message.reply_text(f"❌ User not found.")
    
    async def cmd_deny(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /deny command - deny/remove a pending user (admin only)."""
        user = update.effective_user
        
        if not self._is_admin(user.id):
            await update.message.reply_text("🚫 Access denied.")
            return
        
        args = context.args
        if not args:
            await update.message.reply_text(
                "Usage: /deny [user_id]\n\n"
                "This will remove the user from pending list."
            )
            return
        
        target_user_id = args[0]
        
        # Remove from pending
        db.remove_pending_approval(target_user_id)
        
        # Optionally could also delete the user entirely
        await update.message.reply_text(f"❌ User {target_user_id[:12]}... removed from pending.")
    
    # ==================== Message Handlers ====================
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages."""
        user = update.effective_user
        text = update.message.text
        
        user_data, is_new = self._get_or_create_user(str(user.id), user.username)
        
        if is_new:
            await update.message.reply_text(
                "👋 Welcome! Your account has been created and is pending approval.\n"
                "You'll be notified once approved."
            )
            return
        
        if not user_data.get('is_active'):
            await update.message.reply_text("⏳ Your account is pending approval.")
            return
        
        # Extract Chinese words
        chinese_words = extract_chinese_words(text)
        
        if not chinese_words:
            await update.message.reply_text(
                "I couldn't find any Chinese characters in your message.\n"
                "Send me Chinese text and I'll extract the words for you!"
            )
            return
        
        # Get current deck ID (returns deck number like "1", "2", or None for main)
        current_deck = self._get_current_deck_id(context)
        base_user_id = user_data['id']
        
        logger.info(f"handle_text: user={base_user_id[:8]}..., current_deck={current_deck}, words={chinese_words}")
        
        # Check for existing words in the CURRENT deck specifically
        # Pass base_user_id and current_deck to filter correctly
        words = db.get_words_by_user(base_user_id, current_deck)
        logger.info(f"handle_text: found {len(words)} existing words in deck {current_deck}")
        existing_chars = {w['character'] for w in words}
        
        new_words = [w for w in chinese_words if w not in existing_chars]
        skipped = [w for w in chinese_words if w in existing_chars]
        
        if not new_words:
            deck_name = "main deck" if not current_deck else f"deck {current_deck}"
            await update.message.reply_text(
                f"📚 All {len(chinese_words)} words are already in your {deck_name}!\n"
                f"Use /dictionary to see them."
            )
            return
        
        # Check if words exist in other decks or users (to copy data instead of scraping)
        global_words = {}
        # First check all decks of current user (get all words for this user)
        all_user_words = db.get_words_by_user(base_user_id)
        logger.info(f"handle_text: found {len(all_user_words)} words across all user decks")
        for w in all_user_words:
            if w['character'] in new_words and w['character'] not in global_words:
                global_words[w['character']] = w
        
        # Then check other users' dictionaries
        all_users = db.get_users()
        for other_user in all_users:
            if other_user['id'] != user_data['id']:
                other_words = db.get_words_by_user(other_user['id'])
                for w in other_words:
                    if w['character'] in new_words and w['character'] not in global_words:
                        global_words[w['character']] = w
        
        # Words to scrape (not found anywhere)
        words_to_scrape = [w for w in new_words if w not in global_words]
        words_to_copy = [w for w in new_words if w in global_words]
        
        logger.info(f"handle_text: new_words={new_words}, words_to_copy={words_to_copy}, words_to_scrape={words_to_scrape}")
        
        # Process words
        status_message = await update.message.reply_text(
            f"⏳ Processing {len(new_words)} new words...\n"
            f"This may take a moment."
        )
        
        added = []
        failed = []
        copied = []
        
        # First, copy words that already exist in other decks/users (no scraping needed)
        for word_text in words_to_copy:
            try:
                source_word = global_words[word_text]
                # Copy word details and update user_id to current deck
                # user_id format: base_user_id for deck 1, base_user_id-N for deck N (N>1)
                if current_deck and current_deck != "1":
                    target_user_id = f"{base_user_id}-{current_deck}"
                else:
                    target_user_id = base_user_id
                
                logger.info(f"Copying word '{word_text}' to deck {current_deck} with user_id={target_user_id[:20]}...")
                
                # Only include fields that exist in the database schema
                # Schema: character, user_id, pinyin, translation, meaning, stroke_gifs, 
                #         pronunciation, exemplary_image, anki_usage_examples, real_usage_examples, styled_term
                word_details = {
                    'character': source_word['character'],
                    'pinyin': source_word.get('pinyin', ''),
                    'styled_term': source_word.get('styled_term', ''),
                    'translation': source_word.get('translation', ''),
                    'meaning': source_word.get('meaning', ''),
                    'stroke_gifs': source_word.get('stroke_gifs', ''),
                    'pronunciation': source_word.get('pronunciation', ''),
                    'exemplary_image': source_word.get('exemplary_image', ''),
                    'anki_usage_examples': source_word.get('anki_usage_examples', ''),
                    'real_usage_examples': source_word.get('real_usage_examples', ''),
                    'user_id': target_user_id  # Use proper deck user_id format
                }
                import json
                logger.info(f"Word details being sent: {json.dumps(word_details, default=str)[:500]}")
                result = db.create_word(word_details)
                logger.info(f"Created word '{word_text}' in deck {current_deck}, result={result}")
                copied.append(word_text)
            except Exception as e:
                logger.error(f"Error copying word {word_text}: {e}", exc_info=True)
                # Don't try to scrape - just mark as failed
                failed.append(word_text)
        
        # Then scrape words that don't exist anywhere
        for i, word_text in enumerate(words_to_scrape):
            try:
                # Create progress callback for this word (sync wrapper for async edit_text)
                import asyncio
                
                async def edit_progress(stage: str, message: str):
                    try:
                        progress_text = (
                            f"⏳ Processing {i+1}/{len(words_to_scrape)}: {word_text}\n"
                            f"{message}"
                        )
                        await status_message.edit_text(progress_text)
                    except:
                        pass
                
                def progress_callback(stage: str, message: str):
                    # Schedule the async call
                    asyncio.create_task(edit_progress(stage, message))
                
                # Update status to show current progress
                asyncio.create_task(edit_progress("start", f"🔄 Starting scrape for {word_text}..."))
                
                word_details = dictionary_service.get_word_details(word_text, progress_callback)
                # user_id format: base_user_id for deck 1, base_user_id-N for deck N (N>1)
                if current_deck and current_deck != "1":
                    target_user_id = f"{base_user_id}-{current_deck}"
                else:
                    target_user_id = base_user_id
                word_details['user_id'] = target_user_id  # Use proper deck user_id format
                db.create_word(word_details)
                added.append(word_text)
                
                # Show brief success indicator
                success_text = (
                    f"✅ {word_text} added!\n"
                    f"📝 {(word_details.get('pinyin') or '')[:30]}..."
                )
                try:
                    await status_message.edit_text(success_text)
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"Error adding word {word_text}: {e}")
                failed.append(word_text)
                try:
                    await status_message.edit_text(f"❌ Failed: {word_text}")
                except:
                    pass
        
        # Update status message
        total_added = len(added) + len(copied)
        result_text = f"✅ Added {total_added} words!\n"
        if copied:
            result_text += f"📋 Copied {len(copied)} from existing\n"
        if added:
            result_text += f"🔍 Scraped {len(added)} new\n"
        if skipped:
            result_text += f"⏭️ Skipped {len(skipped)} existing in this deck\n"
        if failed:
            result_text += f"❌ Failed: {len(failed)}\n"
        
        result_text += f"\nUse /dictionary to see your words\n"
        result_text += "Use /export to download for Anki"
        
        logger.info(f"handle_text complete: added={added}, copied={copied}, failed={failed}, deck={current_deck}")
        
        await status_message.edit_text(result_text)
    
    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle image messages (OCR)."""
        user = update.effective_user
        
        user_data, is_new = self._get_or_create_user(str(user.id), user.username)
        
        if is_new:
            await update.message.reply_text(
                "👋 Welcome! Your account has been created and is pending approval.\n"
                "You'll be notified once approved."
            )
            return
        
        if not user_data.get('is_active'):
            await update.message.reply_text("⏳ Your account is pending approval.")
            return
        
        # TODO: Implement OCR using Google Vision API
        await update.message.reply_text(
            "📸 Image received!\n\n"
            "OCR functionality is being set up.\n"
            "For now, please type or paste the Chinese text directly."
        )
    
    # ==================== Callback Handler ====================
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = update.effective_user
        
        if data == "confirm_wipe":
            user_data = self._get_user_by_telegram(str(user.id))
            if user_data:
                db.delete_all_words(user_data['id'])
                await query.edit_message_text("✅ All your data has been cleared.")
        
        elif data == "cancel_wipe":
            await query.edit_message_text("❌ Data deletion cancelled.")
        
        elif data.startswith("switch_deck_"):
            full_deck_id = data.replace("switch_deck_", "")
            # Extract deck number from full ID (format: USERID-N or just USERID for deck 1)
            if '-' in full_deck_id:
                deck_num = full_deck_id.rsplit('-', 1)[1]
            else:
                deck_num = "1"  # Main deck has no suffix
            context.user_data['current_deck'] = deck_num
            
            # Get word count for this deck
            words = db.get_words_by_user(full_deck_id)
            count = len(words)
            
            await query.edit_message_text(
                f"✅ Switched to Deck {deck_num}.\n\n"
                f"Words in this deck: {count}\n\n"
                f"Use /dictionary, /export, etc. to work with this deck."
            )
    
    # ==================== Run ====================
    
    def run(self):
        """Run the bot."""
        if not self.initialize():
            logger.error("Failed to initialize bot!")
            return
        
        logger.info("Starting Telegram bot...")
        
        # Create event loop for Python 3.10+ compatibility
        import asyncio
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


# Global instance
telegram_bot = TelegramBotService()


if __name__ == "__main__":
    telegram_bot.run()
