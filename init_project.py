#!/usr/bin/env python
"""
Script para inicializar o projeto Django Energy Manager.
Execute este script após instalar as dependências para configurar o banco de dados.
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

def main():
    """Inicializa o projeto Django."""
    print("🚀 Inicializando Energy Manager...")
    
    # Configurar Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'energy_manager.settings')
    django.setup()
    
    try:
        print("📦 Criando migrações...")
        execute_from_command_line(['manage.py', 'makemigrations'])
        
        print("🗄️ Aplicando migrações...")
        execute_from_command_line(['manage.py', 'migrate'])
        
        print("👤 Criando superusuário...")
        print("Por favor, insira os dados do superusuário:")
        execute_from_command_line(['manage.py', 'createsuperuser'])
        
        print("📊 Carregando dados iniciais...")
        # Aqui você pode adicionar comandos para carregar dados iniciais
        
        print("✅ Projeto inicializado com sucesso!")
        print("\n📋 Próximos passos:")
        print("1. Configure sua chave da API OpenWeather no arquivo .env")
        print("2. Execute: python manage.py runserver")
        print("3. Acesse: http://localhost:8000")
        print("4. Faça login com as credenciais do superusuário")
        
    except Exception as e:
        print(f"❌ Erro durante a inicialização: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
