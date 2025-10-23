#!/usr/bin/env python
"""
Script de inicialização rápida para o Energy Manager.
"""

import os
import sys
import subprocess
import time

def run_command(command, description):
    """Executa um comando e exibe o resultado."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} concluído!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro em {description}: {e}")
        print(f"Saída: {e.stdout}")
        print(f"Erro: {e.stderr}")
        return False

def main():
    """Função principal de inicialização."""
    print("🚀 Iniciando Energy Manager...")
    print("=" * 50)
    
    # Verificar se estamos no diretório correto
    if not os.path.exists('manage.py'):
        print("❌ Execute este script no diretório raiz do projeto!")
        sys.exit(1)
    
    # 1. Instalar dependências
    print("\n📦 Instalando dependências...")
    if not run_command("pip install -r requirements.txt", "Instalação de dependências"):
        print("❌ Falha na instalação de dependências!")
        sys.exit(1)
    
    # 2. Criar migrações
    print("\n🗄️ Configurando banco de dados...")
    if not run_command("python manage.py makemigrations", "Criação de migrações"):
        print("❌ Falha na criação de migrações!")
        sys.exit(1)
    
    # 3. Aplicar migrações
    if not run_command("python manage.py migrate", "Aplicação de migrações"):
        print("❌ Falha na aplicação de migrações!")
        sys.exit(1)
    
    # 4. Carregar dados iniciais
    print("\n📊 Carregando dados iniciais...")
    if os.path.exists('leituras_sim.csv'):
        if not run_command("python load_initial_data.py", "Carregamento de dados iniciais"):
            print("⚠️ Aviso: Falha ao carregar dados iniciais, mas o sistema funcionará!")
    else:
        print("⚠️ Arquivo leituras_sim.csv não encontrado. Dados iniciais não serão carregados.")
    
    # 5. Criar superusuário (se não existir)
    print("\n👤 Verificando superusuário...")
    try:
        from django.contrib.auth.models import User
        import django
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'energy_manager.settings')
        django.setup()
        
        if not User.objects.filter(is_superuser=True).exists():
            print("Criando superusuário padrão...")
            user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            print("✅ Superusuário criado: admin / admin123")
        else:
            print("✅ Superusuário já existe!")
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível verificar/criar superusuário: {e}")
    
    # 6. Iniciar servidor
    print("\n🌐 Iniciando servidor...")
    print("=" * 50)
    print("✅ Energy Manager configurado com sucesso!")
    print("\n📋 Informações de acesso:")
    print("   🌐 URL: http://localhost:8000")
    print("   👤 Usuário: admin")
    print("   🔑 Senha: admin123")
    print("\n🔧 Para configurar a API do OpenWeather:")
    print("   1. Copie env.example para .env")
    print("   2. Adicione sua chave OPENWEATHER_API_KEY")
    print("\n🚀 Iniciando servidor Django...")
    print("   Pressione Ctrl+C para parar o servidor")
    print("=" * 50)
    
    # Iniciar servidor Django
    try:
        subprocess.run(["python", "manage.py", "runserver"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Servidor parado pelo usuário.")
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")

if __name__ == '__main__':
    main()
