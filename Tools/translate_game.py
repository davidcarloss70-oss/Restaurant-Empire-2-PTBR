import os
import re
import json
import shutil
import time
from deep_translator import GoogleTranslator

# Tenta carregar o caminho do jogo do app_config.json
app_config_path = "app_config.json"
GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\Restaurant Empire 2"
if os.path.exists(app_config_path):
    try:
        with open(app_config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            if cfg.get("game_path"):
                GAME_DIR = cfg["game_path"]
    except Exception as e:
        print(f"Aviso: Não foi possível ler app_config.json: {e}")

RESOURCE_DIR = os.path.join(GAME_DIR, "resource")
SCRIPT_EXTRACTED_DIR = os.path.join(GAME_DIR, "script", "extracted")

CACHE_FILE = "translation_cache.json"

# Override dictionary for months, days, and time units
OVERRIDE_DICT = {
    # Months
    "January": "Janeiro",
    "February": "Fevereiro",
    "March": "Março",
    "April": "Abril",
    "May": "Maio",
    "June": "Junho",
    "July": "Julho",
    "August": "Agosto",
    "September": "Setembro",
    "October": "Outubro",
    "November": "Novembro",
    "December": "Dezembro",
    "Jan": "Jan",
    "Feb": "Fev",
    "Mar": "Mar",
    "Apr": "Abr",
    "Jun": "Jun",
    "Jul": "Jul",
    "Aug": "Ago",
    "Sep": "Set",
    "Oct": "Out",
    "Nov": "Nov",
    "Dec": "Dez",
    
    # Days
    "Monday": "Segunda-feira",
    "Tuesday": "Terça-feira",
    "Wednesday": "Quarta-feira",
    "Thursday": "Quinta-feira",
    "Friday": "Sexta-feira",
    "Saturday": "Sábado",
    "Sunday": "Domingo",
    "Mon": "Seg",
    "Tue": "Ter",
    "Wed": "Qua",
    "Thur": "Qui",
    "Fri": "Sex",
    "Sat": "Sáb",
    "Sun": "Dom",
    
    # Time units
    "second": "segundo",
    "seconds": "segundos",
    "minute": "minuto",
    "minutes": "minutos",
    "hour": "hora",
    "hours": "horas",
    "day": "dia",
    "days": "dias",
    "month": "mês",
    "months": "meses",
    "year": "ano",
    "years": "anos",
    "sec": "seg",
    "secs": "seg",
    "min": "min",
    "mins": "min",
    "hr": "h",
    "hrs": "h",
    "yr": "ano",
    "yrs": "anos",
    "mth": "mês",
    "mths": "meses",
    
    # Common UI terms
    "AM": "AM",
    "PM": "PM",
    "New Player": "Novo Jogador"
}

# Protected words that must not be translated
PROTECTED_WORDS = [
    # Proper names
    "Armand", "Delia", "Michel", "Gordini", "Don", "Trevor Chan", "Trevor", "Chan", "Albert",
    "Armand's", "Delia's", "Michel's", "Gordini's",
    # Cities
    "Paris", "Rome", "Munich", "London", "New York", "Los Angeles",
    # French dishes & characteristic foods (do not translate)
    "Croissant", "Croissants", "Escargot", "Escargots", "Coq au vin", "Foie gras", "Ratatouille",
    "Bouillabaisse", "Quiche", "Quiches", "Crêpe", "Crêpes", "Crème brûlée", "Mousse", "Soufflé", "Soufflés",
    # Italian characteristic foods
    "Pizza", "Pizzas", "Pasta", "Spaghetti", "Lasagna", "Lasagnas", "Risotto", "Tiramisu",
    # German characteristic foods
    "Sauerkraut", "Bratwurst", "Pretzel", "Pretzels", "Schnitzel", "Strudel",
    # Credits
    "davidcarloss"
]

class TranslationSession:
    def __init__(self):
        self.translator = GoogleTranslator(source='en', target='pt')
        self.cache = {}
        self.load_cache()
        
    def load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                print(f"Loaded {len(self.cache)} cached translations.")
            except Exception as e:
                print(f"Error loading cache: {e}")
                self.cache = {}
                
    def save_cache(self):
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving cache: {e}")
            
    def translate_clean_text(self, text):
        # Fallback single string lookup/translation if needed
        if text in self.cache:
            val = self.cache[text]
            return val if isinstance(val, str) else text
        if text.strip() in OVERRIDE_DICT:
            return OVERRIDE_DICT[text.strip()]
        
        # Modo Offline: se não está no cache, manter o original (em inglês)
        # Isso evita que a aplicação demore horas tentando traduzir textos pela internet
        return text

    def batch_translate(self, unique_texts):
        # Filters out texts already in cache or override dict
        to_translate = []
        for text in unique_texts:
            if text in self.cache:
                continue
            if text.strip() in OVERRIDE_DICT:
                continue
            # Check if it's placeholder-only
            stripped = text.strip()
            is_placeholder_only = True
            for char in stripped:
                if char not in "{}0123456789VFCW ,.:;!?-_/\\":
                    is_placeholder_only = False
                    break
            if is_placeholder_only:
                continue
            to_translate.append(text)
            
        if not to_translate:
            print("No new unique texts to translate.")
            return
            
        total = len(to_translate)
        print(f"Starting batch translation of {total} new unique texts...")
        
        batch_size = 50
        for i in range(0, total, batch_size):
            batch = to_translate[i:i+batch_size]
            print(f"  Translating batch {i//batch_size + 1}/{(total-1)//batch_size + 1} ({len(batch)} items)...")
            try:
                translated_batch = self.translator.translate_batch(batch)
                for orig, trans in zip(batch, translated_batch):
                    self.cache[orig] = trans
                self.save_cache()
                time.sleep(0.5) # Anti-block delay
            except Exception as e:
                print(f"Error in batch: {e}")
                # Fallback to single translations in this batch
                for text in batch:
                    try:
                        self.cache[text] = self.translator.translate(text)
                        time.sleep(0.1)
                    except:
                        pass
                self.save_cache()

    def protect_and_translate(self, text):
        if not text or text.strip() == "":
            return text
            
        # 1. Protect variable braces like {award_name} (no pipes inside)
        braces_vars = re.findall(r'\{([^|{}]+)\}', text)
        braces_placeholders = {}
        for i, var in enumerate(braces_vars):
            ph = f"{{V{i}}}"
            braces_placeholders[ph] = f"{{{var}}}"
            text = text.replace(f"{{{var}}}", ph)
            
        # 2. Protect formatting codes like %1d, %3,4d, %s
        fmt_codes = re.findall(r'%[0-9]*(?:,[0-9]*)?[a-zA-Z]', text)
        fmt_placeholders = {}
        for i, code in enumerate(fmt_codes):
            ph = f"{{F{i}}}"
            fmt_placeholders[ph] = code
            text = text.replace(code, ph)
            
        # 3. Handle choice lists like {second|seconds}
        choices_blocks = re.findall(r'(\{[^{}]*\|[^{}]*\})', text)
        choices_placeholders = {}
        for i, block in enumerate(choices_blocks):
            ph = f"{{C{i}}}"
            items = block[1:-1].split('|')
            translated_items = []
            for item in items:
                if item.strip() == "":
                    translated_items.append("")
                elif item.strip() in OVERRIDE_DICT:
                    translated_items.append(OVERRIDE_DICT[item.strip()])
                else:
                    translated_items.append(self.translate_clean_text(item))
            translated_block = "{" + "|".join(translated_items) + "}"
            choices_placeholders[ph] = translated_block
            text = text.replace(block, ph)
            
        # 4. Protect words that must remain original
        word_placeholders = {}
        for i, word in enumerate(PROTECTED_WORDS):
            ph = f"{{W{i}}}"
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, text):
                word_placeholders[ph] = word
                text = re.sub(pattern, ph, text)
                
        # 5. Get translation from cache
        # The cache keys use {V}, {F}, {C}, {W} without numbers!
        cache_key = text
        cache_key = re.sub(r'\{V\d+\}', '{V}', cache_key)
        cache_key = re.sub(r'\{F\d+\}', '{F}', cache_key)
        cache_key = re.sub(r'\{C\d+\}', '{C}', cache_key)
        cache_key = re.sub(r'\{W\d+\}', '{W}', cache_key)
        
        translated_text = self.translate_clean_text(cache_key)
        
        if isinstance(translated_text, str) and translated_text != cache_key:
            # We found it in the cache! But it has {V}, {F}, etc.
            # We must restore the numbers so step 6 can replace them back!
            v_count = 0
            while "{V}" in translated_text:
                translated_text = translated_text.replace("{V}", f"{{V{v_count}}}", 1)
                v_count += 1
            f_count = 0
            while "{F}" in translated_text:
                translated_text = translated_text.replace("{F}", f"{{F{f_count}}}", 1)
                f_count += 1
            c_count = 0
            while "{C}" in translated_text:
                translated_text = translated_text.replace("{C}", f"{{C{c_count}}}", 1)
                c_count += 1
            w_count = 0
            while "{W}" in translated_text:
                translated_text = translated_text.replace("{W}", f"{{W{w_count}}}", 1)
                w_count += 1
        else:
            translated_text = text
            
        # 6. Restore placeholders
        for ph, word in word_placeholders.items():
            translated_text = translated_text.replace(ph, word)
        for ph, block in choices_placeholders.items():
            translated_text = translated_text.replace(ph, block)
        for ph, code in fmt_placeholders.items():
            translated_text = translated_text.replace(ph, code)
        for ph, var in braces_placeholders.items():
            translated_text = translated_text.replace(ph, var)
            
        return translated_text

