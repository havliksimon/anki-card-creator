"""Chinese language utilities."""
import re
from typing import Tuple, List
import pypinyin
from pypinyin import pinyin, Style


# Tone colors for Chinese characters
TONE_COLORS = {
    1: '#ff0000',  # Red
    2: '#ffaa00',  # Orange
    3: '#00aa00',  # Green
    4: '#0000ff',  # Blue
    0: 'var(--text-secondary)'   # Neutral
}


def is_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    return any('\u4e00' <= char <= '\u9fff' for char in text)


def extract_chinese_words(text: str) -> List[str]:
    """Extract Chinese words from text."""
    pattern = re.compile(r'[\u4e00-\u9fff]+')
    return pattern.findall(text)


def get_tone_number(syllable: str) -> int:
    """Get tone number from pinyin syllable."""
    TONE_MARKS = {
        'ā': 1, 'á': 2, 'ǎ': 3, 'à': 4,
        'ō': 1, 'ó': 2, 'ǒ': 3, 'ò': 4,
        'ē': 1, 'é': 2, 'ě': 3, 'è': 4,
        'ī': 1, 'í': 2, 'ǐ': 3, 'ì': 4,
        'ū': 1, 'ú': 2, 'ǔ': 3, 'ù': 4,
        'ǖ': 1, 'ǘ': 2, 'ǚ': 3, 'ǜ': 4,
    }
    for char in syllable:
        if char in TONE_MARKS:
            return TONE_MARKS[char]
    return 0


def chinese_to_styled_pinyin(chinese_str: str) -> Tuple[str, str]:
    """
    Convert Chinese string to styled pinyin and hanzi.
    Returns: (styled_pinyin, styled_hanzi)
    """
    pinyin_list_of_lists = pinyin(chinese_str, style=Style.TONE, heteronym=False, errors='neutralize')
    
    pinyin_spans = []
    char_spans = []
    
    for char_in_word, pinyin_syllables_for_char in zip(chinese_str, pinyin_list_of_lists):
        syllable = pinyin_syllables_for_char[0] if pinyin_syllables_for_char else char_in_word
        
        tone = get_tone_number(syllable)
        color = TONE_COLORS.get(tone, TONE_COLORS[0])
        
        # Handle punctuation or non-converted characters
        if syllable == char_in_word and tone == 0:
            pinyin_spans.append(char_in_word)
            char_spans.append(char_in_word)
        elif color == TONE_COLORS[0]:
            pinyin_spans.append(syllable)
            char_spans.append(char_in_word)
        else:
            pinyin_spans.append(f'<span style="color:{color}">{syllable}</span>')
            char_spans.append(f'<span style="color:{color}">{char_in_word}</span>')
    
    return ' '.join(pinyin_spans), ''.join(char_spans)


def get_coverage_percentage(char_count: int) -> float:
    """Calculate Chinese text coverage percentage based on character count."""
    tiers = [
        (0, 0),
        (140, 50),
        (300, 60),
        (600, 75),
        (750, 80),
        (1250, 90),
        (1900, 95),
        (float('inf'), 95)
    ]
    
    for i in range(len(tiers) - 1):
        lower_count, lower_percent = tiers[i]
        upper_count, upper_percent = tiers[i+1]
        if lower_count <= char_count < upper_count:
            if upper_count == lower_count:
                return lower_percent
            ratio = (char_count - lower_count) / (upper_count - lower_count)
            return lower_percent + ratio * (upper_percent - lower_percent)
    
    return 95.0


def get_hsk_progress(char_count: int) -> dict:
    """Get HSK progress information."""
    HSK_LEVEL_DATA = [
        {"level": 1, "cumulative": 500},
        {"level": 2, "cumulative": 1272},
        {"level": 3, "cumulative": 2245},
        {"level": 4, "cumulative": 3245},
        {"level": 5, "cumulative": 4316},
        {"level": 6, "cumulative": 5456},
    ]
    
    current_hsk = 0
    for level in HSK_LEVEL_DATA:
        if char_count >= level['cumulative']:
            current_hsk = level['level']
    
    next_level = None
    progress_next = 0.0
    words_needed_next = 0
    words_achieved_next = 0
    
    if current_hsk < 6:
        current_level_cumulative = HSK_LEVEL_DATA[current_hsk - 1]['cumulative'] if current_hsk > 0 else 0
        next_level = HSK_LEVEL_DATA[current_hsk]
        words_needed_next = next_level['cumulative'] - current_level_cumulative
        words_achieved_next = char_count - current_level_cumulative
        progress_next = (words_achieved_next / words_needed_next) * 100 if words_needed_next > 0 else 0
    
    total_hsk6 = HSK_LEVEL_DATA[-1]['cumulative']
    progress_hsk6 = (char_count / total_hsk6) * 100
    
    return {
        'current_level': current_hsk,
        'next_level': next_level['level'] if next_level else 6,
        'progress_next': progress_next,
        'words_achieved_next': words_achieved_next,
        'words_needed_next': words_needed_next,
        'progress_hsk6': progress_hsk6,
        'total_hsk6': total_hsk6
    }
