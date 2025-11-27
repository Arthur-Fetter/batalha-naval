from random import randrange
import threading
import socket
import time
import pygame

class utils:
    def getMyIP(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            IP = s.getsockname()[0]
        except:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

class Game:
    def __init__(self, player):
        self.utils = utils()
        self.my_ip = self.utils.getMyIP()
        self.udp_port = 5000
        self.tcp_port = 5001
        self.players_ip_list = []
        self.player = player
        self.lock_ip_list = threading.Lock()
        self.running = True
        self.next_action: dict | None = None
        self.lock_next_action = threading.Lock()
        self.animations = []
        self.lock_animations = threading.Lock()
        self.score = {'shot': 0, 'hit': 0}
        self.lock_score = threading.Lock()
        self.game_logs = []
        self.lock_game_logs = threading.Lock()

    def addToIPList(self, ip):
        with self.lock_ip_list:
            if ip not in self.players_ip_list:
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
        udp.bind(("0.0.0.0", 5000))
        print(f"[UDP] Ouvindo na porta {self.udp_port}...")
        
        while self.running:
            try:
                udp.settimeout(1.0)
                msg, client = udp.recvfrom(1024)
                
                message = msg.decode()
                client_ip = client[0]

                if client_ip == self.my_ip:
                    continue
                
                print(f"\n[UDP] Recebido {message} de {client_ip}")
                
                if "Conectando" in message:
                    print("[CONECTANDO]")
                    self.addToIPList(client_ip)
                    with self.lock_ip_list:
                        lista_str = str(self.players_ip_list)

                    msg_resposta = f"participantes:{lista_str}"
                    self.sendTCP(msg_resposta, client_ip)
                    self.addLog(f"Novo jogador detectado: {client_ip}")

                elif message.startswith("saindo"):
                    self.addLog(f"Jogador saindo da partida: {client_ip}")
                    self.players_ip_list.remove(client_ip)

                elif message.startswith("shot:"):
                    coords = message.split(":")[1].split(",")
                    gx, gy = int(coords[0]), int(coords[1])
                    
                    hit = ((gx, gy) == (self.player.position[0], self.player.position[1]))
                    tipo_visual = 'agua'
                    
                    if hit:
                        print(f"[COMBATE] Fui atingido por {client_ip} em ({gx},{gy})!")
                        self.addLog(f"ALERTA: Você foi atingido por {client_ip}!")
                        tipo_visual = 'acerto'
                        
                        with self.lock_score:
                            self.score['shot'] += 1
                        
                        self.sendTCP("hit", client_ip) 
                    
                    with self.lock_animations:
                        self.animations.append({
                            'grid_x': gx,
                            'grid_y': gy,
                            'vida': 30, 
                            'tipo': tipo_visual
                        })
                elif message.startswith("move"):
                    self.addLog(f"O inimigo {client_ip} se moveu!")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[UDP] Erro UDP: {e}")
                import traceback
                traceback.print_exc()

    def tcpListen(self):
        """Thread listening on port 5001"""
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.bind(("0.0.0.0", 5001))
        tcp.listen(5)
        print("[TCP] Ouvindo na porta 5001...")
        
        while self.running:
            try:
                tcp.settimeout(1.0)
                conn, addr = tcp.accept()

                with conn:
                    data = conn.recv(4096)
                    msg = data.decode()
                    print(f"[TCP] Recebido de {addr[0]}: {msg}")

                    if msg.startswith("scout:"):
                        coords = msg.split(":")[1].split(",")
                        scout_x, scout_y = int(coords[0]), int(coords[1])
                        
                        my_x, my_y = self.player.position
                        
                        if (scout_x, scout_y) == (my_x, my_y):
                            print("[TCP] Scout descobriu meu navio!")
                            conn.sendall(b"hit")
                        else:
                            dx = 1 if my_x > scout_x else (-1 if my_x < scout_x else 0)
                            dy = 1 if my_y > scout_y else (-1 if my_y < scout_y else 0)
                            
                            response = f"info:{dx},{dy}"
                            print(f"[TCP] Respondendo scout com dica: {response}")
                            conn.sendall(response.encode())
                    elif msg.startswith("participantes:"):
                        str_list = msg.split(":", 1)[1] 
                        
                        limpo = str_list.replace("[","").replace("]","").replace("'","").replace(" ","")
                        ips = limpo.split(",")
                        
                        for ip in ips:
                            if ip and ip != self.my_ip:
                                self.addToIPList(ip)
                                    
                    elif msg == "hit":
                        print("[TCP] Confirmação de acerto recebida!")
                        with self.lock_score:
                            self.score['hit'] += 1
                print(f"\n[TCP] Conexão de {addr}")
                conn.close()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Erro TCP: {e}")
    
    def sendTCP(self, message, ip, await_response=False):
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.settimeout(2)

        try:
            print(f"[TCP] Enviando '{message}' para {ip}...")
            tcp.connect((ip, self.tcp_port))
            tcp.sendall(message.encode())

            if await_response:
                data = tcp.recv(1024) 
                resposta = data.decode()
                print(f"[TCP] Resposta recebida: {resposta}")

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
            print(f"[UDP] Erro ao enviar mensagem: {e}")
        finally:
            udp.close()

    def addLog(self, texto):
        with self.lock_game_logs:
            import datetime
            hora = datetime.datetime.now().strftime("%H:%M:%S")
            mensagem_formatada = f"[{hora}] {texto}"
            
            self.game_logs.append(mensagem_formatada)
            
            if len(self.game_logs) > 5:
                self.game_logs.pop(0)

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

                msg_rede = msg
                if msg_rede.startswith("move"):
                    msg_rede = "moved"

                if protocolo == "UDP":
                    print(f"[Timer] Enviando UDP Broadcast: {msg_rede}")
                    self.sendUDP(msg_rede)

                elif protocolo == "TCP":
                    is_scout = msg_rede.startswith("scout")
                    
                    response = self.sendTCP(msg_rede, target, await_response=is_scout)
                    
                    if is_scout and response:
                        if response == "hit":
                            self.addLog(f"SCOUT SUCESSO! Inimigo encontrado em {target}")
                        
                        elif response.startswith("info:"):
                            data = response.split(":")[1].split(",")
                            dx, dy = int(data[0]), int(data[1])
                            
                            coord_x = "Direita" if dx == 1 else ("Esquerda" if dx == -1 else "Mesmo X")
                            coord_y = "Baixo" if dy == 1 else ("Cima" if dy == -1 else "Mesmo Y")
                            
                            self.addLog(f"SCOUT ({target}): O navio está para {coord_x} e {coord_y}")
                    if target:
                        print(f"[Timer] Enviando TCP para {target}: {msg_rede}")
                        self.sendTCP(msg_rede, target)
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

    game.sendUDP("Conectando")
 
    while game.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False
                game.sendUDP("saindo")
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                gx = (mx - 50) // gameMap.cell_size
                gy = (my - 50) // gameMap.cell_size
                
                if 0 <= gx < 10 and 0 <= gy < 10:
                    print(f"[Game loop] Clique na célula: {gx}, {gy}")
                    nova_acao = None

                    if event.button == 3:
                        with game.lock_next_action:
                            print(f"next action: {game.next_action}")
                            if game.next_action is None:
                                nova_acao = {
                                    "protocol": "UDP",
                                    "message": f"shot:{gx},{gy}",
                                    "target_ip": None
                                }
                            else:
                               print("[Game loop] Aguarde o timer...")
                               game.addLog("Aguarde o timer...")
                    elif event.button == 1:
                        keys = pygame.key.get_pressed()
                        is_shift_pressed = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
                        
                        if is_shift_pressed:
                            target_ip = None
                            with game.lock_ip_list:
                                if len(game.players_ip_list) > 0:
                                    target_ip = game.players_ip_list[0] 
                            
                            if target_ip:
                                print(f"[Input] SCOUT (TCP) agendado em {gx},{gy}")
                                nova_acao = {
                                    "protocol": "TCP",
                                    "message": f"scout:{gx},{gy}",
                                    "target_ip": target_ip
                                }
                            else:
                                game.addLog("Erro: Ninguém na lista para sondar.")
                        else:
                            navio_x, navio_y = game.player.position[0], game.player.position[1]
                            
                            dx = gx - navio_x
                            dy = gy - navio_y
                            
                            print(f"[Game loop] Clique Esquerdo em ({gx}, {gy}). Delta: ({dx}, {dy})")

                            direcao = None
                            
                            if abs(dx) + abs(dy) != 1:
                                print("[Game loop] Movimento Inválido! Clique apenas numa casa adjacente (Cima/Baixo/Esq/Dir).")
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

                    if nova_acao:
                        with game.lock_next_action:
                            print("got to assigning nova acao")
                            if game.next_action is None:
                                game.next_action = nova_acao
                                game.addLog(f"Ação agendada: {nova_acao['message']}")
                                print(f"[Game loop] >> Ação agendada: {nova_acao['message']}")
                            else:
                                game.next_action = nova_acao 
                                game.addLog(f"Ação ATUALIZADA para: {nova_acao['message']}")
                                print(f"[Game loop] >> Ação ATUALIZADA para: {nova_acao['message']}")

        screen.fill(gameMap.bg_color)
        
        gameMap.drawGrid(screen)
        
        gameMap.drawShip(screen, game.player.position[0], game.player.position[1])

        with game.lock_animations:
            animacoes_restantes = []

            for anim in game.animations:
                anim['vida'] -= 1

                if anim['vida'] > 0:
                    animacoes_restantes.append(anim)

                    px = 50 + (anim['grid_x'] * 50) + 25
                    py = 50 + (anim['grid_y'] * 50) + 25

                    if anim['tipo'] == 'acerto':
                        raio = int(anim['vida'] * 0.8) 
                        pygame.draw.circle(screen, (255, 0, 0), (px, py), raio)
                        
                        pygame.draw.circle(screen, (255, 255, 0), (px, py), raio // 2)

                    elif anim['tipo'] == 'agua':
                        raio = 15
                        pygame.draw.circle(screen, (100, 100, 255), (px, py), raio)

            game.animations = animacoes_restantes

        log_pos = 600
        with game.lock_game_logs:
            for mensagem in game.game_logs:
                texto_img = font.render(mensagem, True, (255, 255, 255))
                screen.blit(texto_img, (20, log_pos))
                log_pos += 20

        pygame.display.flip()
        clock.tick(30)
    screen.fill((0, 0, 0))
    
    big_font = pygame.font.SysFont(None, 60)
    medium_font = pygame.font.SysFont(None, 40)

    txt_titulo = big_font.render("FIM DE JOGO", True, (255, 0, 0))
    txt_placar = medium_font.render(f"Acertos: {game.score['hit']} | Recebidos: {game.score['shot']}", True, (255, 255, 255))
    txt_final = big_font.render(f"SCORE: {game.score['hit'] - game.score['shot']}", True, (0, 255, 0))

    screen.blit(txt_titulo, (gameMap.screen_width//2 - 140, 200))
    screen.blit(txt_placar, (gameMap.screen_width//2 - 180, 300))
    screen.blit(txt_final,  (gameMap.screen_width//2 - 100, 400))

    pygame.display.flip()

    print("Exibindo placar por 5 segundos...")
    time.sleep(5)
    pygame.quit()
   
if __name__ == "__main__":
    main()
