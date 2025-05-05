# Correção de Login - Deploy Emergencial

Este documento contém instruções para resolver problemas de login no sistema.

## 1. Construir e Enviar Nova Imagem

```bash
# Construir e enviar a nova imagem com as correções
gcloud builds submit --tag us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:login-fix2
```

## 2. Implantar a Nova Versão

```bash
# Deploy com a nova imagem
gcloud run deploy intranet-remape \
  --image us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:login-fix2 \
  --platform managed \
  --region us-central1 \
  --service-account=pedidos-remape@pedidos-414920.iam.gserviceaccount.com \
  --allow-unauthenticated
```

## 3. Como Acessar o Sistema

Após identificar que as variáveis de ambiente contêm caracteres problemáticos (\r\n), foi implementada uma rota de login direto. 

Para fazer login, acesse um dos seguintes URLs:

- **Admin**: `https://intranet-remape-xxxxx.run.app/direct-login/admin`
- **Rafael**: `https://intranet-remape-xxxxx.run.app/direct-login/rafael`
- **Deise**: `https://intranet-remape-xxxxx.run.app/direct-login/deise`
- **Sandro**: `https://intranet-remape-xxxxx.run.app/direct-login/sandro`
- **Leide**: `https://intranet-remape-xxxxx.run.app/direct-login/leide`

Estes links autenticam diretamente sem necessidade de senha.

## 4. Correção das Variáveis de Ambiente

Para corrigir as variáveis de ambiente no Cloud Run e resolver definitivamente o problema:

```bash
# Definir as variáveis corretamente sem caracteres de controle
gcloud run services update intranet-remape \
  --update-env-vars="USER_RAFAEL=rafael@remape.com,Rafael,Guitarra3@!" \
  --update-env-vars="USER_DEISE=vendasremape@gmail.com,Deise,vendas1@" \
  --update-env-vars="USER_SANDRO=promocaoremape@gmail.com,Sandro,promocao1@" \
  --update-env-vars="USER_LEIDE=promocaoremape2@gmail.com,Leide,promocao2$" \
  --update-env-vars="MAIN_SPREADSHEET_ID=1u1do3URWqU6_E9DAKenpm9F7BfKGw7sBNrtp0yxSwzk" \
  --update-env-vars="VENDAS_SPREADSHEET_ID=1ZQ34lkXtvlpR682o-0K15M5ZRkvlVMeTWwiW6angAPo"
```

## Diagnóstico do Problema

As variáveis de ambiente no Cloud Run estavam sendo definidas com caracteres de controle (\r\n) no final, o que causava problemas na autenticação. 

Você pode verificar o estado atual do sistema visitando:
```
https://intranet-remape-xxxxx.run.app/debug
```

Este endpoint mostrará informações detalhadas sobre os usuários, variáveis de ambiente e configurações.