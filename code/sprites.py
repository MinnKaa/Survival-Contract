import pygame
from settings import *
from math import atan2, degrees
from os.path import join
import os

BASE_PATH = os.path.dirname(os.path.dirname(__file__))

class Sprite(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft = pos)
        self.ground = True

class CollisionSprite(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft = pos)

class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos, frames, groups, player, collision_sprites, health):
        super().__init__(groups)
        self.player = player
        self.frames, self.frame_index = frames, 0 
        self.image = self.frames[self.frame_index]
        self.animation_speed = 6
        self.rect = self.image.get_rect(center = pos)
        
        # Hitbox chuẩn để xử lý va chạm mượt mà
        self.hitbox_rect = self.rect.inflate(-20, -40)
        
        self.collision_sprites = collision_sprites
        self.direction = pygame.Vector2()
        self.speed = 150 
        self.image.set_colorkey((0, 0, 0))

        # ✅ LOGIC TẦM NHÌN: 
        # detect_radius: Vào khoảng cách này quái mới đuổi (nên để 500-600)
        # attack_radius: Khoảng cách dừng lại để không đè lên Player
        self.detect_radius = 600 
        self.attack_radius = 50 
        
        self.health = health 
        self.death_time = 0
        self.death_duration = 400

        # ✅ LOGIC BOSS
        self.is_boss = (health >= 30) 
        self.last_fire_time = 0
        self.fire_cooldown = 3000 
        self.fire_frames = None 
        self.boss_bullet_group = None

    def boss_attack(self):
        current_time = pygame.time.get_ticks()
        if self.is_boss and current_time - self.last_fire_time > self.fire_cooldown:
            if self.fire_frames and self.boss_bullet_group:
                player_pos = pygame.Vector2(self.player.rect.center)
                my_pos = pygame.Vector2(self.rect.center)
                
                # Boss cũng chỉ bắn khi thấy Player trong tầm 1000px
                if (player_pos - my_pos).length() < 1000:
                    direction = (player_pos - my_pos).normalize()
                    BossFire(self.rect.center, direction, self.boss_bullet_group, self.fire_frames)
                    self.last_fire_time = current_time

    def hit(self):
        if self.death_time == 0:
            self.health -= 1
            if self.health <= 0:
                self.destroy()
    
    def animate(self, dt):
        self.frame_index += self.animation_speed * dt
        self.image = self.frames[int(self.frame_index) % len(self.frames)]

    def move(self, dt):
        player_pos = pygame.math.Vector2(self.player.rect.center)
        enemy_pos = pygame.math.Vector2(self.rect.center)
        distance = player_pos.distance_to(enemy_pos)

        # ✅ CHỈ DI CHUYỂN KHI PLAYER Ở TRONG TẦM NHÌN
        if distance < self.detect_radius:
            if distance > self.attack_radius:
                self.direction = (player_pos - enemy_pos).normalize()
            else:
                self.direction = pygame.Vector2(0, 0)
        else:
            # Ở xa quá thì đứng im tại chỗ (Vị trí từ Tiled)
            self.direction = pygame.Vector2(0, 0)

        # Xử lý di chuyển và va chạm
        if self.direction.length() > 0:
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

    def destroy(self):
        self.death_time = pygame.time.get_ticks()
        mask = pygame.mask.from_surface(self.image)
        white_surf = mask.to_surface(setcolor='white', unsetcolor=(0,0,0,0))
        self.image = white_surf
    
    def death_timer(self):
        if pygame.time.get_ticks() - self.death_time >= self.death_duration:
            self.kill()

    def update(self, dt):
        if self.death_time == 0:
            self.move(dt)
            if self.is_boss:
                self.boss_attack()
            
            # ✅ CHỈ CHẠY ANIMATION KHI CÓ DI CHUYỂN
            if self.direction.length() > 0:
                self.animate(dt)
            else:
                # Đứng yên thì dừng ở frame đầu tiên (không bị khựng nửa chừng)
                self.frame_index = 0
                self.image = self.frames[0]
        else:
            self.death_timer()
            
