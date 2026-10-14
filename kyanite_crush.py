#!/usr/bin/env python3
"""Kyanite Crush — neon asteroids arcade for ElbowOS. Python 3 + pygame.
Ship in center rotates and fires. Shatter cyan/magenta/gold shards.
A/D or Left/Right rotate, Space fire. R restart.
"""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/workspace/artifacts/KYANITE_CRUSH_ElbowOS.mp4")
TITLE, HANDLE = "KYANITE CRUSH", "x.com/ElbowOS"

# Palette: deep indigo + neon cyan / magenta / gold
BG = (8, 4, 28)
INK = (16, 8, 48)
CYAN = (40, 230, 255)
MAG = (255, 60, 200)
GOLD = (255, 200, 70)
WHITE = (245, 250, 255)
LIME = (120, 255, 140)
ROSE = (255, 80, 120)
NAVY = (6, 12, 36)

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.display.init()
            self.screen = pygame.display.set_mode((W, H), pygame.HIDDEN)
        pygame.display.set_caption(TITLE)
        self.font_big = pygame.font.SysFont("monospace", 72, bold=True)
        self.font_med = pygame.font.SysFont("monospace", 48, bold=True)
        self.font_sm = pygame.font.SysFont("monospace", 32, bold=True)
        self.reset()

    def reset(self):
        self.ship_x, self.ship_y = W // 2, H // 2 + 40
        self.angle = -math.pi / 2
        self.vx = self.vy = 0.0
        self.bullets = []
        self.shards = []
        self.score = 0
        self.lives = 3
        self.spawn_timer = 0
        self.invuln = 0
        self.dead = False
        self.frame = 0
        for _ in range(4):
            self.spawn_shard()

    def spawn_shard(self):
        side = random.randint(0, 3)
        if side == 0:  # top
            x, y = random.randint(80, W-80), -40
        elif side == 1:  # bottom
            x, y = random.randint(80, W-80), H + 40
        elif side == 2:  # left
            x, y = -40, random.randint(200, H-200)
        else:
            x, y = W + 40, random.randint(200, H-200)
        ang = math.atan2(self.ship_y - y, self.ship_x - x) + random.uniform(-0.4, 0.4)
        spd = random.uniform(2.2, 4.8)
        size = random.choice([28, 36, 44, 52])
        col = random.choice([CYAN, MAG, GOLD, LIME])
        self.shards.append({
            "x": x, "y": y, "vx": math.cos(ang)*spd, "vy": math.sin(ang)*spd,
            "size": size, "col": col, "rot": random.uniform(0, 6.28),
            "spin": random.uniform(-0.08, 0.08), "pts": size // 4
        })

    def update(self, keys, auto=False):
        if self.dead:
            return
        self.frame += 1
        # Rotation
        if auto:
            # Aim at nearest shard
            nearest = None
            nd = 1e9
            for s in self.shards:
                d = math.hypot(s["x"] - self.ship_x, s["y"] - self.ship_y)
                if d < nd:
                    nd, nearest = d, s
            if nearest:
                target = math.atan2(nearest["y"] - self.ship_y, nearest["x"] - self.ship_x)
                diff = (target - self.angle + math.pi) % (2*math.pi) - math.pi
                self.angle += max(-0.12, min(0.12, diff * 0.35))
            if self.frame % 8 == 0 and nearest and nd < 700:
                self.fire()
        else:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.angle -= 0.09
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.angle += 0.09
            if keys[pygame.K_SPACE] and self.frame % 6 == 0:
                self.fire()
        # Ship thrust (light)
        if not auto and (keys[pygame.K_UP] or keys[pygame.K_w]):
            self.vx += math.cos(self.angle) * 0.18
            self.vy += math.sin(self.angle) * 0.18
        self.vx *= 0.985
        self.vy *= 0.985
        self.ship_x += self.vx
        self.ship_y += self.vy
        # Wrap
        self.ship_x %= W
        self.ship_y %= H
        if self.invuln > 0:
            self.invuln -= 1
        # Bullets
        for b in self.bullets[:]:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            b["life"] -= 1
            if b["life"] <= 0 or not (0 < b["x"] < W and 0 < b["y"] < H):
                self.bullets.remove(b)
        # Shards
        self.spawn_timer += 1
        if self.spawn_timer > 28 and len(self.shards) < 9:
            self.spawn_shard()
            self.spawn_timer = 0
        for s in self.shards[:]:
            s["x"] += s["vx"]
            s["y"] += s["vy"]
            s["rot"] += s["spin"]
            # Wrap
            s["x"] %= W
            s["y"] %= H
            # Bullet hits
            for b in self.bullets[:]:
                if math.hypot(b["x"] - s["x"], b["y"] - s["y"]) < s["size"] * 0.7:
                    self.score += s["pts"]
                    self.bullets.remove(b)
                    self.shards.remove(s)
                    if s["size"] > 30:
                        # Split
                        for _ in range(2):
                            ang = random.uniform(0, 6.28)
                            ns = s["size"] * 0.55
                            self.shards.append({
                                "x": s["x"], "y": s["y"],
                                "vx": math.cos(ang)*random.uniform(2, 4),
                                "vy": math.sin(ang)*random.uniform(2, 4),
                                "size": ns, "col": s["col"], "rot": s["rot"],
                                "spin": random.uniform(-0.1, 0.1), "pts": int(ns)//5
                            })
                    break
            # Ship collision
            if self.invuln <= 0 and math.hypot(s["x"] - self.ship_x, s["y"] - self.ship_y) < s["size"] * 0.65 + 18:
                self.lives -= 1
                self.invuln = 90
                if self.lives <= 0:
                    self.dead = True
                # Push ship
                self.vx = -s["vx"] * 1.5
                self.vy = -s["vy"] * 1.5

    def fire(self):
        spd = 14
        self.bullets.append({
            "x": self.ship_x + math.cos(self.angle)*28,
            "y": self.ship_y + math.sin(self.angle)*28,
            "vx": math.cos(self.angle)*spd + self.vx*0.3,
            "vy": math.sin(self.angle)*spd + self.vy*0.3,
            "life": 55
        })

    def draw(self):
        self.screen.fill(BG)
        # Subtle grid
        for i in range(0, W, 90):
            pygame.draw.line(self.screen, INK, (i, 0), (i, H), 1)
        for j in range(0, H, 90):
            pygame.draw.line(self.screen, INK, (0, j), (W, j), 1)
        # Shards as rotating polygons
        for s in self.shards:
            pts = []
            n = 6 if s["size"] > 40 else 5
            for k in range(n):
                a = s["rot"] + k * (2*math.pi / n)
                pts.append((s["x"] + math.cos(a)*s["size"], s["y"] + math.sin(a)*s["size"]*0.85))
            pygame.draw.polygon(self.screen, s["col"], pts, 3)
            # Inner glow
            pygame.draw.circle(self.screen, s["col"], (int(s["x"]), int(s["y"])), int(s["size"]*0.3), 1)
        # Bullets
        for b in self.bullets:
            pygame.draw.circle(self.screen, GOLD, (int(b["x"]), int(b["y"])), 5)
            pygame.draw.circle(self.screen, WHITE, (int(b["x"]), int(b["y"])), 2)
        # Ship (triangle)
        if self.invuln % 6 < 4 or self.invuln == 0:
            tip = (self.ship_x + math.cos(self.angle)*26, self.ship_y + math.sin(self.angle)*26)
            left = (self.ship_x + math.cos(self.angle + 2.4)*18, self.ship_y + math.sin(self.angle + 2.4)*18)
            right = (self.ship_x + math.cos(self.angle - 2.4)*18, self.ship_y + math.sin(self.angle - 2.4)*18)
            pygame.draw.polygon(self.screen, CYAN, [tip, left, right], 3)
            pygame.draw.circle(self.screen, MAG, (int(self.ship_x), int(self.ship_y)), 6)
        # HUD
        title_surf = self.font_big.render(TITLE, True, CYAN)
        self.screen.blit(title_surf, (W//2 - title_surf.get_width()//2, 60))
        score_s = self.font_med.render(f"SCORE {self.score}", True, GOLD)
        self.screen.blit(score_s, (40, 160))
        lives_s = self.font_med.render(f"LIVES {self.lives}", True, MAG)
        self.screen.blit(lives_s, (W - lives_s.get_width() - 40, 160))
        handle = self.font_sm.render(HANDLE, True, WHITE)
        self.screen.blit(handle, (W//2 - handle.get_width()//2, H - 80))
        if self.dead:
            over = self.font_big.render("CRUSHED", True, ROSE)
            self.screen.blit(over, (W//2 - over.get_width()//2, H//2 - 40))
        pygame.display.flip()

    def play_interactive(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
                    self.reset()
            keys = pygame.key.get_pressed()
            self.update(keys, auto=False)
            self.draw()
            clock.tick(FPS)
        pygame.quit()

    def record(self):
        self.reset()
        frames = FPS * SECS
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
            "-i", "-", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-movflags", "+faststart", OUT
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        clock = pygame.time.Clock()
        for i in range(frames):
            self.update({}, auto=True)
            self.draw()
            raw = pygame.image.tostring(self.screen, "RGB")
            try:
                proc.stdin.write(raw)
            except BrokenPipeError:
                break
            clock.tick(FPS)
        proc.stdin.close()
        proc.wait()
        err = proc.stderr.read().decode() if proc.stderr else ""
        if proc.returncode != 0:
            print("FFMPEG ERROR:", err[-800:], file=sys.stderr)
            sys.exit(1)
        print(f"Recorded {OUT}")
        pygame.quit()

if __name__ == "__main__":
    g = Game()
    if RECORD:
        g.record()
    else:
        g.play_interactive()
