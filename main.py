from typing import Any, Set
import pygame as pg
from pygame.locals import *
from alloc import Alloc, makeJobQueue, Block, Job
from collections import defaultdict

pg.init()
# SCREEN_HEIGHT = pg.display.Info().current_h
# SCREEN_WIDTH = pg.display.Info().current_w
# BOUND_HEIGHT = SCREEN_HEIGHT
# BOUND_WIDTH = SCREEN_WIDTH - 400

SCREEN_HEIGHT = 600
SCREEN_WIDTH = 800
BOUND_HEIGHT = SCREEN_HEIGHT
BOUND_WIDTH = SCREEN_WIDTH - 300

TICK_UPDATE_INTERVAL_MS = 1000
CHANGE_SCHEME_DELAY_MS = 5000

schemes = ["First Fit", "Best Fit"]


class Anim:
    def reset(self) -> None:
        self.running = True
        self.simRunning = True
        self.displayTick = 0
        self.tick = 0
        self.changeSchemeTimer = pg.time.get_ticks()
        self.displayTick = 0
        self.schemeText = self.font.render(
            f"Scheme: {schemes[self.scheme]}", True, (0, 0, 0)
        )
        self.statusText = []
        self.jobs = makeJobQueue(
            (
                (5, 5760),
                (4, 4190),
                (8, 3290),
                (2, 2030),
                (2, 2550),
                (6, 6990),
                (8, 8940),
                (10, 740),
                (7, 3930),
                (6, 6890),
                (5, 6580),
                (8, 3820),
                (9, 9140),
                (10, 420),
                (10, 220),
                (7, 7540),
                (3, 3210),
                (1, 1380),
                (9, 9850),
                (3, 3610),
                (7, 7540),
                (2, 2710),
                (8, 8390),
                (5, 5950),
                (10, 760),
            )
        )
        self.alloc = Alloc(
            [
                9500,
                7000,
                4500,
                8500,
                3000,
                9000,
                1000,
                5500,
                1500,
                500,
            ]
        )
        self.ramRects: list[tuple[pg.Rect, Block]] = []
        self.waitingJobRects: dict[int, tuple[pg.Rect, Any]] = {}
        self.jobHeight = BOUND_HEIGHT // max(1, len(self.jobs))
        self.rejectedList: Set[Job] = set()
        self.drawInitialRAM()
        self.relayoutWaitingJobs()

    def __init__(self) -> None:
        self.screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pg.time.Clock()
        self.tickTimer = pg.time.get_ticks()
        self.bg = pg.Rect(
            BOUND_WIDTH,
            SCREEN_HEIGHT - BOUND_HEIGHT,
            SCREEN_WIDTH - BOUND_WIDTH,
            SCREEN_HEIGHT,
        )
        self.runs = 0
        self.schemeStats = defaultdict(lambda: defaultdict(int))
        self.scheme = 0
        self.font = pg.font.SysFont("Arial", 18)
        self.smallFont = pg.font.SysFont("Arial", 12)
        self.vel = pg.math.Vector2(1, 1)
        self.textX = BOUND_WIDTH + 10
        self.textY = SCREEN_HEIGHT - BOUND_HEIGHT + 50

        self.statuStextX = BOUND_WIDTH + 10
        self.statuStextY = SCREEN_HEIGHT - BOUND_HEIGHT + 100

        self.tick = 0
        self.text = self.font.render(
            f"Tick: {self.tick} | Allocated: 0 | Jobs: 0", True, (0, 0, 0)
        )

        self.reset()

    def handleEvents(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    self.simRunning = not self.simRunning

    def drawInitialRAM(self):
        self.ramRects = []
        y = SCREEN_HEIGHT - BOUND_HEIGHT  # start at top of RAM region
        height = BOUND_HEIGHT // len(self.alloc.ram)
        for block_id, block in sorted(
            self.alloc.ram.items(), key=lambda kv: int(kv[0])
        ):
            rect = pg.Rect((BOUND_WIDTH // 2) + 20, y, (BOUND_WIDTH // 2) - 30, height)
            self.ramRects.append((rect, block))
            y += height  # move downward

    def relayoutWaitingJobs(self):
        """Recompute positions for waiting jobs."""
        self.waitingJobRects = {}
        y = SCREEN_HEIGHT - BOUND_HEIGHT + 10
        for job in [*self.jobs, *self.rejectedList]:
            rect = pg.Rect(10, y, (BOUND_WIDTH // 2) - 20, self.jobHeight)
            self.waitingJobRects[job.id] = (rect, job)
            y += self.jobHeight

    def update(self):
        if self.simRunning:
            t0 = pg.time.get_ticks()

            if t0 - self.tickTimer >= TICK_UPDATE_INTERVAL_MS:
                self.tick += 1
                self.tickTimer = t0

            if len(self.jobs) != 0 and t0 - self.tickTimer < 50:
                job = self.jobs.popleft()
                if self.scheme == 1:
                    alloced = self.alloc.bestFit(self.tick, job)
                else:
                    alloced = self.alloc.firstFit(self.tick, job)

                if not alloced:
                    if self.alloc.canAllocate(job):
                        self.jobs.appendleft(job)
                    else:
                        self.rejectedList.add(job)

            self.alloc.deallocate(self.tick)

            self.schemeText = self.font.render(
                f"Scheme: {schemes[self.scheme]}", True, (0, 0, 0)
            )
            self.text = self.font.render(
                f"Tick: {self.tick} | Allocated: {len(self.alloc.busyList)} | Jobs: {len(self.jobs)}",
                True,
                (0, 0, 0),
            )
            self.statusText = []
            usageStats = self.alloc.calcStats()
            self.statusText += [self.font.render("", True, (0, 0, 0))]
            for stat, val in usageStats.items():
                self.statusText += [
                    self.font.render(f"{stat} -> {val}", True, (0, 0, 0))
                ]
            self.statusText += [
                self.font.render(
                    f"Runs: {self.runs}",
                    True,
                    (0, 0, 0),
                )
            ]

            for scheme, stats in self.schemeStats.items():
                self.statusText += [
                    self.font.render(
                        f"{scheme} ->",
                        True,
                        (0, 0, 0),
                    )
                ]
                for stat, val in stats.items():
                    if not stat.startswith("ticks taken run"):
                        self.statusText += [
                            self.font.render(
                                f"    {stat}: {val:.2f}",
                                True,
                                (0, 0, 0),
                            )
                        ]

            if len(self.jobs) == 0 and len(self.alloc.busyList) == 0 and self.tick > 0:
                stats = self.schemeStats[schemes[self.scheme]]
                stats["ticks taken run " + str(self.runs + 1)] = self.tick
                totalTicks = sum(
                    v for k, v in stats.items() if k.startswith("ticks taken run")
                )
                stats["average ticks taken"] = totalTicks / (self.runs + 1)
                if t0 - self.changeSchemeTimer >= CHANGE_SCHEME_DELAY_MS:
                    if self.scheme == 1:
                        self.runs += 1

                    self.changeSchemeTimer = pg.time.get_ticks()
                    self.scheme = not self.scheme
                    self.reset()
                    self.simRunning = True

            if len(self.waitingJobRects) != len(self.jobs):
                self.relayoutWaitingJobs()

    def render(self):
        self.screen.fill((0, 0, 0))

        for i, (rect, block) in enumerate(self.ramRects):
            color = (0, 255, 0) if block.busy else (255, 0, 0)

            # Draw block first so label is visible on top
            pg.draw.rect(self.screen, color, rect)
            pg.draw.rect(self.screen, (0, 0, 0), rect, 2)

            # Prepare label (show index and size)
            labelText = (
                f"#{i + 1} {block.size}K{'' if not block.busy else f' | J{block.jid}'}"
            )
            label = self.font.render(labelText, True, (0, 0, 0))
            lw, lh = label.get_size()
            padding = 4

            # If the block is tall/wide enough, center the label inside the block,
            # otherwise place it to the right to avoid clipping.
            if rect.height >= lh + 2 * padding and rect.width >= lw + 2 * padding:
                lx = rect.x + (rect.width - lw) / 2
                ly = rect.y + (rect.height - lh) / 2
            else:
                lx = rect.right + 6
                ly = rect.y + max(0, (rect.height - lh) / 2)

            self.screen.blit(label, (int(lx), int(ly)))

        for rect, job in self.waitingJobRects.values():
            color = (200, 200, 0) if job not in self.rejectedList else (200, 0, 0)
            pg.draw.rect(self.screen, color, rect)
            pg.draw.rect(self.screen, (0, 0, 0), rect, 2)

            labelText = f"J{job.id} {job.size}K"
            label = self.smallFont.render(labelText, True, (0, 0, 0))
            lw, lh = label.get_size()
            padding = 4

            if rect.height >= lh + 2 * padding and rect.width >= lw + 2 * padding:
                lx = rect.x + (rect.width - lw) / 2
                ly = rect.y + (rect.height - lh) / 2
            else:
                lx = rect.right + 6
                ly = rect.y + max(0, (rect.height - lh) / 2)

            self.screen.blit(label, (int(lx), int(ly)))

        pg.draw.rect(self.screen, (255, 255, 255), self.bg)
        self.screen.blit(self.schemeText, (self.textX, self.textY - 30))
        self.screen.blit(self.text, (self.textX, self.textY))
        for i, line in enumerate(self.statusText):
            self.screen.blit(line, (self.statuStextX, self.statuStextY + i * 20))
        # self.statusText = []
        pg.display.flip()
        self.clock.tick(60)


if __name__ == "__main__":
    anim = Anim()
    while anim.running:
        # Handle events
        anim.handleEvents()

        # Update
        anim.update()

        # Render
        anim.render()

    pg.quit()
