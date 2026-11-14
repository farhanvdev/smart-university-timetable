import random, math, time
from collections import defaultdict

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
SLOTS = [1, 2, 3, 4, 5, 6]

def cost(schedule):
    batch_days, teacher_days = defaultdict(list), defaultdict(list)
    for x in schedule:
        batch_days[(x["batch_id"], x["day"])].append(x["slot"])
        teacher_days[(x["teacher_id"], x["day"])].append(x["slot"])
    score = 0
    for values in batch_days.values():
        v = sorted(values)
        if v:
            score += max(0, v[-1] - v[0] + 1 - len(set(v))) * 10
    for values in teacher_days.values():
        v = sorted(values)
        score += sum(2 for a,b in zip(v,v[1:]) if b == a+1)
        score += max(0, len(v)-3) * 5
    return score

def valid(schedule, availability):
    teachers, rooms, batches = set(), set(), set()
    for x in schedule:
        k = (x["day"], x["slot"])
        if k not in availability.get(x["teacher_id"], set()): return False
        tk, rk, bk = (x["teacher_id"], *k), (x["room_id"], *k), (x["batch_id"], *k)
        if tk in teachers or rk in rooms or bk in batches: return False
        teachers.add(tk); rooms.add(rk); batches.add(bk)
    return True

def solve_csp(db):
    """Build a clash-free schedule with MRV ordering and backtracking.

    Each event's domain includes eligible teachers, available periods and
    suitable rooms. Dynamic legality checks enforce teacher, room and batch
    non-overlap while the search assigns events.
    """
    from ..models import Subject, Teacher, Classroom, Batch, TeacherSubject, TeacherAvailability
    teachers = db.query(Teacher).all()
    subjects = {x.id: x for x in db.query(Subject).all()}
    rooms = db.query(Classroom).all()
    batches = db.query(Batch).all()
    links = db.query(TeacherSubject).all()

    availability = defaultdict(set)
    for a in db.query(TeacherAvailability).all():
        availability[a.teacher_id].add((a.day, a.slot))
    eligible = defaultdict(list)
    for link in links:
        eligible[link.subject_id].append(link.teacher_id)

    events = []
    for batch in batches:
        for subject in subjects.values():
            teacher_options = eligible[subject.id]
            if not teacher_options:
                raise ValueError(f"No eligible teacher is assigned to {subject.name}.")
            possible_rooms = [r.id for r in rooms
                              if r.room_type == subject.required_room_type and r.capacity >= batch.strength]
            if not possible_rooms:
                raise ValueError(f"No suitable room is available for {subject.name} and {batch.name}.")
            for lecture_no in range(subject.lectures_per_week):
                domains = []
                for teacher_id in teacher_options:
                    for day in DAYS:
                        for slot in SLOTS:
                            if (day, slot) in availability.get(teacher_id, set()):
                                for room_id in possible_rooms:
                                    domains.append((teacher_id, day, slot, room_id))
                if not domains:
                    raise ValueError(f"No available teacher, room or time for {subject.name}.")
                events.append({
                    "event_id": f"{batch.id}-{subject.id}-{lecture_no}",
                    "subject_id": subject.id,
                    "batch_id": batch.id,
                    "batch_strength": batch.strength,
                    "domain": domains,
                })

    # Minimum Remaining Values: assign the most constrained events first.
    events.sort(key=lambda event: len(event["domain"]))
    assigned = []
    used_teachers, used_rooms, used_batches = set(), set(), set()
    slot_load = defaultdict(int)
    teacher_day_load = defaultdict(int)

    def backtrack(index):
        if index == len(events):
            return True
        event = events[index]
        candidates = []
        for teacher_id, day, slot, room_id in event["domain"]:
            period = (day, slot)
            if ((teacher_id, day, slot) in used_teachers or
                (room_id, day, slot) in used_rooms or
                (event["batch_id"], day, slot) in used_batches):
                continue
            # Prefer less crowded periods and distribute each teacher's load.
            score = (slot_load[period], teacher_day_load[(teacher_id, day)], random.random())
            candidates.append((score, teacher_id, day, slot, room_id))
        candidates.sort(key=lambda item: item[0])

        for _, teacher_id, day, slot, room_id in candidates:
            teacher_key = (teacher_id, day, slot)
            room_key = (room_id, day, slot)
            batch_key = (event["batch_id"], day, slot)
            period = (day, slot)
            used_teachers.add(teacher_key)
            used_rooms.add(room_key)
            used_batches.add(batch_key)
            slot_load[period] += 1
            teacher_day_load[(teacher_id, day)] += 1
            assigned.append({
                "event_id": event["event_id"],
                "subject_id": event["subject_id"],
                "teacher_id": teacher_id,
                "batch_id": event["batch_id"],
                "batch_strength": event["batch_strength"],
                "room_id": room_id,
                "day": day,
                "slot": slot,
            })

            if backtrack(index + 1):
                return True

            assigned.pop()
            used_teachers.remove(teacher_key)
            used_rooms.remove(room_key)
            used_batches.remove(batch_key)
            slot_load[period] -= 1
            teacher_day_load[(teacher_id, day)] -= 1
        return False

    if not backtrack(0):
        raise ValueError("No clash-free timetable found. Add rooms/availability or reduce weekly lectures.")

    return assigned, teachers, batches, dict(availability)

def optimize(initial, availability, iterations, mode):
    current = [dict(x) for x in initial]
    best = [dict(x) for x in initial]
    current_cost = best_cost = cost(best)
    start = time.perf_counter()
    tabu, tabu_limit = [], 30
    for step in range(iterations):
        candidate = [dict(x) for x in current]
        item = random.choice(candidate)
        choices = [(d,s) for d in DAYS for s in SLOTS if (d,s) in availability.get(item["teacher_id"],set())]
        if not choices: continue
        old = (item["day"],item["slot"])
        new = random.choice(choices)
        move = (item["event_id"], old, new)
        if mode == "tabu" and move in tabu: continue
        item["day"],item["slot"] = new
        if not valid(candidate,availability): continue
        new_cost = cost(candidate)
        accept = new_cost <= current_cost
        if mode == "sa" and not accept:
            temp = max(.05, 20 * (1-step/iterations))
            accept = random.random() < math.exp((current_cost-new_cost)/temp)
        if mode == "tabu":
            accept = new_cost < current_cost or new_cost < best_cost
        if accept:
            current,current_cost = candidate,new_cost
            if mode == "tabu":
                tabu.append((item["event_id"],new,old))
                if len(tabu)>tabu_limit: tabu.pop(0)
            if new_cost < best_cost:
                best,best_cost = [dict(x) for x in candidate],new_cost
    return best,best_cost,round((time.perf_counter()-start)*1000,2)
