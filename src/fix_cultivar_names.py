#!/usr/bin/env python3
"""
Script to fix common errors in cultivar names:
- Latin/Cyrillic character confusion
- Spacing issues
- Capitalization problems
- Merged words
"""

import re
import sys


# Mapping of Latin letters to Cyrillic equivalents
LATIN_TO_CYRILLIC = {
    'a': 'а', 'A': 'А',
    'c': 'с', 'C': 'С',
    'e': 'е', 'E': 'Е',
    'k': 'к', 'K': 'К',
    'm': 'м', 'M': 'М',
    'o': 'о', 'O': 'О',
    'p': 'р', 'P': 'Р',
    'y': 'у', 'Y': 'У',
}


def fix_latin_cyrillic(text):
    """Replace Latin letters with Cyrillic equivalents."""
    result = text
    for latin, cyrillic in LATIN_TO_CYRILLIC.items():
        result = result.replace(latin, cyrillic)
    return result


def normalize_spacing(text):
    """Remove extra spaces and trim edges."""
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    # Trim leading and trailing spaces
    text = text.strip()
    return text


def fix_capitalization(text):
    """Ensure first letter is uppercase."""
    if not text:
        return text
    # Check if first character is a Cyrillic or Latin letter
    first_char = text[0]
    if first_char.isalpha():
        return first_char.upper() + text[1:]
    return text


def separate_words(text):
    """Detect and separate merged words (lowercase + uppercase pattern)."""
    # Pattern: lowercase Cyrillic letter followed by uppercase Cyrillic letter
    # This indicates a word boundary
    pattern = r'([а-яё])([А-ЯЁ])'
    # Insert space between lowercase and uppercase Cyrillic letters
    result = re.sub(pattern, r'\1 \2', text)
    return result


def fix_cultivar_name(name):
    """Apply all fixes to a cultivar name."""
    if not name.strip():
        return name
    
    # Apply fixes in sequence
    fixed = name
    fixed = fix_latin_cyrillic(fixed)
    fixed = separate_words(fixed)
    fixed = normalize_spacing(fixed)
    fixed = fix_capitalization(fixed)
    
    return fixed


def main():
    """Main processing function."""
    input_file = 'ugly_names.txt'
    output_file = 'ugly_names_fixed.txt'
    
    # Read input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.", file=sys.stderr)
        sys.exit(1)
    
    # Process each line
    fixed_lines = []
    for line in lines:
        original = line.rstrip('\n')
        fixed = fix_cultivar_name(original)
        fixed_lines.append(fixed)
    
    # Write output file
    with open(output_file, 'w', encoding='utf-8') as f:
        for fixed in fixed_lines:
            f.write(fixed + '\n')
    
    # Print summary
    print(f"Processed {len(fixed_lines)} cultivar names")
    print(f"Output written to '{output_file}'")
    
    # Show some examples of fixes
    print("\nSample fixes:")
    count = 0
    for original, fixed in zip(lines, fixed_lines):
        original = original.rstrip('\n')
        if original != fixed and count < 5:
            print(f"  '{original}' → '{fixed}'")
            count += 1


if __name__ == '__main__':
    main()

