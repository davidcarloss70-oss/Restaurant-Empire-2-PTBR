import os
import shutil
import translate_game

def translate_all_safe():
    print("=== Starting Full Translation (Safe Mode) ===")
    resource_dir = translate_game.RESOURCE_DIR
    
    # 1. Restore ALL TXR files to English from backup
    baks = [f for f in os.listdir(resource_dir) if f.endswith('.txr.bak')]
    for f in baks:
        shutil.copy2(os.path.join(resource_dir, f), os.path.join(resource_dir, f[:-4]))
    print("Restored all TXR files to English from backups.")
    
    # 2. Setup session
    session = translate_game.TranslationSession()
    
    # 3. Add credits
    translate_game.add_credits_to_game()
    
    # 4. Translate dialogues (extracted_script.res)
    translate_game.translate_dialogues(session)
    
    # 5. Files to SKIP entirely (crash regardless of content)
    skip_files = {"t_chefas.txr"}
    
    # 6. Files needing special handling
    special_files = {"t_basic.txr"}
    
    # 7. Translate normal TXR files
    txr_files = sorted([f for f in os.listdir(resource_dir) if f.endswith('.txr')])
    
    for filename in txr_files:
        if filename in skip_files:
            print(f"  SKIPPED {filename} (known crash file)")
            continue
            
        if filename in special_files:
            # Special handling for t_basic.txr: translate everything EXCEPT SELCMP descriptions
            print(f"  Special handling for {filename} (skipping SELCMP descriptions)...")
            path = os.path.join(resource_dir, filename)
            read_path = path + ".bak"
            with open(read_path, 'r', encoding='windows-1252', errors='replace') as f:
                lines = f.readlines()
                
            has_hash = False
            new_lines = []
            translated_lines = 0
            
            for line in lines:
                stripped = line.strip('\r\n')
                if stripped == '#':
                    has_hash = True
                    new_lines.append(line)
                    continue
                if has_hash and stripped and '|' in stripped:
                    parts = stripped.split('|', 3)
                    if len(parts) == 4:
                        # parts[0]=ID, parts[1]=Category, parts[2]=Subindex, parts[3]=Text
                        
                        # Check if it's the campaign description which causes Stack Buffer Overrun
                        if parts[1] == 'SELCMP' and parts[2] in ['2', '3']:
                            new_lines.append(line)
                            continue
                            
                        orig_text = parts[3]
                        parts[3] = session.protect_and_translate(orig_text)
                        new_line = '|'.join(parts) + ('\r\n' if line.endswith('\r\n') else '\n')
                        new_lines.append(new_line)
                        translated_lines += 1
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
                    
            with open(path, 'w', encoding='windows-1252', errors='replace') as f:
                f.writelines(new_lines)
            print(f"  Saved translated UI in {filename} (translated {translated_lines} data lines)")
            continue
            
        # Normal translation
        path = os.path.join(resource_dir, filename)
        read_path = path + ".bak"
        with open(read_path, 'r', encoding='windows-1252', errors='replace') as f:
            lines = f.readlines()
            
        new_lines = []
        has_hash = False
        for line in lines:
            stripped = line.strip('\r\n')
            if stripped == '#':
                has_hash = True
                new_lines.append(line)
                continue
            if has_hash and stripped and '|' in stripped:
                parts = stripped.split('|', 3)
                if len(parts) == 4:
                    orig_text = parts[3]
                    parts[3] = session.protect_and_translate(orig_text)
                    new_line = '|'.join(parts) + ('\r\n' if line.endswith('\r\n') else '\n')
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
                
        with open(path, 'w', encoding='windows-1252', errors='replace') as f:
            f.writelines(new_lines)
        print(f"  Saved translated UI in {filename}")
    
    # Ensure skipped files are definitely original English
    for skip_file in skip_files:
        path = os.path.join(resource_dir, skip_file)
        if os.path.exists(path + ".bak"):
            shutil.copy2(path + ".bak", path)
            
    print("=== Safe Translation Workflow Completed! ===")

if __name__ == '__main__':
    translate_all_safe()
