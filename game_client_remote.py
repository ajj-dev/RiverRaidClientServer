import pygame
import json
import time
import paramiko
from collections import deque

class RiverRaidClient:
    def __init__(self, vps_host, ssh_key_path, ssh_user='gameserver'):
        print("Connecting To VPS...")
        
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            self.ssh.connect(
                hostname=vps_host,
                username=ssh_user,
                key_filename=ssh_key_path,
                timeout=10
            )
            self.sftp = self.ssh.open_sftp()
            print("Connected to VPS")
        except Exception as e:
            print(f"Connection failed: {e}")
            raise
        
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("River Raid - VPS Edition")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        self.ping_history = deque(maxlen=60)
        
        self.last_good_state = None
        
    def send_input(self, dx, speed, shoot, restart = False):
        start = time.time()
        try:
            data = {
                'dx': dx,
                'speed': speed,
                'shoot': shoot,
                'restart': restart,
                'timestamp': time.time()
            }
            
            # Write to VPS using SFTP
            with self.sftp.open('/tmp/player_input.json', 'w') as f:
                f.write(json.dumps(data))
            
            rtt = (time.time() - start) * 1000
            self.ping_history.append(rtt)
        except Exception as e:
            print(f"Input error: {e}")
    
    def fetch_game_state(self):
        try:
            # Read from VPS using SFTP
            with self.sftp.open('/tmp/game_state.json', 'r') as f:
                data = f.read()
                if data:
                    self.last_good_state = json.loads(data)
                    return self.last_good_state
        except Exception as e:
            # Use cached state on error
            pass
        return self.last_good_state
    
    def render(self, state):
        if state is None:
            pygame.display.flip()
            return
        # River background
        self.screen.fill((20, 120, 200))
        
        if state:
            # River walls (land)
            walls = state.get('river_walls', {'left': 0, 'right': 800})
            pygame.draw.rect(self.screen, (34, 139, 34), (0, 0, int(walls['left']), 600))
            pygame.draw.rect(self.screen, (34, 139, 34), (int(walls['right']), 0, 800 - int(walls['right']), 600))
            
            # Fuel depots
            for depot in state.get('fuel_depots', []):
                pygame.draw.rect(self.screen, (255, 255, 255), (depot['x'] - 25, depot['y'], 50, 80))
                pygame.draw.rect(self.screen, (0, 200, 0), (depot['x'] - 20, depot['y'] + 5, 40, 70))
                f_label = self.font.render('F', True, (255, 255, 255))
                self.screen.blit(f_label, (depot['x'] - 10, depot['y'] + 30))
            
            # Bridges
            for bridge in state.get('bridges', []):
                if bridge['destroyed']:
                    continue
                else:
                    pygame.draw.rect(self.screen, (100, 100, 100), (0, bridge['y'], 800, 20))
                    b_text = self.small_font.render(f"BRIDGE {bridge['id']}", True, (255, 255, 255))
                    self.screen.blit(b_text, (350, bridge['y']))
            
            # Helicopters
            for h in state.get('helicopters', []):
                pygame.draw.ellipse(self.screen, (200, 0, 0), (h['x'] - 15, h['y'] - 12, 30, 25))
                h_label = self.font.render('H', True, (255, 255, 255))
                self.screen.blit(h_label, (h['x'] - 10, h['y'] - 12))

            # Tankers
            for t in state.get('tankers', []):
                pygame.draw.rect(self.screen, (0, 150, 0), (t['x'] - 20, t['y'] - 10, 40, 20))
                b_label = self.font.render('B', True, (255, 255, 255))
                self.screen.blit(b_label, (t['x'] - 10, t['y'] - 10))

            # Jets
            for j in state.get('jets', []):
                pygame.draw.polygon(self.screen, (255, 255, 0), [
                    (j['x'], j['y'] - 12),
                    (j['x'] - 12, j['y'] + 12),
                    (j['x'] + 12, j['y'] + 12)
                ])
                j_label = self.font.render('J', True, (0, 0, 0))
                self.screen.blit(j_label, (j['x'] - 8, j['y'] - 8))
            
            # Bullet
            if state.get('bullet'):
                bullet = state['bullet']
                pygame.draw.rect(self.screen, (255, 255, 0), (bullet['x'] - 2, bullet['y'], 4, 15))
            
            # Player (A)
            p = state['player']
            pygame.draw.polygon(self.screen, (255, 255, 255), [
                (p['x'], p['y'] - 20),
                (p['x'] - 15, p['y'] + 20),
                (p['x'] + 15, p['y'] + 20)
            ])
            a_label = self.font.render('A', True, (255, 0, 0))
            self.screen.blit(a_label, (p['x'] - 10, p['y'] - 5))
            
            # HUD
            lives_text = self.font.render(f"Lives: {p['lives']}", True, (255, 255, 255))
            fuel_bar_width = int(p['fuel'] * 2)
            fuel_color = (0, 255, 0) if p['fuel'] > 30 else (255, 0, 0)
            pygame.draw.rect(self.screen, fuel_color, (10, 50, fuel_bar_width, 20))
            pygame.draw.rect(self.screen, (255, 255, 255), (10, 50, 200, 20), 2)
            fuel_text = self.small_font.render(f"Fuel: {int(p['fuel'])}", True, (255, 255, 255))
            
            score_text = self.font.render(f"Score: {p['score']}", True, (255, 255, 255))
            
            avg_ping = sum(self.ping_history) / len(self.ping_history) if self.ping_history else 0
            ping_text = self.small_font.render(f"Latency: {avg_ping:.1f}ms", True, (255, 255, 0))
            
            self.screen.blit(lives_text, (10, 10))
            self.screen.blit(fuel_text, (220, 52))
            self.screen.blit(score_text, (10, 85))
            self.screen.blit(ping_text, (650, 10))
            
            # Instructions
            controls = self.small_font.render("Arrow Keys: Move | SPACE: Shoot", True, (200, 200, 200))
            self.screen.blit(controls, (250, 570))
            
            if state.get('respawning'):
                respawn_text = self.font.render("RESPAWNING...", True, (255, 255, 0))
                respawn_rect = respawn_text.get_rect(center=(400, 300))
                self.screen.blit(respawn_text, respawn_rect)
                
                lives_remaining = self.font.render(f"Lives: {state['player']['lives']}", True, (255, 255, 255))
                lives_rect = lives_remaining.get_rect(center=(400, 350))
                self.screen.blit(lives_remaining, lives_rect)
            
            if state.get('game_over'):
                go_text = self.font.render("GAME OVER", True, (255, 0, 0))
                final_score = self.font.render(f"Final Score: {p['score']}", True, (255, 255, 255))
                self.screen.blit(go_text, (300, 250))
                self.screen.blit(final_score, (280, 320))
                restart_text = self.small_font.render("Press R to Restart", True, (200, 200, 200))
                restart_rect = restart_text.get_rect(center=(400, 400))
                self.screen.blit(restart_text, restart_rect)
        
        pygame.display.flip()
    
    def run(self):
        running = True
        frame_count = 0
        
        while running:
            frame_count += 1
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            keys = pygame.key.get_pressed()
            
            state = self.fetch_game_state()
            if state and state.get('game_over'):
                restart = keys[pygame.K_r]
                self.send_input(0, 0, False, restart)
                self.render(state)
                continue
            
            # Movement
            dx = 0
            if keys[pygame.K_LEFT]:
                dx = -5
            if keys[pygame.K_RIGHT]:
                dx = 5
                
            # Speed Control
            speed = 0
            if keys[pygame.K_UP]:
                speed = 1
            if keys[pygame.K_DOWN]:
                speed = -1
                
            # Shooting
            shoot = keys[pygame.K_SPACE]
            
            # Send to server (local file)
            self.send_input(dx, speed, shoot, False)
            
            # Fetch state
            state = self.fetch_game_state()
            
            if state is None:
                print(f"Frame {frame_count}: STATE IS NONE!")
            
            # Render
            self.render(state)
            
            self.clock.tick(60)
            
        self.sftp.close()
        self.ssh.close()
        pygame.quit()

if __name__ == '__main__':
    VPS_HOST = '123.45.67.89' # VPS IP Address
    SSH_KEY = 'C:/Users/PcNub/.ssh/id_rsa' # RSA Key Location
    SSH_USER = 'LinuxUser' # Username on VPS
    
    client = RiverRaidClient(VPS_HOST, SSH_KEY, SSH_USER)
    client.run()