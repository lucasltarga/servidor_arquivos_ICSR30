import socket
import threading
import hashlib
from protocolo import (
    ler_ate_delimitador, CHUNK_SIZE, CODIFICACAO, CMD_APELIDO, CMD_SAIR, CMD_OK_SAIR,
    CMD_CHAT, CMD_ARQUIVO, CMD_ARQ_NOME, CMD_ARQ_TAM, CMD_HASH, CMD_LISTAR, CMD_LISTA, CMD_ERRO
)

class Cliente:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.apelido = ''
        self.rodando = True
        self.buffer_recv = b''
        self.nome_arquivo_atual = None

    def baixar_arquivo_e_validar(self, tamanho, nome_arquivo):
        sha = hashlib.sha256()
        restante = tamanho
        with open(nome_arquivo, 'wb') as f:
            while restante > 0:
                leitura = min(CHUNK_SIZE, restante)
                try:
                    chunk = self.sock.recv(leitura)
                except:
                    print('Erro na recepcao do arquivo')
                    return
                if not chunk:
                    print('Conexao perdida durante transferencia')
                    return
                f.write(chunk)
                sha.update(chunk)
                restante -= len(chunk)
        hash_local = sha.hexdigest()
        linha, self.buffer_recv = ler_ate_delimitador(self.sock, self.buffer_recv)
        if not linha or not linha.startswith(f'{CMD_HASH}|'):
            print('Erro: metadado HASH ausente')
            return
        hash_servidor = linha.split('|', 1)[1].strip()
        if hash_local == hash_servidor:
            print(f'Arquivo salvo como {nome_arquivo} - Integridade OK')
        else:
            print('FALHA NA INTEGRIDADE! Hashes diferentes.')
            print(f'Local : {hash_local}')
            print(f'Serv  : {hash_servidor}')

    def exibir_chat(self, linha):
        partes = linha.split('|', 1)[1]
        print(f'\n[CHAT] {partes}')

    def exibir_lista_arquivos(self, linha):
        arquivos = linha.split('|', 1)[1]
        if arquivos:
            lista = arquivos.split(',')
            print('\nArquivos disponiveis no servidor:')
            for arq in lista:
                print(f'  {arq}')
        else:
            print('\nNenhum arquivo disponivel no servidor.')

    def exibir_erro(self, linha):
        msg = linha.split('|', 1)[1]
        print(f'Erro do servidor: {msg}')

    def tratar_comando_recebido(self, linha):
        if linha.startswith(f'{CMD_CHAT}|'):
            self.exibir_chat(linha)
        elif linha.startswith(f'{CMD_ARQ_NOME}|'):
            self.nome_arquivo_atual = linha.split('|', 1)[1]
        elif linha.startswith(f'{CMD_ARQ_TAM}|'):
            tamanho = int(linha.split('|', 1)[1])
            nome = self.nome_arquivo_atual if self.nome_arquivo_atual else 'arquivo_recebido.bin'
            self.baixar_arquivo_e_validar(tamanho, nome)
            self.nome_arquivo_atual = None
        elif linha.startswith(f'{CMD_LISTA}|'):
            self.exibir_lista_arquivos(linha)
        elif linha.startswith(f'{CMD_ERRO}|'):
            self.exibir_erro(linha)
        elif linha == CMD_OK_SAIR:
            self.rodando = False
            print('Desconectado com sucesso.')

    def escutar_servidor(self):
        while self.rodando:
            linha, self.buffer_recv = ler_ate_delimitador(self.sock, self.buffer_recv)
            if linha is None:
                if self.rodando:
                    print('Conexao encerrada pelo servidor.')
                    self.rodando = False
                break
            self.tratar_comando_recebido(linha)

    def executar(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.apelido = input('Apelido: ').strip()
        self.sock.sendall(f'{CMD_APELIDO}|{self.apelido}\n'.encode(CODIFICACAO))
        t = threading.Thread(target=self.escutar_servidor, daemon=True)
        t.start()
        while self.rodando:
            print('\n1 - Sair')
            print('2 - Solicitar Arquivo')
            print('3 - Chat')
            opcao = input('Opcao: ').strip()
            if not self.rodando:
                break
            if opcao == '1':
                self.sock.sendall(f'{CMD_SAIR}\n'.encode(CODIFICACAO))
                break
            elif opcao == '2':
                arquivo = input('Nome do arquivo (vazio para listar): ').strip()
                if arquivo:
                    self.sock.sendall(f'{CMD_ARQUIVO}|{arquivo}\n'.encode(CODIFICACAO))
                else:
                    self.sock.sendall(f'{CMD_LISTAR}\n'.encode(CODIFICACAO))
            elif opcao == '3':
                texto = input('Mensagem: ').strip()
                if texto:
                    self.sock.sendall(f'{CMD_CHAT}|{texto}\n'.encode(CODIFICACAO))
            else:
                print('Opcao invalida.')
        self.rodando = False
        try:
            self.sock.close()
        except:
            pass

if __name__ == '__main__':
    cliente = Cliente(host='127.0.0.1', port=5555)
    cliente.executar()