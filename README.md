# Sistema Intranet REMAPE

Este aplicativo utiliza FastAPI para criar uma interface web que permite visualizar o conteúdo de planilhas do Google Sheets com dados de visitas, prospecções, despesas, questionários e vendas da empresa REMAPE.

## Funcionalidades

- Sistema de login com autenticação por JWT
- Navegação entre diferentes abas das planilhas
- Filtro por data inicial e final em cada aba
- Visualização do conteúdo de cada aba em formato de tabela
- Cards com resumos e estatísticas dos dados
- Gráficos para análise visual das vendas
- Filtragem automática de dados por vendedor baseado no login
- Recursos de busca, ordenação e paginação nas tabelas (via DataTables)
- Interface responsiva e moderna com ícones (via Bootstrap e Font Awesome)

## Planilhas Conectadas

O aplicativo está configurado para acessar duas planilhas do Google Sheets:

1. Planilha Principal (`MAIN_SPREADSHEET_ID`):
   - VISITAS (formato de data: 01/12/2023 13:44:40)
   - PROSPECÇÃO (formato de data: 01/12/2023 13:44:40)
   - DESPESAS (formato de data: 01/12/2023)
   - QUESTIONÁRIO (formato de data: 01/12/2023 13:44:40)

2. Planilha de Vendas (`VENDAS_SPREADSHEET_ID`):
   - Vendas (formato de data: 19/12/2024 ou 07/08/23)

## Requisitos

- Python 3.8 ou superior
- Conta Google com acesso ao Google Cloud Platform
- Acesso de leitura às planilhas especificadas

## Configuração Local

1. Clone este repositório:
```bash
git clone https://github.com/seu-usuario/intranet-remape.git
cd intranet-remape
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

4. Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
```
# Google Sheet IDs
MAIN_SPREADSHEET_ID=seu-id-da-planilha-principal
VENDAS_SPREADSHEET_ID=seu-id-da-planilha-de-vendas

# JWT Secret Key
SECRET_KEY=sua-chave-secreta-para-jwt

# Usuários (email,nome,senha)
USER_RAFAEL=rafael@remape.com,Rafael,sua-senha
USER_DEISE=vendasremape@gmail.com,Deise,sua-senha
USER_SANDRO=promocaoremape@gmail.com,Sandro,sua-senha
USER_LEIDE=promocaoremape2@gmail.com,Leide,sua-senha
```

## Execução Local

Para iniciar o aplicativo, execute:

```bash
python main.py
```

Acesse o aplicativo no navegador através do endereço: http://localhost:8000

## Docker

Este projeto inclui um Dockerfile para facilitar a implantação em contêineres.

### Construindo a imagem Docker

```bash
docker build -t intranet-remape .
```

### Executando em Docker

```bash
docker run -p 8080:8080 --env-file .env -v $(pwd)/credentials.json:/app/credentials.json intranet-remape
```

## Deploy no Google Cloud Run

Para instruções detalhadas sobre como implantar no Google Cloud Run, consulte o arquivo [DEPLOY.md](DEPLOY.md).

## Estrutura do Projeto

```
.
├── main.py               # Aplicativo principal do FastAPI
├── requirements.txt      # Dependências do projeto
├── credentials.json      # Credenciais do Google Cloud Platform (você precisa criar)
├── .env                  # Arquivo de variáveis de ambiente (você precisa criar)
├── Dockerfile            # Configuração para construir a imagem Docker
├── .dockerignore         # Arquivos a serem ignorados pelo Docker
├── DEPLOY.md             # Instruções para deploy no Google Cloud Run
├── templates/            # Templates HTML
│   ├── base.html         # Template base com navegação
│   ├── index.html        # Página inicial
│   ├── sheet.html        # Visualização de aba específica
│   └── login.html        # Página de login
└── static/               # Arquivos estáticos (CSS, JS, imagens)
    └── MARCA REMAPE.jpg  # Logo da empresa
```

## Permissões de Usuário

- **rafael@remape.com (Rafael)**: Acesso a todos os dados em todas as abas
- **Outros usuários**: Acesso apenas aos seus próprios dados:
  - Nas abas VISITAS, PROSPECÇÃO, DESPESAS e QUESTIONÁRIO: filtrado pelo email na coluna VENDEDOR
  - Na aba VENDAS: filtrado pelo nome do usuário na coluna VENDEDOR

## Licença

Este projeto está licenciado sob a licença MIT.