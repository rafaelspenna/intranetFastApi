# Deploy Final - Sistema Intranet REMAPE

Este documento contém instruções para a implantação final do sistema Intranet REMAPE, com acesso normalizado via tela de login.

## 1. Construir e Enviar Nova Imagem

```bash
# Construir e enviar a nova imagem
gcloud builds submit --tag us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:v1.0
```

## 2. Implantar a Nova Versão

```bash
# Deploy da versão final
gcloud run deploy intranet-remape \
  --image us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:v1.0 \
  --platform managed \
  --region us-central1 \
  --service-account=pedidos-remape@pedidos-414920.iam.gserviceaccount.com \
  --allow-unauthenticated
```

## 3. Verificações e Acessos

Após o deploy:

1. **Verificar funcionamento**: Acesse a URL fornecida pelo Cloud Run
2. **Fazer login**: Use a tela de login com os seguintes usuários:
   - `rafael@remape.com` / `Guitarra3@!` (acesso a todos os dados)
   - `vendasremape@gmail.com` / `vendas1@` (Deise - dados filtrados)
   - `promocaoremape@gmail.com` / `promocao1@` (Sandro - dados filtrados)
   - `promocaoremape2@gmail.com` / `promocao2$` (Leide - dados filtrados)
3. **Verificar filtragem de dados**: Confirme que:
   - O usuário Rafael tem acesso a todos os dados
   - Os outros usuários só veem seus próprios dados

## 4. Manutenção e Segurança

### 4.1 Monitoramento

```bash
# Verificar logs do sistema
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=intranet-remape" --limit=50
```

### 4.2 Atualizações Futuras

Para futuras atualizações do sistema:

```bash
# Construir nova versão
gcloud builds submit --tag us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:v1.x

# Atualizar serviço
gcloud run deploy intranet-remape \
  --image us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:v1.x
```

### 4.3 Backup e Recuperação

Para fazer backup das configurações:

```bash
# Exportar configurações do serviço
gcloud run services describe intranet-remape --format=json > intranet-remape-config.json
```

## 5. Informações Adicionais

- **Autenticação**: O sistema usa autenticação baseada em JWT com cookies
- **Credenciais Google Sheets**: Armazenadas no Secret Manager
- **Usuários**: Definidos nas variáveis de ambiente do Cloud Run
- **Arquivos estáticos**: Servidos diretamente pelo FastAPI

---

Seu sistema Intranet REMAPE está agora completamente configurado e pronto para uso em produção!