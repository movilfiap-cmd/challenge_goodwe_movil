# Sistema de Gerenciamento de Energia Inteligente

Um sistema completo de gerenciamento de energia construído com Django, que monitora o consumo de dispositivos domésticos, integra com APIs meteorológicas e oferece controle inteligente baseado em previsões do tempo.

## 🚀 Funcionalidades

### 📊 Dashboard Inteligente
- Visão geral em tempo real do consumo de energia
- Gráficos interativos de consumo por dispositivo
- Estatísticas de eficiência energética
- Alertas e notificações em tempo real

### 🔌 Gerenciamento de Dispositivos
- Cadastro de dispositivos manuais, Tuya e Smart
- Monitoramento em tempo real do status dos dispositivos
- Controle remoto de dispositivos compatíveis
- Histórico detalhado de consumo por dispositivo

### 📈 Análise de Consumo
- Relatórios detalhados de consumo diário, semanal e mensal
- Tendências de consumo e previsões
- Comparação de eficiência entre dispositivos
- Estimativas de custo baseadas em tarifas locais

### 🌤️ Integração Meteorológica
- Previsões do tempo via API OpenWeather
- Ajuste automático de limites de consumo baseado no clima
- Fatores de irradiação solar para otimização
- Alertas meteorológicos que afetam o consumo

### 🔔 Sistema de Alertas
- Alertas de consumo excessivo
- Notificações de dispositivos offline
- Alertas meteorológicos
- Sistema de severidade configurável

## 🛠️ Tecnologias Utilizadas

### Backend
- **Django 4.2.7** - Framework web principal
- **Django REST Framework** - API REST
- **Django Simple JWT** - Autenticação JWT
- **Celery** - Tarefas assíncronas
- **Redis** - Cache e broker de mensagens
- **SQLite/PostgreSQL** - Banco de dados

### Frontend
- **Bootstrap 5** - Framework CSS
- **Chart.js** - Gráficos interativos
- **Font Awesome** - Ícones
- **JavaScript Vanilla** - Interatividade

### Integrações
- **OpenWeather API** - Dados meteorológicos
- **Tuya API** - Dispositivos inteligentes
- **Requests** - Comunicação HTTP

## 📋 Pré-requisitos

- Python 3.8+
- Redis (para Celery)
- Chave da API OpenWeather (opcional)

## 🚀 Instalação

### 1. Clone o repositório
```bash
git clone <repository-url>
cd energy-manager
```

### 2. Crie um ambiente virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente
```bash
cp env.example .env
# Edite o arquivo .env com suas configurações
```

### 5. Execute as migrações
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Crie um superusuário
```bash
python manage.py createsuperuser
```

### 7. Execute o servidor
```bash
python manage.py runserver
```

## 🔧 Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# Django Settings
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# OpenWeather API
OPENWEATHER_API_KEY=sua-chave-openweather-aqui

# Celery Settings
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Configuração do Redis

Para usar as funcionalidades de cache e tarefas assíncronas:

```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Windows
# Baixe e instale o Redis para Windows
```

### Configuração do Celery

Para executar tarefas em background:

```bash
# Terminal 1 - Servidor Django
python manage.py runserver

# Terminal 2 - Worker Celery
celery -A energy_manager worker --loglevel=info

# Terminal 3 - Beat (agendador de tarefas)
celery -A energy_manager beat --loglevel=info
```

## 📱 Uso da Aplicação

### 1. Acesso à Interface Web
- Abra seu navegador e acesse `http://localhost:8000`
- Faça login com suas credenciais de superusuário

### 2. Dashboard
- Visualize o consumo total em tempo real
- Monitore o status dos dispositivos
- Acompanhe alertas e notificações

### 3. Gerenciamento de Dispositivos
- Adicione novos dispositivos (Manual, Tuya ou Smart)
- Configure limites de consumo
- Monitore o status online/offline

