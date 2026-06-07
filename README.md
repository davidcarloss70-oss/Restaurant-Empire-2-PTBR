# Restaurant Empire 2 - Tradução para Português do Brasil (PT-BR)

Bem-vindo ao repositório oficial da tradução completa para Português do Brasil do clássico **Restaurant Empire 2** (versão Steam). 

Este repositório contém tanto os **arquivos prontos para instalar (Patch)** quanto as **ferramentas de engenharia reversa (Tools)** desenvolvidas para tornar essa tradução possível, caso a comunidade queira aprimorar ou traduzir para outros idiomas.

---

## 🎮 Como Instalar a Tradução (Para Jogadores)

Se você quer apenas jogar o jogo em Português, siga estes passos simples:

1. Baixe o conteúdo da pasta `Patch/` deste repositório.
2. Navegue até a pasta de instalação do jogo na Steam:
   - Geralmente fica em: `C:\Program Files (x86)\Steam\steamapps\common\Restaurant Empire 2\resource`
3. Copie todos os arquivos da pasta `Patch/` e cole na pasta `resource` do jogo, **substituindo** os arquivos originais quando solicitado.
   - *Nota: Os arquivos terminados em `.bak` que estão na pasta do patch são backups originais em inglês. Eles garantem que você possa reverter as alterações, se necessário, e também são usados pelos scripts para re-traduzir.*
4. Abra o jogo e divirta-se!

---

## 🛠️ Ferramentas e Como Foi Feito (Para Modders e Desenvolvedores)

Traduzir Restaurant Empire 2 foi um grande desafio de engenharia reversa devido à idade da engine do jogo e formatos obscuros. Tudo foi automatizado com Python na pasta `Tools/`.

### Desafios Encontrados e Soluções:
1. **Crashs de Buffer (Tamanho de Texto):** A interface do jogo original dava *Stack Buffer Overrun* (crash para o desktop) se textos muito grandes fossem exibidos em certos painéis.
   - *Solução:* O script ignora blocos críticos e textos muito longos na tela de seleção de campanha (`t_basic.txr`) mantendo-os em inglês. Além disso, termos muito longos foram encurtados com manipulação manual no cache (ex: *AVERAGE RESTAURANT RATING* virou *CLASS. MÉDIA*).
2. **Textos Binários e Tutoriais:** Os textos não estavam em simples blocos de notas. Eles estavam em estruturas `.txr`, em diálogos `.res` (separados por `~`), e as dicas de tela e sandbox estavam no obscuro arquivo `STD.SET`.
   - *Solução:* Foram criados scripts extratores específicos para a estrutura TXR e para injeção binária precisa (`translate_std_set.py`).
3. **Encoding de Fonte MS-DOS:** A engine de dicas do painel do `STD.SET` não suporta acentuação padrão Windows (UTF-8/Windows-1252), renderizando letras acentuadas como caracteres especiais (ex: `Ò` e `Û`).
   - *Solução:* O tradutor de `.SET` passa o texto em PT-BR por um removedor de acentos (`unicodedata`), permitindo que a dica seja renderizada corretamente sem corrupção gráfica.
4. **Nomes Protegidos:** O motor principal não conseguiria ligar as missões aos diálogos se traduzíssemos o nome do tio *Michel*, da esposa *Delia*, etc.
   - *Solução:* O `translate_game.py` substitui os nomes-chave por tokens tipo `{W1}` antes de jogar no tradutor online, devolvendo o nome original na frase traduzida.

### Como usar as Ferramentas

Se o jogo for atualizado ou se você quiser modificar as traduções manualmente, você pode rodar as ferramentas Python localizadas em `Tools/`.

**Pré-requisitos:**
- Ter o Python instalado.
- Instalar as dependências do `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```

**Fluxo de Execução:**
Dentro da pasta `Tools`, com o console apontado para lá e a variável de caminho do jogo configurada (dentro do código fonte):

```bash
# 1. Traduz todos os menus da interface e diálogos da campanha:
python translate_all_safe.py

# 2. Traduz as dicas e o conteúdo interativo da caixa de dicas (injeta direto no binário):
python translate_std_set.py

# 3. Traduz todos os diálogos de Tutorial dos 12 mapas iniciais:
python translate_tutorials.py
```

*Os scripts leem o `translation_cache.json` para não traduzirem de novo na internet o que já está salvo. Para corrigir um erro de tradução, você pode editar diretamente o arquivo `.json` ou utilizar o script de injeção direta `patch_cache2.py` e rodar os executores novamente.*

## 🏆 Créditos
Projeto de tradução, scripts e engenharia reversa criados por **davidcarloss** com auxílio de agentes de inteligência artificial. Divirta-se e bom apetite!
