from dataclasses import dataclass
from collections import defaultdict, deque
from typing import Deque


@dataclass
class Job:
    id: int
    time: int
    size: int


@dataclass
class Block:
    id: int
    size: int
    jid: int = -1
    busy: bool = False
    jobStart: int = -1

    def __str__(self) -> str:
        return f"({self.id})\t{self.size}K\t{'' if self.jid == -1 else f'[{self.jid}]'}"

    def allocate(self, tick: int, job: Job) -> None:
        self.jid = job.id
        self.busy = True
        self.jobStart = tick

    def deallocate(self) -> None:
        self.jid = -1
        self.busy = False
        self.jobStart = -1


def makeJobQueue(jobTimes: tuple) -> Deque[Job]:
    res: Deque[Job] = deque()
    for i, (time, size) in enumerate(jobTimes):
        res.append(Job(id=i + 1, time=time, size=size))
    return res


LEAST_USED_BLOCK = "Least Used Block"
MAX_INTERNAL_FRAG = "Maximum Internal Fragmentation"


class Alloc:
    def __init__(self, sizes: list[int]) -> None:
        self.freeList: set[int] = set()
        self.busyList: set[int] = set()
        self.jobMap: dict[int, Job] = dict()
        self.ram: dict[int, Block] = dict()
        self.blockUsage: dict[int, int] = defaultdict(int)
        self.usageStats: dict[str, str] = dict()
        for i, size in enumerate(sizes):
            idx = i + 1
            self.ram[idx] = Block(id=idx, size=size)
            self.freeList.add(idx)
        self.totalMemory = sum(sizes)

    def firstFit(self, tick: int, job: Job) -> bool:
        for idx in self.freeList:
            block = self.ram[idx]
            if block.size >= job.size:
                self.jobMap[job.id] = job
                block.allocate(tick, job)
                self.freeList.remove(idx)
                self.busyList.add(idx)
                self.ram[idx] = block
                self.blockUsage[idx] += 1
                return True
        return False

    def bestFit(self, tick: int, job: Job) -> bool:
        sortedBlocks = sorted(self.freeList, key=lambda idx: self.ram[idx].size)
        oldFreeList = self.freeList
        self.freeList = sortedBlocks
        res = self.firstFit(tick, job)
        self.freeList = oldFreeList
        return res

    def deallocate(self, tick: int) -> None:
        toRemove = []
        for idx in self.busyList:
            block = self.ram[idx]
            timespent = tick - block.jobStart
            if timespent >= self.jobMap[block.jid].time:
                block.deallocate()
                self.freeList.add(idx)
                toRemove.append(idx)
                self.ram[idx] = block
        for idx in toRemove:
            self.busyList.remove(idx)

    def outputState(self) -> str:
        lines = []
        for idx, block in self.ram.items():
            lines += [str(block)]
        return "\n".join(lines)

    def calcStats(self) -> dict[str, str]:
        sortedUsage = sorted(self.blockUsage.items(), key=lambda tup: tup[1])
        if len(sortedUsage) != 0:
            self.usageStats[LEAST_USED_BLOCK] = sortedUsage[0][0]
        return self.usageStats

    def printState(self) -> None:
        print(self.outputState())


if __name__ == "__main__":
    jobs = makeJobQueue(
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
            # (9, 9850),
            (3, 3610),
            (7, 7540),
            (2, 2710),
            (8, 8390),
            (5, 5950),
            (10, 760),
        )
    )
    alloc = Alloc(
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

    tick = 0
    while True:
        if len(jobs) != 0:
            job = jobs.pop()
            alloced = alloc.firstFit(tick, job)
            if not alloced:
                jobs.appendleft(job)
        alloc.deallocate(tick)

        alloc.printState()
        print(f"Wait Queue: {len(jobs)}\nTick: {tick}")
        print()
        tick += 1
        if len(alloc.busyList) == 0 and len(jobs) == 0:
            break

    # tick = 0
    # while True:
    #     if len(jobs) != 0:
    #         job = jobs.pop()
    #         alloced = alloc.bestFit(tick, job)
    #         if not alloced:
    #             jobs.append(job)
    #     alloc.deallocate(tick)
    #
    #     alloc.printState()
    #     print(f"Wait Queue: {len(jobs)}\nTick: {tick}")
    #     print()
    #     tick += 1
    #     if len(alloc.busyList) == 0 and len(jobs) == 0:
    #         break
