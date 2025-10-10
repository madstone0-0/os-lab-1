from dataclasses import dataclass
from collections import defaultdict, deque
from typing import Deque
from statistics import mean, median


@dataclass
class Job:
    id: int
    time: int
    size: int

    def __hash__(self) -> int:
        return self.id


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


class Alloc:
    def __init__(self, sizes: list[int]) -> None:
        self.freeList: set[int] = set()
        self.busyList: set[int] = set()
        self.jobMap: dict[int, Job] = dict()
        self.ram: dict[int, Block] = dict()
        self.blockUsage: dict[int, int] = defaultdict(int)
        self.usageStats: dict[str, str | list[str]] = dict()
        # Storage utilization tracking
        self.totalMemoryUsed: int = (
            0  # Sum of block sizes that were allocated at least once
        )
        self.usedBlocks: set[int] = set()  # Track which blocks were used at least once
        # Internal fragmentation tracking
        self.totalFragmentation: int = 0  # Running sum of wasted space
        self.totalJobMemory: int = 0  # Sum of all job sizes allocated
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

                # Track memory utilization (first time this block is used)
                if idx not in self.usedBlocks:
                    self.totalMemoryUsed += block.size
                    self.usedBlocks.add(idx)

                # Track internal fragmentation
                fragmentation = block.size - job.size
                self.totalFragmentation += fragmentation
                self.totalJobMemory += job.size

                return True
        return False

    def bestFit(self, tick: int, job: Job) -> bool:
        sortedBlocks = sorted(self.freeList, key=lambda idx: self.ram[idx].size)
        oldFreeList = self.freeList
        self.freeList = sortedBlocks
        res = self.firstFit(tick, job)
        self.freeList = oldFreeList
        return res

    def canAllocate(self, job: Job) -> bool:
        for block in [*self.freeList, *self.busyList]:
            if self.ram[block].size >= job.size:
                return True
        return False

    def deallocate(self, tick: int) -> None:
        self.totalTicks = tick
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

    def calcStorageUtilization(self) -> dict[str, str | list[str]]:
        """Calculate storage utilization metrics using adaptive thresholds based on actual usage patterns."""
        totalBlocks = len(self.ram)

        # Get usage counts for all blocks
        neverUsedBlocks = []
        usedBlocks = []

        # Loop through ALL blocks in ram (not just ones in blockUsage dict)
        for blockId in self.ram.keys():
            usageCount = self.blockUsage[
                blockId
            ]  # defaultdict(int) returns 0 if never accessed

            if usageCount == 0:
                neverUsedBlocks.append(blockId)
            else:
                usedBlocks.append((blockId, usageCount))

        # Calculate adaptive thresholds based on actual usage patterns
        if usedBlocks:
            usageCounts = [count for _, count in usedBlocks]
            meanUsage = mean(usageCounts)
            medianUsage = median(usageCounts)

            # Define "heavily used" as above mean usage (adaptive threshold)
            heavily_used_threshold = max(1, int(meanUsage))
        else:
            meanUsage = 0
            medianUsage = 0
            heavily_used_threshold = 1

        # Categorize blocks using adaptive thresholds
        lightlyUsedBlocks = []
        heavilyUsedBlocks = []

        for blockId, usageCount in usedBlocks:
            if usageCount >= heavily_used_threshold:
                heavilyUsedBlocks.append((blockId, usageCount))
            else:
                lightlyUsedBlocks.append((blockId, usageCount))

        # Calculate percentages
        neverUsedPercentage = (
            (len(neverUsedBlocks) / totalBlocks) * 100 if totalBlocks > 0 else 0
        )
        lightlyUsedPercentage = (
            (len(lightlyUsedBlocks) / totalBlocks) * 100 if totalBlocks > 0 else 0
        )
        heavilyUsedPercentage = (
            (len(heavilyUsedBlocks) / totalBlocks) * 100 if totalBlocks > 0 else 0
        )

        # Find most used block (highest count)
        mostUsedBlock = max(usedBlocks, key=lambda x: x[1]) if usedBlocks else None

        # Find least used block (lowest count > 0)
        leastUsedBlock = min(usedBlocks, key=lambda x: x[1]) if usedBlocks else None

        # Calculate memory utilization percentage
        memoryUtilizationPercentage = (
            (self.totalMemoryUsed / self.totalMemory) * 100
            if self.totalMemory > 0
            else 0
        )

        return {
            "never_used_blocks": neverUsedBlocks,
            "lightly_used_blocks": lightlyUsedBlocks,
            "heavily_used_blocks": heavilyUsedBlocks,
            "never_used_percentage": neverUsedPercentage,
            "lightly_used_percentage": lightlyUsedPercentage,
            "heavily_used_percentage": heavilyUsedPercentage,
            "most_used_block": mostUsedBlock,
            "least_used_block": leastUsedBlock,
            "total_memory_used": self.totalMemoryUsed,
            "total_memory_available": self.totalMemory,
            "memory_utilization_percentage": memoryUtilizationPercentage,
            "heavily_used_threshold": heavily_used_threshold,
            "mean_usage": meanUsage,
            "median_usage": medianUsage,
        }

    def calcInternalFragmentation(self) -> dict[str, str | list[str]]:
        """Calculate internal fragmentation metrics."""
        # Calculate fragmentation percentage
        totalAllocatedMemory = self.totalJobMemory + self.totalFragmentation
        fragmentationPercentage = (
            (self.totalFragmentation / totalAllocatedMemory) * 100
            if totalAllocatedMemory > 0
            else 0
        )

        return {
            "total_fragmentation": self.totalFragmentation,
            "total_job_memory": self.totalJobMemory,
            "total_allocated_memory": totalAllocatedMemory,
            "fragmentation_percentage": fragmentationPercentage,
        }

    def calcStats(self) -> dict[str, str | list[str]]:
        """
        Calculate and return a comprehensive set of statistics about memory usage,
        """
        # Calculate least used block
        sortedUsage = sorted(self.blockUsage.items(), key=lambda tup: tup[1])
        if len(sortedUsage) != 0:
            self.usageStats["Least Used Block"] = sortedUsage[0][0]

        # Calculate throughput
        totalJobs = len(self.jobMap)
        throughput = totalJobs / self.totalTicks if self.totalTicks > 0 else 0
        self.usageStats["Throughput (jobs/tick)"] = throughput

        # Add storage utilization stats with meaningful thresholds
        storageStats = self.calcStorageUtilization()

        # Basic utilization metrics
        self.usageStats["% Never Used"] = (
            f"{storageStats['never_used_percentage']:.1f}%"
        )
        self.usageStats["% Lightly Used"] = (
            f"{storageStats['lightly_used_percentage']:.1f}%"
        )
        self.usageStats["% Heavily Used"] = (
            f"{storageStats['heavily_used_percentage']:.1f}%"
        )
        self.usageStats["Memory Used"] = (
            f"{storageStats['total_memory_used']}K/{storageStats['total_memory_available']}K"
        )
        self.usageStats["Memory Util %"] = (
            f"{storageStats['memory_utilization_percentage']:.1f}%"
        )
        self.usageStats["Heavy Threshold"] = (
            f"≥{storageStats['heavily_used_threshold']} allocs (mean: {storageStats['mean_usage']:.1f})"
        )

        # Detailed block information
        if storageStats["never_used_blocks"]:
            self.usageStats["Never Used Blocks"] = [
                f"Block {bid}" for bid in storageStats["never_used_blocks"]
            ]

        if storageStats["lightly_used_blocks"]:
            self.usageStats["Lightly Used Blocks"] = [
                f"Block {bid}({count}x)"
                for bid, count in storageStats["lightly_used_blocks"]
            ]

        if storageStats["heavily_used_blocks"]:
            self.usageStats["Heavily Used Blocks"] = [
                f"Block {bid}({count}x)"
                for bid, count in storageStats["heavily_used_blocks"]
            ]

        # Most/least used for context
        if storageStats["most_used_block"]:
            blockId, count = storageStats["most_used_block"]
            self.usageStats["Most Used Block"] = f"Block {blockId} ({count}x)"

        if storageStats["least_used_block"]:
            blockId, count = storageStats["least_used_block"]
            self.usageStats["Least Used Block"] = f"Block {blockId} ({count}x)"

        # Add internal fragmentation stats
        fragStats = self.calcInternalFragmentation()
        self.usageStats["Total Internal Fragmentation"] = (
            f"{fragStats['total_fragmentation']}K"
        )
        self.usageStats["Internal Fragmentation %"] = (
            f"{fragStats['fragmentation_percentage']:.1f}%"
        )
        self.usageStats["Total Job Memory"] = f"{fragStats['total_job_memory']}K"

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
            # Print final statistics
            print("\n" + "=" * 60)
            print("FINAL SIMULATION STATISTICS")
            print("=" * 60)
            stats = alloc.calcStats()
            for stat, value in stats.items():
                print(f"{stat}: {value}")
            print("=" * 60)
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
