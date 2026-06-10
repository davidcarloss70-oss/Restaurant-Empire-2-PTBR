import os
import shutil
import translate_game

def translate_tutorials():
    print("=== Translating Tutorials ===")
    tutorial_dir = os.path.join(translate_game.GAME_DIR, "tutorial")
    if not os.path.exists(tutorial_dir):
        print(f"Tutorial folder not found: {tutorial_dir}")
        return
        
    # Setup session
    session = translate_game.TranslationSession()
    
    translated_count = 0
    
    for f in sorted(os.listdir(tutorial_dir)):
        if not f.endswith('.res'):
            continue
            
        path = os.path.join(tutorial_dir, f)
        
        # Backup if not exists
        if not os.path.exists(path + ".bak"):
            shutil.copy2(path, path + ".bak")
            
        # Read from backup
        with open(path + ".bak", 'r', encoding='windows-1252', errors='replace') as file:
            content = file.read()
            
        # The files use \r\n, split by lines
        is_crlf = '\r\n' in content
        lines = content.replace('\r\n', '\n').split('\n')
        
        new_lines = []
        in_message = False
        message_buffer = []
        
        def translate_buffer():
            if not message_buffer:
                return []
            
            # Combine, translate paragraphs, and return
            # Wait, each line in message_buffer could be a paragraph or empty line.
            translated = []
            for mline in message_buffer:
                mline_stripped = mline.strip()
                if not mline_stripped:
                    translated.append(mline)
                else:
                    # check if starts with [MESSAGE]
                    prefix = ""
                    text_to_translate = mline
                    if mline.startswith("[MESSAGE]"):
                        prefix = "[MESSAGE]"
                        text_to_translate = mline[9:]
                        
                    if text_to_translate.strip():
                        # The text may contain underscores for italics, protect them maybe?
                        # Let's just pass to translator
                        t_text = session.protect_and_translate(text_to_translate)
                        translated.append(prefix + t_text)
                    else:
                        translated.append(mline)
            return translated
        
        for line in lines:
            if line.startswith('[') and not line.startswith('[MESSAGE]'):
                if in_message:
                    # Flush message buffer
                    new_lines.extend(translate_buffer())
                    message_buffer = []
                    in_message = False
                new_lines.append(line)
            elif line.startswith('[MESSAGE]'):
                if in_message:
                    # Flush previous if any
                    new_lines.extend(translate_buffer())
                    message_buffer = []
                in_message = True
                message_buffer.append(line)
            else:
                if in_message:
                    message_buffer.append(line)
                else:
                    new_lines.append(line)
                    
        if in_message:
            new_lines.extend(translate_buffer())
            
        join_str = '\r\n' if is_crlf else '\n'
        new_content = join_str.join(new_lines)
        
        with open(path, 'w', encoding='windows-1252', errors='replace') as file:
            file.write(new_content)
            
        print(f"Translated tutorial {f}")
        translated_count += 1
        
    session.save_cache()
    print(f"Successfully translated {translated_count} tutorial files!")

if __name__ == '__main__':
    translate_tutorials()