### 4. Análise de Consumo
- Visualize gráficos de consumo por período
- Analise tendências e padrões
- Compare eficiência entre dispositivos

### 5. Integração Meteorológica
- Configure sua localização
- Atualize previsões do tempo
- Ajuste limites baseados no clima

## 🔌 Integração com Dispositivos Tuya

### Configuração
1. Obtenha as credenciais do Tuya IoT Platform
2. Configure o IP local e chave do dispositivo
3. Teste a conexão antes de salvar

### Dispositivos Suportados
- Tomadas inteligentes
- Lâmpadas controláveis
- Dispositivos de monitoramento de energia

## 📊 API REST

### Endpoints Principais

#### Dispositivos
- `GET /api/v1/devices/` - Listar dispositivos
- `POST /api/v1/devices/` - Criar dispositivo
- `GET /api/v1/devices/{id}/` - Detalhes do dispositivo
- `PUT /api/v1/devices/{id}/` - Atualizar dispositivo
- `DELETE /api/v1/devices/{id}/` - Deletar dispositivo

#### Consumo
- `GET /api/v1/readings/` - Leituras de consumo
- `POST /api/v1/readings/` - Registrar leitura
- `GET /api/v1/readings/summary/` - Resumo de consumo
- `GET /api/v1/readings/stats/` - Estatísticas

#### Clima
- `GET /api/v1/forecasts/` - Previsões meteorológicas
- `POST /api/v1/forecasts/fetch_forecast/` - Buscar previsão
- `GET /api/v1/forecasts/summary/` - Resumo meteorológico

#### Alertas
- `GET /api/v1/alerts/` - Listar alertas
- `POST /api/v1/alerts/{id}/mark_as_read/` - Marcar como lido
- `POST /api/v1/alerts/{id}/mark_as_resolved/` - Marcar como resolvido

### Autenticação
O sistema usa JWT (JSON Web Tokens) para autenticação:

```bash
# Obter token
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "seu_usuario", "password": "sua_senha"}'

# Usar token
curl -H "Authorization: Bearer SEU_TOKEN" \
  http://localhost:8000/api/v1/devices/
```

## 🧪 Testes

```bash
# Executar todos os testes
python manage.py test

# Executar testes de uma app específica
python manage.py test devices

# Executar com cobertura
coverage run --source='.' manage.py test
coverage report
```

## 📈 Monitoramento

### Logs
Os logs são salvos em `logs/django.log` e incluem:
- Requisições HTTP
- Erros de aplicação
- Atividades de dispositivos
- Integrações com APIs externas

### Métricas
- Consumo total por período
- Eficiência energética
- Status dos dispositivos
- Alertas ativos

## 🔒 Segurança

### Medidas Implementadas
- Autenticação JWT
- CORS configurado
- Validação de entrada
- Sanitização de dados
- Rate limiting (recomendado para produção)

### Recomendações para Produção
- Use HTTPS
- Configure firewall
- Monitore logs de segurança
- Implemente backup automático
- Use variáveis de ambiente para secrets

## 🚀 Deploy

### Docker (Recomendado)
```bash
# Construir imagem
docker build -t energy-manager .

# Executar container
docker run -p 8000:8000 energy-manager
```

### Deploy Manual
1. Configure servidor web (Nginx/Apache)
2. Configure WSGI (Gunicorn/uWSGI)
3. Configure banco de dados PostgreSQL
4. Configure Redis
5. Configure SSL/HTTPS

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 📞 Suporte

Para suporte e dúvidas:
- Abra uma issue no GitHub
- Consulte a documentação da API
- Verifique os logs de erro

## 🔮 Roadmap

### Próximas Funcionalidades
- [ ] Integração com mais plataformas IoT
- [ ] Machine Learning para previsões
- [ ] App mobile
- [ ] Integração com smart grids
- [ ] Relatórios avançados de sustentabilidade
- [ ] Integração com sistemas de energia solar

---

**Desenvolvido com ❤️ para um futuro mais sustentável**
