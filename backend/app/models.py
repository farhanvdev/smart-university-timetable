from sqlalchemy import Column, Integer, String, ForeignKey
from .database import Base

class Teacher(Base):
    __tablename__="teachers"
    id=Column(Integer,primary_key=True)
    name=Column(String,nullable=False)
    department=Column(String,default="Information Technology")
    max_per_day=Column(Integer,default=3)

class Subject(Base):
    __tablename__="subjects"
    id=Column(Integer,primary_key=True)
    code=Column(String,unique=True)
    name=Column(String)
    lectures_per_week=Column(Integer,default=3)
    required_room_type=Column(String,default="classroom")

class Classroom(Base):
    __tablename__="classrooms"
    id=Column(Integer,primary_key=True)
    name=Column(String,unique=True)
    capacity=Column(Integer,default=60)
    room_type=Column(String,default="classroom")

class Batch(Base):
    __tablename__="batches"
    id=Column(Integer,primary_key=True)
    name=Column(String,unique=True)
    semester=Column(Integer,default=5)
    strength=Column(Integer,default=50)

class TeacherSubject(Base):
    __tablename__="teacher_subjects"
    id=Column(Integer,primary_key=True)
    teacher_id=Column(Integer,ForeignKey("teachers.id"))
    subject_id=Column(Integer,ForeignKey("subjects.id"))

class TeacherAvailability(Base):
    __tablename__="teacher_availability"
    id=Column(Integer,primary_key=True)
    teacher_id=Column(Integer,ForeignKey("teachers.id"))
    day=Column(String)
    slot=Column(Integer)

class TimetableRun(Base):
    __tablename__="timetable_runs"
    id=Column(Integer,primary_key=True)
    algorithm=Column(String)
    cost=Column(Integer)
    created_at=Column(String)

class ScheduledClass(Base):
    __tablename__="scheduled_classes"
    id=Column(Integer,primary_key=True)
    run_id=Column(Integer,ForeignKey("timetable_runs.id"))
    subject_id=Column(Integer)
    teacher_id=Column(Integer)
    batch_id=Column(Integer)
    room_id=Column(Integer)
    day=Column(String)
    slot=Column(Integer)
