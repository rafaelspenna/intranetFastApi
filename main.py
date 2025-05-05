# main.py - versão simplificada para Cloud Run
from fastapi import FastAPI, Request, HTTPException, Depends, Form, status, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys
import json
import yaml
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Função para ler o arquivo env.yaml
def load_yaml_config(file_path='env.yaml'):
    """Carrega configurações de um arquivo YAML"""
    config = {}
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                yaml_data = yaml.safe_load(file)
                if yaml_data and isinstance(yaml_data, dict):
                    config = yaml_data
                    print(f"Configuração carregada do arquivo {file_path}")
                else:
                    print(f"Formato inválido no arquivo {file_path}")
        else:
            print(f"Arquivo {file_path} não encontrado")
    except Exception as e:
        print(f"Erro ao carregar arquivo {file_path}: {e}")
    return config

# Tentar carregar configurações do arquivo YAML
config = load_yaml_config()

# Configuração de segurança
SECRET_KEY = os.getenv("SECRET_KEY", "a30e2cc67c8b5cfcc2ab1fc0d8da5ad50e1ec8a84f0a2e28bfe50b237de3cce5")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Token expira em 24 horas

# Contexto de senha para hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# IDs das planilhas - primeiro tenta carregar do yaml, depois das variáveis de ambiente, depois dos valores padrão
MAIN_SPREADSHEET_ID = config.get('MAIN_SPREADSHEET_ID', os.getenv("MAIN_SPREADSHEET_ID", "1u1do3URWqU6_E9DAKenpm9F7BfKGw7sBNrtp0yxSwzk"))
VENDAS_SPREADSHEET_ID = config.get('VENDAS_SPREADSHEET_ID', os.getenv("VENDAS_SPREADSHEET_ID", "1ZQ34lkXtvlpR682o-0K15M5ZRkvlVMeTWwiW6angAPo"))

# Exibir as IDs de planilhas carregadas
print(f"MAIN_SPREADSHEET_ID: {MAIN_SPREADSHEET_ID}")
print(f"VENDAS_SPREADSHEET_ID: {VENDAS_SPREADSHEET_ID}")

# Função para carregar usuários do arquivo YAML e variáveis de ambiente
def load_users_from_config():
    users = {}
    
    # 1. Tentar carregar usuários do arquivo YAML
    if config and 'USERS' in config and isinstance(config['USERS'], dict):
        print("Carregando usuários do arquivo YAML...")
        for username, user_data in config['USERS'].items():
            try:
                if isinstance(user_data, dict) and 'email' in user_data and 'full_name' in user_data and 'password' in user_data:
                    email = user_data['email'].strip()
                    full_name = user_data['full_name'].strip()
                    password = user_data['password']
                    
                    users[email] = {
                        "username": email,
                        "full_name": full_name,
                        "hashed_password": pwd_context.hash(password),
                        "disabled": False
                    }
                    print(f"Usuário carregado do YAML: {email}, Nome: {full_name}")
            except Exception as e:
                print(f"Erro ao carregar usuário {username} do YAML: {e}")
    
    # 2. Carregar usuários das variáveis de ambiente
    print("Carregando usuários das variáveis de ambiente...")
    for key, value in os.environ.items():
        if key.startswith('USER_'):
            try:
                # Limpar a string de valor, removendo caracteres de controle como \r\n
                clean_value = value.strip().rstrip('\r\n').strip()
                print(f"Variável {key}: '{value}' -> '{clean_value}'")
                
                parts = clean_value.split(',')
                if len(parts) >= 3:  # Garantir que temos pelo menos email, nome e senha
                    email = parts[0].strip()
                    full_name = parts[1].strip()
                    # Para a senha, pegue o resto da string caso tenha vírgulas na senha
                    password = ','.join(parts[2:]).strip()
                    
                    users[email] = {
                        "username": email,
                        "full_name": full_name,
                        "hashed_password": pwd_context.hash(password),
                        "disabled": False
                    }
                    print(f"Usuário carregado da variável de ambiente: {email}, Nome: {full_name}")
            except Exception as e:
                print(f"Erro ao carregar usuário {key} da variável de ambiente: {e}")
    
    return users

# Lista de abas para ler - verificar se foi configurado no YAML
SHEET_NAMES = config.get('SHEET_NAMES', ["VISITAS", "PROSPECÇÃO", "DESPESAS", "QUESTIONÁRIO", "VENDAS"])

# Inicializar o banco de dados de usuários
users_db = load_users_from_config()