class Gun(pygame.sprite.Sprite):
    def __init__(self, player, groups):
        self.player = player 
        self.distance = 140
        self.player_direction = pygame.Vector2(0,1)

        super().__init__(groups)
        self.gun_surf = pygame.image.load(join(BASE_PATH, 'images', 'gun', 'gun.png')).convert_alpha()
        self.image = self.gun_surf
        self.rect = self.image.get_rect(center = self.player.rect.center + self.player_direction * self.distance)
    
    def get_direction(self):
        if self.player.direction.length() > 0:
            self.player_direction = self.player.direction.normalize()

    def rotate_gun(self):
        angle = degrees(atan2(self.player_direction.x, self.player_direction.y)) - 90
        if self.player_direction.x > 0:
            self.image = pygame.transform.rotozoom(self.gun_surf, angle, 1)
        else:
            self.image = pygame.transform.rotozoom(self.gun_surf, abs(angle), 1)
            self.image = pygame.transform.flip(self.image, False, True)

    def update(self, _):
        self.get_direction()
        self.rotate_gun()
        self.rect.center = self.player.rect.center + self.player_direction * self.distance

class Bullet(pygame.sprite.Sprite):
    def __init__(self, surf, pos, direction, groups):
        super().__init__(groups)
        self.image = surf 
        self.rect = self.image.get_rect(center = pos)
        self.pos = pygame.Vector2(self.rect.center)
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = 1000
        self.direction = direction
        self.speed = 1200 
    
    def update(self, dt):
        self.pos += self.direction * self.speed * dt
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        if pygame.time.get_ticks() - self.spawn_time >= self.lifetime:
            self.kill()

class Item(pygame.sprite.Sprite):
    def __init__(self, pos, item_type, groups, surf): 
        super().__init__(groups)
        self.item_type = item_type
        self.image = surf 
        self.rect = self.image.get_rect(center = pos)
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = 15000 

    def update(self, dt):
        if pygame.time.get_ticks() - self.spawn_time >= self.lifetime:
            self.kill()

# ✅ CLASS ĐẠN BOSS CÓ HOẠT ẢNH
class BossFire(pygame.sprite.Sprite):
    def __init__(self, pos, direction, groups, frames):
        super().__init__(groups)
        
        # Hoạt ảnh từ boss_fire
        self.frames = frames
        self.frame_index = 0
        self.animation_speed = 10 # 10 khung hình/giây
        img = self.frames[int(self.frame_index) % len(self.frames)].convert_alpha()
        # Khung hình đầu tiên
        self.image = self.frames[self.frame_index]
        # Xoay ảnh theo hướng bắn
        angle = degrees(atan2(-direction.y, direction.x))
        self.image = pygame.transform.rotate(self.image, angle)
        
        self.rect = self.image.get_rect(center = pos)
        
        # Di chuyển
        self.direction = direction
        self.speed = 350
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = 3000 # Bay tối đa 3 giây

    def animate(self, dt):
        self.frame_index += self.animation_speed * dt
        # Chuyển khung hình (0->1->2->3->4->0...)
        img = self.frames[int(self.frame_index) % len(self.frames)]
        
        # Cập nhật và xoay ảnh hoạt ảnh
        angle = degrees(atan2(-self.direction.y, self.direction.x))
        self.image = pygame.transform.rotate(img, angle)

    def update(self, dt):
        self.rect.center += self.direction * self.speed * dt
        self.animate(dt)
        if pygame.time.get_ticks() - self.spawn_time > self.lifetime:
            self.kill()

class Portal(pygame.sprite.Sprite):
    def __init__(self, pos, groups):
        super().__init__(groups)
        self.image = pygame.Surface((100, 100), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (0, 255, 255), (50, 50), 40, 5) 
        self.rect = self.image.get_rect(center = pos)