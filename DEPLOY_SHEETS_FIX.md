# Correção do Acesso às Planilhas do Google Sheets

Este documento contém instruções para resolver o problema de acesso às planilhas do Google Sheets.

## 1. O Problema

Após o login, quando o usuário tenta acessar qualquer aba (VISITAS, DESPESAS, etc.), o sistema retorna um erro como:
```
{"detail":"Erro ao processar a aba 'VENDAS': "}
```

Este erro ocorre porque o sistema não consegue se autenticar no Google Sheets. As possíveis causas são:

1. O arquivo `credentials.json` não está sendo incluído na imagem Docker
2. A conta de serviço não tem permissões para acessar as planilhas
3. As credenciais não estão sendo carregadas corretamente no ambiente do Cloud Run

## 2. Solução - Opção 1: Usar Secret Manager

### 2.1. Criar um Secret no Cloud Secret Manager

```bash
# Verificar se o arquivo credentials.json existe localmente
cat credentials.json

# Criar um Secret com o conteúdo do arquivo
cat credentials.json | gcloud secrets create google-sheets-credentials --data-file=-

# Dar permissão à conta de serviço do Cloud Run
gcloud secrets add-iam-policy-binding google-sheets-credentials \
  --member="serviceAccount:pedidos-remape@pedidos-414920.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 2.2. Atualizar o Cloud Run para usar o Secret

```bash
# Atualizar o serviço para usar o Secret como variável de ambiente
gcloud run services update intranet-remape \
  --update-secrets="GOOGLE_CREDENTIALS=google-sheets-credentials:latest"
```

## 3. Solução - Opção 2: Usar Identity and Access Management (IAM)

### 3.1. Dar permissões à conta de serviço na planilha

1. Abra a planilha principal no navegador
2. Clique em "Compartilhar"
3. Adicione o email da conta de serviço `pedidos-remape@pedidos-414920.iam.gserviceaccount.com` como editor
4. Repita o mesmo processo para a planilha de vendas

### 3.2. Fazer nova implantação com autenticação implícita

```bash
# Construir e enviar nova imagem com as correções
gcloud builds submit --tag us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:sheets-fix

# Implantar a nova versão
gcloud run deploy intranet-remape \
  --image us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:sheets-fix \
  --platform managed \
  --region us-central1 \
  --service-account=pedidos-remape@pedidos-414920.iam.gserviceaccount.com \
  --allow-unauthenticated
```

## 4. Diagnóstico e Monitoramento

Para monitorar o problema e verificar se as correções funcionaram:

1. Acesse a página de debug:
```
https://intranet-remape-xxxxx.run.app/debug
```

2. Verifique os logs do Cloud Run:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=intranet-remape" --limit=50
```

3. Use o login direto para testar o acesso:
```
https://intranet-remape-xxxxx.run.app/direct-login/rafael
```