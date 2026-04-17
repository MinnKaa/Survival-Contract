import pygame
from settings import *

class AllSprites(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.Vector2()
    
    def draw(self, target_pos):
        # Tính toán khoảng cách từ tâm màn hình đến mục tiêu (người chơi)
        self.offset.x = -(target_pos[0] - WINDOW_WIDTH / 2)
        self.offset.y = -(target_pos[1] - WINDOW_HEIGHT / 2)

        # Phân loại layer: ground vẽ trước, object vẽ sau
        ground_sprites = [sprite for sprite in self if hasattr(sprite, 'ground')] 
        object_sprites = [sprite for sprite in self if not hasattr(sprite, 'ground')] 
        
        for layer in [ground_sprites, object_sprites]:
            # Sắp xếp theo trục Y (centery) để tạo hiệu ứng chiều sâu (Y-sorting)
            # Giúp nhân vật có thể đứng sau hoặc đứng trước cây cối/vật thể
            for sprite in sorted(layer, key = lambda sprite: sprite.rect.centery):
                # Vẽ sprite lên màn hình với vị trí đã cộng thêm offset của camera
                self.display_surface.blit(sprite.image, sprite.rect.topleft + self.offset)