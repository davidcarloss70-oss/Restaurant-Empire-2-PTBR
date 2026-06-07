import json

path = r'translation_cache.json'
with open(path, 'r', encoding='utf-8') as f:
    cache = json.load(f)

# Correct keys based on actual cache values
cache["Quit to Main Menu"] = "Sair para o Menu"
cache["Quit to Windows"] = "Sair para Windows"
cache["OPENING HOURS:"] = "HORA ABERTURA:"
cache["CLOSING HOURS:"] = "HORA FECHAMENTO:"
cache["LAST ORDER TIME:"] = "ÚLTIMO PEDIDO:"
cache["PLAY GAME!"] = "JOGAR!"
cache["CUSTOMERS SHARING TABLES:"] = "COMPARTILHAR MESAS:"

# Remove the wrong ones we added before just to clean up (optional)
wrong_keys = ["Exit to Main Menu", "Exit to Windows", "OPENING TIME", "CLOSING TIME", "LAST ORDER TIME", "CUSTOMERS SHARING TABLES"]
for k in wrong_keys:
    if k in cache:
        del cache[k]

with open(path, 'w', encoding='utf-8') as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print("Cache updated correctly!")
