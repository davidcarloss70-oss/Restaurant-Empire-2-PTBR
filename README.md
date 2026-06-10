# Restaurant Empire 2 - Tradução para Português do Brasil (PT-BR)

Bem-vindo ao repositório oficial da tradução completa para Português do Brasil do clássico **Restaurant Empire 2** (versão Steam). 

🎮 **[Confira o Guia Oficial da Tradução na Steam clicando aqui!](https://steamcommunity.com/sharedfiles/filedetails/?id=3740389404)**

Este repositório contém tanto os **arquivos prontos para instalar (Patch)** quanto as **ferramentas de engenharia reversa (Tools)** desenvolvidas para tornar essa tradução possível, caso a comunidade queira aprimorar ou traduzir para outros idiomas.

---

## 🎮 Como Instalar a Tradução (Para Jogadores)

Se você quer apenas jogar o jogo em Português, siga estes passos simples:

1. Baixe o arquivo **`RE2_PTBR_Patch.zip`** deste repositório.
2. Na sua biblioteca da Steam, clique com o botão direito no **Restaurant Empire 2** → **Gerenciar** → **Explorar arquivos locais**. Isso abrirá a pasta raiz do jogo.
3. **Extraia o conteúdo do ZIP** diretamente na pasta raiz do jogo, **substituindo** os arquivos quando solicitado.
   - O ZIP contém **apenas os arquivos que foram realmente traduzidos**, organizados nas subpastas corretas:
     - `resource/` → Menus, interface, dicas e créditos (`.txr`, `STD.SET`, `credits.res`, `help.res`)
     - `tutorial/` → Textos dos 12 tutoriais interativos (`tut01.res` a `tut12.res`)
     - `script/extracted/` → Diálogos completos da campanha (`extracted_script.res`)
   - *Nota: Os arquivos `.bak` são backups originais em inglês para que você possa reverter, se necessário.*
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

Se o jogo for atualizado ou se você quiser modificar as traduções manualmente, você tem duas opções na pasta `Tools/`:

#### Opção 1: Aplicativo Visual Gráfico e Editor Offline (Recomendado)
Desenvolvemos uma interface gráfica nativa para aplicar e até editar as traduções livremente!
1. Se você já tem o executável `RE2_Tradutor_UI.exe` na pasta `Tools/`, basta abri-lo!
2. Pelo aplicativo, você pode pesquisar por palavras, editar a tradução desejada no **Cache de Tradução** e clicar em "Salvar".
3. Com 1 clique no botão **Aplicar Edições no Jogo**, o programa executa todos os scripts pesados e atualiza o jogo na hora.
   - **Nota (v1.0):** O aplicativo agora é **100% offline**, rodando os scripts diretamente pelo cache local (`translation_cache.json`) sem bater em nenhuma API do Google, o que garante que a aplicação das edições leve apenas 1 a 2 segundos em vez de horas! Ele também possui sistema de Backup para restauração.

*(Se você não tiver o `.exe`, pode gerá-lo rodando `python build_exe.py` ou `uv run build_exe.py`)*

#### Opção 2: Linha de Comando (Modo Antigo/Avançado)

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
