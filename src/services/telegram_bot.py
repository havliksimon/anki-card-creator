"""Telegram Bot Service for Anki Card Creator - Simplified Deck Logic.

Original App Logic:
- Regular users: ONE dictionary only (their own)
- Admin: Can access ANY deck via /selectdict [number]
- Decks are auto-created when words are added
- All commands operate on CURRENTLY SELECTED deck only

Commands:
- /start - Initial setup
- /help - Show available commands  
- /export, /csv, /e - Export dictionary to CSV
- /dictionary - View saved words
- /list, /l - List admin's decks (admin only)
- /listall - List all users/decks (admin debug)
- /selectdict, /s - Switch deck (admin only)
- /backup - Backup menu (admin only)
- /rmdict - Remove words
- /search - Search for words
- /clearmydata - Clear all user data
- /dictinfo - Show dictionary statistics
"""
import os
import io
import csv
import logging
import re
import base64
import json
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


class TelegramBot:
    """Telegram Bot with simplified deck logic matching original app."""
    
    def __init__(self):
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.admin_id = os.environ.get('TELEGRAM_ADMIN_ID')
        self.application = None
    
    def _is_admin(self, telegram_id: str) -> bool:
        """Check if user is admin."""
        return str(telegram_id) == str(self.admin_id)
    
    def _get_or_create_user(self, telegram_id: str, username: str = None) -> Tuple[Dict, bool]:
        """Get existing user or create new one."""
        user = db.get_user_by_telegram_id(telegram_id)
        if user:
            return user, False
        
        # Create new user
        import uuid
        user_id = str(uuid.uuid4())
        user_data = {
            'id': user_id,
            'telegram_id': telegram_id,
            'telegram_username': username,
            'is_active': False,  # Requires approval
            'is_admin': False
        }
        db.create_user(user_data)
        
        # Add to pending approvals
        db.create_pending_approval(user_id)
        
        return user_data, True
    
    def _get_user_by_telegram(self, telegram_id: str) -> Optional[Dict]:
        """Get user by telegram ID."""
        return db.get_user_by_telegram_id(telegram_id)
    
    # ==================== DECK MANAGEMENT (ADMIN ONLY) ====================
    
    def _get_current_deck_id(self, context: ContextTypes.DEFAULT_TYPE, user_data: Dict) -> str:
        """Get the current deck ID for operations.
        
        For regular users: always returns their own user_id
        For admin: returns the deck selected via /selectdict or their own
        """
        is_admin = user_data.get('is_admin', False)
        
        if not is_admin:
            # Regular users always use their own deck
            return user_data['id']
        
        # Admin: check if they have a selected deck
        selected_deck = context.user_data.get('admin_selected_deck')
        if selected_deck:
            return selected_deck
        
        # Default to admin's own deck
        return user_data['id']
    
    def _get_all_decks(self) -> List[Dict]:
        """Get all decks with word counts (for admin /list)."""
        # First, get all unique user_ids from words table via a simple count query
        # We query each deck individually to get accurate counts
        try:
            users = db.get_users()
        except:
            users = []
        
        # Find admin user
        admin_user = next((u for u in users if u.get('is_admin')), None)
        admin_id = admin_user['id'] if admin_user else None
        
        # Get all words and extract unique user_ids
        # Use a more reliable method - query words and get distinct user_ids
        try:
            all_words = db.get_all_words()
            unique_user_ids = set()
            for word in all_words:
                uid = word.get('user_id')
                if uid:
                    unique_user_ids.add(uid)
        except Exception as e:
            logger.error(f"Error getting words: {e}")
            unique_user_ids = set()
        
        # If we got no results, try querying admin's main deck at least
        if not unique_user_ids and admin_id:
            unique_user_ids.add(admin_id)
        
        # Build deck list with accurate counts
        decks = []
        for uid in unique_user_ids:
            # Get accurate count by querying this specific deck
            try:
                words = db.get_words_by_user(uid)
                count = len(words)
            except:
                count = 0
            
            # Find user info
            user = next((u for u in users if u.get('id') == uid), None)
            if not user and uid.isdigit():
                # Legacy numeric deck - assign to admin
                user = admin_user
            
            is_admin_deck = user.get('is_admin', False) if user else False
            telegram_id = user.get('telegram_id', '') if user else ''
            
            decks.append({
                'id': uid,
                'word_count': count,
                'is_admin': is_admin_deck,
                'telegram_id': telegram_id
            })
        
        # Sort by word count desc
        decks.sort(key=lambda x: x['word_count'], reverse=True)
        return decks
    
    def _format_word_list(self, words: List[Dict], page: int = 1) -> str:
        """Format word list for display."""
        if not words:
            return "📚 This deck is empty.\n\nSend me Chinese text to add words!"
        
        lines = [f"📚 *Dictionary ({len(words)} words)*\n"]
        
        # Pagination
        per_page = 10
        total_pages = (len(words) + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        
        start = (page - 1) * per_page
        end = start + per_page
        page_words = words[start:end]
        
        for i, word in enumerate(page_words, start + 1):
            char = word.get('character', '?')
            pinyin = word.get('pinyin', '')[:30]
            lines.append(f"{i}. {char} - {pinyin}")
        
        if total_pages > 1:
            lines.append(f"\n📄 Page {page}/{total_pages}")
            lines.append(f"Use /dictionary {page+1} for next page")
        
        return "\n".join(lines)
    
    def _export_to_csv(self, user_id: str) -> bytes:
        """Export deck to CSV."""
        words = db.get_words_by_user(user_id)
        
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
            component2 = word.get('component2', '')
            component1 = word.get('component1', '')
            real_usage_examples = word.get('real_usage_examples', '')
            
            # Parse stroke GIFs
            stroke_order = word.get('stroke_gifs', '')
            stroke_urls = stroke_order.split(', ') if stroke_order else []
            stroke_order_fields = stroke_urls[:6]
            while len(stroke_order_fields) < 6:
                stroke_order_fields.append('')
            
            csv_row = [
                character, styled_term, pinyin, translation, meaning,
                pronunciation, example_link, exemplary_image, example_usage,
                reading, component2, component1, real_usage_examples
            ] + stroke_order_fields
            
            writer.writerow(csv_row)
        
        return output.getvalue().encode('utf-8')
    
    # ==================== Command Handlers ====================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        user_data, is_new = self._get_or_create_user(str(user.id), user.username)
        
        if is_new:
            await update.message.reply_text(
                "👋 Welcome to Anki Card Creator!\n\n"
                "Your account has been created and is pending approval.\n"
                "You'll be notified once approved.\n\n"
                "Once approved, send me Chinese text and I'll create flashcards for you!"
            )
        else:
            await update.message.reply_text(
                "👋 Welcome back!\n\n"
                "Send me Chinese text to add words to your dictionary.\n"
                "Use /help to see all commands."
            )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = (
            "📖 *Available Commands*\n\n"
            "*Basic:*\n"
            "/start - Start the bot\n"
            "/help - Show this help\n\n"
            "*Dictionary:*\n"
            "/dictionary [page] - View your words\n"
            "/export - Export to CSV for Anki\n"
            "/dictinfo - Show statistics\n"
            "/search [term] - Search dictionary\n"
            "/rmdict [index|character] - Remove word\n\n"
            "*Account:*\n"
            "/clearmydata - Delete all your data\n\n"
        )
        
        user = update.effective_user
        if self._is_admin(user.id):
            help_text += (
                "*Admin Commands:*\n"
                "/list, /l - List your decks\n"
                "/listall - List all users/decks (debug)\n"
                "/selectdict [n], /s [n] - Switch to deck N\n"
                "/backup - Backup menu\n"
                "/wipedict [user_id] - Wipe a deck\n"
                "/stats - System statistics\n"
                "/pending - Show pending approvals\n"
                "/approve [id] - Approve user\n"
            )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def cmd_dictionary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /dictionary command."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        if not user_data.get('is_active'):
            await update.message.reply_text("⏳ Your account is pending approval.")
            return
        
        # Get current deck
        deck_id = self._get_current_deck_id(context, user_data)
        
        # Get page
        args = context.args
        page = int(args[0]) if args and args[0].isdigit() else 1
        
        words = db.get_words_by_user(deck_id)
        text = self._format_word_list(words, page)
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
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
        
        deck_id = self._get_current_deck_id(context, user_data)
        words = db.get_words_by_user(deck_id)
        
        # Show which deck we're viewing (for admin)
        deck_label = ""
        if user_data.get('is_admin'):
            if deck_id == user_data['id']:
                deck_label = " (Your main deck)"
            elif deck_id.isdigit():
                deck_label = f" (Legacy deck {deck_id})"
            else:
                deck_label = f" (Deck: {deck_id[:20]}...)"
        
        info_text = (
            f"📊 *Dictionary Stats*{deck_label}\n\n"
            f"Total Words: {len(words)}\n"
            f"User ID: `{user_data['id'][:8]}...`\n\n"
            "Keep adding words to build your vocabulary!"
        )
        await update.message.reply_text(info_text, parse_mode='Markdown')
    
    async def cmd_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /export command."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        if not user_data.get('is_active'):
            await update.message.reply_text("⏳ Your account is pending approval.")
            return
        
        deck_id = self._get_current_deck_id(context, user_data)
        words = db.get_words_by_user(deck_id)
        
        if not words:
            await update.message.reply_text("📚 This deck is empty!")
            return
        
        csv_data = self._export_to_csv(deck_id)
        
        # Filename includes deck info for admin
        if user_data.get('is_admin') and deck_id != user_data['id']:
            if deck_id.isdigit():
                deck_suffix = f"_deck{deck_id}"
            else:
                deck_suffix = f"_{deck_id[:8]}"
        else:
            deck_suffix = ""
        
        await update.message.reply_document(
            document=csv_data,
            filename=f"anki_dictionary_{user.id}{deck_suffix}.csv",
            caption=f"📥 Your dictionary ({len(words)} words)"
        )
    
    async def cmd_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list and /l commands (admin only)."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        if not user_data.get('is_admin'):
            await update.message.reply_text("🚫 Admin only command.")
            return
        
        decks = self._get_all_decks()
        
        if not decks:
            await update.message.reply_text("No decks found.")
            return
        
        current_deck = self._get_current_deck_id(context, user_data)
        
        # Build inline keyboard with clickable deck buttons
        keyboard = []
        lines = ["📚 *Your Decks*\n"]
        
        for deck in decks:
            deck_id = deck['id']
            count = deck['word_count']
            
            # Determine deck number for display and callback
            if deck_id == user_data['id']:
                deck_num = "1"
                display_name = "1 (Your main)"
            elif deck_id.isdigit():
                deck_num = deck_id
                display_name = deck_id
            elif '-' in deck_id:
                try:
                    deck_num = deck_id.rsplit('-', 1)[1]
                    display_name = deck_num
                except:
                    deck_num = deck_id
                    display_name = deck_id[:12]
            else:
                deck_num = deck_id
                display_name = deck_id[:12]
            
            is_current = (deck_id == current_deck)
            marker = "🎯 " if is_current else ""
            
            lines.append(f"{marker}Deck {display_name}: {count} words")
            
            # Add clickable button for this deck
            button_text = f"{marker}Deck {display_name} ({count} words)"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"selectdeck_{deck_num}")])
        
        lines.append(f"\nClick a button to switch decks:")
        
        await update.message.reply_text(
            "\n".join(lines), 
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def cmd_listall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /listall command (admin debug)."""
        user = update.effective_user
        
        if not self._is_admin(user.id):
            await update.message.reply_text("🚫 Admin only.")
            return
        
        users = db.get_users()
        
        text = "👥 *All Users and Their Decks*\n\n"
        
        for u in users:
            telegram_id = u.get('telegram_id', 'N/A')
            username = u.get('telegram_username', 'N/A')
            is_active = "✅" if u.get('is_active') else "⏳"
            is_admin = "🔧" if u.get('is_admin') else ""
            
            # Get word count for this user
            words = db.get_words_by_user(u.get('id'))
            word_count = len(words)
            
            text += f"{is_active} {is_admin} `{telegram_id}`\n"
            text += f"   Words: {word_count}\n"
            if username and username != 'N/A':
                text += f"   @{username}\n"
            text += "\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_selectdict(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /selectdict and /s commands (admin only)."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        if not user_data.get('is_admin'):
            await update.message.reply_text("🚫 Admin only command.")
            return
        
        args = context.args
        
        if not args:
            # Show current selection and available decks
            current = self._get_current_deck_id(context, user_data)
            decks = self._get_all_decks()
            
            text = f"📂 *Current Deck:* `{current[:20]}...`\n\n"
            text += "Available decks:\n"
            for deck in decks[:10]:
                deck_id = deck['id']
                if deck_id == user_data['id']:
                    label = "1 (Your main)"
                elif deck_id.isdigit():
                    label = deck_id
                else:
                    label = deck_id[:12]
                text += f"  • {label}\n"
            
            text += "\nUse `/selectdict [number]` to switch"
            await update.message.reply_text(text, parse_mode='Markdown')
            return
        
        deck_input = args[0]
        
        # Validate and set deck
        if deck_input.isdigit():
            deck_num = deck_input
            # Check if this deck exists
            all_decks = self._get_all_decks()
            matching = [d for d in all_decks if d['id'] == deck_num or d['id'].endswith(f"-{deck_num}")]
            
            if matching:
                target_deck = matching[0]['id']
            else:
                # Legacy numeric deck might not have words yet
                target_deck = deck_num
        elif deck_input.startswith("userid-") or len(deck_input) > 20:
            # Full user ID provided
            target_deck = deck_input
        else:
            await update.message.reply_text("❌ Invalid deck identifier.")
            return
        
        # Set the selected deck
        context.user_data['admin_selected_deck'] = target_deck
        
        # Verify by getting word count
        words = db.get_words_by_user(target_deck)
        
        await update.message.reply_text(
            f"✅ Switched to deck: `{target_deck[:30]}...`\n"
            f"Words in this deck: {len(words)}\n\n"
            f"All commands now operate on this deck.\n"
            f"Use `/selectdict 1` to return to your main deck.",
            parse_mode='Markdown'
        )
    
    async def cmd_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /backup command (admin only)."""
        user = update.effective_user
        
        if not self._is_admin(user.id):
            await update.message.reply_text("🚫 Admin only.")
            return
        
        keyboard = [
            [InlineKeyboardButton("💾 Backup Now", callback_data="backup_now")],
            [InlineKeyboardButton("🔄 Restore Last", callback_data="restore_last")],
            [InlineKeyboardButton("📋 List Backups", callback_data="list_backups")],
        ]
        
        await update.message.reply_text(
            "📦 *Backup Menu*\n\nSelect an option:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _handle_backup_callback(self, query, data):
        """Handle backup menu callbacks."""
        if data == "backup_now":
            await query.edit_message_text("⏳ Creating backup...")
            try:
                # TODO: Implement actual backup
                await query.edit_message_text("✅ Backup created successfully!")
            except Exception as e:
                await query.edit_message_text(f"❌ Backup failed: {e}")
        
        elif data == "restore_last":
            keyboard = [
                [InlineKeyboardButton("✅ Yes, restore", callback_data="confirm_restore")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_restore")],
            ]
            await query.edit_message_text(
                "⚠️ *Restore Backup*\n\nThis will overwrite current data. Continue?",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == "list_backups":
            # TODO: List actual backups
            await query.edit_message_text(
                "📋 *Available Backups*\n\n"
                "(Backup listing not yet implemented)"
            )
        
        elif data == "confirm_restore":
            await query.edit_message_text("⏳ Restoring...")
            # TODO: Implement restore
            await query.edit_message_text("✅ Restore completed!")
        
        elif data == "cancel_restore":
            await query.edit_message_text("❌ Restore cancelled.")
    
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
        
        deck_id = self._get_current_deck_id(context, user_data)
        
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
        
        words = db.get_words_by_user(deck_id)
        if not words:
            await update.message.reply_text("📚 This deck is empty.")
            return
        
        target = args[0]
        
        # Try to remove by index
        if target.isdigit():
            idx = int(target) - 1
            if 0 <= idx < len(words):
                word = words[idx]
                db.delete_word(word['id'], deck_id)
                await update.message.reply_text(f"✅ Removed: {word['character']}")
            else:
                await update.message.reply_text(f"❌ Invalid index. Use 1-{len(words)}")
        else:
            # Remove by character
            found = False
            for word in words:
                if word['character'] == target:
                    db.delete_word(word['id'], deck_id)
                    await update.message.reply_text(f"✅ Removed: {target}")
                    found = True
                    break
            if not found:
                await update.message.reply_text(f"❌ Word '{target}' not found.")
    
    async def cmd_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        user = update.effective_user
        user_data = self._get_user_by_telegram(str(user.id))
        
        if not user_data:
            await update.message.reply_text("❌ Please use /start first.")
            return
        
        deck_id = self._get_current_deck_id(context, user_data)
        
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /search [character or pinyin]")
            return
        
        query = args[0].lower()
        words = db.get_words_by_user(deck_id)
        
        results = []
        for i, word in enumerate(words, 1):
            char = word.get('character', '').lower()
            pinyin = word.get('pinyin', '').lower()
            if query in char or query in pinyin:
                results.append(f"{i}. {word['character']} - {word['pinyin'][:30]}")
        
        if results:
            text = "🔍 *Search Results:*\n\n" + "\n".join(results[:20])
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
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, delete all", callback_data="confirm_wipe")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_wipe")],
        ]
        
        deck_id = self._get_current_deck_id(context, user_data)
        words = db.get_words_by_user(deck_id)
        
        await update.message.reply_text(
            f"⚠️ *Clear All Data*\n\n"
            f"This will delete all {len(words)} words from the current deck.\n"
            f"This action cannot be undone.\n\n"
            f"Are you sure?",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ==================== Admin Commands ====================
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command (admin only)."""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("🚫 Admin only.")
            return
        
        stats = db.get_stats()
        users = db.get_users()
        
        text = (
            "📊 *System Statistics*\n\n"
            f"Total Users: {stats.get('total_users', 0)}\n"
            f"Total Words: {stats.get('total_words', 0)}\n"
            f"Active Users: {stats.get('active_users', 0)}\n"
            f"Pending Approvals: {len(db.get_pending_approvals())}"
        )
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_wipedict(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /wipedict command (admin only)."""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("🚫 Admin only.")
            return
        
        args = context.args
        if not args:
            # Wipe current deck
            user_data = self._get_user_by_telegram(str(update.effective_user.id))
            deck_id = self._get_current_deck_id(context, user_data)
            words = db.get_words_by_user(deck_id)
            db.delete_all_words(deck_id)
            await update.message.reply_text(f"🗑️ Wiped {len(words)} words from current deck.")
            return
        
        target_id = args[0]
        words = db.get_words_by_user(target_id)
        db.delete_all_words(target_id)
        await update.message.reply_text(f"🗑️ Wiped {len(words)} words from deck {target_id[:20]}...")
    
    async def cmd_pending(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pending command (admin only)."""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("🚫 Admin only.")
            return
        
        pending = db.get_pending_approvals()
        
        if not pending:
            await update.message.reply_text("✅ No pending approvals.")
            return
        
        text = "⏳ *Pending Approvals*\n\n"
        for p in pending:
            user = db.get_user_by_id(p.get('user_id'))
            if user:
                telegram_id = user.get('telegram_id', 'N/A')
                username = user.get('telegram_username', 'N/A')
                text += f"ID: `{telegram_id}`\n"
                if username != 'N/A':
                    text += f"@{username}\n"
                text += f"Approve: `/approve {p['user_id'][:8]}`\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_approve(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /approve command (admin only)."""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("🚫 Admin only.")
            return
        
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /approve [user_id]")
            return
        
        target_id = args[0]
        
        # Find user by partial ID
        users = db.get_users()
        target_user = None
        for u in users:
            if u['id'].startswith(target_id):
                target_user = u
                break
        
        if not target_user:
            await update.message.reply_text("❌ User not found.")
            return
        
        # Activate user
        db.update_user(target_user['id'], {'is_active': True})
        db.remove_pending_approval(target_user['id'])
        
        await update.message.reply_text(
            f"✅ Approved user: `{target_user.get('telegram_id', 'N/A')}`",
            parse_mode='Markdown'
        )
    
    # ==================== Message Handlers ====================
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages - add words to current deck."""
        user = update.effective_user
        text = update.message.text
        
        user_data, is_new = self._get_or_create_user(str(user.id), user.username)
        
        if is_new:
            await update.message.reply_text(
                "👋 Welcome! Your account has been created and is pending approval."
            )
            return
        
        if not user_data.get('is_active'):
            await update.message.reply_text("⏳ Your account is pending approval.")
            return
        
        # Extract Chinese words
        chinese_words = extract_chinese_words(text)
        
        if not chinese_words:
            await update.message.reply_text(
                "I couldn't find any Chinese characters.\n"
                "Send me Chinese text and I'll extract the words!"
            )
            return
        
        # Get current deck
        deck_id = self._get_current_deck_id(context, user_data)
        
        # Check existing words in this deck
        existing_words = db.get_words_by_user(deck_id)
        existing_chars = {w['character'] for w in existing_words}
        
        new_words = [w for w in chinese_words if w not in existing_chars]
        skipped = [w for w in chinese_words if w in existing_chars]
        
        if not new_words:
            await update.message.reply_text(
                f"📚 All {len(chinese_words)} words are already in this deck!\n"
                f"Use /dictionary to see them."
            )
            return
        
        # Check if words exist in other decks (for copying)
        # Search ALL words in database, including legacy numeric decks
        global_words = {}
        try:
            all_words_in_db = db.get_all_words()
            for w in all_words_in_db:
                char = w.get('character')
                if char in new_words and char not in global_words:
                    global_words[char] = w
        except Exception as e:
            logger.error(f"Error searching all words: {e}")
            # Fallback: search user decks
            all_users = db.get_users()
            for u in all_users:
                try:
                    u_words = db.get_words_by_user(u['id'])
                    for w in u_words:
                        if w['character'] in new_words and w['character'] not in global_words:
                            global_words[w['character']] = w
                except:
                    pass
        
        words_to_copy = [w for w in new_words if w in global_words]
        words_to_scrape = [w for w in new_words if w not in global_words]
        
        # Process
        status_msg = await update.message.reply_text(
            f"⏳ Processing {len(new_words)} words..."
        )
        
        added = []
        copied = []
        failed = []
        
        # Copy existing words
        for word_text in words_to_copy:
            try:
                source = global_words[word_text]
                word_details = {
                    'character': source['character'],
                    'pinyin': source.get('pinyin', ''),
                    'styled_term': source.get('styled_term', ''),
                    'translation': source.get('translation', ''),
                    'meaning': source.get('meaning', ''),
                    'stroke_gifs': source.get('stroke_gifs', ''),
                    'pronunciation': source.get('pronunciation', ''),
                    'exemplary_image': source.get('exemplary_image', ''),
                    'anki_usage_examples': source.get('anki_usage_examples', ''),
                    'real_usage_examples': source.get('real_usage_examples', ''),
                    'user_id': deck_id
                }
                result = db.create_word(word_details)
                if result:
                    copied.append(word_text)
                    logger.info(f"Copied '{word_text}' to deck {deck_id}")
                else:
                    logger.error(f"Failed to copy '{word_text}' - create_word returned None")
                    failed.append(word_text)
            except Exception as e:
                logger.error(f"Error copying {word_text}: {e}", exc_info=True)
                failed.append(word_text)
        
        # Scrape new words
        for word_text in words_to_scrape:
            try:
                details = dictionary_service.get_word_details(word_text)
                details['user_id'] = deck_id
                result = db.create_word(details)
                if result:
                    added.append(word_text)
                    logger.info(f"Scraped and added '{word_text}' to deck {deck_id}")
                else:
                    logger.error(f"Failed to add scraped word '{word_text}'")
                    failed.append(word_text)
            except Exception as e:
                logger.error(f"Error scraping {word_text}: {e}", exc_info=True)
                failed.append(word_text)
        
        # Result
        result_text = f"✅ Added {len(added) + len(copied)} words!\n"
        if copied:
            result_text += f"📋 Copied {len(copied)} from existing\n"
        if added:
            result_text += f"🔍 Scraped {len(added)} new\n"
        if failed:
            result_text += f"❌ Failed: {len(failed)}\n"
        
        result_text += "\nUse /dictionary to see your words"
        
        await status_msg.edit_text(result_text)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("backup_") or data in ["confirm_restore", "cancel_restore"]:
            await self._handle_backup_callback(query, data)
        elif data.startswith("selectdeck_"):
            # Handle deck selection from inline keyboard
            deck_num = data.replace("selectdeck_", "")
            user = update.effective_user
            user_data = self._get_user_by_telegram(str(user.id))
            
            if not user_data or not user_data.get('is_admin'):
                await query.edit_message_text("🚫 Admin only.")
                return
            
            # Find the deck with this number
            decks = self._get_all_decks()
            target_deck = None
            for deck in decks:
                deck_id = deck['id']
                if deck_id == user_data['id'] and deck_num == "1":
                    target_deck = deck_id
                    break
                elif deck_id.isdigit() and deck_id == deck_num:
                    target_deck = deck_id
                    break
                elif '-' in deck_id:
                    try:
                        if deck_id.rsplit('-', 1)[1] == deck_num:
                            target_deck = deck_id
                            break
                    except:
                        pass
            
            if not target_deck:
                await query.edit_message_text(f"❌ Deck {deck_num} not found.")
                return
            
            # Set the selected deck
            context.user_data['admin_selected_deck'] = target_deck
            words = db.get_words_by_user(target_deck)
            
            await query.edit_message_text(
                f"✅ Switched to Deck {deck_num}\n"
                f"Words: {len(words)}\n\n"
                f"All commands now use this deck."
            )
        elif data == "confirm_wipe":
            user = update.effective_user
            user_data = self._get_user_by_telegram(str(user.id))
            if user_data:
                deck_id = self._get_current_deck_id(context, user_data)
                db.delete_all_words(deck_id)
                await query.edit_message_text("✅ All data cleared.")
        elif data == "cancel_wipe":
            await query.edit_message_text("❌ Cancelled.")
    
    # ==================== Setup ====================
    
    def setup_handlers(self, application: Application):
        """Setup command handlers."""
        # Basic commands
        application.add_handler(CommandHandler("start", self.cmd_start))
        application.add_handler(CommandHandler("help", self.cmd_help))
        
        # Dictionary commands
        application.add_handler(CommandHandler("dictionary", self.cmd_dictionary))
        application.add_handler(CommandHandler("dictinfo", self.cmd_dictinfo))
        application.add_handler(CommandHandler(["export", "csv", "e"], self.cmd_export))
        application.add_handler(CommandHandler(["list", "l"], self.cmd_list))
        application.add_handler(CommandHandler("listall", self.cmd_listall))
        application.add_handler(CommandHandler(["selectdict", "s"], self.cmd_selectdict))
        application.add_handler(CommandHandler("backup", self.cmd_backup))
        application.add_handler(CommandHandler("rmdict", self.cmd_rmdict))
        application.add_handler(CommandHandler("search", self.cmd_search))
        application.add_handler(CommandHandler("clearmydata", self.cmd_clearmydata))
        
        # Admin commands
        application.add_handler(CommandHandler("stats", self.cmd_stats))
        application.add_handler(CommandHandler("wipedict", self.cmd_wipedict))
        application.add_handler(CommandHandler("pending", self.cmd_pending))
        application.add_handler(CommandHandler("approve", self.cmd_approve))
        
        # Callbacks
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    def initialize(self) -> bool:
        """Initialize the bot."""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not set!")
            return False
        
        try:
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers(self.application)
            logger.info("Telegram bot initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            return False
    
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
        
        self.application.run_polling()


# Global instance
telegram_bot = TelegramBot()