# Adicionar usuários fixos independentemente das variáveis de ambiente
# Isso é necessário para garantir o acesso em caso de problemas com as variáveis
if "rafael@remape.com" not in users_db:
    users_db["rafael@remape.com"] = {
        "username": "rafael@remape.com",
        "full_name": "Rafael",
        "hashed_password": pwd_context.hash("Guitarra3@!"),
        "disabled": False
    }
    print("Adicionado usuário padrão rafael@remape.com")

# Adicionar usuário de desenvolvimento para fácil acesso
if "admin" not in users_db:
    users_db["admin"] = {
        "username": "admin",
        "full_name": "Administrador",
        "hashed_password": pwd_context.hash("admin"),
        "disabled": False
    }
    print("Adicionado usuário admin")

# Garantir que todos os usuários indicados estejam disponíveis
for user_email, user_info in {
    "vendasremape@gmail.com": {"full_name": "Deise", "password": "vendas1@"},
    "promocaoremape@gmail.com": {"full_name": "Sandro", "password": "promocao1@"},
    "promocaoremape2@gmail.com": {"full_name": "Leide", "password": "promocao2$"}
}.items():
    if user_email not in users_db:
        users_db[user_email] = {
            "username": user_email,
            "full_name": user_info["full_name"],
            "hashed_password": pwd_context.hash(user_info["password"]),
            "disabled": False
        }
        print(f"Adicionado usuário padrão {user_email}")

print(f"Total de usuários carregados: {len(users_db)}")
print(f"Usuários disponíveis: {list(users_db.keys())}")

# Modelo de usuário
class User(BaseModel):
    username: str
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

# Modelo completo de usuário com senha
class UserInDB(User):
    hashed_password: str

# Inicializar o aplicativo FastAPI
app = FastAPI(title="Sistema REMAPE")

# Configurar a pasta de templates e arquivos estáticos
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Função para verificar e obter um usuário do banco de dados
def get_user(username: str):
    if username in users_db:
        user_dict = users_db[username]
        return UserInDB(**user_dict)
    return None

# Função para verificar senha
def verify_password(plain_password, hashed_password):
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Erro ao verificar senha: {e}")
        return False

# Função para autenticar usuário
def authenticate_user(username: str, password: str):
    print(f"Tentativa de autenticação para {username}")
    
    # Para teste: se o usuário for admin e a senha for admin, autorizar
    if username == "admin" and password == "admin":
        print("Login direto como admin")
        return UserInDB(
            username="admin",
            full_name="Administrador",
            hashed_password="irrelevant", # Não será usado
            disabled=False
        )
    
    # Para o usuário Rafael, aceitar se a senha for Guitarra3@!
    if username == "rafael@remape.com" and password == "Guitarra3@!":
        print("Login direto como rafael@remape.com")
        return UserInDB(
            username="rafael@remape.com",
            full_name="Rafael",
            hashed_password="irrelevant", # Não será usado
            disabled=False
        )
    
    # Autenticação normal
    user = get_user(username)
    if not user:
        print(f"Usuário não encontrado: {username}")
        return False
        
    print(f"Verificando senha para {username}")
    if not verify_password(password, user.hashed_password):
        print(f"Senha incorreta para {username}")
        return False
        
    print(f"Autenticação bem-sucedida para {username}")
    return user

# Função para criar token de acesso
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Middleware para verificar sessão do usuário
async def get_current_user(token: Optional[str] = Cookie(None)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_302_FOUND,
        detail="Could not validate credentials",
        headers={"Location": "/login"}
    )
    try:
        if token is None:
            raise credentials_exception
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        user = get_user(username)
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception

