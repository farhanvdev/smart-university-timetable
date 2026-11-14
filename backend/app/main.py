from fastapi import FastAPI,Depends,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from .database import Base,engine,SessionLocal,get_db
from .models import Teacher,Subject,Classroom,Batch,TimetableRun,ScheduledClass
from .seed import seed
from .algorithms.engine import solve_csp,optimize,cost
from pydantic import BaseModel,Field

app=FastAPI(title="Smart University Timetable Generator",version="1.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173"],allow_methods=["*"],allow_headers=["*"])
class GenerateInput(BaseModel):
    algorithm:str=Field("compare",pattern="^(compare|csp|sa|tabu)$")
    iterations:int=Field(1200,ge=100,le=10000)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db=SessionLocal()
    try: seed(db)
    finally: db.close()

@app.get("/")
def root(): return {"message":"API running","docs":"/docs"}

@app.get("/api/dashboard")
def dashboard(db:Session=Depends(get_db)):
    return {"teachers":db.query(Teacher).count(),"subjects":db.query(Subject).count(),
            "classrooms":db.query(Classroom).count(),"batches":db.query(Batch).count()}

@app.get("/api/teachers")
def teachers(db:Session=Depends(get_db)):
    return [{"id":x.id,"name":x.name,"department":x.department,"max_per_day":x.max_per_day} for x in db.query(Teacher).all()]
@app.get("/api/subjects")
def subjects(db:Session=Depends(get_db)):
    return [{"id":x.id,"code":x.code,"name":x.name,"lectures_per_week":x.lectures_per_week,"room_type":x.required_room_type} for x in db.query(Subject).all()]
@app.get("/api/classrooms")
def rooms(db:Session=Depends(get_db)):
    return [{"id":x.id,"name":x.name,"capacity":x.capacity,"room_type":x.room_type} for x in db.query(Classroom).all()]
@app.get("/api/batches")
def batches(db:Session=Depends(get_db)):
    return [{"id":x.id,"name":x.name,"semester":x.semester,"strength":x.strength} for x in db.query(Batch).all()]

def save(db,schedule,algorithm,score):
    run=TimetableRun(algorithm=algorithm,cost=score,created_at=datetime.now().isoformat(timespec="seconds"))
    db.add(run); db.flush()
    for x in schedule:
        db.add(ScheduledClass(run_id=run.id,subject_id=x["subject_id"],teacher_id=x["teacher_id"],
            batch_id=x["batch_id"],room_id=x["room_id"],day=x["day"],slot=x["slot"]))
    db.commit()
    return run.id

def serial(db,rid):
    rows=db.query(ScheduledClass).filter_by(run_id=rid).all()
    out=[]
    for x in rows:
        out.append({"id":x.id,"subject":db.get(Subject,x.subject_id).name,"subject_code":db.get(Subject,x.subject_id).code,
            "teacher":db.get(Teacher,x.teacher_id).name,"batch":db.get(Batch,x.batch_id).name,
            "room":db.get(Classroom,x.room_id).name,"day":x.day,"slot":x.slot})
    return out

@app.post("/api/timetable/generate")
def generate(data:GenerateInput,db:Session=Depends(get_db)):
    try: initial,teachers,batches,availability=solve_csp(db)
    except ValueError as e: raise HTTPException(422,str(e))
    initial_cost=cost(initial); results=[]
    if data.algorithm in ("compare","csp"):
        rid=save(db,initial,"CSP",initial_cost)
        results.append({"algorithm":"CSP","run_id":rid,"cost":initial_cost,"time_ms":0,"classes":serial(db,rid)})
    if data.algorithm in ("compare","sa"):
        schedule,score,ms=optimize(initial,availability,data.iterations,"sa")
        rid=save(db,schedule,"Simulated Annealing",score)
        results.append({"algorithm":"Simulated Annealing","run_id":rid,"cost":score,"time_ms":ms,"classes":serial(db,rid)})
    if data.algorithm in ("compare","tabu"):
        schedule,score,ms=optimize(initial,availability,data.iterations,"tabu")
        rid=save(db,schedule,"Tabu Search",score)
        results.append({"algorithm":"Tabu Search","run_id":rid,"cost":score,"time_ms":ms,"classes":serial(db,rid)})
    return {"initial_cost":initial_cost,"results":results,"message":"Generated schedules satisfy hard constraints."}

@app.get("/api/timetable/runs/{rid}/csv")
def csv_export(rid:int,db:Session=Depends(get_db)):
    import csv,io
    from fastapi.responses import StreamingResponse
    rows=serial(db,rid)
    if not rows: raise HTTPException(404,"Timetable not found")
    f=io.StringIO(); w=csv.DictWriter(f,fieldnames=["day","slot","batch","subject","subject_code","teacher","room"])
    w.writeheader(); w.writerows(rows); f.seek(0)
    return StreamingResponse(iter([f.getvalue()]),media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="timetable-{rid}.csv"'})
