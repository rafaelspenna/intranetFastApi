# Deploy com configuração YAML

## 1. Criar o arquivo env.yaml

```bash
# Copiar o arquivo de exemplo
cp env.yaml.example env.yaml

# Editar o arquivo com seus valores (opcional)
# O arquivo já contém todos os valores necessários
```

## 2. Construir e Enviar Nova Imagem

```bash
# Construir e enviar a nova imagem
gcloud builds submit --tag us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:yaml-config
```

## 3. Implantar o Aplicativo com o Arquivo YAML

```bash
# Criar um Secret Manager secret para o arquivo YAML (opcional)
gcloud secrets create env-yaml --data-file=env.yaml

# Deploy com o arquivo YAML incluído
gcloud run deploy intranet-remape \
  --image us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:yaml-config \
  --platform managed \
  --region us-central1 \
  --service-account=pedidos-remape@pedidos-414920.iam.gserviceaccount.com \
  --allow-unauthenticated
```

## 4. Verificar a Configuração

Acesse o endpoint `/debug` para verificar se a configuração foi carregada corretamente:

```
https://intranet-remape-xxxxx.run.app/debug
```

## Notas Importantes

1. O aplicativo agora vai carregar configurações de três fontes, em ordem de prioridade:
   - Arquivo env.yaml
   - Variáveis de ambiente no Cloud Run
   - Valores padrão codificados

2. O arquivo env.yaml deve estar na pasta raiz do aplicativo quando o contêiner é construído

3. Os usuários disponíveis serão:
   - Todos os usuários definidos no env.yaml
   - Todos os usuários definidos nas variáveis de ambiente
   - Os usuários padrão: rafael@remape.com, admin, e os outros usuários específicos
   
4. Para fazer login, você pode usar qualquer um dos usuários configurados.

5. Os filtros funcionarão automaticamente com base no usuário logado:
   - Usuário rafael@remape.com verá todos os dados
   - Outros usuários verão apenas seus próprios dados
   - Em VENDAS, o filtro é pelo nome do usuário (Deise, Sandro, Leide)
   - Nas outras abas, o filtro é pelo email do usuário