def backup_file(path):
    backup_path = path + ".bak"
    if not os.path.exists(backup_path):
        shutil.copy2(path, backup_path)
        print(f"Backed up {os.path.basename(path)} to {os.path.basename(backup_path)}")

def collect_dialogue_texts(script_res):
    if not os.path.exists(script_res):
        return []
    with open(script_res, 'r', encoding='windows-1252', errors='replace') as f:
        content = f.read()
    normalized_content = content.replace("\r\n", "\n")
    blocks = normalized_content.split("~\n")
    texts = []
    for block in blocks:
        if not block.strip():
            continue
        lines = block.split("\n")
        if len(lines) >= 3:
            texts.append(lines[1])
    return texts

def collect_txr_texts():
    txr_files = [f for f in os.listdir(RESOURCE_DIR) if f.endswith('.txr')]
    texts = []
    for filename in txr_files:
        path = os.path.join(RESOURCE_DIR, filename)
        # Read from backup if it exists to get original English strings
        read_path = path + ".bak" if os.path.exists(path + ".bak") else path
        with open(read_path, 'r', encoding='windows-1252', errors='replace') as f:
            lines = f.readlines()
        has_hash = False
        for line in lines:
            stripped = line.strip('\r\n')
            if stripped == '#':
                has_hash = True
                continue
            if has_hash and stripped and '|' in stripped:
                parts = stripped.split('|', 3)
                if len(parts) == 4:
                    texts.append(parts[3])
    return texts