# Middleware para verificar se o usuário está ativo
async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Função para autenticar e obter o cliente Google Sheets
def get_gspread_client():
    try:
        # Escopo para acesso ao Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Tentar carregar as credenciais de várias fontes
        credentials_found = False
        creds = None
        
        # 1. Tentar como variável de ambiente JSON (usado no Cloud Run com Secret Manager)
        credentials_json = os.getenv("GOOGLE_CREDENTIALS")
        if credentials_json:
            try:
                print("Tentando autenticar com GOOGLE_CREDENTIALS da variável de ambiente")
                credentials_dict = json.loads(credentials_json)
                creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
                credentials_found = True
                print("Autenticado com sucesso usando GOOGLE_CREDENTIALS da variável de ambiente")
            except Exception as e:
                print(f"Erro ao usar GOOGLE_CREDENTIALS da variável de ambiente: {e}")
        
        # 2. Tentar credenciais implícitas (quando rodando no Google Cloud)
        if not credentials_found:
            try:
                print("Tentando autenticar com credenciais implícitas do Google Cloud")
                import google.auth
                default_credentials, _ = google.auth.default(scopes=scope)
                creds = default_credentials
                credentials_found = True
                print("Autenticado com sucesso usando credenciais implícitas")
            except Exception as e:
                print(f"Erro ao usar credenciais implícitas: {e}")
        
        # 3. Tentar arquivo local
        if not credentials_found:
            print("Tentando autenticar com arquivo de credenciais local")
            credentials_path = "credentials.json"
            
            if os.path.exists(credentials_path):
                file_size = os.path.getsize(credentials_path)
                print(f"Arquivo credentials.json encontrado ({file_size} bytes)")
                
                # Verificar conteúdo do arquivo
                with open(credentials_path, 'r') as f:
                    content = f.read()
                    try:
                        credentials_dict = json.loads(content)
                        if 'type' in credentials_dict and credentials_dict['type'] == 'service_account':
                            print("Arquivo de credenciais parece válido (contém type=service_account)")
                        else:
                            print("Arquivo de credenciais parece inválido (não contém type=service_account)")
                            print(f"Conteúdo parcial: {content[:100]}...")
                    except json.JSONDecodeError:
                        print("Arquivo de credenciais não é um JSON válido")
                        print(f"Conteúdo parcial: {content[:100]}...")
                
                # Tentar carregar as credenciais
                try:
                    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
                    credentials_found = True
                    print(f"Autenticado com sucesso usando arquivo {credentials_path}")
                except Exception as e:
                    print(f"Erro ao carregar arquivo {credentials_path}: {e}")
            else:
                print(f"Arquivo {credentials_path} não encontrado")
                
                # Se não existir e estamos em desenvolvimento, criar um arquivo com instruções
                if os.getenv("ENVIRONMENT") != "production":
                    with open("credentials.json", "w") as f:
                        json.dump({
                            "info": "Você precisa criar um arquivo de credenciais do Google Cloud Platform",
                            "instructions": "Visite https://console.cloud.google.com, crie um projeto, ative a API do Google Sheets e crie uma chave de conta de serviço"
                        }, f, indent=4)
                    print("Arquivo de instruções credentials.json criado")
        
        # Se não conseguimos autenticar, lançar exceção
        if not credentials_found or creds is None:
            raise ValueError("Não foi possível obter credenciais válidas de nenhuma fonte")
        
        # Inicializar o cliente gspread
        client = gspread.authorize(creds)
        return client
    
    except Exception as e:
        print(f"Erro ao autenticar no Google Sheets: {e}")
        if isinstance(e, FileNotFoundError):
            raise HTTPException(status_code=500, detail=f"Arquivo de credenciais não encontrado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao autenticar no Google Sheets: {str(e)}")

# Função para obter a planilha principal
def get_main_spreadsheet():
    try:
        client = get_gspread_client()
        return client.open_by_key(MAIN_SPREADSHEET_ID)
    except Exception as e:
        print(f"Erro ao acessar a planilha principal: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao acessar a planilha principal: {str(e)}")

# Função para obter a planilha de vendas
def get_vendas_spreadsheet():
    try:
        client = get_gspread_client()
        return client.open_by_key(VENDAS_SPREADSHEET_ID)
    except Exception as e:
        print(f"Erro ao acessar a planilha de vendas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao acessar a planilha de vendas: {str(e)}")

# Função para converter uma aba em DataFrame
def sheet_to_dataframe(sheet):
    try:
        # Obter todos os valores da aba
        data = sheet.get_all_values()
        
        # Converter para DataFrame, usando a primeira linha como cabeçalho
        if data:
            df = pd.DataFrame(data[1:], columns=data[0])
            return df
        return pd.DataFrame()
    
    except Exception as e:
        print(f"Erro ao processar a aba: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar a aba: {str(e)}")

