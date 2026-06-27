import os

CHUNK_SIZE = 4096
CODIFICACAO = 'utf-8'
DELIMITADOR = b'\n'

CMD_APELIDO = 'APELIDO'
CMD_SAIR = 'SAIR'
CMD_OK_SAIR = 'OK_SAIR'
CMD_CHAT = 'CHAT'
CMD_ARQUIVO = 'ARQUIVO'
CMD_ARQ_NOME = 'ARQ_NOME'
CMD_ARQ_TAM = 'ARQ_TAM'
CMD_HASH = 'HASH'
CMD_LISTAR = 'LISTAR'
CMD_LISTA = 'LISTA'
CMD_ERRO = 'ERRO'

def ler_ate_delimitador(sock, buffer):
    while DELIMITADOR not in buffer:
        try:
            dados = sock.recv(CHUNK_SIZE)
        except:
            return None, buffer
        if not dados:
            return None, buffer
        buffer += dados
    linha_bytes, restante = buffer.split(DELIMITADOR, 1)
    return linha_bytes.decode(CODIFICACAO), restante

def validar_caminho(nome_solicitado, diretorio_base):
    base_dir = os.path.abspath(diretorio_base)
    caminho_abs = os.path.abspath(os.path.join(base_dir, nome_solicitado))
    if os.path.commonpath([caminho_abs, base_dir]) != base_dir:
        return False, None
    return True, caminho_abs

def listar_arquivos_disponiveis(diretorio_base):
    return [f for f in os.listdir(diretorio_base) if os.path.isfile(os.path.join(diretorio_base, f))]