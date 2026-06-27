import socket
import threading
import os
import hashlib
from protocolo import (
    ler_ate_delimitador, validar_caminho, listar_arquivos_disponiveis,
    CHUNK_SIZE, CODIFICACAO, DELIMITADOR, CMD_APELIDO, CMD_SAIR, CMD_OK_SAIR,
    CMD_CHAT, CMD_ARQUIVO, CMD_ARQ_NOME, CMD_ARQ_TAM, CMD_HASH, CMD_LISTAR, CMD_LISTA, CMD_ERRO
)

class Servidor:
    def __init__(self, host, port, diretorio):
        self.host = host
        self.port = port
        self.diretorio = diretorio
        self.clientes = {}
        self.clientes_lock = threading.Lock()
        self.clientes_transferencia = set()
        self.transferencia_lock = threading.Lock()
        self.mensagens_pendentes = {}
        self.pendentes_lock = threading.Lock()

    def enviar_mensagem(self, sock, mensagem):
        try:
            sock.sendall(mensagem.encode(CODIFICACAO) + DELIMITADOR)
        except:
            self.remover_cliente(sock)

    def broadcast(self, mensagem, remetente=None):
        with self.clientes_lock:
            sockets = list(self.clientes.keys())
        for s in sockets:
            if s != remetente:
                with self.transferencia_lock:
                    em_transferencia = s in self.clientes_transferencia
                if em_transferencia:
                    self.enfileirar_mensagem_pendente(s, mensagem)
                else:
                    self.enviar_mensagem(s, mensagem)

    def enfileirar_mensagem_pendente(self, sock, mensagem):
        with self.pendentes_lock:
            if sock not in self.mensagens_pendentes:
                self.mensagens_pendentes[sock] = []
            self.mensagens_pendentes[sock].append(mensagem)

    def enviar_mensagens_pendentes(self, sock):
        with self.pendentes_lock:
            if sock in self.mensagens_pendentes:
                for msg in self.mensagens_pendentes[sock]:
                    self.enviar_mensagem(sock, msg)
                del self.mensagens_pendentes[sock]

    def remover_cliente(self, sock):
        with self.clientes_lock:
            self.clientes.pop(sock, None)
        with self.transferencia_lock:
            self.clientes_transferencia.discard(sock)
        with self.pendentes_lock:
            self.mensagens_pendentes.pop(sock, None)
        try:
            sock.close()
        except:
            pass

    def servir_arquivo(self, conn, nome_solicitado):
        with self.transferencia_lock:
            self.clientes_transferencia.add(conn)
        try:
            seguro, caminho_abs = validar_caminho(nome_solicitado, self.diretorio)
            if not seguro:
                conn.sendall(f'{CMD_ERRO}|Caminho invalido\n'.encode(CODIFICACAO))
                return
            if not os.path.isfile(caminho_abs):
                conn.sendall(f'{CMD_ERRO}|Arquivo nao encontrado\n'.encode(CODIFICACAO))
                return
            
            apelido = self.clientes[conn]
            print(f'Servindo arquivo {nome_solicitado} para {apelido}')
            
            tamanho = os.path.getsize(caminho_abs)
            nome_base = os.path.basename(nome_solicitado)
            
            conn.sendall(f'{CMD_ARQ_NOME}|{nome_base}\n'.encode(CODIFICACAO))
            conn.sendall(f'{CMD_ARQ_TAM}|{tamanho}\n'.encode(CODIFICACAO))
            
            sha = hashlib.sha256()
            with open(caminho_abs, 'rb') as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    sha.update(chunk)
                    conn.sendall(chunk)
            
            hash_hex = sha.hexdigest()
            conn.sendall(f'{CMD_HASH}|{hash_hex}\n'.encode(CODIFICACAO))
        finally:
            with self.transferencia_lock:
                self.clientes_transferencia.discard(conn)
            self.enviar_mensagens_pendentes(conn)

    def gerenciar_sessao_cliente(self, conn, addr):
        buffer = b''
        linha, buffer = ler_ate_delimitador(conn, buffer)
        if not linha or not linha.startswith(f'{CMD_APELIDO}|'):
            conn.close()
            return
        apelido = linha.split('|', 1)[1].strip()
        with self.clientes_lock:
            self.clientes[conn] = apelido
        print(f'{apelido} conectou-se ({addr[0]}:{addr[1]})')
        self.broadcast(f'{CMD_CHAT}|servidor:{apelido} entrou no chat', remetente=conn)
        try:
            while True:
                comando, buffer = ler_ate_delimitador(conn, buffer)
                if comando is None:
                    break
                if comando == CMD_SAIR:
                    conn.sendall(f'{CMD_OK_SAIR}\n'.encode(CODIFICACAO))
                    break
                elif comando.startswith(f'{CMD_CHAT}|'):
                    texto = comando.split('|', 1)[1]
                    print(f'Chat de {apelido}: {texto}')
                    self.broadcast(f'{CMD_CHAT}|{apelido}:{texto}', remetente=conn)
                elif comando.startswith(f'{CMD_ARQUIVO}|'):
                    nome = comando.split('|', 1)[1].strip()
                    print(f'{apelido} solicitou arquivo: {nome}')
                    self.servir_arquivo(conn, nome)
                elif comando == CMD_LISTAR:
                    arquivos = listar_arquivos_disponiveis(self.diretorio)
                    conn.sendall(f'{CMD_LISTA}|{",".join(arquivos)}\n'.encode(CODIFICACAO))
                    print(f'{apelido} solicitou listagem de arquivos')
                else:
                    conn.sendall(f'{CMD_ERRO}|Comando desconhecido\n'.encode(CODIFICACAO))
        except Exception as e:
            print(f'Erro com cliente {apelido}: {e}')
        finally:
            print(f'{apelido} desconectou-se')
            self.broadcast(f'{CMD_CHAT}|servidor:{apelido} saiu do chat', remetente=conn)
            self.remover_cliente(conn)

    def executar(self):
        if not os.path.exists(self.diretorio):
            os.makedirs(self.diretorio)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(5)
        print(f'Servidor escutando em {self.host}:{self.port}')
        try:
            while True:
                conn, addr = sock.accept()
                t = threading.Thread(target=self.gerenciar_sessao_cliente, args=(conn, addr), daemon=True)
                t.start()
        except KeyboardInterrupt:
            print('Encerrando servidor...')
        finally:
            sock.close()

if __name__ == '__main__':
    servidor = Servidor(host='0.0.0.0', port=5555, diretorio='./arquivos')
    servidor.executar()