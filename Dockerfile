FROM python:3.11-slim

WORKDIR /app

# Copiar arquivos de requisitos e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante dos arquivos
COPY . .

# Expor a porta que o app vai usar
EXPOSE 8080

# Variável de ambiente para indicar que está em produção
ENV ENVIRONMENT=production

# Comando direto para executar a aplicação
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT