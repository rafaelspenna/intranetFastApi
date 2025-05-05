# Deploy Urgente no Google Cloud Run

Este guia contém instruções para realizar um deploy urgente que deve resolver o problema atual.

## 1. Substituir o arquivo main.py

```bash
# Substituir o arquivo main.py pelo simplificado
cp main.py.simple main.py
```

## 2. Construir e Enviar Imagem

```bash
# Construir e enviar a nova imagem com tag especial
gcloud builds submit --tag us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:emergencia
```

## 3. Deploy Emergencial

```bash
# Deploy com configurações mínimas e variáveis como strings diretas
gcloud run deploy intranet-remape \
  --image us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:emergencia \
  --platform managed \
  --region us-central1 \
  --service-account=pedidos-remape@pedidos-414920.iam.gserviceaccount.com \
  --allow-unauthenticated
```

## 4. Verificar se o Aplicativo Está Funcionando

Acesse a URL fornecida pelo Cloud Run após o deploy para verificar se o aplicativo está funcionando.