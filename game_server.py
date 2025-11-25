import os
import platform
import threading
import json
import time
import random
from dataclasses import dataclass, asdict
from typing import List, Optional

# File paths
if platform.system() == 'Windows':
    GAME_STATE_PATH = 'game_state.json'
    PLAYER_INPUT_PATH = 'player_input.json'
else:
    GAME_STATE_PATH = '/tmp/game_state.json'
    PLAYER_INPUT_PATH = '/tmp/player_input.json'

@dataclass
class Entity:
    x: float
    y: float
    width: float = 30
    height: float = 30
    alive: bool = True
    
    def collides_with(self, other: 'Entity') -> bool:
        return (abs(self.x - other.x) < (self.width + other.width) / 2 and 
                abs(self.y - other.y) < (self.height + other.height) / 2)

@dataclass
class Bullet(Entity):
    width: float = 5
    height: float = 15
    speed: float = -10
    
    def update(self, scroll_speed):
        self.y += self.speed
        self.y += scroll_speed
        
        if self.y < -20 or self.y > 620:
            self.alive = False

@dataclass
class Player(Entity):
    width: float = 30
    height: float = 40
    x: float = 400
    y: float = 520
    fuel: float = 100.0
    lives: int = 3
    score: int = 0
    invincible_timer: float = 0
    
    def move(self, dx):
        self.x += dx
        self.x = max(15, min(785, self.x))

@dataclass  
class Helicopter(Entity):
    width: float = 30
    height: float = 25
    points: int = 60
    vx: float = 0
    activated: bool = False
    activation_distance: float = 300
    
    def update(self, scroll_speed, player_y, bridge_count):
        self.y += scroll_speed
        
        if bridge_count >= 1 and not self.activated:
            if abs(self.y - player_y) < self.activation_distance:
                self.activated = True
                self.vx = random.choice([-1.5, 1.5])
                
        if self.activated:
            self.x += self.vx

@dataclass
class Tanker(Entity):
    width: float = 40
    height: float = 20  
    points: int = 30
    vx: float = 0
    activated: bool = False
    activation_distance: float = 250
    
    def update(self, scroll_speed, player_y, bridge_count):
        self.y += scroll_speed
        
        if bridge_count >= 1 and not self.activated:
            if abs(self.y - player_y) < self.activation_distance:
                self.activated = True
                self.vx = random.choice([-1, 1])
                
        if self.activated:
            self.x += self.vx

@dataclass
class Jet(Entity):
    width: float = 25
    height: float = 25 
    points: int = 100
    vx: float = 3
    direction: int = 1
    
    def update(self, scroll_speed, player_y, bridge_count):
        self.y += scroll_speed
        
        self.x += self.vx * self.direction
        
        if self.x > 820:
            self.direction = -1
        elif self.x < -20:
            self.direction = 1

@dataclass
class FuelDepot(Entity):
    width: float = 50
    height: float = 80
    points_if_destroyed: int = 80
    refuel_rate: float = 30.0 
    
    def update(self, scroll_speed):
        self.y += scroll_speed

@dataclass
class Bridge(Entity):
    width: float = 800
    height: float = 20
    points: int = 500
    destroyed: bool = False
    bridge_id: int = 0
    
    def update(self, scroll_speed):
        self.y += scroll_speed

class RiverSegment:
    def __init__(self, y_start: float, width: int, center_x: float):
        self.y_start = y_start
        self.width = width 
        self.center_x = center_x
        
    def get_walls_at_y(self, y: float):
        left_wall = self.center_x - self.width / 2
        right_wall = self.center_x + self.width / 2
        return (left_wall, right_wall)

