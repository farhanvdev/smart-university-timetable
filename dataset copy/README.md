# CampusFlow demo dataset

These CSV files contain fictional, synthetically generated university scheduling data for the CampusFlow project. They are not records from a real university and were not downloaded from Kaggle, UCI, or another external source.

| File | Records | Description |
|---|---:|---|
| teachers.csv | 30 | Faculty members and scheduling limits |
| subjects.csv | 20 | Courses, weekly lecture counts, and room types |
| classrooms.csv | 15 | 11 classrooms and 4 computer labs with capacities |
| batches.csv | 10 | Student groups, semesters, and strengths |
| teacher_subjects.csv | 60 | Faculty-to-subject eligibility links |
| teacher_availability.csv | 892 | Available teacher day/period combinations |

The backend seed script (`backend/app/seed.py`) creates the same sample records automatically when it starts with a fresh SQLite database.
