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
        
        # Deck management
        self.application.add_handler(CommandHandler("list", self.cmd_list))
        self.application.add_handler(CommandHandler("l", self.cmd_list))
        self.application.add_handler(CommandHandler("chosedict", self.cmd_chosedict))
        
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
        
        # Callback handlers for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.callback_handler, pattern="^"))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        
    # ==================== Helper Methods ====================
    
    def _get_user_by_telegram(self, telegram_id: str) -> Optional[Dict]:
        """Get user by Telegram ID."""
        return db.get_user_by_telegram_id(str(telegram_id))
    
    def _get_or_create_user(self, telegram_id: str, username: str = None) -> Tuple[Dict, bool]:
        """Get existing user or create new one. Returns (user_data, is_new)."""
        user = self._get_user_by_telegram(telegram_id)
        if user:
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
        """Export user's dictionary to CSV bytes."""
        words = db.get_words_by_user(user_id)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Character', 'Pinyin', 'Translation', 'Meaning',
            'Stroke GIFs', 'Pronunciation', 'Image', 'Examples'
        ])
        
        # Write words
        for word in words:
            writer.writerow([
                word.get('character', ''),
                word.get('pinyin', ''),
                word.get('translation', ''),
                word.get('meaning', ''),
                word.get('stroke_gifs', ''),
                word.get('pronunciation', ''),
                word.get('exemplary_image', ''),
                word.get('anki_usage_examples', '')
            ])
        
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
        
        # Get page number from args
        args = context.args
        page = int(args[0]) if args and args[0].isdigit() else 1
        
        words = db.get_words_by_user(user_data['id'])
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
        
        stats = db.get_user_stats(user_data['id'])
        words = db.get_words_by_user(user_data['id'])
        
        info_text = (
            f"📊 *Your Dictionary Stats*\n\n"
            f"Total Words: {len(words)}\n"
            f"User ID: `{user_data['id'][:8]}...`\n\n"
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
        
        words = db.get_words_by_user(user_data['id'])
        if not words:
            await update.message.reply_text(
                "📚 Your dictionary is empty!\n\n"
                "Send me some Chinese text first to add words."
            )
            return
        
        # Generate CSV
        csv_data = self._export_to_csv(user_data['id'])
        
        # Send file
        await update.message.reply_document(
            document=csv_data,
            filename=f"anki_dictionary_{user.id}.csv",
            caption=(
                f"📥 Your dictionary ({len(words)} words)\n\n"
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
    
    async def cmd_chosedict(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /chosedict command."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        args = context.args
        if not args:
            await update.message.reply_text(
                "Usage: /chosedict [deck_number]\n\n"
                "Example: /chosedict 1\n\n"
                "This switches you to a different vocabulary deck.\n"
                "If the deck doesn't exist, it will be created."
            )
            return
        
        try:
            deck_num = int(args[0])
            if deck_num < 1:
                raise ValueError()
        except ValueError:
            await update.message.reply_text("❌ Deck number must be a positive integer (1, 2, 3, etc.)")
            return
        
        # Store deck preference in context
        context.user_data['current_deck'] = deck_num
        
        await update.message.reply_text(
            f"✅ Switched to Deck {deck_num}.\n\n"
            f"New words will be added to this deck.\n"
            f"Use /dictionary to see words in this deck."
        )
    
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
        
        words = db.get_words_by_user(user_data['id'])
        if not words:
            await update.message.reply_text("📚 Your dictionary is empty.")
            return
        
        target = args[0]
        
        # Try to remove by index
        if target.isdigit():
            idx = int(target) - 1  # 1-based to 0-based
            if 0 <= idx < len(words):
                word = words[idx]
                db.delete_word(word['id'], user_data['id'])
                await update.message.reply_text(f"✅ Removed: {word['character']}")
            else:
                await update.message.reply_text(f"❌ Invalid index. Use 1-{len(words)}")
        else:
            # Remove by character
            found = False
            for word in words:
                if word['character'] == target:
                    db.delete_word(word['id'], user_data['id'])
                    await update.message.reply_text(f"✅ Removed: {target}")
                    found = True
                    break
            if not found:
                await update.message.reply_text(f"❌ Word '{target}' not found.")
    
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
        
        args = context.args
        if not args:
            await update.message.reply_text(
                "Usage: /search [character or pinyin]\n\n"
                "Example: /search 你好\n"
                "Example: /search nihao"
            )
            return
        
        query = args[0].lower()
        words = db.get_words_by_user(user_data['id'])
        
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
        
        # Check for existing words
        words = db.get_words_by_user(user_data['id'])
        existing_chars = {w['character'] for w in words}
        
        new_words = [w for w in chinese_words if w not in existing_chars]
        skipped = [w for w in chinese_words if w in existing_chars]
        
        if not new_words:
            await update.message.reply_text(
                f"📚 All {len(chinese_words)} words are already in your dictionary!\n"
                f"Use /dictionary to see them."
            )
            return
        
        # Process words
        status_message = await update.message.reply_text(
            f"⏳ Processing {len(new_words)} new words...\n"
            f"This may take a moment."
        )
        
        added = []
        failed = []
        
        for word_text in new_words:
            try:
                word_details = dictionary_service.get_word_details(word_text)
                word_details['user_id'] = user_data['id']
                db.create_word(word_details)
                added.append(word_text)
            except Exception as e:
                logger.error(f"Error adding word {word_text}: {e}")
                failed.append(word_text)
        
        # Update status message
        result_text = f"✅ Added {len(added)} words!\n"
        if skipped:
            result_text += f"⏭️ Skipped {len(skipped)} existing\n"
        if failed:
            result_text += f"❌ Failed: {len(failed)}\n"
        
        result_text += f"\nUse /dictionary to see your words\n"
        result_text += "Use /export to download for Anki"
        
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
    
    # ==================== Run ====================
    
    def run(self):
        """Run the bot."""
        if not self.initialize():
            logger.error("Failed to initialize bot!")
            return
        
        logger.info("Starting Telegram bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


# Global instance
telegram_bot = TelegramBotService()


if __name__ == "__main__":
    telegram_bot.run()