# Função para filtrar DataFrame por data e vendedor
def filter_dataframe_by_date(df, start_date=None, end_date=None, sheet_name=None, current_user=None):
    # Se não houver datas para filtrar, retorna o DataFrame original
    if not start_date and not end_date:
        if df.empty:
            return df
    
    # Verificar se o DataFrame tem a coluna DATA
    if 'DATA' not in df.columns and not df.empty:
        return df
    
    # Fazer uma cópia para não modificar o original
    filtered_df = df.copy()
    
    # Converter a coluna de data para datetime, considerando os diferentes formatos
    try:
        if not filtered_df.empty and 'DATA' in filtered_df.columns:
            if sheet_name == "DESPESAS":
                # Para a aba DESPESAS, formato: 01/12/2023
                filtered_df['DATA'] = pd.to_datetime(filtered_df['DATA'], format='%d/%m/%Y', errors='coerce')
            elif sheet_name == "VENDAS":
                # Para a aba VENDAS, formatos: 19/12/2024 ou 07/08/23
                # Usar pd.to_datetime com detecção automática de formato
                filtered_df['DATA'] = pd.to_datetime(filtered_df['DATA'], dayfirst=True, errors='coerce')
            else:
                # Para as outras abas, formato: 01/12/2023 13:44:40
                filtered_df['DATA'] = pd.to_datetime(filtered_df['DATA'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
            
            # Filtrar por data de início, se fornecida
            if start_date:
                start_dt = pd.to_datetime(start_date, format='%Y-%m-%d')
                filtered_df = filtered_df[filtered_df['DATA'].dt.date >= start_dt.date()]
            
            # Filtrar por data de fim, se fornecida
            if end_date:
                end_dt = pd.to_datetime(end_date, format='%Y-%m-%d')
                filtered_df = filtered_df[filtered_df['DATA'].dt.date <= end_dt.date()]
    except Exception as e:
        print(f"Erro ao filtrar por data: {e}")
        # Se houver erro na conversão, retorna o DataFrame original
        return df
    
    # Filtrar por vendedor se o usuário não for rafael@remape.com
    if current_user and current_user.username != "rafael@remape.com" and not filtered_df.empty:
        try:
            # Para a aba VENDAS, filtrar pelo nome do vendedor (full_name)
            if sheet_name == "VENDAS" and 'VENDEDOR' in filtered_df.columns:
                # Filtrar pelo full_name sem distinção entre maiúsculas e minúsculas
                filtered_df = filtered_df[filtered_df['VENDEDOR'].str.lower() == current_user.full_name.lower()]
            # Para as outras abas, filtrar pelo email do vendedor
            elif 'VENDEDOR' in filtered_df.columns and sheet_name in ["VISITAS", "PROSPECÇÃO", "DESPESAS", "QUESTIONÁRIO"]:
                filtered_df = filtered_df[filtered_df['VENDEDOR'] == current_user.username]
        except Exception as e:
            print(f"Erro ao filtrar por vendedor: {e}")
    
    return filtered_df

# Rota para a página de login
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Rota para processar o login
@app.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    # Adicionar log para debug
    print(f"Tentativa de login via formulário: {username}")
    print(f"Usuários disponíveis: {list(users_db.keys())}")
    
    # Autenticação normal
    user = authenticate_user(username, password)
    if not user:
        # Log de falha
        print(f"Falha na autenticação para {username}")
        return templates.TemplateResponse("login.html", 
                                         {"request": request, 
                                          "error": "Email ou senha inválidos"})
    
    # Criar token de acesso
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Definir cookie com o token
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="token", value=access_token, httponly=True)
    
    print(f"Login bem-sucedido para {username}, redirecionando para /")
    return response

# Rota alternativa para login direto (emergência)
@app.get("/direct-login/{user_type}")
async def direct_login(response: Response, user_type: str):
    print(f"Tentativa de login direto como: {user_type}")
    
    if user_type == "admin":
        username = "admin"
        full_name = "Administrador"
    elif user_type == "rafael":
        username = "rafael@remape.com"
        full_name = "Rafael"
    elif user_type == "deise":
        username = "vendasremape@gmail.com"
        full_name = "Deise"
    elif user_type == "sandro":
        username = "promocaoremape@gmail.com"
        full_name = "Sandro"
    elif user_type == "leide":
        username = "promocaoremape2@gmail.com"
        full_name = "Leide"
    else:
        return {"error": "Usuário não reconhecido"}
    
    # Criar token de acesso
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    
    # Definir cookie com o token
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="token", value=access_token, httponly=True)
    
    print(f"Login direto bem-sucedido como {username}, redirecionando para /")
    return response

# Rota para logout
@app.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="token")
    return response

# Rota para a página inicial
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: User = Depends(get_current_active_user)):
    return templates.TemplateResponse("index.html", {"request": request, "sheet_names": SHEET_NAMES, "user": current_user})