def pre_process_and_extract_unique_clean(texts):
    # This prepares the exact strings that Google Translate needs to work on
    # i.e., after removing variables, formatting, choice lists, and protected words
    unique_clean = set()
    for text in texts:
        if not text or text.strip() == "":
            continue
            
        # Braces
        braces_vars = re.findall(r'\{([^|{}]+)\}', text)
        for var in braces_vars:
            text = text.replace(f"{{{var}}}", f"{{V}}")
            
        # Formatting codes
        fmt_codes = re.findall(r'%[0-9]*(?:,[0-9]*)?[a-zA-Z]', text)
        for code in fmt_codes:
            text = text.replace(code, f"{{F}}")
            
        # Choice blocks (their items are translated separately, so add them directly to unique_clean)
        choices_blocks = re.findall(r'(\{[^{}]*\|[^{}]*\})', text)
        for block in choices_blocks:
            items = block[1:-1].split('|')
            for item in items:
                if item.strip() and item.strip() not in OVERRIDE_DICT:
                    unique_clean.add(item)
            text = text.replace(block, f"{{C}}")
            
        # Protected words
        for word in PROTECTED_WORDS:
            pattern = r'\b' + re.escape(word) + r'\b'
            text = re.sub(pattern, f"{{W}}", text)
            
        # Check if the final text is placeholder only
        stripped = text.strip()
        is_placeholder_only = True
        for char in stripped:
            if char not in "{}0123456789VFCW ,.:;!?-_/\\":
                is_placeholder_only = False
                break
                
        if not is_placeholder_only:
            unique_clean.add(text)
            
    return sorted(list(unique_clean))

def translate_dialogues(session):
    script_res = os.path.join(SCRIPT_EXTRACTED_DIR, "extracted_script.res")
    if not os.path.exists(script_res):
        return
    backup_file(script_res)
    
    # Read from backup to get original English strings
    read_path = script_res + ".bak" if os.path.exists(script_res + ".bak") else script_res
    with open(read_path, 'r', encoding='windows-1252', errors='replace') as f:
        content = f.read()
    is_crlf = "\r\n" in content
    normalized_content = content.replace("\r\n", "\n")
    blocks = normalized_content.split("~\n")
    
    new_blocks = []
    for block in blocks:
        if not block.strip():
            new_blocks.append(block)
            continue
        lines = block.split("\n")
        if len(lines) >= 3:
            eng_text = lines[1]
            lines[2] = session.protect_and_translate(eng_text)
            new_blocks.append("\n".join(lines))
        else:
            new_blocks.append(block)
            
    join_str = "~\r\n" if is_crlf else "~\n"
    new_content = join_str.join(new_blocks)
    if is_crlf:
        new_content = new_content.replace("\n", "\r\n").replace("\r\r\n", "\r\n")
        
    with open(script_res, 'w', encoding='windows-1252', errors='replace') as f:
        f.write(new_content)
    print("Saved translated dialogues.")

