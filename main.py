# main.py
from fastapi import FastAPI, Request, HTTPException, Depends, Form, status, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de segurança
SECRET_KEY = os.getenv("SECRET_KEY", "a30e2cc67c8b5cfcc2ab1fc0d8da5ad50e1ec8a84f0a2e28bfe50b237de3cce5")  # Chave secreta para JWT
ALGORITHM = "HS256"  # Algoritmo para JWT
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Token expira em 24 horas

# Contexto de senha para hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Carregar usuários do arquivo .env
# Formato nos env vars: USER_NAME=email,full_name,password
def load_users_from_env():
    users = {}
    for key, value in os.environ.items():
        if key.startswith('USER_'):
            try:
                email, full_name, password = value.split(',')
                # Garantir que o email e o nome estão devidamente formatados
                email = email.strip()
                full_name = full_name.strip()
                users[email] = {
                    "username": email,
                    "full_name": full_name,
                    "hashed_password": pwd_context.hash(password),
                    "disabled": False
                }
                print(f"Usuário carregado: {email}, Nome: {full_name}")
            except Exception as e:
                print(f"Erro ao carregar usuário {key}: {e}")
    return users

# Inicializar o banco de dados de usuários
users_db = load_users_from_env()

# Se nenhum usuário foi carregado do .env, usar o usuário padrão
if not users_db:
    users_db = {
        "rafael@remape.com": {
            "username": "rafael@remape.com",
            "full_name": "Rafael",
            "hashed_password": pwd_context.hash("Guitarra3@!"),
            "disabled": False
        }
    }

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

# IDs das planilhas
MAIN_SPREADSHEET_ID = os.getenv("MAIN_SPREADSHEET_ID", "1u1do3URWqU6_E9DAKenpm9F7BfKGw7sBNrtp0yxSwzk")
VENDAS_SPREADSHEET_ID = os.getenv("VENDAS_SPREADSHEET_ID", "1ZQ34lkXtvlpR682o-0K15M5ZRkvlVMeTWwiW6angAPo")

# Lista de abas para ler
SHEET_NAMES = ["VISITAS", "PROSPECÇÃO", "DESPESAS", "QUESTIONÁRIO", "VENDAS"]

# Função para verificar e obter um usuário do banco de dados
def get_user(username: str):
    if username in users_db:
        user_dict = users_db[username]
        return UserInDB(**user_dict)
    return None

# Função para verificar senha
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Função para autenticar usuário
def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
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
        
        # Verificar se o arquivo de credenciais existe
        if not os.path.exists("credentials.json"):
            # Se não existir, criar um arquivo com instruções
            with open("credentials.json", "w") as f:
                json.dump({
                    "info": "Você precisa criar um arquivo de credenciais do Google Cloud Platform",
                    "instructions": "Visite https://console.cloud.google.com, crie um projeto, ative a API do Google Sheets e crie uma chave de conta de serviço"
                }, f, indent=4)
            raise FileNotFoundError("Arquivo de credenciais não encontrado. Consulte as instruções em credentials.json")
        
        # Carregar credenciais e autenticar
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        return gspread.authorize(creds)
    
    except Exception as e:
        print(f"Erro ao autenticar no Google Sheets: {e}")
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

# Rota para a página de login
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Rota para processar o login
@app.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    user = authenticate_user(username, password)
    if not user:
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

# Rota para exibir uma aba específica
@app.get("/sheet/{sheet_name}", response_class=HTMLResponse)
async def get_sheet(request: Request, sheet_name: str, start_date: str = None, end_date: str = None, current_user: User = Depends(get_current_active_user)):
    if sheet_name not in SHEET_NAMES:
        raise HTTPException(status_code=404, detail=f"Aba '{sheet_name}' não encontrada")
    
    try:
        # Obter a planilha correta com base no nome da aba
        if sheet_name == "VENDAS":
            spreadsheet = get_vendas_spreadsheet()
        else:
            spreadsheet = get_main_spreadsheet()
        
        # Abrir a aba específica
        if sheet_name == "VENDAS":
            sheet = spreadsheet.sheet1  # Assume que a aba de vendas é a primeira aba
        else:
            sheet = spreadsheet.worksheet(sheet_name)
        
        # Converter para DataFrame
        df = sheet_to_dataframe(sheet)
        
        # Filtrar por data e vendedor, se necessário
        df_filtered = filter_dataframe_by_date(df, start_date, end_date, sheet_name, current_user)
        
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

# Inicializar o aplicativo com uvicorn
if __name__ == "__main__":
    import uvicorn
    import socket
    
    # Obter o endereço IP local (opcional, para informações)
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("\n===== Servidor FastAPI iniciado =====")
    print("Acesse o aplicativo usando um dos seguintes URLs:")
    print(f"    http://localhost:8000")
    print(f"    http://127.0.0.1:8000")
    print(f"    http://{local_ip}:8000 (para acesso na rede local)")
    print("=====================================")
    
    # Exibir informações dos usuários carregados
    print("\nUsuários carregados:")
    for email, data in users_db.items():
        print(f"  - {email} ({data['full_name']})")
    print("\n")
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)