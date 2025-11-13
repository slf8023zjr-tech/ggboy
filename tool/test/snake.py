import pygame
import sys
import random

# ==== 基本参数 ====
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 400
CELL_SIZE = 20  # 每个格子的尺寸

# 网格大小
GRID_WIDTH = WINDOW_WIDTH // CELL_SIZE
GRID_HEIGHT = WINDOW_HEIGHT // CELL_SIZE

# 颜色定义
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_GRAY = (40, 40, 40)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

# 方向
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)


def random_food_position(snake):
    """随机生成食物位置，不能和蛇身重合"""
    while True:
        x = random.randint(0, GRID_WIDTH - 1)
        y = random.randint(0, GRID_HEIGHT - 1)
        if (x, y) not in snake:
            return (x, y)


def draw_grid(screen):
    """画背景网格（可选，纯装饰）"""
    for x in range(0, WINDOW_WIDTH, CELL_SIZE):
        pygame.draw.line(screen, DARK_GRAY, (x, 0), (x, WINDOW_HEIGHT))
    for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
        pygame.draw.line(screen, DARK_GRAY, (0, y), (WINDOW_WIDTH, y))


def draw_snake(screen, snake):
    """绘制蛇"""
    for segment in snake:
        rect = pygame.Rect(segment[0] * CELL_SIZE, segment[1] * CELL_SIZE,
                           CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(screen, GREEN, rect)


def draw_food(screen, food_pos):
    """绘制食物"""
    rect = pygame.Rect(food_pos[0] * CELL_SIZE, food_pos[1] * CELL_SIZE,
                       CELL_SIZE, CELL_SIZE)
    pygame.draw.rect(screen, RED, rect)


def show_text(screen, text, size, color, center):
    """居中显示文字"""
    font = pygame.font.SysFont("consolas", size)
    surface = font.render(text, True, color)
    rect = surface.get_rect()
    rect.center = center
    screen.blit(surface, rect)


def main():
    pygame.init()
    pygame.display.set_caption("贪吃蛇 Snake Game")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    # 初始化蛇：长度3，居中
    start_x = GRID_WIDTH // 2
    start_y = GRID_HEIGHT // 2
    snake = [(start_x, start_y),
             (start_x - 1, start_y),
             (start_x - 2, start_y)]
    direction = RIGHT

    food = random_food_position(snake)
    score = 0
    game_over = False

    while True:
        # ===== 事件处理 =====
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                # 方向控制，避免直接反向（掉头咬自己）
                if event.key in (pygame.K_UP, pygame.K_w):
                    if direction != DOWN:
                        direction = UP
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    if direction != UP:
                        direction = DOWN
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if direction != RIGHT:
                        direction = LEFT
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if direction != LEFT:
                        direction = RIGHT

                # 游戏结束时，R 重开，Q 退出
                if game_over:
                    if event.key == pygame.K_r:
                        # 重置游戏
                        start_x = GRID_WIDTH // 2
                        start_y = GRID_HEIGHT // 2
                        snake = [(start_x, start_y),
                                 (start_x - 1, start_y),
                                 (start_x - 2, start_y)]
                        direction = RIGHT
                        food = random_food_position(snake)
                        score = 0
                        game_over = False
                    elif event.key == pygame.K_q:
                        pygame.quit()
                        sys.exit()

        if not game_over:
            # ===== 逻辑更新 =====
            head_x, head_y = snake[0]
            dx, dy = direction
            new_head = (head_x + dx, head_y + dy)

            # 撞墙检测
            if (new_head[0] < 0 or new_head[0] >= GRID_WIDTH or
                    new_head[1] < 0 or new_head[1] >= GRID_HEIGHT):
                game_over = True
            # 撞到自己
            elif new_head in snake:
                game_over = True
            else:
                # 正常前进：在头部插入新位置
                snake.insert(0, new_head)

                # 吃到食物
                if new_head == food:
                    score += 1
                    food = random_food_position(snake)
                    # 不删除尾巴 ⇒ 蛇变长
                else:
                    # 没吃到 ⇒ 删除尾巴，长度不变
                    snake.pop()

        # ===== 绘制 =====
        screen.fill(BLACK)
        draw_grid(screen)
        draw_snake(screen, snake)
        draw_food(screen, food)

        # 显示分数
        show_text(screen, f"Score: {score}", 24, WHITE, (80, 20))

        # 游戏结束提示
        if game_over:
            show_text(screen, "GAME OVER", 48, RED,
                      (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30))
            show_text(screen, "Press R to Restart, Q to Quit", 24, WHITE,
                      (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))

        pygame.display.flip()
        clock.tick(10)  # 控制帧率，数值越大，蛇移动越快


if __name__ == "__main__":
    main()
