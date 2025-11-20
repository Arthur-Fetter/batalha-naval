from random import randrange
import threading
import socket
import time

class Game:
    def __init__(self, player):
        self.players_ip_list = []
        self.player = player
        self.lock_ip_list = threading.Lock()
        self.running = True

    def addToIPList(self, ip):
        with self.lock_ip_list:
            if ip not in self.lock_ip_list:
                self.players_ip_list.append(ip)

    def removeFromIPList(self, ip):
        with self.lock_ip_list:
            try:
                self.players_ip_list.remove(ip)
            except:
                pass

    def udpListen(self):
        """Thread listening on port 5000"""
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.bind(("", 5000))
        print("[UDP] Ouvindo na porta 5000...")
        
        while self.running:
            try:
                udp.settimeout(1.0)
                msg, client = udp.recvfrom(1024)
                
                message = msg.decode()
                ip = client[0]
                
                print(f"\n[UDP Recebido] {message} de {ip}")
                
                if "Conectando" in message:
                    self.addToIPList(ip)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Erro UDP: {e}")

    def tcpListen(self):
        """Thread listening on port 5001"""
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.bind(("", 5001))
        tcp.listen(5)
        print("[TCP] Ouvindo na porta 5001...")
        
        while self.running:
            try:
                tcp.settimeout(1.0)
                conn, addr = tcp.accept()
                # Treat TCP connection based on messages
                # Right now, connection is just closed
                print(f"\n[TCP] Conexão de {addr}")
                conn.close()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Erro TCP: {e}")

    def gameTimer(self):
        """Thread que controla o tempo de 10s"""
        while self.running:
            time.sleep(10)
            print("\n--- 10 segundos passaram (Rodada de envio liberada) ---")

class GameMap:
    def __init__(self, grid_height, grid_width):
        self.height = grid_height
        self.width = grid_width

class Player:
    def __init__(self, gameMap):
        self.map = gameMap
        self.position = [randrange(gameMap.height), randrange(gameMap.width)]

def main():
    print("hello world!")
    gameMap = GameMap(10, 10)
    player = Player(gameMap)
    game = Game(player)

    t_udp = threading.Thread(target=game.udpListen)
    t_tcp = threading.Thread(target=game.tcpListen)
    t_timer = threading.Thread(target=game.gameTimer)
    
    t_udp.daemon = True
    t_tcp.daemon = True
    t_timer.daemon = True
    
    t_udp.start()
    t_tcp.start()
    t_timer.start()
    
    print("Bem vindo à Batalha Naval P2P!")
    
    try:
        while True:
            cmd = input("Digite um comando (sair, listar): ")
            
            if cmd == "sair":
                game.running
                print("Encerrando...")
                break
            
            elif cmd == "listar":
                with game.lock_ip_list: 
                    print(f"Participantes atuais: {game.players_ip_list}")
 
    except KeyboardInterrupt:
        game.running

if __name__ == "__main__":
    main()
