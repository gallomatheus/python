import os

# Caminho do diretório que contém os arquivos .sql
diretorio = '/home/matheus.gallo/Documentos/PASTA_APOIO_PROCESSOS/Checklist/SDP_CRUZ'

# Iterar sobre todos os arquivos no diretório
for nome_arquivo in os.listdir(diretorio):
    # Verificar se o arquivo termina com '.sql'
    if nome_arquivo.endswith('.sql'):
        caminho_arquivo = os.path.join(diretorio, nome_arquivo)
        
        # Ler o conteúdo do arquivo
        with open(caminho_arquivo, 'r') as arquivo:
            conteudo = arquivo.readlines()
        
        # Adicionar uma linha em branco e 'exit;' na última linha, se não existir
        if not conteudo[-1].strip() == 'exit;':
            # Adicionar uma linha em branco
            conteudo.append('\n')
            # Adicionar 'exit;' na linha seguinte
            conteudo.append('exit;\n')
            
            # Escrever o conteúdo de volta no arquivo
            with open(caminho_arquivo, 'w') as arquivo:
                arquivo.writelines(conteudo)

print("Todos os arquivos .sql foram atualizados com 'exit;' no final")


