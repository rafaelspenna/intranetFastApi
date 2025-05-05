# Deploy Rápido - Login Fix

## 1. Construir e Enviar Nova Imagem
```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:login-fix
```

## 2. Implantar a Nova Versão
```bash
gcloud run deploy intranet-remape \
  --image us-central1-docker.pkg.dev/pedidos-414920/intranet-remape/app:login-fix \
  --platform managed \
  --region us-central1 \
  --service-account=pedidos-remape@pedidos-414920.iam.gserviceaccount.com \
  --allow-unauthenticated
```

## 3. Como fazer login

Você tem três opções para fazer login:

1. Usar o usuário admin:
   - Email: `admin`
   - Senha: `admin`

2. Usar o usuário Rafael:
   - Email: `rafael@remape.com`
   - Senha: `Guitarra3@!`

3. Se você tiver outros usuários configurados que estejam funcionando, continue usando-os.

## 4. Diagnosticar o problema:

1. Acesse o endpoint de saúde para ver as variáveis e usuários disponíveis:
   ```
   https://intranet-remape-xxxxx.run.app/healthz
   ```

2. Este endpoint mostrará os usuários disponíveis e as variáveis de ambiente configuradas.

## Próximos passos

Depois que o login estiver funcionando com os usuários admin e rafael@remape.com, podemos:

1. Implementar o carregamento de usuários a partir do arquivo env.yaml. Para isso, você pode fazer o seguinte:

```bash
# Configuração do ambiente com o arquivo env.yaml
gcloud run services update intranet-remape \
  --update-env-vars=USER_RAFAEL=rafael@remape.com,Rafael,Guitarra3@! \
  --update-env-vars=USER_DEISE=vendasremape@gmail.com,Deise,vendas1@ \
  --update-env-vars=USER_SANDRO=promocaoremape@gmail.com,Sandro,promocao1@ \
  --update-env-vars=USER_LEIDE=promocaoremape2@gmail.com,Leide,promocao2$
```

2. Para carregar o arquivo env.yaml inteiro, podemos usar:

```bash
# Ler o arquivo env.yaml e convertê-lo em argumentos de linha de comando
gcloud run services update intranet-remape \
  --update-env-vars="$(cat env.yaml | grep -v '^#' | tr '\n' ',')"
```

3. Em uma futura atualização, podemos modificar o código para ler diretamente o arquivo YAML.