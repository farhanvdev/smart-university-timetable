"""Synthetic demo data for CampusFlow.

This is generated, fictional university data (not a real institutional dataset).
Delete backend/timetable.db before restarting the API to load this expanded seed.
"""
from .models import Teacher, Subject, Classroom, Batch, TeacherSubject, TeacherAvailability

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
SLOTS = range(1, 7)

TEACHER_NAMES = [
    "Dr. A. Sharma", "Prof. R. Mehta", "Dr. S. Kapoor", "Prof. N. Rao", "Dr. P. Verma",
    "Prof. K. Singh", "Dr. M. Iyer", "Prof. S. Gupta", "Dr. R. Nair", "Prof. V. Das",
    "Dr. N. Malhotra", "Prof. A. Khanna", "Dr. T. Joshi", "Prof. P. Menon", "Dr. L. Bansal",
    "Prof. D. Sethi", "Dr. H. Chawla", "Prof. J. Reddy", "Dr. F. Ali", "Prof. C. Bose",
    "Dr. I. Kulkarni", "Prof. G. Rao", "Dr. E. Thomas", "Prof. B. Jain", "Dr. W. Qureshi",
    "Prof. U. Shah", "Dr. Y. Mishra", "Prof. Z. Khan", "Dr. O. Fernandes", "Prof. X. Roy",
]

SUBJECTS = [
    ("IT501", "Data Structures and Algorithms", 2, "classroom"),
    ("IT502", "Database Management Systems", 2, "classroom"),
    ("IT503", "Operating Systems", 2, "classroom"),
    ("IT504", "Computer Networks", 2, "classroom"),
    ("IT505", "Software Engineering", 1, "classroom"),
    ("IT506", "Artificial Intelligence", 2, "classroom"),
    ("IT507", "Machine Learning", 1, "classroom"),
    ("IT508", "Theory of Computation", 1, "classroom"),
    ("IT509", "Computer Organization", 1, "classroom"),
    ("IT510", "Discrete Mathematics", 1, "classroom"),
    ("IT511", "Probability and Statistics", 1, "classroom"),
    ("IT512", "Web Technologies", 1, "classroom"),
    ("IT513", "Compiler Design", 1, "classroom"),
    ("IT514", "Cyber Security", 1, "classroom"),
    ("IT515", "Cloud Computing", 1, "classroom"),
    ("IT516", "Data Mining", 1, "classroom"),
    ("IT517L", "Database Systems Lab", 1, "lab"),
    ("IT518L", "Operating Systems Lab", 1, "lab"),
    ("IT519L", "Networks and Security Lab", 1, "lab"),
    ("IT520L", "AI and Machine Learning Lab", 1, "lab"),
]

BATCHES = [
    ("IT-3A", 3, 58), ("IT-3B", 3, 52), ("IT-4A", 4, 60), ("IT-4B", 4, 48),
    ("IT-5A", 5, 55), ("IT-5B", 5, 42), ("IT-6A", 6, 62), ("IT-6B", 6, 50),
    ("IT-7A", 7, 57), ("IT-7B", 7, 45),
]


def seed(db):
    # The seed is loaded only into a fresh database. Existing databases are
    # intentionally left untouched to avoid duplicating IDs and relationships.
    if db.query(Teacher).count() or db.query(Subject).count():
        return

    teachers = [
        Teacher(name=name, department="Information Technology", max_per_day=4)
        for name in TEACHER_NAMES
    ]
    subjects = [
        Subject(code=code, name=name, lectures_per_week=lectures, required_room_type=room_type)
        for code, name, lectures, room_type in SUBJECTS
    ]

    # Eleven lecture rooms and four computer laboratories.
    rooms = [
        Classroom(name=f"Block {block}-{number:03d}", capacity=capacity, room_type="classroom")
        for block, number, capacity in [
            ("A", 101, 75), ("A", 102, 70), ("A", 103, 65), ("A", 201, 75),
            ("A", 202, 70), ("B", 101, 65), ("B", 102, 70), ("B", 201, 75),
            ("B", 202, 68), ("C", 101, 70), ("C", 201, 65),
        ]
    ]
    rooms += [
        Classroom(name=f"Computer Lab {i}", capacity=70, room_type="lab")
        for i in range(1, 5)
    ]
    batches = [Batch(name=name, semester=semester, strength=strength) for name, semester, strength in BATCHES]

    db.add_all(teachers + subjects + rooms + batches)
    db.flush()

    # Give every subject three eligible faculty members. Rotating the faculty
    # by batch and lecture keeps the sample realistic while allowing the CSP
    # solver several choices when resolving clashes.
    for subject_index, subject in enumerate(subjects):
        base = (subject_index * 7) % len(teachers)
        for offset in range(3):
            teacher = teachers[(base + offset * 9) % len(teachers)]
            db.add(TeacherSubject(teacher_id=teacher.id, subject_id=subject.id))

    # Faculty availability: 30 weekly periods per teacher, with a few
    # non-identical blocked periods to make availability constraints meaningful.
    for teacher_index, teacher in enumerate(teachers):
        for day_index, day in enumerate(DAYS):
            for slot in SLOTS:
                blocked = (teacher_index % 7 == 0 and slot == 6 and day_index == 4)
                blocked = blocked or (teacher_index % 11 == 0 and slot == 1 and day_index == 0)
                if not blocked:
                    db.add(TeacherAvailability(teacher_id=teacher.id, day=day, slot=slot))

    db.commit()
