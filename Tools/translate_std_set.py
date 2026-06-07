import os
import shutil
import re
import translate_game
import unicodedata

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def translate_std_set():
    resource_dir = translate_game.RESOURCE_DIR
    path = os.path.join(resource_dir, "STD.SET")
    
    if not os.path.exists(path):
        print("STD.SET not found!")
        return
        
    # Backup
    if not os.path.exists(path + ".bak"):
        shutil.copy2(path, path + ".bak")
        
    session = translate_game.TranslationSession()
    
    with open(path + ".bak", 'rb') as f:
        content = bytearray(f.read())
        
    # We will search for the tips
    # Pattern: ID (e.g. CUSTOMER 1) followed by text, followed by many spaces
    pattern = re.compile(rb'(CUSTOMER|GENERAL|CONTROL|SCENARIO|SANDBOX)\s+\d{1,2}\s*([a-zA-Z\s,."\'\-!?()]+?)( {10,})')
    
    translated_count = 0
    offset = 0
    
    while True:
        m = pattern.search(content, offset)
        if not m:
            break
            
        orig_text_bytes = m.group(2)
        trailing_spaces = m.group(3)
        
        # We only want to translate if it looks like a real sentence (contains spaces)
        orig_text = orig_text_bytes.decode('windows-1252', errors='ignore').strip()
        if len(orig_text) > 10 and ' ' in orig_text:
            translated_text = session.protect_and_translate(orig_text)
            
            # STRIP ACCENTS for STD.SET because the game uses a DOS font for these tooltips!
            translated_text = remove_accents(translated_text)
            
            translated_bytes = translated_text.encode('windows-1252', errors='replace')
            
            total_available_length = len(orig_text_bytes) + len(trailing_spaces)
            
            # Truncate if too long (leave 1 space just in case)
            if len(translated_bytes) > total_available_length - 1:
                translated_bytes = translated_bytes[:total_available_length - 1]
                
            # Pad with spaces to exact original length
            padded_translated = translated_bytes.ljust(total_available_length, b' ')
            
            # Replace in content
            start_idx = m.start(2)
            end_idx = m.end(3)
            
            content[start_idx:end_idx] = padded_translated
            translated_count += 1
            print(f"Translated tip: {orig_text[:30]}... -> {translated_text[:30]}...")
            
            # Next search starts after this block
            offset = start_idx + len(padded_translated)
        else:
            offset = m.end(2)
            
    with open(path, 'wb') as f:
        f.write(content)
        
    session.save_cache()
    print(f"Translated {translated_count} tips in STD.SET!")

if __name__ == '__main__':
    translate_std_set()
