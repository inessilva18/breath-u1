# uninformed_search.py
from collections import deque
from typing import List

def bfs_schedule(tasks: List[str], available_slots: int) -> List[str]:
    if not tasks or available_slots == 0:
        return []
    queue = deque(tasks)
    schedule = []
    while queue and len(schedule) < available_slots:
        task = queue.popleft()
        schedule.append(f"Slot {len(schedule)+1}: {task}")
    return schedule

def calculate_stress_slots(stress_level: float) -> int:
    if stress_level > 0.7:
        return 2
    elif stress_level > 0.4:
        return 3
    else:
        return 4