# Rota para exibir uma aba específica
@app.get("/sheet/{sheet_name}", response_class=HTMLResponse)
async def get_sheet(request: Request, sheet_name: str, start_date: str = None, end_date: str = None, current_user: User = Depends(get_current_active_user)):
    if sheet_name not in SHEET_NAMES:
        raise HTTPException(status_code=404, detail=f"Aba '{sheet_name}' não encontrada")
    
    try:
        print(f"Acessando aba {sheet_name} para o usuário {current_user.username}")
        
        # Obter a planilha correta com base no nome da aba
        try:
            if sheet_name == "VENDAS":
                print(f"Obtendo planilha de VENDAS (ID: {VENDAS_SPREADSHEET_ID})")
                spreadsheet = get_vendas_spreadsheet()
            else:
                print(f"Obtendo planilha principal (ID: {MAIN_SPREADSHEET_ID})")
                spreadsheet = get_main_spreadsheet()
        except Exception as e:
            print(f"Erro ao obter planilha: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Erro ao acessar a planilha do Google Sheets: {str(e)}")
        
        # Abrir a aba específica
        try:
            if sheet_name == "VENDAS":
                print("Abrindo aba sheet1 da planilha VENDAS")
                sheet = spreadsheet.sheet1  # Assume que a aba de vendas é a primeira aba
            else:
                print(f"Abrindo aba {sheet_name} da planilha principal")
                sheet = spreadsheet.worksheet(sheet_name)
        except Exception as e:
            print(f"Erro ao abrir aba {sheet_name}: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Erro ao abrir a aba '{sheet_name}': {str(e)}")
        
        # Converter para DataFrame
        try:
            print(f"Convertendo aba {sheet_name} para DataFrame")
            df = sheet_to_dataframe(sheet)
            print(f"Aba {sheet_name} convertida com sucesso: {len(df)} linhas")
        except Exception as e:
            print(f"Erro ao converter aba {sheet_name} para DataFrame: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Erro ao processar os dados da aba '{sheet_name}': {str(e)}")
        
        # Filtrar por data e vendedor, se necessário
        try:
            print(f"Filtrando dados por data e vendedor para {current_user.username}")
            df_filtered = filter_dataframe_by_date(df, start_date, end_date, sheet_name, current_user)
            print(f"Dados filtrados: {len(df_filtered)} linhas")
        except Exception as e:
            print(f"Erro ao filtrar dados: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Erro ao filtrar os dados da aba '{sheet_name}': {str(e)}")
        
        # Filtrar colunas e adicionar contagem para VISITAS, PROSPECÇÃO, QUESTIONÁRIO, DESPESAS e VENDAS
        if sheet_name == "VISITAS":
            # Garantir que todas as colunas existam antes de filtrar
            colunas_desejadas = ['DATA', 'VENDEDOR', 'CLIENTE', 'INDÚSTRIA', 'PERCEPÇÃO MERCADO', 'OBS']
            colunas_existentes = [col for col in colunas_desejadas if col in df_filtered.columns]
            
            # Filtrar apenas as colunas existentes
            df_filtered = df_filtered[colunas_existentes]
            
            # Contar o número de visitas no período
            num_registros = len(df_filtered)
            tipo_registro = "visitas"
            
        elif sheet_name == "PROSPECÇÃO":
            # Garantir que todas as colunas existam antes de filtrar
            colunas_desejadas = ['DATA', 'VENDEDOR', 'NOME DA EMPRESA', 'ENDEREÇO', 'CNPJ', 'RESPONSÁVEL', 
                                'TELEFONE', 'E-MAIL', 'OBSERVAÇÕES', 'ID INSTAGRAM']
            colunas_existentes = [col for col in colunas_desejadas if col in df_filtered.columns]
            
            # Filtrar apenas as colunas existentes
            df_filtered = df_filtered[colunas_existentes]
            
            # Contar o número de prospecções no período
            num_registros = len(df_filtered)
            tipo_registro = "prospecções"
            
        elif sheet_name == "QUESTIONÁRIO":
            # Garantir que todas as colunas existam antes de filtrar
            colunas_desejadas = ['VENDEDOR', 'DATA', 'NOME', 'ENDEREÇO', 'TELEFONE', 'RAMO DE ATUAÇÃO',
                                'MÉDIA DIÁRIA DE CLIENTES', 'PRINCIPAIS DISTRIBUIDORES/LOJAS', 'PRINCIPAL DISTRIBUIDOR/LOJA',
                                '% UTILIZADO DRW', 'MARCAS UTILIZADAS DRW', 'PRINCIPAL MARCA DRW', 'DRW NÃO COMPRA/NÃO É A PRINCIPAL?',
                                '% UTILIZADO IKS', 'MARCAS UTILIZADAS IKS', 'PRINCIPAL MARCA IKS', 'IKS NÃO COMPRA/NÃO É A PRINCIPAL?',
                                '% UTILIZADO MOB', 'MARCAS UTILIZADAS MOB', 'PRINCIPAL MARCA MOB', 'MOB NÃO COMPRA/NÃO É A PRINCIPAL?',
                                '% UTILIZADO TAR', 'MARCAS UTILIZADAS TAR', 'PRINCIPAL MARCA TAR', 'TAR NÃO COMPRA/NÃO É A PRINCIPAL?',
                                '% UTILIZADO ZEN', 'MARCAS UTILIZADAS ZEN', 'PRINCIPAL MARCA ZEN', 'ZEN NÃO COMPRA/NÃO É A PRINCIPAL?',
                                'ID INSTAGRAM']
            colunas_existentes = [col for col in colunas_desejadas if col in df_filtered.columns]
            
            # Filtrar apenas as colunas existentes
            df_filtered = df_filtered[colunas_existentes]
            
            # Contar o número de questionários no período
            num_registros = len(df_filtered)
            tipo_registro = "questionários"
            
        elif sheet_name == "DESPESAS":
            # Garantir que todas as colunas existam antes de filtrar
            colunas_desejadas = ['DATA', 'VENDEDOR', 'KM INICIAL', 'KM FINAL', 'ESTACIONAMENTO', 
                               'PEDÁGIO', 'OUTRAS DESPESAS', 'DESCRIÇÃO DE OUTRAS DESPESAS', 'KM TOTAL']
            colunas_existentes = [col for col in colunas_desejadas if col in df_filtered.columns]
            
            # Filtrar apenas as colunas existentes
            df_filtered = df_filtered[colunas_existentes]
            
            # Inicializar variáveis para os somatórios
            totais_despesas = {
                'km_total': 0,
                'estacionamento': 0,
                'pedagio': 0,
                'outras_despesas': 0
            }
            
            # Calcular os somatórios das colunas relevantes
            if 'KM TOTAL' in df_filtered.columns:
                # Converter para numérico, ignorando erros (NaN para valores não numéricos)
                df_filtered['KM TOTAL'] = pd.to_numeric(df_filtered['KM TOTAL'], errors='coerce')
                totais_despesas['km_total'] = df_filtered['KM TOTAL'].sum()
                
            if 'ESTACIONAMENTO' in df_filtered.columns:
                # Limpar valores monetários (remover R$, pontos, vírgulas) e converter para numérico
                df_filtered['ESTACIONAMENTO'] = df_filtered['ESTACIONAMENTO'].astype(str)
                df_filtered['ESTACIONAMENTO'] = df_filtered['ESTACIONAMENTO'].str.replace('R$', '').str.replace('.', '').str.replace(',', '.').str.strip()
                df_filtered['ESTACIONAMENTO'] = pd.to_numeric(df_filtered['ESTACIONAMENTO'], errors='coerce')
                totais_despesas['estacionamento'] = df_filtered['ESTACIONAMENTO'].sum()
                
            if 'PEDÁGIO' in df_filtered.columns:
                # Limpar valores monetários e converter para numérico
                df_filtered['PEDÁGIO'] = df_filtered['PEDÁGIO'].astype(str)
                df_filtered['PEDÁGIO'] = df_filtered['PEDÁGIO'].str.replace('R$', '').str.replace('.', '').str.replace(',', '.').str.strip()
                df_filtered['PEDÁGIO'] = pd.to_numeric(df_filtered['PEDÁGIO'], errors='coerce')
                totais_despesas['pedagio'] = df_filtered['PEDÁGIO'].sum()
                
            if 'OUTRAS DESPESAS' in df_filtered.columns:
                # Limpar valores monetários e converter para numérico
                df_filtered['OUTRAS DESPESAS'] = df_filtered['OUTRAS DESPESAS'].astype(str)
                df_filtered['OUTRAS DESPESAS'] = df_filtered['OUTRAS DESPESAS'].str.replace('R$', '').str.replace('.', '').str.replace(',', '.').str.strip()
                df_filtered['OUTRAS DESPESAS'] = pd.to_numeric(df_filtered['OUTRAS DESPESAS'], errors='coerce')
                totais_despesas['outras_despesas'] = df_filtered['OUTRAS DESPESAS'].sum()
                
            # Contar o número de registros no período
            num_registros = len(df_filtered)
            tipo_registro = "despesas"
            
        elif sheet_name == "VENDAS":
            # Contar o número de vendas no período
            num_registros = len(df_filtered)
            tipo_registro = "vendas"
            
            # Calcular o valor total das vendas no período
            if 'VALOR' in df_filtered.columns:
                # Limpar valores monetários e converter para numérico
                df_filtered['VALOR'] = df_filtered['VALOR'].astype(str)
                df_filtered['VALOR'] = df_filtered['VALOR'].str.replace('R$', '').str.replace('.', '').str.replace(',', '.').str.strip()
                df_filtered['VALOR'] = pd.to_numeric(df_filtered['VALOR'], errors='coerce')
                
                # Somar os valores
                total_vendas = df_filtered['VALOR'].sum()
            else:
                total_vendas = 0
                
            # Dados para gráficos
            dados_grafico_industria = None
            dados_grafico_grupo = None
            
            # Distribuição percentual por indústria
            if 'INDÚSTRIA' in df_filtered.columns and 'VALOR' in df_filtered.columns:
                # Agrupar por indústria e somar os valores
                vendas_por_industria = df_filtered.groupby('INDÚSTRIA')['VALOR'].sum().reset_index()
                
                # Calcular a porcentagem de cada indústria
                vendas_por_industria['PORCENTAGEM'] = (vendas_por_industria['VALOR'] / total_vendas * 100).round(2)
                
                # Ordenar por valor (do maior para o menor)
                vendas_por_industria = vendas_por_industria.sort_values('VALOR', ascending=False)
                
                # Preparar dados para o gráfico de pizza
                labels = vendas_por_industria['INDÚSTRIA'].tolist()
                valores = vendas_por_industria['VALOR'].tolist()
                porcentagens = vendas_por_industria['PORCENTAGEM'].tolist()
                
                # Cores específicas para indústrias especificadas
                cores_especificas = {
                    'MOBENSANI': '#FF0000',  # Vermelho
                    'TARANTO': '#0000FF',    # Azul
                    'IKS': '#FF69B4',        # Rosa
                    'ZEN': '#FFA500',        # Laranja
                    'DRIVEWAY': '#FFFF00'    # Amarelo
                }
                
                # Cores padrão para outras indústrias (tons de verde)
                cores_padrao = [
                    '#4CAF50', '#81C784', '#A5D6A7', '#C8E6C9', '#E8F5E9',
                    '#2E7D32', '#388E3C', '#43A047', '#66BB6A', '#009688',
                    '#26A69A', '#4DB6AC', '#80CBC4', '#B2DFDB', '#E0F2F1'
                ]
                
                # Atribuir cores às indústrias
                cores = []
                for industria in labels:
                    # Verificar se a indústria tem uma cor específica
                    if industria.upper() in cores_especificas:
                        cores.append(cores_especificas[industria.upper()])
                    # Ou encontrar parte do nome da indústria nas cores específicas
                    else:
                        cor_encontrada = False
                        for nome_especifico, cor in cores_especificas.items():
                            if nome_especifico in industria.upper():
                                cores.append(cor)
                                cor_encontrada = True
                                break
                        
                        # Se não encontrou uma cor específica, usar uma cor padrão
                        if not cor_encontrada:
                            cores.append(cores_padrao[len(cores) % len(cores_padrao)])
                
                # Criar dicionário com os dados para o gráfico de indústria
                dados_grafico_industria = {
                    'labels': labels,
                    'valores': valores,
                    'porcentagens': porcentagens,
                    'cores': cores
                }
            
            # Distribuição percentual por GRUPO
            if 'GRUPO' in df_filtered.columns and 'VALOR' in df_filtered.columns:
                # Agrupar por GRUPO e somar os valores
                vendas_por_grupo = df_filtered.groupby('GRUPO')['VALOR'].sum().reset_index()
                
                # Calcular a porcentagem de cada grupo
                vendas_por_grupo['PORCENTAGEM'] = (vendas_por_grupo['VALOR'] / total_vendas * 100).round(2)
                
                # Ordenar por valor (do maior para o menor)
                vendas_por_grupo = vendas_por_grupo.sort_values('VALOR', ascending=False)
                
                # Preparar dados para o gráfico de barras
                grupo_labels = vendas_por_grupo['GRUPO'].tolist()
                grupo_valores = vendas_por_grupo['VALOR'].tolist()
                grupo_porcentagens = vendas_por_grupo['PORCENTAGEM'].tolist()
                
                # Cores para o gráfico de barras (tons de azul)
                grupo_cores = [
                    '#1976D2', '#2196F3', '#42A5F5', '#64B5F6', '#90CAF9',
                    '#0D47A1', '#1565C0', '#1976D2', '#1E88E5', '#2196F3'
                ]
                
                # Garantir que temos cores suficientes
                if len(grupo_labels) > len(grupo_cores):
                    grupo_cores = grupo_cores * (len(grupo_labels) // len(grupo_cores) + 1)
                
                # Limitar ao número de grupos
                grupo_cores = grupo_cores[:len(grupo_labels)]
                
                # Criar dicionário com os dados para o gráfico de grupo
                dados_grafico_grupo = {
                    'labels': grupo_labels,
                    'valores': grupo_valores,
                    'porcentagens': grupo_porcentagens,
                    'cores': grupo_cores
                }
                
            # Criar dicionário com os totais
            totais_vendas = {
                'total_valor': total_vendas,
                'grafico_industria': dados_grafico_industria,
                'grafico_grupo': dados_grafico_grupo
            }
        else:
            num_registros = None
            tipo_registro = None
            totais_despesas = None
            totais_vendas = None
        
        # Converter DataFrame para HTML
        table_html = df_filtered.to_html(classes="table table-striped table-hover", index=False)
        
        # Preparar o contexto para o template
        context = {
            "request": request, 
            "sheet_name": sheet_name, 
            "table_html": table_html,
            "sheet_names": SHEET_NAMES,
            "start_date": start_date,
            "end_date": end_date,
            "num_registros": num_registros,
            "tipo_registro": tipo_registro,
            "user": current_user,
            "filtrado_por_vendedor": current_user.username != "rafael@remape.com"
        }
        
        # Adicionar os totais de despesas ao contexto, se disponíveis
        if sheet_name == "DESPESAS" and totais_despesas:
            context.update({
                "totais_despesas": totais_despesas
            })
            
        # Adicionar os totais de vendas ao contexto, se disponíveis
        if sheet_name == "VENDAS" and 'totais_vendas' in locals():
            context.update({
                "totais_vendas": totais_vendas
            })
        
        # Retornar o template com os dados
        return templates.TemplateResponse("sheet.html", context)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar a aba '{sheet_name}': {str(e)}")

# Rota de saúde para verificar se o serviço está funcionando
@app.get("/healthz")
async def health_check():
    return {
        "status": "healthy", 
        "user_count": len(users_db),
        "users": list(users_db.keys()),
        "env_vars": {k: v for k, v in os.environ.items() if not k.startswith("SECRET") and not "PASSWORD" in k.upper() and not "KEY" in k.upper()}
    }

# Rota para verificar usuários cadastrados (apenas para debug)
@app.get("/users")
async def list_users(current_user: User = Depends(get_current_active_user)):
    # Verificar se o usuário é administrador
    if current_user.username != "rafael@remape.com":
        raise HTTPException(status_code=403, detail="Acesso não autorizado")
    
    # Retornar a lista de usuários (sem as senhas)
    user_list = []
    for email, data in users_db.items():
        user_list.append({
            "username": email,
            "full_name": data["full_name"]
        })
    
    return {"users": user_list}

# Rota pública para debug (remover em produção depois de resolver o problema)
@app.get("/debug")
async def debug_info():
    # Verificar variáveis de ambiente
    env_info = {k: v for k, v in os.environ.items() 
                if not k.startswith("SECRET") 
                and not "PASSWORD" in k.upper() 
                and not "KEY" in k.upper()}
    
    # Listar usuários disponíveis (sem mostrar senhas)
    user_list = []
    for email, data in users_db.items():
        user_list.append({
            "username": email,
            "full_name": data["full_name"]
        })
    
    # Verificar Google Sheets
    sheets_status = "Not tested"
    try:
        # Tentar listar as abas da planilha
        client = get_gspread_client()
        # Verificar se consegue acessar a planilha
        sheets_status = "Connected to Google Sheets API"
    except Exception as e:
        sheets_status = f"Error: {str(e)}"
    
    # Informações de configuração
    config_info = {
        "MAIN_SPREADSHEET_ID": MAIN_SPREADSHEET_ID,
        "VENDAS_SPREADSHEET_ID": VENDAS_SPREADSHEET_ID,
        "SHEET_NAMES": SHEET_NAMES,
        "yaml_file_found": os.path.exists("env.yaml"),
        "yaml_config_loaded": bool(config)
    }
    
    # Verificar se há caracteres problemáticos nas variáveis de ambiente
    env_problems = []
    for key, value in os.environ.items():
        if key.startswith('USER_') or key.endswith('_ID'):
            if '\r' in value or '\n' in value:
                env_problems.append(f"{key}: contém caracteres de controle")
    
    # Links de acesso direto
    direct_login_links = {
        "admin": f"/direct-login/admin",
        "rafael": f"/direct-login/rafael",
        "deise": f"/direct-login/deise",
        "sandro": f"/direct-login/sandro",
        "leide": f"/direct-login/leide"
    }
    
    return {
        "app_status": "running",
        "config": config_info,
        "user_count": len(users_db),
        "users": user_list,
        "env_vars": env_info,
        "env_problems": env_problems,
        "google_sheets_status": sheets_status,
        "login_problems": (
            "Detectamos problemas nas variáveis de ambiente que podem estar causando falhas de login. "
            "Para acessar o sistema, use um dos links de login direto abaixo:"
        ),
        "direct_login_links": direct_login_links
    }

# Se este arquivo for executado diretamente
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Iniciando aplicação na porta {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port)