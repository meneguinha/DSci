# DSci - Buscador, Downloader & Analisador de Artigos Científicos

O **DSci** é uma ferramenta de código aberto projetada para otimizar o fluxo de pesquisa acadêmica. Ele automatiza as etapas de busca por artigos em bases de dados abertas, download dos arquivos PDF correspondentes e análise inteligente do conteúdo usando Inteligência Artificial (LLMs).

A aplicação conta com uma interface gráfica moderna e responsiva desenvolvida em Python com a biblioteca **CustomTkinter**.

---

## 🚀 Como Usar (Sem instalar nada!)

Se você deseja apenas utilizar a aplicação, **não é necessário instalar o Python ou usar o terminal**:

1. Acesse a aba **Releases** do repositório no GitHub.
2. Baixe a versão correspondente ao seu sistema operacional:
   - **Windows**: Baixe o arquivo `DSci-Windows.exe`.
   - **Linux**: Baixe o arquivo `DSci-Linux`.
3. Dê dois cliques no arquivo baixado e comece a usar!

*Nota: Na primeira execução, a aplicação criará automaticamente uma pasta chamada `downloads` no mesmo diretório do executável para organizar os artigos baixados.*

---

## 🛠️ Funcionalidades Principais

*   **Busca Acadêmica Unificada**: Consulta simultaneamente as APIs do **OpenAlex** e **Crossref** por palavras-chave.
*   **Filtros de Open Access e Idioma**: Garante que os artigos retornados sejam de livre acesso e tenham links diretos para download do PDF. Permite filtrar resultados por Português ou Inglês.
*   **Downloader Automatizado**: Baixa múltiplos artigos selecionados de forma paralela com sistema inteligente de resolução de conflitos (sobrescrever, renomear ou pular arquivos existentes).
*   **Análise por Inteligência Artificial (LLM)**:
    *   Extração automática de texto diretamente do PDF baixado.
    *   Integração com qualquer API compatível com OpenAI (incluindo OpenAI local, Groq, OpenRouter, Anthropic, etc.).
    *   Processamento em lote com prompts personalizáveis (ex: resumir artigos, extrair metodologias, responder perguntas específicas).
    *   Cache local do texto extraído para permitir re-análises rápidas sem novo download ou nova extração.
*   **Exportação**: Copie a resposta da IA para a área de transferência ou salve o resultado em arquivos `.txt` ou `.md`.

---

## ⚙️ Configuração da IA

Para utilizar a análise com IA, acesse a aba **Configurações da API** na barra lateral da aplicação e preencha:
1.  **URL Base da API**: URL da API que deseja usar (padrão: `https://api.openai.com/v1`).
2.  **Chave de API**: Sua API Key pessoal da plataforma de LLM.
3.  **Nome do Modelo**: O modelo que deseja utilizar (ex: `gpt-4o-mini`, `llama3-8b-8192`, etc.).

Clique em **Salvar Configurações** para armazenar esses dados localmente com segurança no arquivo `config.json`.

---

## 💻 Desenvolvimento (Rodando a partir do código-fonte)

Caso queira modificar o código ou rodar em modo de desenvolvimento, você precisará do Python instalado em sua máquina.

### Pré-requisitos
*   Python 3.10 ou superior

### Passos para Instalação
1.  Clone este repositório:
    ```bash
    git clone https://github.com/seu-usuario/seu-repositorio.git
    cd seu-repositorio
    ```
2.  Instale as dependências necessárias:
    ```bash
    pip install -r requirements.txt
    ```
3.  Execute a aplicação:
    ```bash
    python main.py
    ```

---

## 📦 Como Compilar Manualmente (PyInstaller)

Caso queira gerar os binários executáveis em sua própria máquina, instale o `pyinstaller` e execute:

*   **No Windows**:
    ```powershell
    python -m PyInstaller --noconsole --onefile --collect-all customtkinter --add-data "papertools_theme.json;." main.py
    ```
*   **No Linux**:
    ```bash
    python -m PyInstaller --noconsole --onefile --collect-all customtkinter --add-data "papertools_theme.json:." main.py
    ```

Os executáveis gerados estarão disponíveis na pasta `dist/`.

---

## 🧪 Tecnologias Utilizadas

*   **Linguagem**: Python 3
*   **Interface Gráfica**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (UI moderna baseada em Tkinter)
*   **Consumo de APIs**: [Requests](https://requests.readthedocs.io/)
*   **Extração de Texto**: [PyPDF](https://pypi.org/project/pypdf/)
*   **Empacotamento**: [PyInstaller](https://pyinstaller.org/)
*   **Automação**: GitHub Actions (para build multiplataforma automático)
