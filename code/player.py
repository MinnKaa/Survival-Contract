import pygame
import os
from os.path import join
from os import walk
from settings import *

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, collision_sprites):
        super().__init__(groups)
        self.load_images() 
        self.state, self.frame_index = 'down', 0
        self.image = self.frames[self.state][self.frame_index]
        self.rect = self.image.get_rect(center = pos)
        self.hitbox_rect = self.rect.inflate(-60, -90) 

        # Movement
        self.direction = pygame.Vector2()
        self.speed = 500
        self.collision_sprites = collision_sprites

        # Health
        self.health = 100
        self.max_health = 100

        # Hiệu ứng (Dùng để nháy màu khi dùng đồ)
        self.display_surface = pygame.display.get_surface()

    def load_images(self):
        self.frames = {'left': [], 'right': [], 'up': [], 'down': []}
        BASE_PATH = os.path.dirname(os.path.dirname(__file__))
        for state in self.frames.keys():
            for folder_path, _, file_names in walk(join(BASE_PATH, 'images', 'player', state)):
                if file_names:
                    for file_name in sorted(file_names, key= lambda name: int(name.split('.')[0])):
                        full_path = join(folder_path, file_name)
                        surf = pygame.image.load(full_path).convert_alpha()
                        self.frames[state].append(surf)

    def draw_health_bar(self, surface, offset):
        # Tọa độ trên màn hình = Tọa độ nhân vật + offset của Camera
        # Công thức này giúp thanh máu luôn "dính" vào nhân vật bất kể map trôi đi đâu
        screen_pos_x = self.rect.centerx + offset.x
        screen_pos_y = self.rect.centery + offset.y

        # Vị trí thanh máu (phía trên đầu)
        bar_x = screen_pos_x - 30
        bar_y = screen_pos_y - 60 
        
        # Vẽ thanh máu (y hệt code cũ của bạn để đảm bảo nó hiện lại)
        pygame.draw.rect(surface, 'red', (bar_x, bar_y, 60, 8))
        current_health_width = (max(0, self.health) / self.max_health) * 60
        pygame.draw.rect(surface, 'green', (bar_x, bar_y, current_health_width, 8))

    def draw_inventory(self, surface, offset, inventory):
        # Khởi tạo font cục bộ ngay tại đây để tránh lỗi chưa load font
        font = pygame.font.SysFont('Arial', 18, bold=True)
        
        # Tọa độ màn hình tương tự thanh máu
        screen_pos_x = self.rect.centerx + offset.x
        screen_pos_y = self.rect.centery + offset.y
        
        # Vị trí thanh item (dưới chân)
        item_y = screen_pos_y + 50 
        
        # Danh sách cấu hình hiển thị
        items = [('health', (255, 50, 50), 'H'), ('bomb', (150, 150, 150), 'B'), ('stun', (255, 215, 0), 'S')]

        for i, (key, color, label) in enumerate(items):
            count = inventory.get(key, 0)
            text_surf = font.render(f"{label}:{count}", True, color)
            
            # Căn giữa các chữ item cách nhau một khoảng
            text_rect = text_surf.get_rect(center = (screen_pos_x - 40 + i * 40, item_y))
            
            # Vẽ một cái nền đen nhỏ để nhìn số cho rõ
            bg_rect = text_rect.inflate(8, 4)
            pygame.draw.rect(surface, (0, 0, 0), bg_rect)
            
            surface.blit(text_surf, text_rect)

    def move(self, dt):
        if self.direction.length() > 1:
            self.direction = self.direction.normalize()

        self.hitbox_rect.x += self.direction.x * self.speed * dt
        self.collision('horizontal')
        self.hitbox_rect.y += self.direction.y * self.speed * dt
        self.collision('vertical')
        self.rect.center = self.hitbox_rect.center

    def collision(self, direction):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.hitbox_rect):
                if direction == 'horizontal':
                    if self.direction.x > 0: self.hitbox_rect.right = sprite.rect.left
                    if self.direction.x < 0: self.hitbox_rect.left = sprite.rect.right
                else:
                    if self.direction.y < 0: self.hitbox_rect.top = sprite.rect.bottom
                    if self.direction.y > 0: self.hitbox_rect.bottom = sprite.rect.top

    def animate(self, dt):
        if self.direction.x != 0:
            self.state = 'right' if self.direction.x > 0 else 'left'
        if self.direction.y != 0:
            self.state = 'down' if self.direction.y > 0 else 'up'

        self.frame_index = self.frame_index + 5 * dt if self.direction.length() > 0.1 else 0
        self.image = self.frames[self.state][int(self.frame_index) % len(self.frames[self.state])]

    def update(self, dt):
        self.move(dt)
        self.animate(dt)