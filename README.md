# Visualizador de Planilhas do Google Sheets

Este aplicativo utiliza FastAPI para criar uma interface web que permite visualizar o conteúdo de uma planilha do Google Sheets.

## Planilha de Exemplo

O aplicativo está configurado para acessar a planilha com o ID:
`1u1do3URWqU6_E9DAKenpm9F7BfKGw7sBNrtp0yxSwzk`

As abas que serão visualizadas são:
- VISITAS (formato de data: 01/12/2023 13:44:40)
- PROSPECÇÃO (formato de data: 01/12/2023 13:44:40)
- DESPESAS (formato de data: 01/12/2023)
- QUESTIONÁRIO (formato de data: 01/12/2023 13:44:40)

## Requisitos

- Python 3.8 ou superior
- Conta Google com acesso ao Google Cloud Platform
- Acesso de leitura à planilha especificada

## Configuração

1. Clone este repositório:
```bash
git clone https://github.com/seu-usuario/visualizador-planilhas.git
cd visualizador-planilhas
```

2. Crie um ambiente virtual e instale as dependências:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Configure as credenciais do Google Cloud Platform:
   
   a. Acesse o [Console do Google Cloud](https://console.cloud.google.com/)
   
   b. Crie um novo projeto
   
   c. Ative a API do Google Sheets e a API do Google Drive
   
   d. Crie uma conta de serviço e baixe o arquivo de credenciais JSON
   
   e. Renomeie o arquivo para `credentials.json` e coloque-o na pasta raiz do projeto
   
   f. Compartilhe a planilha com o e-mail da conta de serviço (similar a: `conta-servico@projeto.iam.gserviceaccount.com`)

4. Crie a estrutura de pastas para os templates:
```bash
mkdir -p templates static
```

5. Mova os arquivos HTML para a pasta templates:
   - `base.html`
   - `index.html`
   - `sheet.html`

## Execução

Para iniciar o aplicativo, execute:

```bash
python main.py
```

Acesse o aplicativo no navegador através do endereço: http://localhost:8000

## Estrutura do Projeto

```
.
├── main.py               # Aplicativo principal do FastAPI
├── requirements.txt      # Dependências do projeto
├── credentials.json      # Credenciais do Google Cloud Platform (você precisa criar)
├── templates/            # Templates HTML
│   ├── base.html         # Template base
│   ├── index.html        # Página inicial
│   └── sheet.html        # Visualização de aba específica
└── static/               # Arquivos estáticos (CSS, JS, imagens)
```

## Funcionalidades

- Navegação entre diferentes abas da planilha
- Filtro por data inicial e final em cada aba
- Visualização do conteúdo de cada aba em formato de tabela
- Recursos de busca, ordenação e paginação nas tabelas (via DataTables)
- Interface responsiva e moderna com ícones (via Bootstrap e Font Awesome)
- Tratamento de diferentes formatos de data dependendo da aba

## Personalização

Para alterar a planilha ou as abas a serem visualizadas, modifique as constantes `SPREADSHEET_ID` e `SHEET_NAMES` no arquivo `main.py`.

## Licença

Este projeto está licenciado sob a licença MIT.