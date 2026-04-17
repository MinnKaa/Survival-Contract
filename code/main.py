import pygame 
import os
from os.path import join
from random import choice, randint

from settings import *
from player import Player
from sprites import *
from pytmx.util_pygame import load_pygame
from groups import AllSprites
from hand_tracking import HandController

BASE_PATH = os.path.dirname(os.path.dirname(__file__))

class Game:
    def __init__(self):
        pygame.init()
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Survivor')
        self.clock = pygame.time.Clock()
        self.running = True
        self.boss = None
        self.current_level = 1
        self.portal_spawned = False
        self.game_win = False  # Trạng thái thắng game
        self.hand_controller = HandController()

        self.minimap_size = 180

        # Khởi tạo font chữ
        self.font = pygame.font.Font(None, 100)
        self.small_font = pygame.font.Font(None, 50)

        # Groups 
        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()
        self.item_sprites = pygame.sprite.Group() 
        self.portal_group = pygame.sprite.Group()
        self.boss_bullet_sprites = pygame.sprite.Group() 

        # Item Logic & Effects
        self.inventory = {'health': 0, 'bomb': 0, 'stun': 0}
        self.item_last_use_time = 0
        self.item_cooldown = 2000 
        self.flash_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.flash_alpha = 0
        self.flash_color = (255, 255, 255)

        # Gun Timers
        self.can_shoot = True
        self.shoot_time = 0 
        self.gun_cooldown = 200
        
        self.load_images()
        
        # Audio
        self.shoot_sound = pygame.mixer.Sound(join(BASE_PATH, 'audio', 'shoot.wav'))
        self.shoot_sound.set_volume(0.2)
        pygame.mixer.music.load(join(BASE_PATH, 'audio', 'music.wav'))
        pygame.mixer.music.play(loops = -1)

        self.setup()

    def load_images(self):
        self.bullet_surf = pygame.image.load(join(BASE_PATH, 'images', 'gun', 'bullet.png')).convert_alpha()
        self.item_surfs = {
            'health': pygame.transform.scale(pygame.image.load(join(BASE_PATH, 'images', 'items', 'health.png')), (32,32)).convert_alpha(),
            'bomb': pygame.transform.scale(pygame.image.load(join(BASE_PATH, 'images', 'items', 'bomb.png')), (32,32)).convert_alpha(),
            'stun': pygame.transform.scale(pygame.image.load(join(BASE_PATH, 'images', 'items', 'stun.png')), (32,32)).convert_alpha()
        }
        
        enemies_path = join(BASE_PATH, 'images', 'enemies')
        self.enemy_frames = {}
        
        for folder in os.listdir(enemies_path):
            f_path = join(enemies_path, folder)
            if os.path.isdir(f_path) and folder != 'boss_fire':
                size = (192, 192) if folder == 'dragon' else (128, 100)
                frames = []
                for f in sorted(os.listdir(f_path)):
                    if f.endswith('.png'):
                        img = pygame.image.load(join(f_path, f)).convert_alpha()
                        img = pygame.transform.scale(img, size)
                        frames.append(img)
                self.enemy_frames[folder] = frames

        fire_path = join(BASE_PATH, 'images', 'enemies', 'boss_fire')
        self.boss_fire_frames = []
        if os.path.exists(fire_path):
            for f in sorted(os.listdir(fire_path)):
                if f.endswith('.png'):
                    img = pygame.image.load(join(fire_path, f)).convert_alpha()
                    img = pygame.transform.scale(img, (60, 60))
                    self.boss_fire_frames.append(img)

    def draw_minimap(self):
        minimap = pygame.Surface((self.minimap_size, self.minimap_size))
        minimap.fill((30, 30, 30))
        scale_x = self.minimap_size / self.map_width
        scale_y = self.minimap_size / self.map_height

        for enemy in self.enemy_sprites:
            ex = int(enemy.rect.centerx * scale_x)
            ey = int(enemy.rect.centery * scale_y)
            color = (255, 165, 0) if getattr(enemy, 'is_boss', False) else (255, 0, 0)
            radius = 6 if getattr(enemy, 'is_boss', False) else 3
            pygame.draw.circle(minimap, color, (ex, ey), radius)

        px = int(self.player.rect.centerx * scale_x)
        py = int(self.player.rect.centery * scale_y)
        pygame.draw.circle(minimap, (0, 255, 0), (px, py), 4)

        if self.portal_spawned:
            ptx = int(self.portal.rect.centerx * scale_x)
            pty = int(self.portal.rect.centery * scale_y)
            pygame.draw.circle(minimap, (0, 255, 255), (ptx, pty), 5)

        pygame.draw.rect(minimap, (255, 255, 255), minimap.get_rect(), 2)
        self.display_surface.blit(minimap, (10, WINDOW_HEIGHT - self.minimap_size - 10))

    def draw_boss_health(self):
        if self.boss and self.boss.alive():
            # Cấu hình thanh máu
            bar_width = 400
            bar_height = 20
            x = (WINDOW_WIDTH - bar_width) // 2
            y = 30
            
            # Tính toán tỉ lệ máu (Máu tối đa của boss ở map 3 là 30)
            ratio = self.boss.health / 30
            
            # Vẽ khung nền (màu xám/đen)
            pygame.draw.rect(self.display_surface, (50, 50, 50), (x - 2, y - 2, bar_width + 4, bar_height + 4))
            # Vẽ thanh máu (màu đỏ)
            pygame.draw.rect(self.display_surface, (255, 0, 0), (x, y, bar_width * ratio, bar_height))
            
            # Vẽ tên Boss phía trên thanh máu cho ngầu
            boss_text = self.small_font.render("DRAGON BOSS", True, (255, 255, 255))
            text_rect = boss_text.get_rect(center = (WINDOW_WIDTH // 2, y - 15))
            self.display_surface.blit(boss_text, text_rect)

    def setup(self):
        # 1. Reset các group (Giữ nguyên)
        self.all_sprites = AllSprites()
        self.collision_sprites, self.enemy_sprites = pygame.sprite.Group(), pygame.sprite.Group()
        self.bullet_sprites, self.item_sprites = pygame.sprite.Group(), pygame.sprite.Group()
        self.portal_group, self.boss_bullet_sprites = pygame.sprite.Group(), pygame.sprite.Group()
        self.boss = None
        self.portal_spawned = False
        self.spawn_positions = [] 

        # --- QUẢN LÝ MAP (Giữ nguyên) ---
        if self.current_level == 1: map_name = 'world.tmx'
        elif self.current_level == 2: map_name = 'dungeon.tmx'
        else: map_name = 'boss_arena.tmx'

        try:
            tmx_map = load_pygame(join(BASE_PATH, 'data', 'maps', map_name))
        except:
            tmx_map = load_pygame(join(BASE_PATH, 'data', 'maps', 'world.tmx'))

        self.map_width, self.map_height = tmx_map.width * TILE_SIZE, tmx_map.height * TILE_SIZE

        # Load Layers
        for x, y, image in tmx_map.get_layer_by_name('Ground').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)
        for obj in tmx_map.get_layer_by_name('Objects'):
            CollisionSprite((obj.x, obj.y), obj.image, (self.all_sprites, self.collision_sprites))
        for obj in tmx_map.get_layer_by_name('Collisions'):
            CollisionSprite((obj.x, obj.y), pygame.Surface((obj.width, obj.height)), self.collision_sprites)
        
        # 2. LẤY VỊ TRÍ PLAYER TRƯỚC
        for obj in tmx_map.get_layer_by_name('Entities'):
            if obj.name == 'Player':
                self.player = Player((obj.x, obj.y), self.all_sprites, self.collision_sprites)
                self.gun = Gun(self.player, self.all_sprites)
                player_spawn_pos = pygame.Vector2(obj.x, obj.y) # Lưu lại vị trí để tí nữa né
            else:
                self.spawn_positions.append((obj.x, obj.y))

        # 3. LỌC CÁC VỊ TRÍ QUÁI (Né xa Player và nằm TRONG bản đồ)
        safe_spawn_positions = []
        padding = 120  # Khoảng cách đệm từ mép bản đồ vào trong (tránh quái spawn sát rìa)
        
        for pos in self.spawn_positions:
            # Tọa độ x và y của điểm spawn
            spawn_x, spawn_y = pos[0], pos[1]
            
            # Tính khoảng cách đến Player để không spawn ngay trên đầu người chơi
            dist_to_player = pygame.Vector2(pos).distance_to(player_spawn_pos)
            
            # KIỂM TRA RANH GIỚI: Phải nằm trong chiều rộng và chiều cao của Map
            # self.map_width và self.map_height đã được tính từ tmx_map ở phía trên
            is_inside_map = padding < spawn_x < self.map_width - padding and \
                            padding < spawn_y < self.map_height - padding
            
            if dist_to_player > 400 and is_inside_map:
                safe_spawn_positions.append(pos)
        
        # Nếu danh sách trống (do map quá nhỏ hoặc vị trí lỗi), lấy lại danh sách gốc để tránh crash
        if not safe_spawn_positions:
            safe_spawn_positions = self.spawn_positions

        # 4. QUÁI & BOSS SPAWN (Dùng safe_spawn_positions)
        if self.current_level == 1:
            target_folders, hp, num_enemies = ['bat', 'blob', 'skeleton'], 2, 8
        elif self.current_level == 2:
            target_folders, hp, num_enemies = ['fire', 'sprites'], 3, 10
        else: 
            target_folders, hp, num_enemies = ['dragon'], 30, 1 

        current_enemies = [self.enemy_frames[f] for f in target_folders if f in self.enemy_frames]
        
        for _ in range(num_enemies):
            if safe_spawn_positions:
                pos = choice(safe_spawn_positions)
                enemy = Enemy(pos, choice(current_enemies), (self.all_sprites, self.enemy_sprites), self.player, self.collision_sprites, hp)
                
                if self.current_level == 3 and enemy.is_boss:
                    self.boss = enemy
                    enemy.fire_frames = self.boss_fire_frames
                    enemy.boss_bullet_group = [self.all_sprites, self.boss_bullet_sprites]

    def check_collisions(self):
        for bullet in self.bullet_sprites:
            hits = pygame.sprite.spritecollide(bullet, self.enemy_sprites, False)
            if hits:
                for enemy in hits:
                    enemy.hit()
                    if enemy.health <= 0 and choice([True, False, False]):
                        item_type = choice(['health', 'bomb', 'stun'])
                        Item(enemy.rect.center, item_type, (self.all_sprites, self.item_sprites), self.item_surfs[item_type])
                bullet.kill()

        # Giảm sát thương đạn boss xuống còn 8
        if pygame.sprite.spritecollide(self.player, self.boss_bullet_sprites, True):
            self.player.health -= 8 
            self.flash_color, self.flash_alpha = (255, 0, 0), 120 

        items_hit = pygame.sprite.spritecollide(self.player, self.item_sprites, True)
        for item in items_hit: self.inventory[item.item_type] += 1
        
        for enemy in self.enemy_sprites:
            if enemy.rect.colliderect(self.player.hitbox_rect) and enemy.death_time == 0:
                self.player.health -= 0.6
                if self.player.health <= 0: self.running = False

    def check_win_condition(self):
        if len(self.enemy_sprites) == 0 and not self.portal_spawned and self.current_level < 3:
            portal_pos = (self.map_width // 2, self.map_height // 2)
            self.portal = Portal(portal_pos, (self.all_sprites, self.portal_group))
            self.portal_spawned = True

        if self.portal_spawned:
            if self.player.rect.colliderect(self.portal.rect):
                self.current_level += 1
                self.setup()
        
        # Thắng game khi ở màn 3 và hết quái
        if self.current_level == 3 and len(self.enemy_sprites) == 0:
            self.game_win = True
                
    def run(self):
        while self.running:
            dt = self.clock.tick(30) / 1000 
            self.hand_controller.update()
            
            # --- XỬ LÝ LOGIC ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.running = False
                if self.game_win and event.type == pygame.KEYDOWN:
                    self.running = False

            if not self.game_win:
                self.player.direction = pygame.Vector2(self.hand_controller.direction)
                current_time = pygame.time.get_ticks()
                
                # Bắn súng
                if self.hand_controller.is_shooting and self.can_shoot:
                    Bullet(self.bullet_surf, self.gun.rect.center, self.gun.player_direction, (self.all_sprites, self.bullet_sprites))
                    self.can_shoot, self.shoot_time = False, current_time
                    self.shoot_sound.play()

                if not self.can_shoot and current_time - self.shoot_time >= self.gun_cooldown:
                    self.can_shoot = True

                # Chỉ xử lý Item nếu có tay TRÁI (left_fingers) và tay đó không phải tay đang điều khiển súng
                num_fingers = self.hand_controller.left_fingers
                
                if current_time - self.item_last_use_time > self.item_cooldown:
                    used = False
                    
                    # Thêm điều kiện: Phải thực sự có ngón tay được giơ lên (> 0)
                    if num_fingers > 1: 
                        if num_fingers == 2 and self.inventory['health'] > 0:
                            self.player.health = min(self.player.health + 25, 100)
                            self.inventory['health'] -= 1
                            self.flash_color, self.flash_alpha, used = (0, 255, 0), 150, True
                        
                        elif num_fingers == 3 and self.inventory['bomb'] > 0:
                            explosion_radius = 50
                            for e in self.enemy_sprites:
                                e.health -= 5 # Damage bom
                                if e.health <= 0: e.destroy()
                            self.inventory['bomb'] -= 1
                            self.flash_color, self.flash_alpha, used = (255, 255, 255), 180, True
                        
                        elif num_fingers == 4 and self.inventory['stun'] > 0:
                            for e in self.enemy_sprites: e.speed = 0
                            self.inventory['stun'] -= 1
                            self.flash_color, self.flash_alpha, used = (255, 255, 0), 150, True

                    if used: self.item_last_use_time = current_time

                self.check_collisions()
                self.all_sprites.update(dt) 
                self.check_win_condition() 

            # --- PHẦN DRAW (QUAN TRỌNG: VIẾT VÀO ĐÂY) ---
            # 1. Fill đen toàn bộ màn hình trước
            self.display_surface.fill('black')
            
            # 2. Vẽ map và các nhân vật
            self.all_sprites.draw(self.player.rect.center)
            
            # 3. Vẽ UI của Player (Máu, Túi đồ, Minimap)
            self.player.draw_health_bar(self.display_surface, self.all_sprites.offset)
            self.player.draw_inventory(self.display_surface, self.all_sprites.offset, self.inventory)
            self.draw_minimap()

            # 4. Vẽ thanh máu Boss (Phải vẽ SAU khi fill đen và SAU khi draw map)
            if self.current_level == 3:
                self.draw_boss_health()

            # 5. Các hiệu ứng chồng lên trên cùng
            if self.flash_alpha > 0:
                self.flash_alpha -= 10
                self.flash_surf.set_alpha(self.flash_alpha)
                self.flash_surf.fill(self.flash_color)
                self.display_surface.blit(self.flash_surf, (0,0))

            if self.game_win:
                overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                self.display_surface.blit(overlay, (0,0))
                text_surf = self.font.render("YOU WIN!", True, (255, 215, 0))
                text_rect = text_surf.get_rect(center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
                self.display_surface.blit(text_surf, text_rect)
                sub_surf = self.small_font.render("Press any key to exit", True, (255, 255, 255))
                sub_rect = sub_surf.get_rect(center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 70))
                self.display_surface.blit(sub_surf, sub_rect)

            pygame.display.update()

        pygame.quit()

if __name__ == '__main__':
    game = Game()
    game.run()