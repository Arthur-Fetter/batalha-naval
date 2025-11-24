from random import randrange
import threading
import socket
import time
import pygame

class Game:
    def __init__(self, player):
        self.udp_port = 5000
        self.tcp_port = 5001
        self.players_ip_list = []
        self.player = player
        self.lock_ip_list = threading.Lock()
        self.running = True
        self.next_action: dict | None = None
        self.lock_next_action = threading.Lock()
        
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

    def announceConnection(self):
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        try:
            mensagem = "Conectando"
            print(f"[Broadcast] Enviando '{mensagem}' para todos...")
            
            udp.sendto(mensagem.encode(), ("255.255.255.255", self.udp_port))
            
        except Exception as e:
            print(f"Erro ao enviar broadcast: {e}")
        finally:
            udp.close()

    def udpListen(self):
        """Thread listening on port 5000"""
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.bind(("", 5000))
        print(f"[UDP] Ouvindo na porta {self.udp_port}...")
        
        while self.running:
            try:
                udp.settimeout(1.0)
                msg, client = udp.recvfrom(1024)
                
                message = msg.decode()
                ip = client[0]
                
                print(f"\n[UDP Recebido] {message} de {ip}")
                
                if "Conectando" in message:
                    with self.lock_ip_list:
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
    
    def sendTCP(self, message, ip): 
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.settimeout(2)

        try:
            print(f"[TCP] Enviando '{message}' para {ip}...")
            tcp.connect((ip, self.tcp_port))
        
            tcp.sendall(message.encode())
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
        finally:
            tcp.close()

    def sendUDP(self, message): 
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            print(f"[Broadcast] Enviando '{message}' para todos...")
        
            udp.sendto(message.encode(), ("255.255.255.255", self.udp_port))
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
        finally:
            udp.close()

    def updateShipLocation(self, message):
        split_msg = message.split()
        operator = split_msg[1]
        axys = split_msg[2]
        
        x, y = self.player.position
        
        if axys == "X":
            if operator == "+": x += 1
            else: x -= 1
        elif axys == "Y":
            if operator == "+": y += 1
            else: y -= 1
            
        x = max(0, min(9, x))
        y = max(0, min(9, y))
        
        self.player.position = (x, y)

    def gameTimer(self):
        while self.running:
            time.sleep(10)

            with self.lock_next_action:
                acao = self.next_action
                self.next_action = None

            if acao is not None:
                protocolo = acao["protocol"]
                msg = acao["message"]
                target = acao["target_ip"]

                if protocolo == "UDP":
                    print(f"[Timer] Enviando UDP Broadcast: {msg}")
                    self.sendUDP(msg) 

                elif protocolo == "TCP":
                    if target:
                        print(f"[Timer] Enviando TCP para {target}: {msg}")
                        self.sendTCP(msg, target)
                    else:
                        print("[Erro] Ação TCP sem IP alvo definido!")
                if msg.startswith("move"):
                    self.updateShipLocation(msg)
                    print(f"Posição atualizada para: {self.player.position}")

class GameMap:
    def __init__(self, grid_height, grid_width):
        self.height = grid_height
        self.width = grid_width
        # Pygame attributes
        self.screen_height = 700
        self.screen_width = 700
        self.cell_size = 50
        self.bg_color = (30, 30, 30)
        self.grid_color = (200, 200, 200)
        self.ship_color = (0, 255, 0)
        self.bullet_color = (255, 0, 0)

    def drawGrid(self, screen):
        for x in range(0, 10):
            for y in range(0, 10):
                rect = pygame.Rect(x * self.cell_size + 50, y * self.cell_size + 50, self.cell_size, self.cell_size)
                pygame.draw.rect(screen, self.grid_color, rect, 1)

    def drawShip(self, screen, x, y):
        rect = pygame.Rect(x * self.cell_size + 50, y * self.cell_size + 50, self.cell_size, self.cell_size)
        pygame.draw.rect(screen, self.ship_color, rect)

    def desenhar_tiro(self, screen, x, y):
        center_x = x * self.cell_size + 50 + self.cell_size // 2
        center_y = y * self.cell_size + 50 + self.cell_size // 2
        pygame.draw.circle(screen, self.bullet_color, (center_x, center_y), 10)


class Player:
    def __init__(self, gameMap):
        self.map = gameMap
        self.position = [randrange(gameMap.height), randrange(gameMap.width)]

def main():
    gameMap = GameMap(10, 10)
    player = Player(gameMap)
    game = Game(player)

    pygame.init()
    screen = pygame.display.set_mode((gameMap.screen_width, gameMap.screen_height))
    pygame.display.set_caption("Batalha Naval P2P")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    t_udp = threading.Thread(target=game.udpListen)
    t_tcp = threading.Thread(target=game.tcpListen)
    t_timer = threading.Thread(target=game.gameTimer)
    
    t_udp.daemon = True
    t_tcp.daemon = True
    t_timer.daemon = True
    
    t_udp.start()
    t_tcp.start()
    t_timer.start()

    game.announceConnection()
 
    while game.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False
                # Enviar mensagem de saída UDP aqui...
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                gx = (mx - 50) // gameMap.cell_size
                gy = (my - 50) // gameMap.cell_size
                
                if 0 <= gx < 10 and 0 <= gy < 10:
                    print(f"Clique na célula: {gx}, {gy}")
                    nova_acao = None

                    if event.button == 3:
                        with game.lock_next_action:
                            if game.next_action is None:
                                game.next_action = {
                                    "protocol": "UDP",
                                    "message": f"shot:{gx} {gy}",
                                    "target_ip": None
                                }
                            else:
                               print("Aguarde o timer...")
                    elif event.button == 1:
                        navio_x, navio_y = game.player.position[0], game.player.position[1]
                        
                        dx = gx - navio_x
                        dy = gy - navio_y
                        
                        print(f"[Input] Clique Esquerdo em ({gx}, {gy}). Delta: ({dx}, {dy})")

                        direcao = None
                        
                        if abs(dx) + abs(dy) != 1:
                            print("Movimento Inválido! Clique apenas numa casa adjacente (Cima/Baixo/Esq/Dir).")
                        else:
                            if dx == 1:
                                direcao = "+ X"
                            elif dx == -1:
                                direcao = "- X"
                            elif dy == 1:
                                direcao = "+ Y"
                            elif dy == -1:
                                direcao = "- Y"
                            
                            if direcao:
                                nova_acao = {
                                    "protocol": "UDP",
                                    "message": f"move {direcao}",
                                    "target_ip": None
                                }
                                print(f"updated players position to: {game.player.position[0]}, {game.player.position[1]}")
                        if nova_acao:
                            with game.lock_next_action:
                                if game.next_action is None:
                                    game.next_action = nova_acao
                                    print(f">> Ação agendada: {nova_acao['message']}")
                                else:
                                    game.next_action = nova_acao 
                                    print(f">> Ação ATUALIZADA para: {nova_acao['message']}")

        screen.fill(gameMap.bg_color)
        
        gameMap.drawGrid(screen)
        
        # Desenhar estado do jogo (com Lock para segurança)
        # with lock:
        gameMap.drawShip(screen, game.player.position[0], game.player.position[1])
        #    for tiro in tiros_recebidos:
        #        desenhar_tiro(screen, tiro[0], tiro[1])
        
        texto_status = font.render("Status: Aguardando Timer...", True, (255, 255, 255))
        screen.blit(texto_status, (10, 600))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
   
if __name__ == "__main__":
    main()