class GameServer:
    def __init__(self):
        self.state_lock = threading.Lock()
        
        self.respawning = False
        self.respawn_timer = 0
        
        # Player 
        self.player = Player()
        
        # Bullet 
        self.bullet: Optional[Bullet] = None
        
        # River terrain
        self.river_scroll_speed = 2  
        self.river_y_offset = 0 
        self.river_segments: List[RiverSegment] = []
        self._generate_initial_river()
        
        # Enemies
        self.helicopters: List[Helicopter] = [
            Helicopter(x=random.randint(200, 600), y=-100)
        ]
        self.tankers: List[Tanker] = [
            Tanker(x=random.randint(200, 600), y=-200)
        ]
        self.jets: List[Jet] = []
        
        self.max_helicopters = 2
        self.max_tankers = 2
        self.max_jets = 1
        
        # Fuel depots
        self.fuel_depots: List[FuelDepot] = [
            FuelDepot(x=400, y=-400),
            FuelDepot(x=350, y=-800),
        ]
        
        # Bridges
        self.bridges: List[Bridge] = []
        self.bridge_counter = 0
        self.last_checkpoint_bridge_id = -1
        self._spawn_bridge()
        
        # Game state
        self.game_over = False
        self.pending_input = {'dx': 0, 'shoot': False}
        
    def _generate_initial_river(self):
        for i in range(20): 
            width = 325 
            center = 400 
            segment = RiverSegment(
                y_start = i * 100,
                width = width,
                center_x = center
            )
            self.river_segments.append(segment)
    
    def _spawn_bridge(self):
        self.bridge_counter += 1
        bridge = Bridge(
            x=400,
            y=-1000 * self.bridge_counter,
            bridge_id=self.bridge_counter
        )
        self.bridges.append(bridge)
    
    def thread_H_helicopter(self):
        print("[Thread H] Helicopter started")
        while True:
            with self.state_lock:
                if not self.respawning and not self.game_over:
                    if len(self.helicopters) < self.max_helicopters:
                        if random.random() < 0.01:  
                            self._spawn_enemy("helicopter")
            time.sleep(0.016)
    
    def thread_J_jet(self):
        print("[Thread J] Jet started")
        while True:
            with self.state_lock:
                if not self.respawning and not self.game_over:
                    if len(self.jets) < self.max_jets:
                        if random.random() < 0.005:
                            self._spawn_enemy("jet")
            time.sleep(0.016)
    
    def thread_B_tanker(self):
        print("[Thread B] Tanker started")
        while True:
            with self.state_lock:
                if not self.respawning and not self.game_over:
                    if len(self.tankers) < self.max_tankers:
                        if random.random() < 0.01:  
                            self._spawn_enemy("tanker")
            time.sleep(0.016)
    
    def _spawn_enemy(self, enemy_type):
        x = random.randint(250, 500)
        y = -random.randint(200, 500)
        
        if enemy_type == "helicopter" and len(self.helicopters) < self.max_helicopters:
            self.helicopters.append(Helicopter(x=x, y=y))
        elif enemy_type == "tanker" and len(self.tankers) < self.max_tankers:
            self.tankers.append(Tanker(x=x, y=y))
        elif enemy_type == "jet" and len(self.jets) < self.max_jets:
            # Jet spawns from side, not top
            side = random.choice([-50, 850])
            direction = 1 if side < 0 else -1
            self.jets.append(Jet(x=side, y=random.randint(100, 300), vx=3, direction=direction))
    
    def game_tick(self):
        print("[Game Tick] Started")
        while True:
            while not self.game_over:
                with self.state_lock:
                    if self.respawning:
                        self.respawn_timer -= 0.016
                        if self.respawn_timer <= 0:
                            self.respawning = False
                            print("Respawn Complete")
                        else:
                            time.sleep(0.016)
                            continue
                    
                    # Check invincibility timer
                    if self.player.invincible_timer > 0:
                        self.player.invincible_timer -= 0.016
                    
                    # Apply client input
                    if self.pending_input:
                        dx = self.pending_input.get('dx', 0)
                        self.player.move(dx)
                        
                        speed_change = self.pending_input.get('speed', 0)
                        
                        if speed_change > 0:
                            self.river_scroll_speed = min(3, self.river_scroll_speed + 0.1)
                        elif speed_change < 0:
                            self.river_scroll_speed = max(1, self.river_scroll_speed - 0.1)
                        else:  
                            default_speed = 2.0
                            lerp_factor = 0.1 
                            
                            self.river_scroll_speed += (default_speed - self.river_scroll_speed) * lerp_factor
                            
                            if abs(self.river_scroll_speed - default_speed) < 0.01:
                                self.river_scroll_speed = default_speed
                        
                        # Handle shooting
                        if self.pending_input.get('shoot', False) and self.bullet is None:
                            self.bullet = Bullet(x=self.player.x, y=self.player.y - 20)
                    
                    # Update bullet
                    if self.bullet:
                        self.bullet.update(self.river_scroll_speed)
                        if not self.bullet.alive:
                            self.bullet = None
                    
                    # Scroll river
                    self.river_y_offset += self.river_scroll_speed
                    
                    # Fuel consumption
                    self.player.fuel -= 0.06
                    if self.player.fuel <= 0:
                        self._handle_death("Out of fuel")
                    
                    # Get river boundaries (used multiple times below)
                    river_position = self.river_y_offset
                    segment_index = int(river_position / 100) % len(self.river_segments)
                    current_segment = self.river_segments[segment_index]
                    left_wall, right_wall = current_segment.get_walls_at_y(self.player.y)
                    
                    # Check wall collision
                    if self.player.invincible_timer <= 0:
                        if self.player.x - self.player.width/2 < left_wall or \
                        self.player.x + self.player.width/2 > right_wall:
                            self._handle_death("Hit riverbank")
                    
                    # Update helicopters
                    for heli in self.helicopters[:]:
                        heli.update(self.river_scroll_speed, self.player.y, self.last_checkpoint_bridge_id + 1)
                        
                        if heli.activated:
                            if heli.x < left_wall + 30 or heli.x > right_wall - 30:
                                heli.vx *= -1
                        
                        if heli.y > 650:
                            self.helicopters.remove(heli)
                    
                    # Update tankers
                    for tank in self.tankers[:]:
                        tank.update(self.river_scroll_speed, self.player.y, self.last_checkpoint_bridge_id + 1)
                        
                        if tank.activated:
                            if tank.x < left_wall + 40 or tank.x > right_wall - 40:
                                tank.vx *= -1
                        
                        if tank.y > 650:
                            self.tankers.remove(tank)
                    
                    # Update jets (fly across entire screen, ignore walls)
                    for jet in self.jets[:]:
                        jet.update(self.river_scroll_speed, self.player.y, self.last_checkpoint_bridge_id + 1)
                        
                        # Remove if scrolled off bottom
                        if jet.y > 650:
                            self.jets.remove(jet)
                    
                    # Fuel depot collision
                    for depot in [d for d in self.fuel_depots if d.alive]:
                        depot.update(self.river_scroll_speed)
                        
                        if self.player.collides_with(depot):
                            self.player.fuel = min(100, self.player.fuel + depot.refuel_rate * 0.016)
                        
                        if self.bullet and self.bullet.collides_with(depot):
                            self.player.score += depot.points_if_destroyed
                            self.bullet = None
                            depot.y = -random.randint(300, 600)
                        
                        if depot.y > 650:
                            depot.y = -random.randint(300, 600)
                            depot.x = random.randint(280, 520)
                    
                    # Bridge collision
                    for bridge in [b for b in self.bridges if b.alive]:
                        bridge.update(self.river_scroll_speed)
                        
                        if self.bullet and self.bullet.collides_with(bridge):
                            self.player.score += bridge.points
                            bridge.destroyed = True
                            bridge.alive = False
                            self.bullet = None
                            self.last_checkpoint_bridge_id = bridge.bridge_id
                            print(f"Bridge {bridge.bridge_id} destroyed. Checkpoint saved.")
                            self._spawn_bridge()
                        
                        if not bridge.destroyed and self.player.invincible_timer <= 0:
                            if self.player.collides_with(bridge):
                                self._handle_death("Hit bridge")
                    
                    # Enemy collisions
                    all_enemies = self.helicopters + self.tankers + self.jets
                    
                    for enemy in all_enemies:
                        # Bullet destroys enemy
                        if self.bullet and self.bullet.collides_with(enemy):
                            self.player.score += enemy.points
                            self.bullet = None
                            
                            # Remove enemy from list
                            if isinstance(enemy, Helicopter):
                                self.helicopters.remove(enemy)
                            elif isinstance(enemy, Tanker):
                                self.tankers.remove(enemy)
                            elif isinstance(enemy, Jet):
                                self.jets.remove(enemy)
                        
                        # Player collision
                        if self.player.invincible_timer <= 0:
                            if self.player.collides_with(enemy):
                                self._handle_death(f"Hit {enemy.__class__.__name__}")
                                self.player.invincible_timer = 2.0
                                break
                    
                    # Check game over (AFTER all collisions)
                    if self.player.lives <= 0:
                        self.game_over = True
                        print("=== GAME OVER ===")
                        break
                
                time.sleep(0.016)  # Outside the lock
            
            # Wait for restart input
            print("[Game Tick] Waiting for restart input (press R)...")
            while True:
                with self.state_lock:
                    if self.pending_input.get('restart', False):
                        print("[Game Tick] Restart requested.")
                        self.reset_game()
                        break
                time.sleep(0.1)

            print("[Game Tick] Game restarting.\n")
    
    def _handle_death(self, reason: str):
        self.player.lives -= 1
        print(f"Death: {reason}. Lives remaining: {self.player.lives}")
        
        if self.player.lives > 0:
            self.respawning = True
            self.respawn_timer = 2.0
            
            self.player.y = 520
            self.player.x = 400
            self.player.fuel = 100.0
            self.player.invincible_timer = 0.1
            
            self.bullet = None
            
            # Clear all enemies
            self.helicopters = [Helicopter(x=random.randint(250, 500), y=-random.randint(300, 600))]
            self.tankers = [Tanker(x=random.randint(250, 500), y=-random.randint(300, 600))]
            self.jets = []
            
            for depot in self.fuel_depots:
                depot.y = -random.randint(300, 600)
                depot.x = random.randint(280, 520)
                
            for bridge in self.bridges:
                if not bridge.destroyed:
                    bridge.y = -random.randint(500, 1000)
            print(f"Respawning Player")   
    
    def replicate_state(self):
        print("[Replication] Started")
        
        while True: 
            with self.state_lock:
                # Get River Walls
                river_position = self.river_y_offset
                segment_index = int(river_position / 100) % len(self.river_segments)
                current_segment = self.river_segments[segment_index]
                left_wall, right_wall = current_segment.get_walls_at_y(self.player.y)
                
                state = {
                    'respawning': self.respawning,
                    'player': {
                        'x': self.player.x,
                        'y': self.player.y,
                        'fuel': self.player.fuel,
                        'lives': self.player.lives,
                        'score': self.player.score,
                    },
                    'bullet': {'x': self.bullet.x, 'y': self.bullet.y} if self.bullet else None,
                    'helicopters': [{'x': h.x, 'y': h.y} for h in self.helicopters],
                    'tankers': [{'x': t.x, 'y': t.y} for t in self.tankers],
                    'jets': [{'x': j.x, 'y': j.y} for j in self.jets],
                    'fuel_depots': [{'x': d.x, 'y': d.y} for d in self.fuel_depots],
                    'bridges': [{'x': b.x, 'y': b.y, 'destroyed': b.destroyed, 'id': b.bridge_id} 
                            for b in self.bridges if b.y > -50 and b.y < 650],
                    'river_walls': {'left': left_wall, 'right': right_wall},
                    'game_over': self.game_over,
                    'scroll_speed': self.river_scroll_speed,
                    'timestamp': time.time()
                }
                
                with open(GAME_STATE_PATH, 'w') as f:
                    json.dump(state, f)
            
            time.sleep(0.033)
    
    def handle_client_rpc(self):
        """Read client inputs"""
        print("[Client RPC] Started")
        
        while True:
            try:
                with open(PLAYER_INPUT_PATH, 'r') as f:
                    self.pending_input = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            
            time.sleep(0.016)
    
    def reset_game(self):
        print("[Game] Resetting game state...")
        
        # Reset player
        self.player = Player()
        
        # Clear bullet
        self.bullet = None
        
        # Reset river
        self.river_y_offset = 0
        self.river_segments = []
        self._generate_initial_river()
        
        # Reset enemies (back to single enemies)
        self.helicopters = [Helicopter(x=random.randint(200, 600), y=-100)]
        self.tankers = [Tanker(x=random.randint(200, 600), y=-200)]
        #self.jets = [Jet(x=-50, y=random.randint(100, 300), vx=3, direction=1)]
        self.jets = []
        
        # Reset fuel depots
        self.fuel_depots = [
            FuelDepot(x=400, y=-400),
            FuelDepot(x=350, y=-800),
        ]
        
        # Reset bridges
        self.bridges = []
        self.bridge_counter = 0
        self.last_checkpoint_bridge_id = -1
        self._spawn_bridge()
        
        # Reset game flags
        self.game_over = False
        self.respawning = False
        self.respawn_timer = 0
        self.pending_input = {'dx': 0, 'shoot': False}
        
        print("[Game] Reset complete.")
    
    def start(self):
        print("=== River Raid Server Starting ===")
        
        threads = [
            threading.Thread(target=self.thread_H_helicopter, daemon=True, name="Thread_H"),
            threading.Thread(target=self.thread_J_jet, daemon=True, name="Thread_J"),
            threading.Thread(target=self.thread_B_tanker, daemon=True, name="Thread_B"),
            threading.Thread(target=self.game_tick, daemon=True, name="GameTick"),
            threading.Thread(target=self.replicate_state, daemon=True, name="Replication"),
            threading.Thread(target=self.handle_client_rpc, daemon=True, name="ClientRPC"),
        ]
        
        for t in threads:
            t.start()
            print(f"Started {t.name}")
        
        print("\nServer running... Press Ctrl+C to stop\n")
        
        try:
            while True:
                time.sleep(2)
                if not self.game_over:
                    with self.state_lock:
                     print(f"Lives: {self.player.lives} | Score: {self.player.score} | Fuel: {self.player.fuel:.1f} | Bridge: {self.last_checkpoint_bridge_id + 1}")
        except KeyboardInterrupt:
            print("\n\nServer shutting down...")

if __name__ == '__main__':
    server = GameServer()
    server.start()