def translate_txr_files(session):
    txr_files = [f for f in os.listdir(RESOURCE_DIR) if f.endswith('.txr')]
    txr_files.sort()
    
    for filename in txr_files:
        path = os.path.join(RESOURCE_DIR, filename)
        backup_file(path)
        
        # Read from backup to get original English strings
        read_path = path + ".bak" if os.path.exists(path + ".bak") else path
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

def add_credits_to_game():
    credits_path = os.path.join(RESOURCE_DIR, "credits.res")
    if not os.path.exists(credits_path):
        return
    backup_file(credits_path)
    
    # Read from backup to get original credits
    read_path = credits_path + ".bak" if os.path.exists(credits_path + ".bak") else credits_path
    with open(read_path, 'r', encoding='windows-1252', errors='replace') as f:
        content = f.read()
    
    if "davidcarloss" in content:
        # Check if the target file already has it, if so we are good
        with open(credits_path, 'r', encoding='windows-1252', errors='replace') as f_check:
            if "davidcarloss" in f_check.read():
                print("Credits for davidcarloss already present in credits.res.")
                return

    is_crlf = "\r\n" in content
    normalized = content.replace("\r\n", "\n")
    
    target_block = (
        "\tscroller_text:He Xinqing\n"
        "\tscroller_text_offset:0\n\n"
        "\tdelay_time:10000\n"
        "}"
    )
    
    replacement_block = (
        "\tscroller_text:He Xinqing\n"
        "\tscroller_text:<empty_line>\n"
        "\tscroller_text:PT Translation\n"
        "\tscroller_text:davidcarloss\n"
        "\tscroller_text_offset:0\n\n"
        "\tdelay_time:10000\n"
        "}"
    )
    
    if target_block in normalized:
        new_content = normalized.replace(target_block, replacement_block, 1)
        if is_crlf:
            new_content = new_content.replace("\n", "\r\n").replace("\r\r\n", "\r\n")
        with open(credits_path, 'w', encoding='windows-1252') as f:
            f.write(new_content)
        print("Successfully added credits for davidcarloss inside credits.res!")
    else:
        print("Warning: Could not find target credits block. Appending to end instead.")
        # Fallback append
        linebreak = "\r\n" if is_crlf else "\n"
        credits_block = (
            f"{linebreak}StageInfo"
            f"{linebreak}{{"
            f"{linebreak}\ttop_image:Frame"
            f"{linebreak}\tbot_image:BG1"
            f"{linebreak}\timage_text1:Traducao para Portugues"
            f"{linebreak}\timage_text2:davidcarloss"
            f"{linebreak}\timage_offset:0"
            f"{linebreak}\tmodel_name:Chef-015"
            f"{linebreak}\tanim_code:SandBox2"
            f"{linebreak}\taction_name:Chef_Walk2"
            f"{linebreak}\tcamera_z:72"
            f"{linebreak}"
            f"{linebreak}\tdelay_time:10000"
            f"{linebreak}}}"
        )
        with open(credits_path, 'a', encoding='windows-1252', errors='replace') as f:
            f.write(credits_block)
        print("Appended credits to end of credits.res.")

def main():
    print("=== Starting Restaurant Empire 2 Translation Workflow ===")
    session = TranslationSession()
    
    # Phase 1: Collect all text
    print("Collecting texts...")
    dialogue_texts = collect_dialogue_texts(os.path.join(SCRIPT_EXTRACTED_DIR, "extracted_script.res"))
    ui_texts = collect_txr_texts()
    all_texts = dialogue_texts + ui_texts
    print(f"Collected {len(all_texts)} total text occurrences.")
    
    # Phase 2: Pre-process and find unique strings to translate
    print("Pre-processing and identifying unique clean strings...")
    unique_clean = pre_process_and_extract_unique_clean(all_texts)
    print(f"Found {len(unique_clean)} unique clean strings for translation.")
    
    # Phase 3: Perform batch translation
    session.batch_translate(unique_clean)
    
    # Phase 4: Replace & write translations back
    print("Writing translations back to files...")
    add_credits_to_game()
    translate_txr_files(session)
    translate_dialogues(session)
    
    print("=== Translation Workflow Completed Successfully! ===")

if __name__ == '__main__':
    main()
